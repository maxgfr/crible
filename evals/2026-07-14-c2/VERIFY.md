# Verification worklist

For each pair: read the digest, judge whether it SUPPORTS the finding, write a verdict.
Verdicts: `supported` · `partial` · `refuted` · `unsupported`.

## F6 · src/crible/compute/reconcile.py:56
**Finding:** merge_audited correctly assembles deep audited history (companyfacts primary + FSDS backfill) into the audited frames (audited.py:48-58), but for any symbol that ALSO has a yfinance scrape, build_symbol_snapshot reconciles the audited frame INTO the scraped canonical (snapshot.py:63) and reconcile only OVERRIDES periods already present: merged is seeded from scraped (reconcile.py:56) and audited-only periods are skipped, never appended (reconcile.py:65-66). align_periods (reconcile.py:20-45) only relabels an audited period onto a same-year scraped label. So every audited period older than yfinance's ~4-year window is dropped for scraped symbols — i.e. essentially all US large/mid caps. This directly contradicts the stated purpose of the Phase-2 FSDS source.
```
54: 
55: def reconcile(scraped: pd.DataFrame, audited: pd.DataFrame, symbol: str = "?") -> Reconciliation:
56:     merged = scraped.copy()
57:     audited_fields: dict[str, list[str]] = {}
58:     discrepancies: list[dict] = []
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/compute/reconcile.py:65
**Finding:** merge_audited correctly assembles deep audited history (companyfacts primary + FSDS backfill) into the audited frames (audited.py:48-58), but for any symbol that ALSO has a yfinance scrape, build_symbol_snapshot reconciles the audited frame INTO the scraped canonical (snapshot.py:63) and reconcile only OVERRIDES periods already present: merged is seeded from scraped (reconcile.py:56) and audited-only periods are skipped, never appended (reconcile.py:65-66). align_periods (reconcile.py:20-45) only relabels an audited period onto a same-year scraped label. So every audited period older than yfinance's ~4-year window is dropped for scraped symbols — i.e. essentially all US large/mid caps. This directly contradicts the stated purpose of the Phase-2 FSDS source.
```
63:             if pd.isna(audited_value):
64:                 continue
65:             if period not in merged.index:
66:                 continue
67:             scraped_value = merged.loc[period, column] if column in merged.columns else float("nan")
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/providers/audited.py:44
**Finding:** merge_audited correctly assembles deep audited history (companyfacts primary + FSDS backfill) into the audited frames (audited.py:48-58), but for any symbol that ALSO has a yfinance scrape, build_symbol_snapshot reconciles the audited frame INTO the scraped canonical (snapshot.py:63) and reconcile only OVERRIDES periods already present: merged is seeded from scraped (reconcile.py:56) and audited-only periods are skipped, never appended (reconcile.py:65-66). align_periods (reconcile.py:20-45) only relabels an audited period onto a same-year scraped label. So every audited period older than yfinance's ~4-year window is dropped for scraped symbols — i.e. essentially all US large/mid caps. This directly contradicts the stated purpose of the Phase-2 FSDS source.
```
42:     """Merge several audited frame-dicts for one listing, per statement/freq.
43: 
44:     The primary source wins on every period it reports; each fallback only
45:     backfills periods the merge does not yet have (e.g. SEC FSDS adding
46:     pre-8-year history under companyfacts). Frames are keyed by
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/ingest/enrichment.py:307
**Finding:** merge_audited correctly assembles deep audited history (companyfacts primary + FSDS backfill) into the audited frames (audited.py:48-58), but for any symbol that ALSO has a yfinance scrape, build_symbol_snapshot reconciles the audited frame INTO the scraped canonical (snapshot.py:63) and reconcile only OVERRIDES periods already present: merged is seeded from scraped (reconcile.py:56) and audited-only periods are skipped, never appended (reconcile.py:65-66). align_periods (reconcile.py:20-45) only relabels an audited period onto a same-year scraped label. So every audited period older than yfinance's ~4-year window is dropped for scraped symbols — i.e. essentially all US large/mid caps. This directly contradicts the stated purpose of the Phase-2 FSDS source.
```
305:     """SEC FSDS depth cycle: for each (year, quarter), mirror the archive and
306:     write provider='edgar-fsds' raw for resolved US issuers. companyfacts
307:     (provider='edgar') wins recent periods at reconcile; FSDS backfills the
308:     pre-8-year history companyfacts drops. Public domain — redistributable."""
309:     from crible.ingest.mirror import fetch_if_stale
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/providers/companies_house.py:197
**Finding:** The real Accounts Data Product names files Prod<nnn>_<batch>_<companynumber>_<yyyymmdd>.<ext> (e.g. Prod223_2138_08094273_20230331.html). _company_number does re.findall(r'\d{6,8}', ...) then takes digits[-1] (companies_house.py:197-198), which picks the trailing 8-digit DATE (20230331), not the company number (08094273). Verified empirically: findall -> ['08094273','20230331'], digits[-1]='20230331'. That never matches a wanted company number, so iter_accounts yields nothing and the UK layer ingests zero rows. The unit test masks it: its fixture Prod223_1234567.html has a single digit-run so digits[-1]==digits[0] (tests/test_companies_house.py:62).
```
195: def _company_number(filename: str) -> str | None:
196:     """The 8-digit company number embedded in an accounts filename, or None."""
197:     digits = re.findall(r"\d{6,8}", filename.rsplit("/", 1)[-1])
198:     return digits[-1].zfill(8) if digits else None
199: 
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/providers/companies_house.py:198
**Finding:** The real Accounts Data Product names files Prod<nnn>_<batch>_<companynumber>_<yyyymmdd>.<ext> (e.g. Prod223_2138_08094273_20230331.html). _company_number does re.findall(r'\d{6,8}', ...) then takes digits[-1] (companies_house.py:197-198), which picks the trailing 8-digit DATE (20230331), not the company number (08094273). Verified empirically: findall -> ['08094273','20230331'], digits[-1]='20230331'. That never matches a wanted company number, so iter_accounts yields nothing and the UK layer ingests zero rows. The unit test masks it: its fixture Prod223_1234567.html has a single digit-run so digits[-1]==digits[0] (tests/test_companies_house.py:62).
```
196:     """The 8-digit company number embedded in an accounts filename, or None."""
197:     digits = re.findall(r"\d{6,8}", filename.rsplit("/", 1)[-1])
198:     return digits[-1].zfill(8) if digits else None
199: 
200: 
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/providers/companies_house.py:211
**Finding:** The real Accounts Data Product names files Prod<nnn>_<batch>_<companynumber>_<yyyymmdd>.<ext> (e.g. Prod223_2138_08094273_20230331.html). _company_number does re.findall(r'\d{6,8}', ...) then takes digits[-1] (companies_house.py:197-198), which picks the trailing 8-digit DATE (20230331), not the company number (08094273). Verified empirically: findall -> ['08094273','20230331'], digits[-1]='20230331'. That never matches a wanted company number, so iter_accounts yields nothing and the UK layer ingests zero rows. The unit test masks it: its fixture Prod223_1234567.html has a single digit-run so digits[-1]==digits[0] (tests/test_companies_house.py:62).
```
209:             if not name.lower().endswith((".html", ".xhtml", ".htm")):
210:                 continue
211:             number = _company_number(name)
212:             if number is None or number not in wanted:
213:                 continue
```
**Verdict:** ______  ·  **Note:** ______

## F1 · analysis:src/crible/ingest/enrichment.py
**Finding:** The F4 refactor correctly halved service.py (820->523 LOC) by extracting the audited enrichment cycles, but they all landed in ONE module: enrichment.py is now the #2 hotspot at 617 LOC with nesting depth 14, holding 9 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep). The seam (AuditedBulkProvider) exists; the cycles could each move beside their provider so a new source stops growing one file.
```
"""Audited enrichment cycles — the layers that outrank scraped Yahoo values.

ESEF (EU, filings.xbrl.org) and EDGAR (US, SEC companyfacts) run as separate,
resumable cycles that write provider-tagged raw statements; reconciliation
prefers them over the scraped base. Extracted from service.py (F4) so the
service loop stays small and each new audited source (FSDS, Companies House,
EDINET) plugs in here beside the existing two rather than growing one file.
"""

from __future__ import annotations

import logging
```
**Verdict:** ______  ·  **Note:** ______

## F17 · src/crible/providers/gleif.py:43
**Finding:** fetch_rates pulls Frankfurter's /latest endpoint (fx.py:26) and attach_fx converts every row (all fiscal periods) with that one rate map (fx.py:94-95), so 2015 revenue and 2024 revenue are both normalized at today's EUR rate. The docstring documents the listing-vs-reporting currency approximation but not this temporal one; historical revenue_eur / total_assets_eur look precise but are wrong for cross-period comparison.
```
41:     """Parse a GLEIF relationship file (CSV or zipped CSV) into {ISIN: LEI}."""
42:     path = Path(path)
43:     raw: bytes = path.read_bytes()
44:     if path.suffix == ".zip" or raw[:2] == b"PK":
45:         with zipfile.ZipFile(io.BytesIO(raw)) as archive:
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/ingest/enrichment.py:43
**Finding:** The F4 refactor correctly halved service.py (820->523 LOC) by extracting the audited enrichment cycles, but they all landed in ONE module: enrichment.py is now the #2 hotspot at 617 LOC with nesting depth 14, holding 9 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep). The seam (AuditedBulkProvider) exists; the cycles could each move beside their provider so a new source stops growing one file.
```
41: 
42: 
43: def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
44:     """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
45:     an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/ingest/mirror.py:98
**Finding:** fetch_if_stale writes the data file atomically (temp-then-rename, mirror.py:92-96) but the .meta.json sidecar is a plain write_text (mirror.py:89, 98-100). A crash mid-write corrupts the sidecar; _read_meta then returns {} (mirror.py:47), losing the stored ETag and forcing a full unconditional re-download of the ~200MB GLEIF file next time. Fails safe (never serves stale data) but wastes bandwidth.
```
96:             tmp.rename(path)
97:         etag = getattr(response, "headers", {}) or {}
98:         meta_path.write_text(
99:             json.dumps({"etag": etag.get("ETag"), "fetched_at": now()})
100:         )
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/ingest/mirror.py:47
**Finding:** fetch_if_stale writes the data file atomically (temp-then-rename, mirror.py:92-96) but the .meta.json sidecar is a plain write_text (mirror.py:89, 98-100). A crash mid-write corrupts the sidecar; _read_meta then returns {} (mirror.py:47), losing the stored ETag and forcing a full unconditional re-download of the ~200MB GLEIF file next time. Fails safe (never serves stale data) but wastes bandwidth.
```
45:     try:
46:         return json.loads(meta_path.read_text())
47:     except (json.JSONDecodeError, OSError):
48:         return {}
49: 
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/compute/snapshot.py:200
**Finding:** In build_symbol_snapshot, when a symbol has no yfinance scrape, audited_frames is passed as None (snapshot.py:200) so the reconcile path that populates the audited_fields provenance column never runs — every field is audited yet audited_fields is empty (snapshot.py:101-103). Row-level provider still records the source, so this is a provenance-completeness gap, not a data error.
```
198:             provider="yfinance" if scraped else _frames_provider(audited, "esef"),
199:             audited_frames=audited if scraped else None,
200:             price_quote=(quote[0], quote[1]) if quote else None,
201:             momentum_6m=quote[2] if quote else None,
202:         )
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/compute/snapshot.py:101
**Finding:** In build_symbol_snapshot, when a symbol has no yfinance scrape, audited_frames is passed as None (snapshot.py:200) so the reconcile path that populates the audited_fields provenance column never runs — every field is audited yet audited_fields is empty (snapshot.py:101-103). Row-level provider still records the source, so this is a provenance-completeness gap, not a data error.
```
99:     out["provider"] = provider
100:     out["price_asof"] = price_asof
101:     out["audited_fields"] = [
102:         ",".join(audited_fields.get(str(p), [])) or None for p in out["period"]
103:     ]
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/providers/edinet.py:155
**Finding:** sec_code returns None when the ticker base is not all digits (edinet.py:155), silently skipping the alphanumeric TSE codes the Tokyo exchange began issuing in 2024 (e.g. 130A.T). Those JP listings never resolve to an EDINET securities code. EDINET is opt-in (off without a key) so the blast radius is small.
```
153:         return None
154:     base, _, suffix = symbol.partition(".")
155:     if suffix.upper() not in ("T", "JP") or not base.isdigit():
156:         return None
157:     return f"{base}0" if len(base) == 4 else base.ljust(5, "0")[:5]
```
**Verdict:** ______  ·  **Note:** ______

## F5 · src/crible/ingest/mirror.py:93
**Finding:** fetch_if_stale streams response.iter_bytes to disk with no size ceiling (mirror.py:93-95) and an httpx timeout that is per-operation, not total (mirror.py:80). URLs are hardcoded and trusted (GLEIF, Frankfurter) so there is no SSRF, but a misbehaving/hostile server could fill the disk or keep a slow download alive indefinitely — the ~200MB GLEIF fetch on the auto-heal path is the exposure.
```
91:             response.raise_for_status()
92:             tmp = path.with_name(path.name + ".tmp")
93:             with open(tmp, "wb") as out:
94:                 for block in response.iter_bytes(chunk):
95:                     out.write(block)
```
**Verdict:** ______  ·  **Note:** ______

## F5 · src/crible/ingest/mirror.py:80
**Finding:** fetch_if_stale streams response.iter_bytes to disk with no size ceiling (mirror.py:93-95) and an httpx timeout that is per-operation, not total (mirror.py:80). URLs are hardcoded and trusted (GLEIF, Frankfurter) so there is no SSRF, but a misbehaving/hostile server could fill the disk or keep a slow download alive indefinitely — the ~200MB GLEIF fetch on the auto-heal path is the exposure.
```
78:         import httpx
79: 
80:         http = httpx.Client(timeout=120, follow_redirects=True)
81: 
82:     request_headers = dict(headers or {})
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/compute/snapshot.py:262
**Finding:** build_snapshot_incremental derives its dirty set solely from raw-layer fetch stamps under data/raw (snapshot.py:262 via _newest_raw_stamp snapshot.py:230-242), but the imported price dump lives in data/prices-latest.parquet (price_import.py) OUTSIDE data/raw and is baked into each symbol's cached per-symbol row (snapshot.py:194-202, 161-170). After `crible import-prices` refreshes the dump, `crible compute` recomputes nothing for symbols whose fundamentals did not change, so their close, return_6m and the value/momentum ranks derived from them stay stale — diverging from a full build_snapshot. Production uses the incremental path (service.py:269, cli.py compute); build_snapshot is test-only and no periodic full rebuild self-heals. (Crawled yfinance price bars DO write to raw and self-heal; the gap is specific to the import-dump price path.)
```
260: 
261:     base_mtime = base_path.stat().st_mtime
262:     dirty = [s for s in symbols if _newest_raw_stamp(data_dir, s) > base_mtime]
263:     prev = pd.read_parquet(base_path)
264:     known = set(prev["symbol"]) if "symbol" in prev.columns else set()
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/compute/snapshot.py:236
**Finding:** build_snapshot_incremental derives its dirty set solely from raw-layer fetch stamps under data/raw (snapshot.py:262 via _newest_raw_stamp snapshot.py:230-242), but the imported price dump lives in data/prices-latest.parquet (price_import.py) OUTSIDE data/raw and is baked into each symbol's cached per-symbol row (snapshot.py:194-202, 161-170). After `crible import-prices` refreshes the dump, `crible compute` recomputes nothing for symbols whose fundamentals did not change, so their close, return_6m and the value/momentum ranks derived from them stay stale — diverging from a full build_snapshot. Production uses the incremental path (service.py:269, cli.py compute); build_snapshot is test-only and no periodic full rebuild self-heals. (Crawled yfinance price bars DO write to raw and self-heal; the gap is specific to the import-dump price path.)
```
234:     safe = symbol.replace("/", "_")
235:     newest = 0.0
236:     for directory in root.glob(f"provider=*/symbol={safe}"):
237:         for file in iter_raw_files(directory):
238:             try:
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/compute/snapshot.py:194
**Finding:** build_snapshot_incremental derives its dirty set solely from raw-layer fetch stamps under data/raw (snapshot.py:262 via _newest_raw_stamp snapshot.py:230-242), but the imported price dump lives in data/prices-latest.parquet (price_import.py) OUTSIDE data/raw and is baked into each symbol's cached per-symbol row (snapshot.py:194-202, 161-170). After `crible import-prices` refreshes the dump, `crible compute` recomputes nothing for symbols whose fundamentals did not change, so their close, return_6m and the value/momentum ranks derived from them stay stale — diverging from a full build_snapshot. Production uses the incremental path (service.py:269, cli.py compute); build_snapshot is test-only and no periodic full rebuild self-heals. (Crawled yfinance price bars DO write to raw and self-heal; the gap is specific to the import-dump price path.)
```
192:         if not scraped and not audited:
193:             continue
194:         quote = quotes.get(symbol)
195:         part = build_symbol_snapshot(
196:             symbol,
```
**Verdict:** ______  ·  **Note:** ______

## F18 · src/crible/providers/fx.py:94
**Finding:** build_snapshot_incremental derives its dirty set solely from raw-layer fetch stamps under data/raw (snapshot.py:262 via _newest_raw_stamp snapshot.py:230-242), but the imported price dump lives in data/prices-latest.parquet (price_import.py) OUTSIDE data/raw and is baked into each symbol's cached per-symbol row (snapshot.py:194-202, 161-170). After `crible import-prices` refreshes the dump, `crible compute` recomputes nothing for symbols whose fundamentals did not change, so their close, return_6m and the value/momentum ranks derived from them stay stale — diverging from a full build_snapshot. Production uses the incremental path (service.py:269, cli.py compute); build_snapshot is test-only and no periodic full rebuild self-heals. (Crawled yfinance price bars DO write to raw and self-heal; the gap is specific to the import-dump price path.)
```
92:     for field in FX_FIELDS:
93:         if field in snapshot.columns:
94:             additions[f"{field}_eur"] = [
95:                 to_eur(v, c, rates) for v, c in zip(snapshot[field], snapshot["currency"])
96:             ]
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/ingest/price_import.py:37
**Finding:** build_snapshot_incremental derives its dirty set solely from raw-layer fetch stamps under data/raw (snapshot.py:262 via _newest_raw_stamp snapshot.py:230-242), but the imported price dump lives in data/prices-latest.parquet (price_import.py) OUTSIDE data/raw and is baked into each symbol's cached per-symbol row (snapshot.py:194-202, 161-170). After `crible import-prices` refreshes the dump, `crible compute` recomputes nothing for symbols whose fundamentals did not change, so their close, return_6m and the value/momentum ranks derived from them stay stale — diverging from a full build_snapshot. Production uses the incremental path (service.py:269, cli.py compute); build_snapshot is test-only and no periodic full rebuild self-heals. (Crawled yfinance price bars DO write to raw and self-heal; the gap is specific to the import-dump price path.)
```
35: log = logging.getLogger("crible.ingest.price_import")
36: 
37: PRICES_LATEST = "prices-latest.parquet"
38: RETURN_WINDOW_DAYS = 182  # mirrors compute.ranks.price_return
39: 
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/ingest/service.py:322
**Finding:** fetch_gleif is correctly staleness-aware (fetch_if_stale with a 7-day max_age, gleif.py:24-35), but both auto-heal callers only invoke it when there is NO mapping at all: run_refresh guards `if load_mapping(data)[0] is None` (service.py:322) and the weekly run_loop timer guards the same (service.py:477). Once isin-lei.zip exists it is never re-fetched, so the 7-day max_age is dead code and new EU ISINs (IPOs, relistings) never resolve to an LEI — those companies get no ESEF audited data, a slow silent coverage regression. Only the manual `ingest --fetch-gleif` bypasses the gate.
```
320:         from crible.providers.gleif import load_mapping
321: 
322:         if load_mapping(data)[0] is None:
323:             try:
324:                 _fetch_gleif(data)
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/ingest/service.py:477
**Finding:** fetch_gleif is correctly staleness-aware (fetch_if_stale with a 7-day max_age, gleif.py:24-35), but both auto-heal callers only invoke it when there is NO mapping at all: run_refresh guards `if load_mapping(data)[0] is None` (service.py:322) and the weekly run_loop timer guards the same (service.py:477). Once isin-lei.zip exists it is never re-fetched, so the 7-day max_age is dead code and new EU ISINs (IPOs, relistings) never resolve to an LEI — those companies get no ESEF audited data, a slow silent coverage regression. Only the manual `ingest --fetch-gleif` bypasses the gate.
```
475:                 from crible.providers.gleif import fetch_gleif, load_mapping
476: 
477:                 if load_mapping(config.data_dir())[0] is None:
478:                     fetch_gleif(config.data_dir())
479:             except Exception as exc:  # noqa: BLE001 — never kills the loop
```
**Verdict:** ______  ·  **Note:** ______

## F19 · src/crible/providers/gleif.py:47
**Finding:** sec_code returns None when the ticker base is not all digits (edinet.py:155), silently skipping the alphanumeric TSE codes the Tokyo exchange began issuing in 2024 (e.g. 130A.T). Those JP listings never resolve to an EDINET securities code. EDINET is opt-in (off without a key) so the blast radius is small.
```
45:         with zipfile.ZipFile(io.BytesIO(raw)) as archive:
46:             inner = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
47:             raw = archive.read(inner)
48:     mapping: dict[str, str] = {}
49:     reader = csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")))
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/providers/gleif.py:26
**Finding:** fetch_gleif is correctly staleness-aware (fetch_if_stale with a 7-day max_age, gleif.py:24-35), but both auto-heal callers only invoke it when there is NO mapping at all: run_refresh guards `if load_mapping(data)[0] is None` (service.py:322) and the weekly run_loop timer guards the same (service.py:477). Once isin-lei.zip exists it is never re-fetched, so the 7-day max_age is dead code and new EU ISINs (IPOs, relistings) never resolve to an LEI — those companies get no ESEF audited data, a slow silent coverage regression. Only the manual `ingest --fetch-gleif` bypasses the gate.
```
24: def fetch_gleif(data_dir: Path | str, http=None, max_age_seconds: float = 7 * 24 * 3600) -> Path:
25:     """Download the latest GLEIF ISIN→LEI relationship file into the local
26:     mirror (``data/mirror/gleif/isin-lei.zip``, ~200 MB, refreshed at most
27:     weekly) and return its path. ``load_mapping`` then finds it there, so a
28:     fresh install gets audited-EU coverage with no manual step. Keyless open
```
**Verdict:** ______  ·  **Note:** ______

## F10 · src/crible/providers/edgar_fsds.py:67
**Finding:** SEC FSDS num.txt carries a coreg column (present in the test header, tests/test_fsds.py) where empty = the consolidated registrant and non-empty = a co-registrant/parent/guarantor (common on bond-issuer 10-Ks). parse_fsds_quarter filters rows on tag, uom, qtrs and ddate but never on coreg (edgar_fsds.py:71-92), and cells are first-writer-wins at equal concept rank (edgar_fsds.py:96-99), so whichever num.txt row appears first wins with no guarantee it is the consolidated one. companyfacts (edgar.py) is immune because its units arrays hold only default-member values — this is an FSDS-format-specific risk. (Blast radius is reduced by F6, which drops FSDS-only periods for scraped symbols.)
```
65:     # cik -> (period, column) -> (value, winning-concept rank)
66:     acc: dict[int, dict[tuple[str, str], tuple[float, int]]] = defaultdict(dict)
67:     for row in csv.DictReader(io.StringIO(num_text), delimiter="\t"):
68:         cik = wanted.get(row.get("adsh"))
69:         if cik is None:
```
**Verdict:** ______  ·  **Note:** ______

## F10 · src/crible/providers/edgar_fsds.py:80
**Finding:** SEC FSDS num.txt carries a coreg column (present in the test header, tests/test_fsds.py) where empty = the consolidated registrant and non-empty = a co-registrant/parent/guarantor (common on bond-issuer 10-Ks). parse_fsds_quarter filters rows on tag, uom, qtrs and ddate but never on coreg (edgar_fsds.py:71-92), and cells are first-writer-wins at equal concept rank (edgar_fsds.py:96-99), so whichever num.txt row appears first wins with no guarantee it is the consolidated one. companyfacts (edgar.py) is immune because its units arrays hold only default-member values — this is an FSDS-format-specific risk. (Blast radius is reduced by F6, which drops FSDS-only periods for scraped symbols.)
```
78:             continue
79:         qtrs = str(row.get("qtrs"))
80:         if statement == "balance":
81:             if qtrs != "0":
82:                 continue  # a balance-sheet fact is an instant
```
**Verdict:** ______  ·  **Note:** ______

## F10 · src/crible/providers/edgar_fsds.py:97
**Finding:** SEC FSDS num.txt carries a coreg column (present in the test header, tests/test_fsds.py) where empty = the consolidated registrant and non-empty = a co-registrant/parent/guarantor (common on bond-issuer 10-Ks). parse_fsds_quarter filters rows on tag, uom, qtrs and ddate but never on coreg (edgar_fsds.py:71-92), and cells are first-writer-wins at equal concept rank (edgar_fsds.py:96-99), so whichever num.txt row appears first wins with no guarantee it is the consolidated one. companyfacts (edgar.py) is immune because its units arrays hold only default-member values — this is an FSDS-format-specific risk. (Blast radius is reduced by F6, which drops FSDS-only periods for scraped symbols.)
```
95:         key = (period, column)
96:         prev = acc[cik].get(key)
97:         if prev is not None and prev[1] <= rank:
98:             continue  # an equal-or-earlier-precedence concept already set this cell
99:         acc[cik][key] = (value, rank)
```
**Verdict:** ______  ·  **Note:** ______

## F11 · src/crible/providers/gleif.py:43
**Finding:** Two bulk parsers materialize an entire archive member in RAM. load_isin_lei_map reads the whole zip to bytes (gleif.py:43), decompresses the whole CSV to bytes (gleif.py:47), then decodes it to a str for StringIO (gleif.py:49) — triple-buffered for a file the docstring calls ~200MB (decompressed ~1GB). parse_fsds_quarter does the same archive.read(...).decode(...) on num.txt (edgar_fsds.py:131-132), hundreds of MB uncompressed per quarter. Both run on auto-heal / opt-in ingest paths that the memory-safe mirror streaming was meant to protect — the same OOM class as the prior-cycle F13 bootstrap fix.
```
41:     """Parse a GLEIF relationship file (CSV or zipped CSV) into {ISIN: LEI}."""
42:     path = Path(path)
43:     raw: bytes = path.read_bytes()
44:     if path.suffix == ".zip" or raw[:2] == b"PK":
45:         with zipfile.ZipFile(io.BytesIO(raw)) as archive:
```
**Verdict:** ______  ·  **Note:** ______

## F11 · src/crible/providers/gleif.py:47
**Finding:** Two bulk parsers materialize an entire archive member in RAM. load_isin_lei_map reads the whole zip to bytes (gleif.py:43), decompresses the whole CSV to bytes (gleif.py:47), then decodes it to a str for StringIO (gleif.py:49) — triple-buffered for a file the docstring calls ~200MB (decompressed ~1GB). parse_fsds_quarter does the same archive.read(...).decode(...) on num.txt (edgar_fsds.py:131-132), hundreds of MB uncompressed per quarter. Both run on auto-heal / opt-in ingest paths that the memory-safe mirror streaming was meant to protect — the same OOM class as the prior-cycle F13 bootstrap fix.
```
45:         with zipfile.ZipFile(io.BytesIO(raw)) as archive:
46:             inner = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
47:             raw = archive.read(inner)
48:     mapping: dict[str, str] = {}
49:     reader = csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")))
```
**Verdict:** ______  ·  **Note:** ______

## F11 · src/crible/providers/edgar_fsds.py:131
**Finding:** Two bulk parsers materialize an entire archive member in RAM. load_isin_lei_map reads the whole zip to bytes (gleif.py:43), decompresses the whole CSV to bytes (gleif.py:47), then decodes it to a str for StringIO (gleif.py:49) — triple-buffered for a file the docstring calls ~200MB (decompressed ~1GB). parse_fsds_quarter does the same archive.read(...).decode(...) on num.txt (edgar_fsds.py:131-132), hundreds of MB uncompressed per quarter. Both run on auto-heal / opt-in ingest paths that the memory-safe mirror streaming was meant to protect — the same OOM class as the prior-cycle F13 bootstrap fix.
```
129:             log.warning("fsds: %s missing sub.txt/num.txt — skipped", zip_path)
130:             return
131:         sub_text = archive.read(names["sub.txt"]).decode("utf-8", errors="replace")
132:         num_text = archive.read(names["num.txt"]).decode("utf-8", errors="replace")
133:     for cik, frames in frames_from_fsds(sub_text, num_text, ciks).items():
```
**Verdict:** ______  ·  **Note:** ______

## F12 · src/crible/providers/fx.py:26
**Finding:** fetch_rates pulls Frankfurter's /latest endpoint (fx.py:26) and attach_fx converts every row (all fiscal periods) with that one rate map (fx.py:94-95), so 2015 revenue and 2024 revenue are both normalized at today's EUR rate. The docstring documents the listing-vs-reporting currency approximation but not this temporal one; historical revenue_eur / total_assets_eur look precise but are wrong for cross-period comparison.
```
24: log = logging.getLogger("crible.providers.fx")
25: 
26: FRANKFURTER_URL = "https://api.frankfurter.app/latest?base=EUR"
27: 
28: # absolute-magnitude snapshot fields worth a cross-currency companion; ratios
```
**Verdict:** ______  ·  **Note:** ______

## F12 · src/crible/providers/fx.py:94
**Finding:** fetch_rates pulls Frankfurter's /latest endpoint (fx.py:26) and attach_fx converts every row (all fiscal periods) with that one rate map (fx.py:94-95), so 2015 revenue and 2024 revenue are both normalized at today's EUR rate. The docstring documents the listing-vs-reporting currency approximation but not this temporal one; historical revenue_eur / total_assets_eur look precise but are wrong for cross-period comparison.
```
92:     for field in FX_FIELDS:
93:         if field in snapshot.columns:
94:             additions[f"{field}_eur"] = [
95:                 to_eur(v, c, rates) for v, c in zip(snapshot[field], snapshot["currency"])
96:             ]
```
**Verdict:** ______  ·  **Note:** ______

## F13 · src/crible/ingest/enrichment.py:480
**Finding:** run_edinet processes any swept document whose secCode matches, with no docTypeCode/ordinanceCode filter despite the 'annual securities reports' contract (enrichment.py:480-483). A quarterly/semi-annual report thus reaches the parser; the income branch's full-year duration guard drops interim durations, but the balance branch of _period accepts ANY instant and returns its calendar year (edinet.py:60-63), so an interim balance instant (e.g. 2023-09-30) is booked as the '2023' annual balance — the same interim-as-annual class as the prior-cycle ESEF F9. EDINET is opt-in (off without a key).
```
478:                 log.warning("edinet: %s — resuming next run", exc)
479:                 continue
480:             for doc in documents:
481:                 symbol = by_seccode.get(str(doc.get("secCode") or ""))
482:                 if not symbol:
```
**Verdict:** ______  ·  **Note:** ______

## F13 · src/crible/providers/edinet.py:60
**Finding:** run_edinet processes any swept document whose secCode matches, with no docTypeCode/ordinanceCode filter despite the 'annual securities reports' contract (enrichment.py:480-483). A quarterly/semi-annual report thus reaches the parser; the income branch's full-year duration guard drops interim durations, but the balance branch of _period accepts ANY instant and returns its calendar year (edinet.py:60-63), so an interim balance instant (e.g. 2023-09-30) is booked as the '2023' annual balance — the same interim-as-annual class as the prior-cycle ESEF F9. EDINET is opt-in (off without a key).
```
58:         return None
59:     instant = ctx.get("instant")
60:     if statement == "balance":
61:         if not instant:
62:             return None
```
**Verdict:** ______  ·  **Note:** ______

## F14 · src/crible/providers/edinet.py:80
**Finding:** EDINET reports the same jppfs_cor concept twice — consolidated and parent-only — differentiated only by the context's scenario/dimension members. parse_xbrl_instance reads contexts for start/end/instant only and never inspects dimensions (edinet.py:80-93), and the fact loop keeps the first-seen concept per (period,column) (edinet.py:107-119), so document order decides the basis. For a company with subsidiaries this can silently book parent-only revenue/assets instead of the consolidated figure. EDINET is opt-in (off without a key).
```
78:     root = ET.fromstring(xml if isinstance(xml, bytes) else xml.encode("utf-8"))
79: 
80:     contexts: dict[str, dict[str, str]] = {}
81:     for ctx in root.iter():
82:         if _local(ctx.tag) != "context":
```
**Verdict:** ______  ·  **Note:** ______

## F14 · src/crible/providers/edinet.py:107
**Finding:** EDINET reports the same jppfs_cor concept twice — consolidated and parent-only — differentiated only by the context's scenario/dimension members. parse_xbrl_instance reads contexts for start/end/instant only and never inspects dimensions (edinet.py:80-93), and the fact loop keeps the first-seen concept per (period,column) (edinet.py:107-119), so document order decides the basis. For a company with subsidiaries this can silently book parent-only revenue/assets instead of the consolidated figure. EDINET is opt-in (off without a key).
```
105:             continue  # monetary facts only
106:         column, statement = mapped
107:         period = _period(contexts.get(ctxref), statement)
108:         if period is None:
109:             continue
```
**Verdict:** ______  ·  **Note:** ______

## F15 · src/crible/compute/snapshot.py:239
**Finding:** _newest_raw_stamp returns the max fetched-at stamp for a symbol (snapshot.py:239); a deletion can only lower the newest stamp, never raise it above base_mtime, so the dirty test `> base_mtime` (snapshot.py:262) misses a symbol whose latest raw statement was removed — it keeps its stale cached row while a full rebuild would reflect the removal. prune_raw is safe (it only deletes older versions), so this bites only on an out-of-band removal of the newest file; a full-drop of the symbol IS handled (snapshot.py:265-270).
```
237:         for file in iter_raw_files(directory):
238:             try:
239:                 newest = max(newest, int(file.stem.rsplit("-", 1)[1]) / 1000.0)
240:             except (IndexError, ValueError):
241:                 continue
```
**Verdict:** ______  ·  **Note:** ______

## F15 · src/crible/compute/snapshot.py:262
**Finding:** _newest_raw_stamp returns the max fetched-at stamp for a symbol (snapshot.py:239); a deletion can only lower the newest stamp, never raise it above base_mtime, so the dirty test `> base_mtime` (snapshot.py:262) misses a symbol whose latest raw statement was removed — it keeps its stale cached row while a full rebuild would reflect the removal. prune_raw is safe (it only deletes older versions), so this bites only on an out-of-band removal of the newest file; a full-drop of the symbol IS handled (snapshot.py:265-270).
```
260: 
261:     base_mtime = base_path.stat().st_mtime
262:     dirty = [s for s in symbols if _newest_raw_stamp(data_dir, s) > base_mtime]
263:     prev = pd.read_parquet(base_path)
264:     known = set(prev["symbol"]) if "symbol" in prev.columns else set()
```
**Verdict:** ______  ·  **Note:** ______

## F16 · src/crible/providers/gleif.py:49
**Finding:** load_isin_lei_map decodes the CSV with utf-8, not utf-8-sig (gleif.py:49). If the GLEIF relationship CSV ships with a UTF-8 BOM, the first header key becomes '\ufeffLEI', so lower.get('lei') returns None for every row (gleif.py:52), the `if isin and lei` guard is always false, and the mapping loads 0 relationships — logged as a benign 'loaded 0', silently disabling all audited-EU coverage. Whether it triggers depends on the live file carrying a BOM (not verified here); the unit fixture has none so the test cannot see it.
```
47:             raw = archive.read(inner)
48:     mapping: dict[str, str] = {}
49:     reader = csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")))
50:     for row in reader:
51:         lower = {k.lower(): v for k, v in row.items() if k}
```
**Verdict:** ______  ·  **Note:** ______

## F16 · src/crible/providers/gleif.py:52
**Finding:** load_isin_lei_map decodes the CSV with utf-8, not utf-8-sig (gleif.py:49). If the GLEIF relationship CSV ships with a UTF-8 BOM, the first header key becomes '\ufeffLEI', so lower.get('lei') returns None for every row (gleif.py:52), the `if isin and lei` guard is always false, and the mapping loads 0 relationships — logged as a benign 'loaded 0', silently disabling all audited-EU coverage. Whether it triggers depends on the live file carrying a BOM (not verified here); the unit fixture has none so the test cannot see it.
```
50:     for row in reader:
51:         lower = {k.lower(): v for k, v in row.items() if k}
52:         isin, lei = lower.get("isin"), lower.get("lei")
53:         if isin and lei:
54:             mapping[isin.strip()] = lei.strip()
```
**Verdict:** ______  ·  **Note:** ______

