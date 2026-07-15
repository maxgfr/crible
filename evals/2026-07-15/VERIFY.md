# Verification worklist

For each pair: read the digest, judge whether it SUPPORTS the finding, write a verdict.
Verdicts: `supported` · `partial` · `refuted` · `unsupported`.

## F1 · src/crible/compute/ranks.py:36
**Finding:** The same financial invariant — return = lastClose / (last close at or before asof-182d) - 1, never extrapolated — is coded three independent times: compute.ranks.price_return (src/crible/compute/ranks.py:36, pandas, crawl path), _distill (src/crible/ingest/price_import.py:112, pandas, Stooq path) and a DuckDB SQL variant (src/crible/ingest/price_import.py:168, HuggingFace path). They stay consistent only via cross-referencing comments; the window constant RETURN_WINDOW_DAYS is redeclared at price_import.py:38 separately from ranks.price_return(days=182). A future change (trading vs calendar days, dividend handling, window) must be edited in three places and the imported-dump paths would silently diverge from the crawl path by data source.
```
34: 
35: 
36: def price_return(bars: pd.DataFrame, days: int = 182) -> float:
37:     """Trailing price return over ``days`` calendar days from daily bars.
38: 
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/ingest/price_import.py:112
**Finding:** The same financial invariant — return = lastClose / (last close at or before asof-182d) - 1, never extrapolated — is coded three independent times: compute.ranks.price_return (src/crible/compute/ranks.py:36, pandas, crawl path), _distill (src/crible/ingest/price_import.py:112, pandas, Stooq path) and a DuckDB SQL variant (src/crible/ingest/price_import.py:168, HuggingFace path). They stay consistent only via cross-referencing comments; the window constant RETURN_WINDOW_DAYS is redeclared at price_import.py:38 separately from ranks.price_return(days=182). A future change (trading vs calendar days, dividend handling, window) must be edited in three places and the imported-dump paths would silently diverge from the crawl path by data source.
```
110: 
111: 
112: def _distill(bars: pd.DataFrame) -> tuple[float, str, float] | None:
113:     """(close, asof, return_6m) from a Date/Close frame — price_return rules:
114:     the base is the last close at or before asof − 182 days, never
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/ingest/price_import.py:168
**Finding:** The same financial invariant — return = lastClose / (last close at or before asof-182d) - 1, never extrapolated — is coded three independent times: compute.ranks.price_return (src/crible/compute/ranks.py:36, pandas, crawl path), _distill (src/crible/ingest/price_import.py:112, pandas, Stooq path) and a DuckDB SQL variant (src/crible/ingest/price_import.py:168, HuggingFace path). They stay consistent only via cross-referencing comments; the window constant RETURN_WINDOW_DAYS is redeclared at price_import.py:38 separately from ranks.price_return(days=182). A future change (trading vs calendar days, dividend handling, window) must be edited in three places and the imported-dump paths would silently diverge from the crawl path by data source.
```
166:             ),
167:             base AS (
168:                 SELECT b.symbol, arg_max(b.close, b.date) AS base_close
169:                 FROM bars b
170:                 JOIN latest l USING (symbol)
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/compute/snapshot.py:76
**Finding:** The analyzer-flagged cycle is real to the graph but type-only at runtime: ui/src/data/duckdb.ts:11 does `import type { QueryRunner } from './static-client'` (erased at build) while ui/src/data/static-client.ts:74 reaches back via a lazy dynamic import('./duckdb') (intentional code-split to keep duckdb-wasm out of the initial bundle). No runtime defect, but the QueryRunner interface could live where the other shared contracts already do (ui/src/data/types.ts).
```
74:         if close is not None:
75:             value, price_asof = close
76:             # the current price applies to the LATEST fiscal period only —
77:             # older periods keep NaN rather than pretending historical prices
78:             price = pd.Series(float("nan"), index=canonical.index)
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/compute/ratios.py:109
**Finding:** compute_ratios (src/crible/compute/ratios.py:109) is the snapshot's widest column producer: it reflection-wires every get_* across financetoolkit's ratio modules, each guarded by a blanket `except Exception: continue` (src/crible/compute/ratios.py:123). It has no direct test (only indirect exercise via snapshot building). If financetoolkit renames a parameter or adds a get_* with an unresolvable required arg, the affected ratio columns silently vanish from the snapshot with zero signal — degrading the core product output.
```
107: 
108: 
109: def compute_ratios(canonical: pd.DataFrame, price: pd.Series | None = None) -> pd.DataFrame:
110:     inputs = build_inputs(canonical, price)
111:     out: dict[str, pd.Series] = {}
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/compute/ratios.py:123
**Finding:** compute_ratios (src/crible/compute/ratios.py:109) is the snapshot's widest column producer: it reflection-wires every get_* across financetoolkit's ratio modules, each guarded by a blanket `except Exception: continue` (src/crible/compute/ratios.py:123). It has no direct test (only indirect exercise via snapshot building). If financetoolkit renames a parameter or adds a get_* with an unresolvable required arg, the affected ratio columns silently vanish from the snapshot with zero signal — degrading the core product output.
```
121:             if not all(p.name in inputs for p in required):
122:                 continue
123:             try:
124:                 result = fn(**{p.name: inputs[p.name] for p in required})
125:             except Exception:  # noqa: BLE001 — a single ratio must never kill compute
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/ingest/service.py:422
**Finding:** run_loop (src/crible/ingest/service.py:422) is the primary self-hosted deployment entrypoint (the docker ingest service) yet is marked `# pragma: no cover` — zero test coverage. It hand-rolls six near-identical time-gated maintenance blocks (each an `if now - last_X >= INTERVAL: try: ... except Exception: log.warning`), and run_refresh (src/crible/ingest/service.py:281) re-implements the same enrichment sequence with its own parallel try/except-log blocks. test_service.py covers only run_once and maybe_refresh_universe.
```
420: 
421: 
422: def run_loop(cycle_limit: int = 40, compute_every_seconds: float = 1800.0) -> None:  # pragma: no cover — long-lived loop
423:     # cycle_limit × ~7 requests must stay under the hourly budget so a cycle
424:     # never stalls mid-way on the token bucket before its compute runs
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/providers/edinet.py:26
**Finding:** run_loop (src/crible/ingest/service.py:422) is the primary self-hosted deployment entrypoint (the docker ingest service) yet is marked `# pragma: no cover` — zero test coverage. It hand-rolls six near-identical time-gated maintenance blocks (each an `if now - last_X >= INTERVAL: try: ... except Exception: log.warning`), and run_refresh (src/crible/ingest/service.py:281) re-implements the same enrichment sequence with its own parallel try/except-log blocks. test_service.py covers only run_once and maybe_refresh_universe.
```
24: # 120 = 有価証券報告書 (Annual Securities Report); other doc types (quarterly 140,
25: # semi-annual 160…) carry interim figures we must not book as annual.
26: ANNUAL_DOC_TYPES = {"120"}
27: 
28: # jppfs concept local-name (lowercased) → (canonical column, statement)
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/ingest/service.py:281
**Finding:** run_loop (src/crible/ingest/service.py:422) is the primary self-hosted deployment entrypoint (the docker ingest service) yet is marked `# pragma: no cover` — zero test coverage. It hand-rolls six near-identical time-gated maintenance blocks (each an `if now - last_X >= INTERVAL: try: ... except Exception: log.warning`), and run_refresh (src/crible/ingest/service.py:281) re-implements the same enrichment sequence with its own parallel try/except-log blocks. test_service.py covers only run_once and maybe_refresh_universe.
```
279: 
280: 
281: def run_refresh(
282:     deadline_seconds: float = 9000.0,
283:     esef_limit: int = 25,
```
**Verdict:** ______  ·  **Note:** ______

## F10 · ui/src/data/static-client.ts:74
**Finding:** run_loop (src/crible/ingest/service.py:422) is the primary self-hosted deployment entrypoint (the docker ingest service) yet is marked `# pragma: no cover` — zero test coverage. It hand-rolls six near-identical time-gated maintenance blocks (each an `if now - last_X >= INTERVAL: try: ... except Exception: log.warning`), and run_refresh (src/crible/ingest/service.py:281) re-implements the same enrichment sequence with its own parallel try/except-log blocks. test_service.py covers only run_once and maybe_refresh_universe.
```
72:     (async () => {
73:       const shards = (await manifest())?.prices?.shards.map((s) => s.file) ?? [];
74:       return import("./duckdb").then((m) => m.createDuckDbRunner(base, shards));
75:     });
76: 
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/compute/snapshot.py:42
**Finding:** build_symbol_snapshot (src/crible/compute/snapshot.py:42) interleaves five distinct rules in one body: audited reconcile+alignment, the crawled-vs-imported price fallback (src/crible/compute/snapshot.py:76, 'current price applies to the LATEST fiscal period only'), ratios/scores/growth assembly, momentum resolution, and three provenance columns via positional .iloc writes. Each rule is individually testable but currently reachable only through the whole function.
```
40: 
41: 
42: def build_symbol_snapshot(
43:     symbol: str,
44:     frames: dict[tuple[str, str], pd.DataFrame],
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/compute/snapshot.py:76
**Finding:** build_symbol_snapshot (src/crible/compute/snapshot.py:42) interleaves five distinct rules in one body: audited reconcile+alignment, the crawled-vs-imported price fallback (src/crible/compute/snapshot.py:76, 'current price applies to the LATEST fiscal period only'), ratios/scores/growth assembly, momentum resolution, and three provenance columns via positional .iloc writes. Each rule is individually testable but currently reachable only through the whole function.
```
74:         if close is not None:
75:             value, price_asof = close
76:             # the current price applies to the LATEST fiscal period only —
77:             # older periods keep NaN rather than pretending historical prices
78:             price = pd.Series(float("nan"), index=canonical.index)
```
**Verdict:** ______  ·  **Note:** ______

## F5 · ui/src/data/duckdb.ts:11
**Finding:** The analyzer-flagged cycle is real to the graph but type-only at runtime: ui/src/data/duckdb.ts:11 does `import type { QueryRunner } from './static-client'` (erased at build) while ui/src/data/static-client.ts:74 reaches back via a lazy dynamic import('./duckdb') (intentional code-split to keep duckdb-wasm out of the initial bundle). No runtime defect, but the QueryRunner interface could live where the other shared contracts already do (ui/src/data/types.ts).
```
9: import workerMvp from "@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url";
10: import workerEh from "@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url";
11: import type { QueryRunner } from "./static-client";
12: 
13: const BUNDLES: duckdb.DuckDBBundles = {
```
**Verdict:** ______  ·  **Note:** ______

## F5 · ui/src/data/static-client.ts:74
**Finding:** The analyzer-flagged cycle is real to the graph but type-only at runtime: ui/src/data/duckdb.ts:11 does `import type { QueryRunner } from './static-client'` (erased at build) while ui/src/data/static-client.ts:74 reaches back via a lazy dynamic import('./duckdb') (intentional code-split to keep duckdb-wasm out of the initial bundle). No runtime defect, but the QueryRunner interface could live where the other shared contracts already do (ui/src/data/types.ts).
```
72:     (async () => {
73:       const shards = (await manifest())?.prices?.shards.map((s) => s.file) ?? [];
74:       return import("./duckdb").then((m) => m.createDuckDbRunner(base, shards));
75:     });
76: 
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/providers/edinet.py:26
**Finding:** The (correct) interim-report fix narrows EDINET ingestion to ANNUAL_DOC_TYPES = {"120"} (src/crible/providers/edinet.py:26, applied at src/crible/ingest/enrich/jp.py:58). docType 120 is the annual securities report (有価証券報告書); 130 is its amendment (訂正有価証券報告書). The base commit processed all docs, so this new filter also drops amended annual figures. This is collateral of an otherwise-correct fix and is strictly better than the base (which mis-booked quarterly/semi-annual figures as annual); EDINET is free-key and OFF by default, so blast radius is minimal. Not a regression from a working state, but a small completeness gap: a company that supersedes its 120 with a 130 correction keeps the pre-correction figures.
```
24: # 120 = 有価証券報告書 (Annual Securities Report); other doc types (quarterly 140,
25: # semi-annual 160…) carry interim figures we must not book as annual.
26: ANNUAL_DOC_TYPES = {"120"}
27: 
28: # jppfs concept local-name (lowercased) → (canonical column, statement)
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/ingest/enrich/jp.py:58
**Finding:** The (correct) interim-report fix narrows EDINET ingestion to ANNUAL_DOC_TYPES = {"120"} (src/crible/providers/edinet.py:26, applied at src/crible/ingest/enrich/jp.py:58). docType 120 is the annual securities report (有価証券報告書); 130 is its amendment (訂正有価証券報告書). The base commit processed all docs, so this new filter also drops amended annual figures. This is collateral of an otherwise-correct fix and is strictly better than the base (which mis-booked quarterly/semi-annual figures as annual); EDINET is free-key and OFF by default, so blast radius is minimal. Not a regression from a working state, but a small completeness gap: a company that supersedes its 120 with a 130 correction keeps the pre-correction figures.
```
56:                 if not symbol:
57:                     continue
58:                 if str(doc.get("docTypeCode") or "") not in ANNUAL_DOC_TYPES:
59:                     continue  # only annual securities reports (120), not interim
60:                 try:
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/compute/reconcile.py:72
**Finding:** reconcile (src/crible/compute/reconcile.py:72) does `merged.loc[period, column] = audited_value` inside `for period: for column:`, resolving the label pair on every cell. With deep-history backfill (FSDS/EDGAR add many periods) times ~25 canonical columns this is O(periods x columns) chained .loc scalar assignments per symbol — a real (if bounded) slow path on the flagship deep-history universe.
```
70:     discrepancies: list[dict] = []
71: 
72:     for period in audited.index:
73:         for column in audited.columns:
74:             audited_value = audited.loc[period, column]
```
**Verdict:** ______  ·  **Note:** ______

