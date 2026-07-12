# Verification worklist

For each pair: read the digest, judge whether it SUPPORTS the finding, write a verdict.
Verdicts: `supported` · `partial` · `refuted` · `unsupported`.

## F2 · src/crible/ingest/service.py:1-370
**Finding:** Toujours ouvert (porté du run de base, décision « coût > valeur immédiate » documentée dans PRIORITIES) : le service d'ingestion orchestre queue, budget, backoff, crawler, prix et heartbeat dans un seul module de 370 LOC avec une profondeur d'imbrication de 14 — le pire hotspot du dépôt à l'analyse déterministe.
```
1: """FR-008 — the ingest service loop: bootstrap → crawl → compute → publish.
2: 
3: Runs as the `ingest` Docker service. On first boot the bootstrap sample
4: (~100 liquid symbols: CAC 40 + DAX 40 + 20 US mega-caps, overridable via
5: CRIBLE_BOOTSTRAP_SAMPLE) is front-loaded so a first screen returns rows within
6: hours. Compute runs after every crawl cycle. A heartbeat (data/status.json)
7: exposes budget usage and cycle outcomes to `crible status` and GET /status.
8: """
9: 
10: from __future__ import annotations
11: 
12: import json
13: import logging
14: import os
15: import time
16: 
17: import duckdb
18: 
19: from crible import config
20: from crible.compute.snapshot import build_snapshot, publish_snapshot
21: from crible.ingest.backoff import BackoffPolicy
22: from crible.ingest.budget import TokenBucket
23: from crible.ingest.crawler import Crawler, CrawlOutcome
24: from crible.ingest.queue import CrawlQueue
25: from crible.providers.yfinance_provider import YFinanceProvider
26: from crible.universe import BootstrapReport, refresh_universe
27: 
28: log = logging.getLogger("crible.ingest.service")
29: 
30: CAC40 = [
31:     "AI.PA", "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "BVI.PA", "CAP.PA",
32:     "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EDEN.PA", "ENGI.PA", "EL.PA", "ERF.PA", "RMS.PA",
33:     "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA",
34:     "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "STLAP.PA", "STMPA.PA", "TEP.PA",
35:     "HO.PA", "TTE.PA", "URW.AS", "VIE.PA", "DG.PA",
36: ]
37: DAX40 = [
38:     "ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BEI.DE", "BMW.DE", "BNR.DE", "CBK.DE", "CON.DE",
39:     "1COV.DE", "DTG.DE", "DBK.DE", "DB1.DE", "DHL.DE", "DTE.DE", "EOAN.DE", "FRE.DE", "FME.DE",
40:     "HNR1.DE", "HEI.DE", "HEN3.DE", "IFX.DE", "MBG.DE", "MRK.DE", "MTX.DE", "MUV2.DE",
41:     "P911.DE", "QIA.DE", "RHM.DE", "RWE.DE", "SAP.DE", "SRT3.DE", "SIE.DE", "ENR.DE", "SHL.DE",
42:     "SY1.DE", "VOW3.DE", "VNA.DE", "ZAL.DE", "PAH3.DE",
43: ]
44: US_MEGA = [
45:     "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "LLY", "AVGO", "JPM",
46:     "V", "TSLA", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "COST", "ORCL",
47: ]
48: 
49: 
50: def bootstrap_sample() -> list[str]:
51:     override = os.environ.get("CRIBLE_BOOTSTRAP_SAMPLE")
52:     if override:
53:         return [s.strip() for s in override.split(",") if s.strip()]
54:     return CAC40 + DAX40 + US_MEGA
55: 
56: 
57: def _connect() -> duckdb.DuckDBPyConnection:
58:     path = config.database_path()
59:     path.parent.mkdir(parents=True, exist_ok=True)
60:     return duckdb.connect(str(path))
61: 
62: 
63: def prioritize_sample(con: duckdb.DuckDBPyConnection, symbols: list[str]) -> None:
64:     """Front-load the bootstrap sample: highest priority, due immediately."""
65:     con.execute(
66:         "UPDATE crawl_tasks SET priority = -1, next_due = 0 WHERE symbol IN "
67:         f"({', '.join('?' for _ in symbols)})",
68:         symbols,
69:     )
70: 
71: 
72: def write_heartbeat(payload: dict) -> None:
73:     path = config.data_dir() / "status.json"
74:     path.parent.mkdir(parents=True, exist_ok=True)
75:     tmp = path.with_suffix(".json.tmp")
76:     tmp.write_text(json.dumps(payload, default=str))
77:     tmp.rename(path)
78: 
79: 
80: def update_heartbeat(**fields) -> None:
81:     """Merge fields into the heartbeat (read-modify-write, atomic rename)."""
82:     path = config.data_dir() / "status.json"
83:     current: dict = {}
84:     if path.exists():
85:         try:
86:             current = json.loads(path.read_text())
87:         except json.JSONDecodeError:
88:             current = {}
89:     current.update(fields)
90:     write_heartbeat(current)
91: 
92: 
93: def _queue_stats(con: duckdb.DuckDBPyConnection) -> dict:
94:     """FR-005 AC-3 — coverage %, freshness histogram, per-region backlog."""
95:     stats: dict = {}
96:     tables = {
97:         r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
98:     }
99:     if "companies" in tables:
100:         stats["universe"] = con.execute("SELECT count(*) FROM companies").fetchone()[0]
101:         stats["by_region"] = dict(
102:             con.execute("SELECT region, count(*) FROM companies GROUP BY region").fetchall()
103:         )
104:     if "crawl_tasks" in tables:
105:         crawled = con.execute(
106:             "SELECT count(*) FROM crawl_tasks WHERE last_crawled_at IS NOT NULL"
107:         ).fetchone()[0]
108:         stats["crawled"] = crawled
109:         if stats.get("universe"):
110:             stats["coverage_pct"] = round(100.0 * crawled / stats["universe"], 2)
111:         stats["freshness"] = dict(
112:             con.execute(
113:                 """
114:                 SELECT CASE
115:                     WHEN last_crawled_at IS NULL THEN 'never'
116:                     WHEN last_crawled_at > epoch(now()) - 7*86400 THEN '<7d'
117:                     WHEN last_crawled_at > epoch(now()) - 30*86400 THEN '<30d'
118:                     WHEN last_crawled_at > epoch(now()) - 90*86400 THEN '<90d'
119:                     ELSE 'stale' END AS bucket, count(*)
120:                 FROM crawl_tasks GROUP BY bucket
121:                 """
122:             ).fetchall()
123:         )
124:     return stats
125: 
126: 
127: def run_bootstrap() -> BootstrapReport:
128:     con = _connect()
129:     try:
130:         report = refresh_universe(con)
131:         queue = CrawlQueue(con)
132:         queue.seed_from_universe()
133:         prioritize_sample(con, bootstrap_sample())
134:         return report
135:     finally:
136:         con.close()
137: 
138: 
139: def _make_crawler(con: duckdb.DuckDBPyConnection) -> Crawler:
140:     return Crawler(
141:         queue=CrawlQueue(con),
142:         provider=YFinanceProvider(),
143:         budget=TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600),
144:         backoff=BackoffPolicy(),
145:         data_dir=config.data_dir(),
146:     )
147: 
148: 
149: def run_once(limit: int = 50) -> CrawlOutcome:
150:     con = _connect()
151:     try:
152:         crawler = _make_crawler(con)
153:         outcome = crawler.run_cycle(limit=limit)
154:         update_heartbeat(
155:             requests_last_hour=crawler.budget.used_in_window(),
156:             budget_per_hour=crawler.budget.capacity,
157:             last_cycle={"fetched": len(outcome.fetched), "failed": len(outcome.failed)},
158:             providers={crawler.provider.id: "healthy"},
159:             **_queue_stats(con),
160:             ts=time.time(),
161:         )
162:         return outcome
163:     finally:
164:         con.close()
165: 
166: 
167: ESEF_REFRESH_SECONDS = 90 * 24 * 3600
168: ESEF_SCHEMA = """
169: CREATE TABLE IF NOT EXISTS esef_tasks (
170:     symbol          VARCHAR PRIMARY KEY,
171:     lei             VARCHAR NOT NULL,
172:     last_fetched_at DOUBLE
173: )
174: """
175: 
176: 
177: def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
178:     """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
179:     an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
180:     figures pulled from filings.xbrl.org into provider='esef' raw statements.
181:     Outages are recorded and the cycle resumes next time; unmatched listings
182:     are counted, never errored."""
183:     from crible.providers.gleif import load_isin_lei_map, resolve_leis
184: 
185:     data = config.data_dir()
186:     outcome: dict = {"enriched": [], "unmatched": 0, "outage": None, "skipped": None}
187: 
188:     if mapping is None:
189:         mapping_file = next(
190:             (p for p in (data / "isin-lei.csv", data / "isin-lei.zip") if p.exists()), None
191:         )
192:         if mapping_file is None:
193:             outcome["skipped"] = (
194:                 "no GLEIF mapping file — download the ISIN-LEI relationship file to data/isin-lei.csv"
195:             )
196:             log.info("esef: %s", outcome["skipped"])
197:             return outcome
198:         try:
199:             mapping = load_isin_lei_map(mapping_file)
200:         except Exception as exc:  # noqa: BLE001 — treated as outage (FR-010 AC-2)
201:             outcome["outage"] = f"gleif mapping unreadable: {exc}"
202:             log.warning("esef: %s — resuming next cycle", outcome["outage"])
203:             return outcome
204: 
205:     con = _connect()
206:     try:
207:         con.execute(ESEF_SCHEMA)
208:         companies = [
209:             {"symbol": s, "isin": i}
210:             for s, i in con.execute(
211:                 "SELECT symbol, isin FROM companies WHERE region = 'europe' AND NOT delisted"
212:             ).fetchall()
213:         ]
214:         resolved, unmatched = resolve_leis(companies, mapping)
215:         outcome["unmatched"] = len(unmatched)
216:         # FR-010 AC-4: the unmatched-EU-listings metric is visible in status
217:         update_heartbeat(esef_unmatched=len(unmatched), esef_resolved=len(resolved))
218:         for symbol, lei in resolved.items():
219:             con.execute(
220:                 "INSERT INTO esef_tasks (symbol, lei) VALUES (?, ?) ON CONFLICT (symbol) DO NOTHING",
221:                 [symbol, lei],
222:             )
223:         due = con.execute(
224:             "SELECT symbol, lei FROM esef_tasks WHERE last_fetched_at IS NULL"
225:             " OR last_fetched_at < ? ORDER BY last_fetched_at NULLS FIRST LIMIT ?",
226:             [time.time() - ESEF_REFRESH_SECONDS, limit],
227:         ).fetchall()
228:         if not due:
229:             return outcome
230: 
231:         if client is None:
232:             from crible.providers.esef import EsefClient
233: 
234:             client = EsefClient()
235:         from crible.providers.esef import facts_to_frames
236:         from crible.ingest.raw import write_raw_statement
237: 
238:         for symbol, lei in due:
239:             try:
240:                 filings = client.filings_for_lei(lei)
241:                 if not filings:
242:                     con.execute(
243:                         "UPDATE esef_tasks SET last_fetched_at = ? WHERE symbol = ?",
244:                         [time.time(), symbol],
245:                     )
246:                     continue
247:                 xbrl = client.fetch_xbrl_json(filings[0])
248:                 frames = facts_to_frames(xbrl) if xbrl else {}
249:                 fetched_at = time.time()
250:                 for (statement_type, freq), frame in frames.items():
251:                     write_raw_statement(
252:                         data, symbol=symbol, provider="esef", statement_type=statement_type,
253:                         freq=freq, frame=frame, fetched_at=fetched_at,
254:                     )
255:                 con.execute(
256:                     "UPDATE esef_tasks SET last_fetched_at = ? WHERE symbol = ?",
257:                     [fetched_at, symbol],
258:                 )
259:                 if frames:
260:                     outcome["enriched"].append(symbol)
261:                     log.info("esef: enriched %s (%d statement frame(s)) from filing of LEI %s",
262:                              symbol, len(frames), lei)
263:             except Exception as exc:  # noqa: BLE001 — outage: record, resume next cycle
264:                 outcome["outage"] = f"{symbol}: {exc}"
265:                 log.warning("esef: outage on %s: %s — resuming next cycle", symbol, exc)
266:                 break
267:         return outcome
268:     finally:
269:         con.close()
270: 
271: 
272: def run_price_refresh(budget: TokenBucket, provider=None) -> dict:
273:     """FR-011 — daily price refresh for the priority set within the budget."""
274:     from crible.ingest.prices import PriceRefresher
275: 
276:     if provider is None:
277:         provider = _YfPriceAdapter()
278:     refresher = PriceRefresher(provider=provider, budget=budget, data_dir=config.data_dir())
279:     outcome = refresher.refresh(bootstrap_sample())
280:     return {"refreshed": len(outcome.refreshed), "skipped": len(outcome.skipped), "aborted": outcome.aborted}
281: 
282: 
283: class _YfPriceAdapter:
284:     id = "yfinance"
285: 
286:     def fetch_prices(self, symbol: str):
287:         import yfinance as yf
288: 
289:         from crible.providers.base import RateLimitedError
290:         from crible.providers.yfinance_provider import RATE_LIMIT_MARKERS
291: 
292:         try:
293:             bars = yf.Ticker(symbol).history(period="5d", auto_adjust=False)
294:         except Exception as exc:  # noqa: BLE001
295:             if any(m in str(exc).lower() for m in RATE_LIMIT_MARKERS):
296:                 raise RateLimitedError(str(exc)) from exc
297:             raise
298:         return bars.reset_index() if bars is not None and not bars.empty else None
299: 
300: 
301: def run_compute() -> int:
302:     data = config.data_dir()
303:     if not (data / "universe.parquet").exists() and config.database_path().exists():
304:         # self-heal installs bootstrapped before universe export existed
305:         con = _connect()
306:         try:
307:             from crible.universe import export_universe_parquet
308: 
309:             has = con.execute(
310:                 "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
311:             ).fetchone()[0]
312:             if has:
313:                 export_universe_parquet(con, data)
314:                 log.info("compute: exported missing universe.parquet")
315:         finally:
316:             con.close()
317:     snapshot = build_snapshot(data)
318:     if snapshot.empty:
319:         log.info("compute: no raw data yet — skipping publish")
320:         return 0
321:     publish_snapshot(snapshot, data)
322:     log.info("compute: published %d rows × %d columns", len(snapshot), len(snapshot.columns))
323:     return len(snapshot)
324: 
325: 
326: def run_loop(cycle_limit: int = 40, compute_every_seconds: float = 1800.0) -> None:  # pragma: no cover — long-lived loop
327:     # cycle_limit × ~7 requests must stay under the hourly budget so a cycle
328:     # never stalls mid-way on the token bucket before its compute runs
329:     con = _connect()
330:     has_universe = con.execute(
331:         "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
332:     ).fetchone()[0]
333:     con.close()
334:     if not has_universe:
335:         log.info("first boot — bootstrapping universe")
336:         run_bootstrap()
337: 
338:     first_cycle = not (config.data_dir() / "snapshot").exists()
339:     last_compute = 0.0
340:     last_price_refresh = 0.0
341:     price_budget = TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600)
342:     while True:
343:         # first boot: crawl exactly the bootstrap sample, then publish
344:         # immediately — a first screen must return rows within hours (FR-008)
345:         limit = max(10, len(bootstrap_sample())) if first_cycle else cycle_limit
346:         outcome = run_once(limit=limit)
347:         first_cycle = False
348:         now = time.time()
349: 
350:         # FR-011: daily priority-tier price refresh (shares the request budget)
351:         if now - last_price_refresh >= 20 * 3600:
352:             try:
353:                 log.info("price refresh: %s", run_price_refresh(price_budget))
354:             except Exception as exc:  # noqa: BLE001 — never kills the loop
355:                 log.warning("price refresh failed: %s", exc)
356:             last_price_refresh = now
357: 
358:         # FR-010: audited ESEF enrichment (keyless; idle without a GLEIF file)
359:         try:
360:             esef = run_esef_cycle()
361:             if esef["enriched"] or esef["outage"]:
362:                 log.info("esef cycle: %s", esef)
363:         except Exception as exc:  # noqa: BLE001
364:             log.warning("esef cycle failed: %s", exc)
365: 
366:         if outcome.fetched or now - last_compute >= compute_every_seconds:
367:             run_compute()
368:             last_compute = now
369:         if not outcome.fetched and not outcome.failed:
370:             time.sleep(60)  # queue empty or nothing due — idle politely
371: 
```
**Verdict:** ______  ·  **Note:** ______

## F2 · run:analysis.json
**Finding:** Toujours ouvert (porté du run de base, décision « coût > valeur immédiate » documentée dans PRIORITIES) : le service d'ingestion orchestre queue, budget, backoff, crawler, prix et heartbeat dans un seul module de 370 LOC avec une profondeur d'imbrication de 14 — le pire hotspot du dépôt à l'analyse déterministe.
```
{
  "target": "/Users/maxime/Downloads/crible",
  "files": 78,
  "loc": 6905,
  "languages": {
    ".py": 55,
    ".tsx": 15,
    ".ts": 8
  },
  "hotspots": [
    {
      "path": "src/crible/ingest/service.py",
```
**Verdict:** ______  ·  **Note:** ______

## F11 · tests/test_fr015_ranks.py:128-141
**Finding:** FR-015 est livré (composite_rank + piliers, preset Top ranked, décomposition dans le drawer) mais la grille par défaut n'affiche pas composite_rank et le README ne documente pas la formule du blend — or la transparence du rang est l'argument face aux StockRanks propriétaires ([S21]).
```
126: 
127: 
128: def test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint() -> None:
129:     """The shipped top-ranked preset must not strand a pre-FR-015 snapshot on
130:     « no similar field exists » — the error says HOW to get the column."""
131:     import pytest
132: 
133:     from crible.dsl.parser import DslError
134: 
135:     con = duckdb.connect()
136:     con.register("snapshot_latest", pd.DataFrame({"symbol": ["A"], "piotroski_f": [8]}))
137:     whitelist = whitelist_from_relation(con, "snapshot_latest")
138:     with pytest.raises(DslError) as err:
139:         screen(con, "composite_rank >= 80", whitelist=whitelist, limit=10, offset=0)
140:     assert "crible compute" in str(err.value)
141: 
142: 
143: def test_fr015_top_ranked_preset_ships() -> None:
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/presets.py:52-57
**Finding:** Le preset livré `composite_rank >= 80` référence une colonne qui n'existe que dans les snapshots recalculés après l'upgrade FR-015. Sur une installation existante (snapshot pré-upgrade), la whitelist dérivée de snapshot_latest ne contient pas la colonne et le DSL levait « unknown field 'composite_rank' … no similar field exists » — un preset livré ne doit jamais échouer sans expliquer le remède. Reproduit puis corrigé dans ce cycle : les colonnes build-time portent désormais un hint « recompute the snapshot (`crible compute`) after upgrading » (commit b97193e, test test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint).
```
50:         dsl="return_on_equity > 0.15 AND debt_to_equity_ratio < 1",
51:     ),
52:     Preset(
53:         id="top-ranked",
54:         name="Top ranked",
55:         description="Top quintile of the composite quality/value/momentum rank (FR-015)",
56:         dsl="composite_rank >= 80",
57:     ),
58: ]
59: 
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/store.py:42-44
**Finding:** Le preset livré `composite_rank >= 80` référence une colonne qui n'existe que dans les snapshots recalculés après l'upgrade FR-015. Sur une installation existante (snapshot pré-upgrade), la whitelist dérivée de snapshot_latest ne contient pas la colonne et le DSL levait « unknown field 'composite_rank' … no similar field exists » — un preset livré ne doit jamais échouer sans expliquer le remède. Reproduit puis corrigé dans ce cycle : les colonnes build-time portent désormais un hint « recompute the snapshot (`crible compute`) after upgrading » (commit b97193e, test test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint).
```
40: 
41: 
42: def whitelist_from_relation(con: duckdb.DuckDBPyConnection, relation: str = "snapshot_latest") -> set[str]:
43:     rows = con.execute(f"DESCRIBE {relation}").fetchall()
44:     return {r[0] for r in rows}
45: 
```
**Verdict:** ______  ·  **Note:** ______

## F12 · src/crible/compute/ranks.py:91-122
**Finding:** Le preset livré `composite_rank >= 80` référence une colonne qui n'existe que dans les snapshots recalculés après l'upgrade FR-015. Sur une installation existante (snapshot pré-upgrade), la whitelist dérivée de snapshot_latest ne contient pas la colonne et le DSL levait « unknown field 'composite_rank' … no similar field exists » — un preset livré ne doit jamais échouer sans expliquer le remède. Reproduit puis corrigé dans ce cycle : les colonnes build-time portent désormais un hint « recompute the snapshot (`crible compute`) after upgrading » (commit b97193e, test test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint).
```
89: 
90: 
91: def attach_ranks(snapshot: pd.DataFrame) -> pd.DataFrame:
92:     """Attach FR-015 rank columns to the latest period row of each symbol."""
93:     if snapshot.empty or "symbol" not in snapshot.columns:
94:         return snapshot
95:     snapshot = snapshot.reset_index(drop=True)
96:     for col in RANK_COLUMNS:
97:         snapshot[col] = float("nan")
98:     snapshot["rank_peer_group"] = None
99:     snapshot["rank_missing_pillars"] = None
100: 
101:     period = snapshot["period"] if "period" in snapshot.columns else pd.Series("", index=snapshot.index)
102:     latest_idx = (
103:         snapshot.assign(_period=period.astype(str))
104:         .sort_values("_period")
105:         .groupby("symbol", sort=False)
106:         .tail(1)
107:         .index
108:     )
109:     latest = snapshot.loc[latest_idx]
110: 
111:     region = latest["region"] if "region" in latest.columns else pd.Series(None, index=latest.index)
112:     sector = latest["sector"] if "sector" in latest.columns else pd.Series(None, index=latest.index)
113:     pair = region.astype("string").str.cat(sector.astype("string"), sep="×")
114:     sizes = pair.groupby(pair).transform("size")
115:     group_key = pair.where(pair.notna() & (sizes >= MIN_PEERS), "global")
116: 
117:     for key, members in latest.groupby(group_key, sort=False):
118:         ranks = _rank_group(members)
119:         for col in ranks.columns:
120:             snapshot.loc[members.index, col] = ranks[col]
121:         snapshot.loc[members.index, "rank_peer_group"] = key
122:     return snapshot
123: 
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/dsl/compiler.py:18-31
**Finding:** Le preset livré `composite_rank >= 80` référence une colonne qui n'existe que dans les snapshots recalculés après l'upgrade FR-015. Sur une installation existante (snapshot pré-upgrade), la whitelist dérivée de snapshot_latest ne contient pas la colonne et le DSL levait « unknown field 'composite_rank' … no similar field exists » — un preset livré ne doit jamais échouer sans expliquer le remède. Reproduit puis corrigé dans ce cycle : les colonnes build-time portent désormais un hint « recompute the snapshot (`crible compute`) after upgrading » (commit b97193e, test test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint).
```
16: OPERATORS = {">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=", "==": "=", "!=": "<>", "<>": "<>"}
17: 
18: # FR-015 columns exist only in snapshots computed after the upgrade — the
19: # remedy is a recompute, not a spelling fix.
20: BUILD_TIME_COLUMNS = set(RANK_COLUMNS) | {"rank_peer_group", "rank_missing_pillars", "return_6m"}
21: BUILD_TIME_REMEDY = (
22:     "added at snapshot build time (FR-015) — recompute the snapshot"
23:     " (`crible compute`) after upgrading"
24: )
25: 
26: 
27: def _check_field(field: str, whitelist: set[str], position: int) -> str:
28:     if field in whitelist:
29:         return field
30:     if field in BUILD_TIME_COLUMNS:
31:         raise DslError(f"unknown field {field!r} at position {position}", position=position, hint=BUILD_TIME_REMEDY)
32:     closest = difflib.get_close_matches(field, sorted(whitelist), n=1)
33:     hint = f"did you mean {closest[0]!r}?" if closest else "no similar field exists"
```
**Verdict:** ______  ·  **Note:** ______

## F13 · src/crible/compute/ranks.py:91-122
**Finding:** Le preset livré `composite_rank >= 80` référence une colonne qui n'existe que dans les snapshots recalculés après l'upgrade FR-015. Sur une installation existante (snapshot pré-upgrade), la whitelist dérivée de snapshot_latest ne contient pas la colonne et le DSL levait « unknown field 'composite_rank' … no similar field exists » — un preset livré ne doit jamais échouer sans expliquer le remède. Reproduit puis corrigé dans ce cycle : les colonnes build-time portent désormais un hint « recompute the snapshot (`crible compute`) after upgrading » (commit b97193e, test test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint).
```
89: 
90: 
91: def attach_ranks(snapshot: pd.DataFrame) -> pd.DataFrame:
92:     """Attach FR-015 rank columns to the latest period row of each symbol."""
93:     if snapshot.empty or "symbol" not in snapshot.columns:
94:         return snapshot
95:     snapshot = snapshot.reset_index(drop=True)
96:     for col in RANK_COLUMNS:
97:         snapshot[col] = float("nan")
98:     snapshot["rank_peer_group"] = None
99:     snapshot["rank_missing_pillars"] = None
100: 
101:     period = snapshot["period"] if "period" in snapshot.columns else pd.Series("", index=snapshot.index)
102:     latest_idx = (
103:         snapshot.assign(_period=period.astype(str))
104:         .sort_values("_period")
105:         .groupby("symbol", sort=False)
106:         .tail(1)
107:         .index
108:     )
109:     latest = snapshot.loc[latest_idx]
110: 
111:     region = latest["region"] if "region" in latest.columns else pd.Series(None, index=latest.index)
112:     sector = latest["sector"] if "sector" in latest.columns else pd.Series(None, index=latest.index)
113:     pair = region.astype("string").str.cat(sector.astype("string"), sep="×")
114:     sizes = pair.groupby(pair).transform("size")
115:     group_key = pair.where(pair.notna() & (sizes >= MIN_PEERS), "global")
116: 
117:     for key, members in latest.groupby(group_key, sort=False):
118:         ranks = _rank_group(members)
119:         for col in ranks.columns:
120:             snapshot.loc[members.index, col] = ranks[col]
121:         snapshot.loc[members.index, "rank_peer_group"] = key
122:     return snapshot
123: 
```
**Verdict:** ______  ·  **Note:** ______

## F8 · tests/test_fr015_ranks.py:128-141
**Finding:** Le preset livré `composite_rank >= 80` référence une colonne qui n'existe que dans les snapshots recalculés après l'upgrade FR-015. Sur une installation existante (snapshot pré-upgrade), la whitelist dérivée de snapshot_latest ne contient pas la colonne et le DSL levait « unknown field 'composite_rank' … no similar field exists » — un preset livré ne doit jamais échouer sans expliquer le remède. Reproduit puis corrigé dans ce cycle : les colonnes build-time portent désormais un hint « recompute the snapshot (`crible compute`) after upgrading » (commit b97193e, test test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint).
```
126: 
127: 
128: def test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint() -> None:
129:     """The shipped top-ranked preset must not strand a pre-FR-015 snapshot on
130:     « no similar field exists » — the error says HOW to get the column."""
131:     import pytest
132: 
133:     from crible.dsl.parser import DslError
134: 
135:     con = duckdb.connect()
136:     con.register("snapshot_latest", pd.DataFrame({"symbol": ["A"], "piotroski_f": [8]}))
137:     whitelist = whitelist_from_relation(con, "snapshot_latest")
138:     with pytest.raises(DslError) as err:
139:         screen(con, "composite_rank >= 80", whitelist=whitelist, limit=10, offset=0)
140:     assert "crible compute" in str(err.value)
141: 
142: 
143: def test_fr015_top_ranked_preset_ships() -> None:
```
**Verdict:** ______  ·  **Note:** ______

## F9 · ui/src/App.tsx:29-33
**Finding:** FR-015 est livré (composite_rank + piliers, preset Top ranked, décomposition dans le drawer) mais la grille par défaut n'affiche pas composite_rank et le README ne documente pas la formule du blend — or la transparence du rang est l'argument face aux StockRanks propriétaires ([S21]).
```
27: import { applyTheme, loadTheme, saveTheme, toggled } from "./theme";
28: 
29: const DEFAULT_COLUMNS = [
30:   "symbol", "name", "country", "sector",
31:   "piotroski_f", "altman_z", "beneish_m",
32:   "return_on_equity", "net_profit_margin", "debt_to_equity_ratio",
33: ];
34: const DEFAULT_QUERY = "piotroski_f >= 7";
35: 
```
**Verdict:** ______  ·  **Note:** ______

## F9 · docs/market/2026-07-12/REPORT.md:5
**Finding:** FR-015 est livré (composite_rank + piliers, preset Top ranked, décomposition dans le drawer) mais la grille par défaut n'affiche pas composite_rank et le README ne documente pas la formule du blend — or la transparence du rang est l'argument face aux StockRanks propriétaires ([S21]).
```
3: ## Executive summary
4: 
5: crible occupe un créneau qu'aucun acteur identifié ne sert : le screening fondamental full-univers, self-hosted, sans clé API ni abonnement. Le marché se partage entre SaaS fondamentaux payants — Stockopedia à €550/an (Europe) ou €725/an (US+Europe) [S21], TIKR (données S&P CapitalIQ, 100 000+ actions, ~20 ans d'historique) [S26], Simply Wall St (freemium, 6 M d'utilisateurs revendiqués) [S25][S11], Portfolio123 (backtesting/gestion de stratégies) [S12] — et un écosystème open-source qui fait du *tracking* (Ghostfolio [S4][S8]) ou du *terminal* (OpenBB, 70.5k★/7.1k forks [S23][S9]), pas du screening fondamental packagé. La demande self-host est réelle et non répondue [S23] ; le canal de distribution naturel (awesome-selfhosted) n'a aucun screener dans sa catégorie Money [S24].
6: 
7: ## Problem & customer
```
**Verdict:** ______  ·  **Note:** ______

## F10 · src/crible/compute/ranks.py:91-122
**Finding:** Les rangs FR-015 sont calculés côté write (attach_ranks sur ~161k lignes, groupby percentile). Le chemin de lecture est benchmarké (p95 < 1s, inchangé) mais le surcoût de build n'a pas de garde-fou chiffré — une régression du compute passerait inaperçue jusqu'au crawl suivant.
```
89: 
90: 
91: def attach_ranks(snapshot: pd.DataFrame) -> pd.DataFrame:
92:     """Attach FR-015 rank columns to the latest period row of each symbol."""
93:     if snapshot.empty or "symbol" not in snapshot.columns:
94:         return snapshot
95:     snapshot = snapshot.reset_index(drop=True)
96:     for col in RANK_COLUMNS:
97:         snapshot[col] = float("nan")
98:     snapshot["rank_peer_group"] = None
99:     snapshot["rank_missing_pillars"] = None
100: 
101:     period = snapshot["period"] if "period" in snapshot.columns else pd.Series("", index=snapshot.index)
102:     latest_idx = (
103:         snapshot.assign(_period=period.astype(str))
104:         .sort_values("_period")
105:         .groupby("symbol", sort=False)
106:         .tail(1)
107:         .index
108:     )
109:     latest = snapshot.loc[latest_idx]
110: 
111:     region = latest["region"] if "region" in latest.columns else pd.Series(None, index=latest.index)
112:     sector = latest["sector"] if "sector" in latest.columns else pd.Series(None, index=latest.index)
113:     pair = region.astype("string").str.cat(sector.astype("string"), sep="×")
114:     sizes = pair.groupby(pair).transform("size")
115:     group_key = pair.where(pair.notna() & (sizes >= MIN_PEERS), "global")
116: 
117:     for key, members in latest.groupby(group_key, sort=False):
118:         ranks = _rank_group(members)
119:         for col in ranks.columns:
120:             snapshot.loc[members.index, col] = ranks[col]
121:         snapshot.loc[members.index, "rank_peer_group"] = key
122:     return snapshot
123: 
```
**Verdict:** ______  ·  **Note:** ______

## F10 · tests/test_nfr008_benchmark.py:57-65
**Finding:** Les rangs FR-015 sont calculés côté write (attach_ranks sur ~161k lignes, groupby percentile). Le chemin de lecture est benchmarké (p95 < 1s, inchangé) mais le surcoût de build n'a pas de garde-fou chiffré — une régression du compute passerait inaperçue jusqu'au crawl suivant.
```
55: 
56: def p95(samples: list[float]) -> float:
57:     ordered = sorted(samples)
58:     return ordered[max(0, int(len(ordered) * 0.95) - 1)]
59: 
60: 
61: def test_nfr008_every_preset_screens_the_full_universe_under_1s(con) -> None:
62:     whitelist = whitelist_from_relation(con, "snapshot_latest")
63:     for preset in PRESETS.values():
64:         timings = []
65:         for _ in range(5):
66:             started = time.perf_counter()
67:             screen(con, preset.dsl, whitelist=whitelist, sort="-piotroski_f", limit=100, offset=0)
```
**Verdict:** ______  ·  **Note:** ______

