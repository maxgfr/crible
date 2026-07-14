# Remediation plan — .

Target: `/Users/maxime/Downloads/crible` · 6 fix task(s), most impactful first.
Each task has a matching TDD card under `fixes/` (RED failing test → GREEN change → VERIFY).

## P1 — Major: materially degrades a scored dimension (fidelity, coverage, robustness); a workaround or secondary path exists (1)

- **FIX-001** REGRESSION from the F6 fix: audited-only periods are appended UNSORTED, so the current price, return_6m and every price-derived ratio land on an OLD period instead of the latest — the flagship deep-history universe is now silently mis-priced — An operator ingests SEC FSDS to get deep history for AAPL (the headline Phase-2 feature). AAPL is yfinance-scraped, so reconcile now appends the pre-2021 audited years at the tail; build_symbol_snapshot writes today's price and the 6-month momentum onto a ~2016 row, leaving the 2024 row with NaN price/return_6m. The screener then ranks AAPL on wrong-period price ratios and a blank momentum — the published output is silently corrupted for precisely the universe the deep-history feature targets.
  - fix: Re-sort the merged frame chronologically after the union (e.g. merged = merged.sort_index() at reconcile.py:63, safe because period labels sort chronologically), or insert extra_periods in sorted position; add a fixture asserting an audited-only period deeper than the scrape ends up BEFORE the latest and that price/return_6m still land on the latest period.
  - targets: src/crible/compute/reconcile.py, src/crible/compute/snapshot.py, src/crible/compute/canonical.py

## P2 — Minor: polish, consistency, or documentation drift; no scored dimension materially degraded (5)

- **FIX-002** ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 opportunity still open — The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep) at reconcile.py:43-513. The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
  - fix: Move each run_<source>_cycle next to its provider (or an ingest/cycles/ package), keeping the shared GLEIF/heartbeat helpers in one place.
  - targets: src/crible/ingest/enrichment.py
- **FIX-003** Mirror bulk fetch still has no max-size or total-time cap — c2 F5 opportunity still open — fetch_if_stale streams response.iter_bytes to disk with no byte ceiling (mirror.py:102) under an httpx timeout that is per-operation, not total (mirror.py:88). URLs are hardcoded/trusted (no SSRF), but a misbehaving or hostile mirror could fill the disk or keep a slow ~200MB GLEIF download alive indefinitely on the auto-heal path.
  - fix: Add a byte ceiling while streaming (abort past N bytes) and a wall-clock deadline for the whole transfer.
  - targets: src/crible/ingest/mirror.py
- **FIX-004** Audited-only symbols still carry no field-level provenance (audited_fields empty) — the c2 F3 gap is unresolved on the production path — A JP/UK listing with no yfinance data is enriched purely from EDINET/Companies House; its rows are entirely audited but the audited_fields column is blank, so a user cannot tell the figures are as-filed.
  - fix: When canonical is seeded directly from audited (audited-only path), mark all present fields as audited in audited_fields — pass audited_frames through even when scraped is empty, or populate the column in the audited-only branch as done at snapshot.py:60.
  - targets: src/crible/compute/snapshot.py
- **FIX-005** EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13, unresolved) — A JP company's Q2 report lands in the swept day; its mid-year balance instant is booked as the annual TotalAssets/Equity, distorting every balance-derived ratio for that symbol.
  - fix: Filter list_documents (or the sweep loop) to the annual securities report docTypeCode (120) and/or require the balance instant to match the annual period end; add a fixture with an interim filing asserting it is skipped.
  - targets: src/crible/providers/edinet.py
- **FIX-006** EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14, unresolved) — A group whose non-consolidated (単体) Revenue context is parsed before the consolidated (連結) one books parent-only revenue as the audited group figure.
  - fix: Capture the consolidated/non-consolidated member per context and prefer the consolidated one (or drop non-consolidated when a consolidated exists); add a fixture with both contexts asserting the consolidated value wins.
  - targets: src/crible/providers/edinet.py
