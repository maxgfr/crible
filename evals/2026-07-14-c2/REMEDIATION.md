# Remediation plan — .

Target: `/Users/maxime/Downloads/crible` · 16 fix task(s), most impactful first.
Each task has a matching TDD card under `fixes/` (RED failing test → GREEN change → VERIFY).

## P1 — Major: materially degrades a scored dimension (fidelity, coverage, robustness); a workaround or secondary path exists (2)

- **FIX-001** reconcile discards every audited period the scrape lacks — FSDS/EDGAR deep-history backfill is silently truncated to the yfinance window for scraped symbols — A self-hoster ingests SEC FSDS to get 15+ years of as-filed history for AAPL; because AAPL is yfinance-scraped, reconcile truncates the audited history back to ~4 years and the deep backfill never reaches the snapshot — the headline feature is silently inert for its target universe.
  - fix: In reconcile, union periods: append audited-only periods to merged (marking every field audited) instead of skipping them; add a fixture with an audited period outside the scraped index asserting it survives.
  - targets: src/crible/compute/reconcile.py, src/crible/providers/audited.py, src/crible/ingest/enrichment.py
- **FIX-002** Companies House _company_number parses the filing DATE, not the company number — the whole UK audited layer silently ingests zero rows on real filenames — An operator enables the UK Companies House tier and points it at a real Accounts Data Product ZIP; every filename resolves to a date, no company matches, and the sweep completes 'successfully' with zero UK companies enriched and no error.
  - fix: Take the company-number token by position/pattern (digits[0], or the token before the yyyymmdd), and handle SC/NI/OC alphanumeric prefixes; add a fixture in the real Prod<nnn>_<batch>_<number>_<date> format.
  - targets: src/crible/providers/companies_house.py

## P2 — Minor: polish, consistency, or documentation drift; no scored dimension materially degraded (14)

- **FIX-003** Split ingest/enrichment.py (617 LOC, nesting 14) into per-provider cycle modules — The F4 refactor correctly halved service.py (820->523 LOC) by extracting the audited enrichment cycles, but they all landed in ONE module: enrichment.py is now the #2 hotspot at 617 LOC with nesting depth 14, holding 9 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep). The seam (AuditedBulkProvider) exists; the cycles could each move beside their provider so a new source stops growing one file.
  - fix: Move each run_<source>_cycle next to its provider (or an ingest/cycles/ package), keeping the shared GLEIF/heartbeat helpers in one place; the per-cycle contracts are already clean.
  - targets: src/crible/ingest/enrichment.py
- **FIX-004** Mirror sidecar meta write is non-atomic — a crash mid-write forces a full unconditional re-download — fetch_if_stale writes the data file atomically (temp-then-rename, mirror.py:92-96) but the .meta.json sidecar is a plain write_text (mirror.py:89, 98-100). A crash mid-write corrupts the sidecar; _read_meta then returns {} (mirror.py:47), losing the stored ETag and forcing a full unconditional re-download of the ~200MB GLEIF file next time. Fails safe (never serves stale data) but wastes bandwidth.
  - fix: Write the meta sidecar through the same temp-then-rename path as the data file.
  - targets: src/crible/ingest/mirror.py
- **FIX-005** Audited-only symbols carry no field-level provenance (audited_fields empty) — In build_symbol_snapshot, when a symbol has no yfinance scrape, audited_frames is passed as None (snapshot.py:200) so the reconcile path that populates the audited_fields provenance column never runs — every field is audited yet audited_fields is empty (snapshot.py:101-103). Row-level provider still records the source, so this is a provenance-completeness gap, not a data error.
  - fix: When canonical is seeded directly from audited (snapshot.py:60), mark all present fields as audited in audited_fields (already done there for the empty-canonical branch — verify it reaches the output column).
  - targets: src/crible/compute/snapshot.py
- **FIX-006** EDINET sec_code rejects the new 4-char alphanumeric Tokyo codes (e.g. 130A.T) — sec_code returns None when the ticker base is not all digits (edinet.py:155), silently skipping the alphanumeric TSE codes the Tokyo exchange began issuing in 2024 (e.g. 130A.T). Those JP listings never resolve to an EDINET securities code. EDINET is opt-in (off without a key) so the blast radius is small.
  - fix: Accept a 4-char alphanumeric base and pad to the 5-char EDINET securities code.
  - targets: src/crible/providers/edinet.py
- **FIX-007** Mirror bulk fetch has no max-size or total-time cap — fetch_if_stale streams response.iter_bytes to disk with no size ceiling (mirror.py:93-95) and an httpx timeout that is per-operation, not total (mirror.py:80). URLs are hardcoded and trusted (GLEIF, Frankfurter) so there is no SSRF, but a misbehaving/hostile server could fill the disk or keep a slow download alive indefinitely — the ~200MB GLEIF fetch on the auto-heal path is the exposure.
  - fix: Add a byte ceiling while streaming (raise past N bytes) and a wall-clock deadline for the whole transfer.
  - targets: src/crible/ingest/mirror.py
- **FIX-008** Incremental compute is blind to price-dump refreshes — published prices, return_6m and value/momentum ranks go stale on the persisted-base path — The hosted nightly runs import-prices (fresh Stooq closes) then incremental compute on a persisted base.parquet; no fundamentals changed that day, so the published snapshot keeps yesterday's (or last filing's) prices and momentum until the symbol is next dirtied by a filing.
  - fix: Treat prices-latest.parquet's mtime as a global change signal (mark all symbols dirty, or recompute the price/return_6m columns in finalize), or force a periodic full rebuild.
  - targets: src/crible/compute/snapshot.py, src/crible/ingest/price_import.py
- **FIX-009** GLEIF ISIN->LEI mapping is fetched once and never refreshed — the weekly self-heal is gated on file ABSENCE, so EU audited coverage freezes — A self-hoster's first refresh downloads the GLEIF file; a year later, dozens of newly-listed EU companies still have no audited figures because the mapping was never refreshed despite the weekly timer firing.
  - fix: Call fetch_gleif unconditionally on the weekly timer (let fetch_if_stale decide), dropping the is-None gate; keep the manual command as-is.
  - targets: src/crible/ingest/service.py, src/crible/providers/gleif.py
- **FIX-010** FSDS parser ignores the coreg column — a co-registrant/guarantor value can be booked as the consolidated audited figure — A guarantor-subsidiary 10-K's co-registrant revenue appears before the consolidated row in num.txt; it is booked as the audited annual Revenue for that CIK.
  - fix: Skip rows where coreg is non-empty (consolidated registrant only); add a fixture with a co-registrant row asserting it is dropped.
  - targets: src/crible/providers/edgar_fsds.py
- **FIX-011** Bulk archives are read whole into memory (GLEIF ~1GB decompressed, FSDS num.txt hundreds of MB) — OOM risk on the self-hosted target, defeating the mirror's streaming design — A 1GB-RAM VPS runs the GLEIF auto-fetch on first refresh; loading the ISIN-LEI file peaks several GB of RSS and the process is OOM-killed, leaving the audited-EU layer idle.
  - fix: Stream both: zipfile.open(inner)+io.TextIOWrapper -> csv.reader for GLEIF, and archive.open('num.txt')+TextIOWrapper for FSDS, capping peak memory to the resulting structures.
  - targets: src/crible/providers/gleif.py, src/crible/providers/edgar_fsds.py
- **FIX-012** FX applies the single latest spot rate to every fiscal period — historical *_eur values are silently wrong — A user screens revenue_eur across years for a USD filer; the older years are converted at today's USD/EUR rate, distorting a multi-year EUR trend.
  - fix: Fetch dated ECB rates (Frankfurter supports /<date>) and convert each period at its period-end rate; or scope *_eur to the latest period only and document it.
  - targets: src/crible/providers/fx.py
- **FIX-013** EDINET sweep applies no document-type filter and books interim balance-sheet instants as annual figures — A semi-annual EDINET report for a JP filer is swept; its Sep-30 interim balance-sheet instant is stored as the annual audited TotalAssets for that year.
  - fix: Filter to annual securities-report docTypeCodes in run_edinet, and require the balance instant's month-day to match the entity's fiscal-year-end before tagging it annual.
  - targets: src/crible/ingest/enrichment.py, src/crible/providers/edinet.py
- **FIX-014** EDINET does not distinguish consolidated (連結) from non-consolidated (単体) contexts — parent-only figures can be booked for a group — A JP holding company's parent-only revenue appears first in the XBRL instance and is booked as the audited consolidated revenue, understating the group.
  - fix: Prefer the consolidated context (ConsolidatedMember / no non-consolidated dimension) explicitly; drop parent-only facts when a consolidated one exists.
  - targets: src/crible/providers/edinet.py
- **FIX-015** Incremental compute never marks a symbol dirty when its newest raw file is removed — An operator manually deletes a corrupt newest raw parquet for one symbol; incremental compute keeps serving the row built from it until an unrelated change dirties the symbol.
  - fix: Also treat a drop in a symbol's newest-stamp (or a change in its raw file set) versus a recorded baseline as dirty; or compare a per-symbol raw fingerprint rather than a max stamp.
  - targets: src/crible/compute/snapshot.py
- **FIX-016** GLEIF CSV is decoded as plain utf-8 (not utf-8-sig) — a BOM in the source file would silently zero the entire mapping — GLEIF publishes the file with a BOM; the auto-fetched mapping parses to zero relationships and every EU listing lands in 'unmatched', with only an info-level 'loaded 0' to signal it.
  - fix: Decode with utf-8-sig (or strip a leading BOM); add a BOM'd fixture asserting the mapping still loads.
  - targets: src/crible/providers/gleif.py
