# Verification worklist

For each pair: read the digest, judge whether it SUPPORTS the finding, write a verdict.
Verdicts: `supported` · `partial` · `refuted` · `unsupported`.

## F1 · src/crible/ingest/service.py:788
**Finding:** The shipped self-hosted service runs `crible ingest --loop` (docker-compose.yml:8) → run_loop, which calls run_once once per cycle (service.py:788). run_once builds a FRESH crawler with a FRESH TokenBucket every call (service.py:187 → _make_crawler service.py:178). TokenBucket state is per-instance (budget.py:28), so each cycle starts with a full 330-token budget. With cycle_limit=40 and yfinance requests_per_fetch=7 (yfinance_provider.py:31), one cycle spends 280 < 330 and never throttles, then returns and the loop immediately starts another full-budget cycle (no inter-cycle sleep unless the queue is drained, service.py:819-820). Steady-state crawl therefore issues far more than 330 requests/rolling-hour. run_refresh's own docstring documents exactly this hazard and fixes it by sharing ONE bucket across cycles (service.py:678-680, crawler built once service.py:707) — run_loop never received that fix. budget.py:3-5 calls staying under budget 'a hard constraint of the keyless design, not an optimisation' (NFR-007).
```
786:         # immediately — a first screen must return rows within hours (FR-008)
787:         limit = max(10, len(bootstrap_sample())) if first_cycle else cycle_limit
788:         outcome = run_once(limit=limit)
789:         first_cycle = False
790:         now = time.time()
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/ingest/service.py:184-199
**Finding:** The shipped self-hosted service runs `crible ingest --loop` (docker-compose.yml:8) → run_loop, which calls run_once once per cycle (service.py:788). run_once builds a FRESH crawler with a FRESH TokenBucket every call (service.py:187 → _make_crawler service.py:178). TokenBucket state is per-instance (budget.py:28), so each cycle starts with a full 330-token budget. With cycle_limit=40 and yfinance requests_per_fetch=7 (yfinance_provider.py:31), one cycle spends 280 < 330 and never throttles, then returns and the loop immediately starts another full-budget cycle (no inter-cycle sleep unless the queue is drained, service.py:819-820). Steady-state crawl therefore issues far more than 330 requests/rolling-hour. run_refresh's own docstring documents exactly this hazard and fixes it by sharing ONE bucket across cycles (service.py:678-680, crawler built once service.py:707) — run_loop never received that fix. budget.py:3-5 calls staying under budget 'a hard constraint of the keyless design, not an optimisation' (NFR-007).
```
182: 
183: 
184: def run_once(limit: int = 50) -> CrawlOutcome:
185:     con = _connect()
186:     try:
187:         crawler = _make_crawler(con)
188:         outcome = crawler.run_cycle(limit=limit)
189:         update_heartbeat(
190:             requests_last_hour=crawler.budget.used_in_window(),
191:             budget_per_hour=crawler.budget.capacity,
192:             last_cycle={"fetched": len(outcome.fetched), "failed": len(outcome.failed)},
193:             providers={crawler.provider.id: "healthy"},
194:             **_queue_stats(con),
195:             ts=time.time(),
196:         )
197:         return outcome
198:     finally:
199:         con.close()
200: 
201: 
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/ingest/service.py:174-181
**Finding:** The shipped self-hosted service runs `crible ingest --loop` (docker-compose.yml:8) → run_loop, which calls run_once once per cycle (service.py:788). run_once builds a FRESH crawler with a FRESH TokenBucket every call (service.py:187 → _make_crawler service.py:178). TokenBucket state is per-instance (budget.py:28), so each cycle starts with a full 330-token budget. With cycle_limit=40 and yfinance requests_per_fetch=7 (yfinance_provider.py:31), one cycle spends 280 < 330 and never throttles, then returns and the loop immediately starts another full-budget cycle (no inter-cycle sleep unless the queue is drained, service.py:819-820). Steady-state crawl therefore issues far more than 330 requests/rolling-hour. run_refresh's own docstring documents exactly this hazard and fixes it by sharing ONE bucket across cycles (service.py:678-680, crawler built once service.py:707) — run_loop never received that fix. budget.py:3-5 calls staying under budget 'a hard constraint of the keyless design, not an optimisation' (NFR-007).
```
172: 
173: 
174: def _make_crawler(con: duckdb.DuckDBPyConnection, provider=None) -> Crawler:
175:     return Crawler(
176:         queue=CrawlQueue(con),
177:         provider=provider if provider is not None else YFinanceProvider(),
178:         budget=TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600),
179:         backoff=BackoffPolicy(),
180:         data_dir=config.data_dir(),
181:     )
182: 
183: 
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/ingest/service.py:678-680
**Finding:** The shipped self-hosted service runs `crible ingest --loop` (docker-compose.yml:8) → run_loop, which calls run_once once per cycle (service.py:788). run_once builds a FRESH crawler with a FRESH TokenBucket every call (service.py:187 → _make_crawler service.py:178). TokenBucket state is per-instance (budget.py:28), so each cycle starts with a full 330-token budget. With cycle_limit=40 and yfinance requests_per_fetch=7 (yfinance_provider.py:31), one cycle spends 280 < 330 and never throttles, then returns and the loop immediately starts another full-budget cycle (no inter-cycle sleep unless the queue is drained, service.py:819-820). Steady-state crawl therefore issues far more than 330 requests/rolling-hour. run_refresh's own docstring documents exactly this hazard and fixes it by sharing ONE bucket across cycles (service.py:678-680, crawler built once service.py:707) — run_loop never received that fix. budget.py:3-5 calls staying under budget 'a hard constraint of the keyless design, not an optimisation' (NFR-007).
```
676:     Bootstrap (falling back to the last-good universe.parquet when
677:     FinanceDatabase is down) → prioritized crawl on ONE shared token bucket
678:     until the queue drains or the deadline passes (repeated ``ingest --once``
679:     calls would each get a fresh bucket and bust the hourly budget) → ESEF +
680:     EDGAR enrichment → price refresh → prune the raw layer → compute + publish.
681:     """
682:     from crible.ingest.raw import prune_raw
```
**Verdict:** ______  ·  **Note:** ______

## F1 · src/crible/ingest/budget.py:35-43
**Finding:** The shipped self-hosted service runs `crible ingest --loop` (docker-compose.yml:8) → run_loop, which calls run_once once per cycle (service.py:788). run_once builds a FRESH crawler with a FRESH TokenBucket every call (service.py:187 → _make_crawler service.py:178). TokenBucket state is per-instance (budget.py:28), so each cycle starts with a full 330-token budget. With cycle_limit=40 and yfinance requests_per_fetch=7 (yfinance_provider.py:31), one cycle spends 280 < 330 and never throttles, then returns and the loop immediately starts another full-budget cycle (no inter-cycle sleep unless the queue is drained, service.py:819-820). Steady-state crawl therefore issues far more than 330 requests/rolling-hour. run_refresh's own docstring documents exactly this hazard and fixes it by sharing ONE bucket across cycles (service.py:678-680, crawler built once service.py:707) — run_loop never received that fix. budget.py:3-5 calls staying under budget 'a hard constraint of the keyless design, not an optimisation' (NFR-007).
```
33:             self._stamps.popleft()
34: 
35:     def try_acquire(self, n: int = 1) -> bool:
36:         """Atomically reserve ``n`` upstream requests (all or nothing)."""
37:         self._evict()
38:         if len(self._stamps) + n > self.capacity:
39:             return False
40:         stamp = self._now()
41:         for _ in range(n):
42:             self._stamps.append(stamp)
43:         return True
44: 
45:     def seconds_until_available(self) -> float:
```
**Verdict:** ______  ·  **Note:** ______

## F1 · docker-compose.yml:8
**Finding:** The shipped self-hosted service runs `crible ingest --loop` (docker-compose.yml:8) → run_loop, which calls run_once once per cycle (service.py:788). run_once builds a FRESH crawler with a FRESH TokenBucket every call (service.py:187 → _make_crawler service.py:178). TokenBucket state is per-instance (budget.py:28), so each cycle starts with a full 330-token budget. With cycle_limit=40 and yfinance requests_per_fetch=7 (yfinance_provider.py:31), one cycle spends 280 < 330 and never throttles, then returns and the loop immediately starts another full-budget cycle (no inter-cycle sleep unless the queue is drained, service.py:819-820). Steady-state crawl therefore issues far more than 330 requests/rolling-hour. run_refresh's own docstring documents exactly this hazard and fixes it by sharing ONE bucket across cycles (service.py:678-680, crawler built once service.py:707) — run_loop never received that fix. budget.py:3-5 calls staying under budget 'a hard constraint of the keyless design, not an optimisation' (NFR-007).
```
6:     image: ghcr.io/maxgfr/crible:latest
7:     build: .
8:     command: ["crible", "ingest", "--loop"]
9:     volumes:
10:       - crible-data:/data
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/ingest/crawler.py:60-70
**Finding:** Crawler.crawl_symbol calls provider.fetch_statements(symbol) with no hard timeout (crawler.py:70); there is no signal/thread-join/ThreadPoolExecutor timeout anywhere in ingest/ or providers/. Yet prices.py:6-7 says hangs are 'enforced by the crawler's watchdog' and yfinance_provider.py:6 says 'a per-call watchdog is the crawler's job, not ours' — both delegate hang-protection to a watchdog that was never implemented (ADR-0004 promised it per TODO.md:17-22). yfinance owns its own session and has documented hang cases; a single stuck socket blocks the entire single-threaded run_loop indefinitely with no reschedule.
```
58:             self.sleep(wait)
59: 
60:     def crawl_symbol(self, symbol: str) -> bool:
61:         """Fetch one symbol with in-place backoff on 429. True on success.
62: 
63:         The budget is charged with the provider's per-fetch request estimate
64:         BEFORE fetching: every upstream call counts (NFR-007), not every symbol.
65:         """
66:         cost = getattr(self.provider, "requests_per_fetch", 1)
67:         for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
68:             self._acquire_budget(cost)
69:             try:
70:                 result = self.provider.fetch_statements(symbol)
71:             except RateLimitedError as exc:
72:                 delay = self.backoff.delay(attempt)
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/providers/yfinance_provider.py:6
**Finding:** Crawler.crawl_symbol calls provider.fetch_statements(symbol) with no hard timeout (crawler.py:70); there is no signal/thread-join/ThreadPoolExecutor timeout anywhere in ingest/ or providers/. Yet prices.py:6-7 says hangs are 'enforced by the crawler's watchdog' and yfinance_provider.py:6 says 'a per-call watchdog is the crawler's job, not ours' — both delegate hang-protection to a watchdog that was never implemented (ADR-0004 promised it per TODO.md:17-22). yfinance owns its own session and has documented hang cases; a single stuck socket blocks the entire single-threaded run_loop indefinitely with no reschedule.
```
4: session); Yahoo depth is ~4 annual periods / 4-5 quarters. Rate-limit errors
5: are normalised to RateLimitedError so the crawler can back off; a per-call
6: watchdog is the crawler's job, not ours.
7: """
8: 
```
**Verdict:** ______  ·  **Note:** ______

## F14 · src/crible/ingest/service.py:653
**Finding:** Two distinct IFRS concepts map to the same canonical column (Revenue and RevenueFromContractsWithCustomers → TotalRevenue, esef.py:23-24; ProfitLoss and ProfitLossAttributableToOwnersOfParent → NetIncome, esef.py:27-28). facts_to_frames writes them with last-writer-wins keyed only by (year,column) (esef.py:71), so which concept survives depends on JSON iteration order. For consolidated statements ProfitLoss (group total) and the owners-of-parent figure differ materially (minority interests), yielding a non-deterministic audited NetIncome.
```
651:         finally:
652:             con.close()
653:     snapshot = build_snapshot(data)
654:     if snapshot.empty:
655:         log.info("compute: no raw data yet — skipping publish")
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/ingest/prices.py:6-7
**Finding:** Crawler.crawl_symbol calls provider.fetch_statements(symbol) with no hard timeout (crawler.py:70); there is no signal/thread-join/ThreadPoolExecutor timeout anywhere in ingest/ or providers/. Yet prices.py:6-7 says hangs are 'enforced by the crawler's watchdog' and yfinance_provider.py:6 says 'a per-call watchdog is the crawler's job, not ours' — both delegate hang-protection to a watchdog that was never implemented (ADR-0004 promised it per TODO.md:17-22). yfinance owns its own session and has documented hang cases; a single stuck socket blocks the entire single-threaded run_loop indefinitely with no reschedule.
```
4: source in the keyless core (no redistributable bulk price feed exists).
5: The priority set gets daily refreshes; everything else rides leftover
6: budget. Switch rule: 3 consecutive rate-limit failures (or a hang,
7: enforced by the crawler's watchdog) end the cycle politely — symbols keep
8: their last price, staleness stays visible via price_asof.
9: """
```
**Verdict:** ______  ·  **Note:** ______

## F2 · TODO.md:17-22
**Finding:** Crawler.crawl_symbol calls provider.fetch_statements(symbol) with no hard timeout (crawler.py:70); there is no signal/thread-join/ThreadPoolExecutor timeout anywhere in ingest/ or providers/. Yet prices.py:6-7 says hangs are 'enforced by the crawler's watchdog' and yfinance_provider.py:6 says 'a per-call watchdog is the crawler's job, not ours' — both delegate hang-protection to a watchdog that was never implemented (ADR-0004 promised it per TODO.md:17-22). yfinance owns its own session and has documented hang cases; a single stuck socket blocks the entire single-threaded run_loop indefinitely with no reschedule.
```
15:   (télécharge le fichier de relations GLEIF le plus récent → `data/isin-lei.csv`).
16: 
17: - [ ] **Watchdog anti-hang par requête dans le crawler.**
18:   L'ADR-0004 promet un watchdog ; aujourd'hui on s'appuie sur les timeouts internes de
19:   yfinance. Des pulls peuvent pendre (issues documentées). Envelopper `fetch_statements`
20:   dans un timeout dur (thread + `.join(timeout)` ou signal), traiter comme un échec →
21:   reschedule.
22: 
23: - [ ] **Refresh périodique de l'univers.**
24:   FinanceDatabase n'est téléchargé qu'au premier boot ; `delisted` et les nouvelles
```
**Verdict:** ______  ·  **Note:** ______

## F2 · src/crible/providers/yfinance_provider.py:36-58
**Finding:** Crawler.crawl_symbol calls provider.fetch_statements(symbol) with no hard timeout (crawler.py:70); there is no signal/thread-join/ThreadPoolExecutor timeout anywhere in ingest/ or providers/. Yet prices.py:6-7 says hangs are 'enforced by the crawler's watchdog' and yfinance_provider.py:6 says 'a per-call watchdog is the crawler's job, not ours' — both delegate hang-protection to a watchdog that was never implemented (ADR-0004 promised it per TODO.md:17-22). yfinance owns its own session and has documented hang cases; a single stuck socket blocks the entire single-threaded run_loop indefinitely with no reschedule.
```
34:         return True
35: 
36:     def fetch_statements(self, symbol: str) -> FetchResult:
37:         import yfinance as yf
38: 
39:         try:
40:             ticker = yf.Ticker(symbol)
41:             statements: list[StatementPayload] = []
42:             getters = {
43:                 "income": ticker.get_income_stmt,
44:                 "balance": ticker.get_balance_sheet,
45:                 "cashflow": ticker.get_cash_flow,
46:             }
47:             for statement_type, getter in getters.items():
48:                 for freq in ("yearly", "quarterly"):
49:                     frame = _normalise(getter(freq=freq))
50:                     if frame is not None:
51:                         statements.append(
52:                             StatementPayload(
53:                                 statement_type=statement_type,
54:                                 freq="annual" if freq == "yearly" else "quarterly",
55:                                 frame=frame,
56:                             )
57:                         )
58:             prices = ticker.history(period="1y", auto_adjust=False)
59:             prices = prices.reset_index() if prices is not None and not prices.empty else None
60:         except Exception as exc:  # noqa: BLE001 — classify then re-raise
```
**Verdict:** ______  ·  **Note:** ______

## F5 · src/crible/ingest/service.py:776-778
**Finding:** refresh_universe already exists (universe.py:213) and the nightly run_refresh calls it (service.py:697), but the long-lived Docker service (docker-compose command `crible ingest --loop`) only bootstraps on first boot (service.py:776-778) and never refreshes again. A self-hoster's delisted flags and new listings freeze forever. The upsert is already idempotent, so this is a scheduler, not new logic.
```
774:     ).fetchone()[0]
775:     con.close()
776:     if not has_universe:
777:         log.info("first boot — bootstrapping universe")
778:         run_bootstrap()
779: 
780:     first_cycle = not (config.data_dir() / "snapshot").exists()
```
**Verdict:** ______  ·  **Note:** ______

## F5 · src/crible/universe.py:213-224
**Finding:** refresh_universe already exists (universe.py:213) and the nightly run_refresh calls it (service.py:697), but the long-lived Docker service (docker-compose command `crible ingest --loop`) only bootstraps on first boot (service.py:776-778) and never refreshes again. A self-hoster's delisted flags and new listings freeze forever. The upsert is already idempotent, so this is a scheduler, not new logic.
```
211: 
212: 
213: def refresh_universe(
214:     con: duckdb.DuckDBPyConnection,
215:     fetch: Callable[[], pd.DataFrame] = fetch_financedatabase,
216: ) -> BootstrapReport:
217:     """Fetch + bootstrap; a fetch failure never touches the existing table."""
218:     try:
219:         frame = fetch()
220:     except UniverseSourceError:
221:         raise
222:     except Exception as exc:  # noqa: BLE001
223:         raise UniverseSourceError(f"FinanceDatabase source unreachable: {exc}") from exc
224:     return bootstrap_universe(con, frame)
225: 
```
**Verdict:** ______  ·  **Note:** ______

## F5 · docker-compose.yml:8
**Finding:** refresh_universe already exists (universe.py:213) and the nightly run_refresh calls it (service.py:697), but the long-lived Docker service (docker-compose command `crible ingest --loop`) only bootstraps on first boot (service.py:776-778) and never refreshes again. A self-hoster's delisted flags and new listings freeze forever. The upsert is already idempotent, so this is a scheduler, not new logic.
```
6:     image: ghcr.io/maxgfr/crible:latest
7:     build: .
8:     command: ["crible", "ingest", "--loop"]
9:     volumes:
10:       - crible-data:/data
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/providers/gleif.py:21
**Finding:** The whole ESEF audited-EU enrichment (run_esef_sweep/run_esef_cycle) is wired but stays idle out-of-the-box: it needs data/isin-lei.csv and nothing downloads it. gleif.py:21 defines ISIN_LEI_LATEST_URL but it is never referenced (dead constant); service.py:229 tells the operator to fetch the ~200 MB file by hand. A self-hoster gets zero audited EU coverage until they discover this. The research doc confirms GLEIF publishes the ISIN↔LEI relationship files as keyless open data ([S12][S53]).
```
19: # download-isin-to-lei-relationship-files ; the actual file URL is dated and
20: # resolved at download time. Kept as a constant so the operator can override.
21: ISIN_LEI_LATEST_URL = "https://mapping.gleif.org/api/v2/isin-lei/latest/download"
22: 
23: 
```
**Verdict:** ______  ·  **Note:** ______

## F6 · src/crible/ingest/service.py:227-232
**Finding:** The whole ESEF audited-EU enrichment (run_esef_sweep/run_esef_cycle) is wired but stays idle out-of-the-box: it needs data/isin-lei.csv and nothing downloads it. gleif.py:21 defines ISIN_LEI_LATEST_URL but it is never referenced (dead constant); service.py:229 tells the operator to fetch the ~200 MB file by hand. A self-hoster gets zero audited EU coverage until they discover this. The research doc confirms GLEIF publishes the ISIN↔LEI relationship files as keyless open data ([S12][S53]).
```
225:             (p for p in (data / "isin-lei.csv", data / "isin-lei.zip") if p.exists()), None
226:         )
227:         if mapping_file is None:
228:             outcome["skipped"] = (
229:                 "no GLEIF mapping file — download the ISIN-LEI relationship file to data/isin-lei.csv"
230:             )
231:             log.info("esef: %s", outcome["skipped"])
232:             return outcome
233:         try:
234:             mapping = load_isin_lei_map(mapping_file)
```
**Verdict:** ______  ·  **Note:** ______

## F6 · docs/research/2026-07-13-data-sources/SUMMARY.md:5
**Finding:** The whole ESEF audited-EU enrichment (run_esef_sweep/run_esef_cycle) is wired but stays idle out-of-the-box: it needs data/isin-lei.csv and nothing downloads it. gleif.py:21 defines ISIN_LEI_LATEST_URL but it is never referenced (dead constant); service.py:229 tells the operator to fetch the ~200 MB file by hand. A self-hoster gets zero audited EU coverage until they discover this. The research doc confirms GLEIF publishes the ISIN↔LEI relationship files as keyless open data ([S12][S53]).
```
3: **La plus grosse opportunité : SEC EDGAR en bulk.** Le fichier `companyfacts.zip` contient l'intégralité des données XBRL de l'API Company Facts pour tous les émetteurs US, recompilé chaque nuit — téléchargeable sans clé [S2]. En complément, les Financial Statement Data Sets fournissent trimestriellement les états financiers « as filed » de janvier 2009 à mars 2026, avec le code SIC [S46]. C'est le « paquet de données » idéal : un seul fetch pour tous les fondamentaux US officiels, sans dépendre de Yahoo.
4: 
5: **Univers de symboles : personne n'a « tout », mais on peut croiser.** FinanceDatabase revendique 300 000+ symboles toutes classes d'actifs, maintenu par la communauté en CSV [S1]. Pour la fraîcheur : les JSON EDGAR (tickers/exchanges des cotées US) sont mis à jour en continu [S2], les index quotidiens chaque nuit [S5] ; les bourses publient leurs annuaires (NASDAQ Trader [S23], Euronext [S31], Xetra [S27]) ; OpenFIGI mappe des centaines de milliers d'instruments avec une clé gratuite, « sans limitation quotidienne, hebdomadaire ou mensuelle » [S8] ; GLEIF publie en open data le Golden Copy et les fichiers ISIN↔LEI quotidiens [S12][S53].
6: 
7: **Fondamentaux hors US : bons filons keyless, avec pièges.** filings.xbrl.org agrège les dépôts ESEF européens (3 400+ dès 2022, en xBRL-JSON) mais n'est pas exhaustif — il n'existe pas encore de dépôt central officiel européen [S42]. Companies House (UK) offre un Accounts Data Product en ZIP gratuit [S13] ; EDINET couvre toutes les cotées japonaises (API à clé gratuite) [S28] ; SEDAR+ (Canada) bloque l'accès automatisé derrière un CAPTCHA [S50]. Attention à SimFin : la licence FREE est limitée à la recherche personnelle, redistribution interdite [S26].
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/providers/esef.py:87-103
**Finding:** facts_to_frames promises 'Only full-year instant/duration facts ... are kept' (esef.py:48), but _fiscal_year (esef.py:87-103) derives the fiscal year purely from the period's END date and never validates that a duration spans a full year (contrast EDGAR, which checks a ~full-year span). A duration fact like 2024-07-01/2024-12-31 (an interim period ending Dec 31) is therefore tagged year '2024' and, at esef.py:71 (values.setdefault(year,{})[column]=value, last-writer-wins), can overwrite the true annual value for the same concept/year. Because audited ESEF values OUTRANK scraped Yahoo values at reconciliation (reconcile.py:1-6, 84), a mis-tagged interim number silently corrupts the flagship 'audited & traceable' figure.
```
85: 
86: 
87: def _fiscal_year(period: str) -> str | None:
88:     """xBRL-JSON period → fiscal year string.
89: 
90:     Durations look like '2024-01-01T00:00:00/2025-01-01T00:00:00', instants
91:     like '2025-01-01T00:00:00'. We tag the year that ENDS the period.
92:     """
93:     if not period:
94:         return None
95:     end = period.split("/")[-1]
96:     year = end[:4]
97:     if not year.isdigit():
98:         return None
99:     # a Jan-1 instant/end belongs to the fiscal year that just closed
100:     month_day = end[5:10]
101:     if month_day == "01-01":
102:         return str(int(year) - 1)
103:     return year
104: 
105: 
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/providers/esef.py:45-51
**Finding:** facts_to_frames promises 'Only full-year instant/duration facts ... are kept' (esef.py:48), but _fiscal_year (esef.py:87-103) derives the fiscal year purely from the period's END date and never validates that a duration spans a full year (contrast EDGAR, which checks a ~full-year span). A duration fact like 2024-07-01/2024-12-31 (an interim period ending Dec 31) is therefore tagged year '2024' and, at esef.py:71 (values.setdefault(year,{})[column]=value, last-writer-wins), can overwrite the true annual value for the same concept/year. Because audited ESEF values OUTRANK scraped Yahoo values at reconciliation (reconcile.py:1-6, 84), a mis-tagged interim number silently corrupts the flagship 'audited & traceable' figure.
```
43: 
44: 
45: def facts_to_frames(xbrl_json: dict[str, Any]) -> dict[tuple[str, str], pd.DataFrame]:
46:     """xBRL-JSON → raw frames keyed by (statement_type, 'annual').
47: 
48:     Only full-year instant/duration facts without extra dimensions are kept —
49:     conservative by design: an audited number we are not sure about is a
50:     number we do not take.
51:     """
52:     facts = xbrl_json.get("facts", {})
53:     values: dict[str, dict[str, float]] = {}
```
**Verdict:** ______  ·  **Note:** ______

## F15 · src/crible/ingest/raw.py:51
**Finding:** facts_to_frames promises 'Only full-year instant/duration facts ... are kept' (esef.py:48), but _fiscal_year (esef.py:87-103) derives the fiscal year purely from the period's END date and never validates that a duration spans a full year (contrast EDGAR, which checks a ~full-year span). A duration fact like 2024-07-01/2024-12-31 (an interim period ending Dec 31) is therefore tagged year '2024' and, at esef.py:71 (values.setdefault(year,{})[column]=value, last-writer-wins), can overwrite the true annual value for the same concept/year. Because audited ESEF values OUTRANK scraped Yahoo values at reconciliation (reconcile.py:1-6, 84), a mis-tagged interim number silently corrupts the flagship 'audited & traceable' figure.
```
49:     stamp = f"{int(fetched_at * 1000):015d}"
50:     final = directory / f"{statement_type}-{freq}-{stamp}.parquet"
51:     tmp = directory / f".tmp-{statement_type}-{freq}-{stamp}.parquet"
52:     out = frame.copy()
53:     out["_symbol"] = symbol
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/providers/esef.py:71
**Finding:** facts_to_frames promises 'Only full-year instant/duration facts ... are kept' (esef.py:48), but _fiscal_year (esef.py:87-103) derives the fiscal year purely from the period's END date and never validates that a duration spans a full year (contrast EDGAR, which checks a ~full-year span). A duration fact like 2024-07-01/2024-12-31 (an interim period ending Dec 31) is therefore tagged year '2024' and, at esef.py:71 (values.setdefault(year,{})[column]=value, last-writer-wins), can overwrite the true annual value for the same concept/year. Because audited ESEF values OUTRANK scraped Yahoo values at reconciliation (reconcile.py:1-6, 84), a mis-tagged interim number silently corrupts the flagship 'audited & traceable' figure.
```
69:             continue
70:         column, _ = mapped
71:         values.setdefault(year, {})[column] = value
72: 
73:     frames: dict[tuple[str, str], pd.DataFrame] = {}
```
**Verdict:** ______  ·  **Note:** ______

## F9 · src/crible/compute/reconcile.py:84
**Finding:** facts_to_frames promises 'Only full-year instant/duration facts ... are kept' (esef.py:48), but _fiscal_year (esef.py:87-103) derives the fiscal year purely from the period's END date and never validates that a duration spans a full year (contrast EDGAR, which checks a ~full-year span). A duration fact like 2024-07-01/2024-12-31 (an interim period ending Dec 31) is therefore tagged year '2024' and, at esef.py:71 (values.setdefault(year,{})[column]=value, last-writer-wins), can overwrite the true annual value for the same concept/year. Because audited ESEF values OUTRANK scraped Yahoo values at reconciliation (reconcile.py:1-6, 84), a mis-tagged interim number silently corrupts the flagship 'audited & traceable' figure.
```
82:                         symbol, column, period, scraped_value, audited_value, relative * 100,
83:                     )
84:             merged.loc[period, column] = audited_value
85:             audited_fields.setdefault(str(period), []).append(column)
86: 
```
**Verdict:** ______  ·  **Note:** ______

## F3 · src/crible/compute/ranks.py:96-99
**Finding:** attach_ranks adds rank columns one at a time via repeated single-column assignment on the full snapshot frame (ranks.py:96-99: a per-column loop then two more inserts), triggering pandas' 'DataFrame is highly fragmented' PerformanceWarning — reproduced 16x in the test run (tests/test_refresh.py). It runs on the compute write path over the whole assembled universe, so cost scales with universe size exactly where the README targets ~150k rows.
```
94:         return snapshot
95:     snapshot = snapshot.reset_index(drop=True)
96:     for col in RANK_COLUMNS:
97:         snapshot[col] = float("nan")
98:     snapshot["rank_peer_group"] = None
99:     snapshot["rank_missing_pillars"] = None
100: 
101:     period = snapshot["period"] if "period" in snapshot.columns else pd.Series("", index=snapshot.index)
```
**Verdict:** ______  ·  **Note:** ______

## F16 · src/crible/providers/esef.py:22-39
**Finding:** refresh_universe already exists (universe.py:213) and the nightly run_refresh calls it (service.py:697), but the long-lived Docker service (docker-compose command `crible ingest --loop`) only bootstraps on first boot (service.py:776-778) and never refreshes again. A self-hoster's delisted flags and new listings freeze forever. The upsert is already idempotent, so this is a scheduler, not new logic.
```
20: 
21: # IFRS concept (ifrs-full unless prefixed) → (canonical field, statement type)
22: CONCEPT_MAP: dict[str, tuple[str, str]] = {
23:     "ifrs-full:Revenue": ("TotalRevenue", "income"),
24:     "ifrs-full:RevenueFromContractsWithCustomers": ("TotalRevenue", "income"),
25:     "ifrs-full:GrossProfit": ("GrossProfit", "income"),
26:     "ifrs-full:ProfitLossFromOperatingActivities": ("OperatingIncome", "income"),
27:     "ifrs-full:ProfitLoss": ("NetIncome", "income"),
28:     "ifrs-full:ProfitLossAttributableToOwnersOfParent": ("NetIncome", "income"),
29:     "ifrs-full:Assets": ("TotalAssets", "balance"),
30:     "ifrs-full:CurrentAssets": ("CurrentAssets", "balance"),
31:     "ifrs-full:CurrentLiabilities": ("CurrentLiabilities", "balance"),
32:     "ifrs-full:Equity": ("StockholdersEquity", "balance"),
33:     "ifrs-full:EquityAttributableToOwnersOfParent": ("StockholdersEquity", "balance"),
34:     "ifrs-full:RetainedEarnings": ("RetainedEarnings", "balance"),
35:     "ifrs-full:Inventories": ("Inventory", "balance"),
36:     "ifrs-full:TradeAndOtherCurrentReceivables": ("AccountsReceivable", "balance"),
37:     "ifrs-full:CashAndCashEquivalents": ("CashAndCashEquivalents", "balance"),
38:     "ifrs-full:CashFlowsFromUsedInOperatingActivities": ("OperatingCashFlow", "cashflow"),
39: }
40: 
41: # canonical (yfinance-vocabulary) column → statement type, for frame assembly
```
**Verdict:** ______  ·  **Note:** ______

## F3 · run:runs/core.md#L11
**Finding:** attach_ranks adds rank columns one at a time via repeated single-column assignment on the full snapshot frame (ranks.py:96-99: a per-column loop then two more inserts), triggering pandas' 'DataFrame is highly fragmented' PerformanceWarning — reproduced 16x in the test run (tests/test_refresh.py). It runs on the compute write path over the whole assembled universe, so cost scales with universe size exactly where the README targets ~150k rows.
```
9: 181 passed, 29 warnings in 9.58s        # exit 0
10: ```
11: Warnings of note (real, reproducible): `PerformanceWarning: DataFrame is highly fragmented`
12: raised from `src/crible/compute/ranks.py:97-103` during `attach_ranks` (per-column
13: `snapshot[col] = ...` insertions on a wide frame) — seen 16× in `tests/test_refresh.py`.
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/ingest/service.py:1-820
**Finding:** service.py is the #1 hotspot at 820 LOC with nesting depth 14 (analysis.json). Last cycle's F2 flagged the same module at 370 LOC; the ESEF/EDGAR/bulk enrichment cycles (run_esef_cycle, run_esef_sweep, run_edgar_cycle, run_edgar_bulk, run_refresh, run_loop) were all added to this one file, so the deferred 'extract collaborators' debt is now materially larger and each cycle duplicates the same GLEIF-file / connection / heartbeat boilerplate.
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
26: from crible.universe import BootstrapReport, UniverseSourceError, refresh_universe
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
127: def restore_queue_from_raw(con: duckdb.DuckDBPyConnection, data_dir) -> int:
128:     """Rebuild crawl freshness from the raw layer's filename stamps.
129: 
130:     A nightly Actions run starts from a fresh operational DB — only the raw
131:     parquet layer travels on the data branch. Without this, every night
132:     re-crawls the same queue head instead of advancing (the coverage
133:     plateau observed at ~145 symbols). Raw filenames carry fetched_at as a
134:     zero-padded ms stamp, so the queue state is recoverable exactly.
135:     """
136:     from pathlib import Path
137: 
138:     from crible.ingest.queue import QUARTER_SECONDS
139: 
140:     root = Path(data_dir) / "raw" / "provider=yfinance"
141:     restored = 0
142:     for directory in root.glob("symbol=*"):
143:         stamps = []
144:         for file in directory.glob("*.parquet"):
145:             try:
146:                 stamps.append(int(file.stem.rsplit("-", 1)[1]) / 1000.0)
147:             except (IndexError, ValueError):
148:                 continue
149:         if not stamps:
150:             continue
151:         crawled_at = max(stamps)
152:         con.execute(
153:             "UPDATE crawl_tasks SET last_crawled_at = ?, next_due = ?"
154:             " WHERE symbol = ? AND (last_crawled_at IS NULL OR last_crawled_at < ?)",
155:             [crawled_at, crawled_at + QUARTER_SECONDS,
156:              directory.name.split("=", 1)[1], crawled_at],
157:         )
158:         restored += 1
159:     return restored
160: 
161: 
162: def run_bootstrap() -> BootstrapReport:
163:     con = _connect()
164:     try:
165:         report = refresh_universe(con)
166:         queue = CrawlQueue(con)
167:         queue.seed_from_universe()
168:         prioritize_sample(con, bootstrap_sample())
169:         return report
170:     finally:
171:         con.close()
172: 
173: 
174: def _make_crawler(con: duckdb.DuckDBPyConnection, provider=None) -> Crawler:
175:     return Crawler(
176:         queue=CrawlQueue(con),
177:         provider=provider if provider is not None else YFinanceProvider(),
178:         budget=TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600),
179:         backoff=BackoffPolicy(),
180:         data_dir=config.data_dir(),
181:     )
182: 
183: 
184: def run_once(limit: int = 50) -> CrawlOutcome:
185:     con = _connect()
186:     try:
187:         crawler = _make_crawler(con)
188:         outcome = crawler.run_cycle(limit=limit)
189:         update_heartbeat(
190:             requests_last_hour=crawler.budget.used_in_window(),
191:             budget_per_hour=crawler.budget.capacity,
192:             last_cycle={"fetched": len(outcome.fetched), "failed": len(outcome.failed)},
193:             providers={crawler.provider.id: "healthy"},
194:             **_queue_stats(con),
195:             ts=time.time(),
196:         )
197:         return outcome
198:     finally:
199:         con.close()
200: 
201: 
202: ESEF_REFRESH_SECONDS = 90 * 24 * 3600
203: ESEF_SCHEMA = """
204: CREATE TABLE IF NOT EXISTS esef_tasks (
205:     symbol          VARCHAR PRIMARY KEY,
206:     lei             VARCHAR NOT NULL,
207:     last_fetched_at DOUBLE
208: )
209: """
210: 
211: 
212: def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
213:     """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
214:     an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
215:     figures pulled from filings.xbrl.org into provider='esef' raw statements.
216:     Outages are recorded and the cycle resumes next time; unmatched listings
217:     are counted, never errored."""
218:     from crible.providers.gleif import load_isin_lei_map, resolve_leis
219: 
220:     data = config.data_dir()
221:     outcome: dict = {"enriched": [], "unmatched": 0, "outage": None, "skipped": None}
222: 
223:     if mapping is None:
224:         mapping_file = next(
225:             (p for p in (data / "isin-lei.csv", data / "isin-lei.zip") if p.exists()), None
226:         )
227:         if mapping_file is None:
228:             outcome["skipped"] = (
229:                 "no GLEIF mapping file — download the ISIN-LEI relationship file to data/isin-lei.csv"
230:             )
231:             log.info("esef: %s", outcome["skipped"])
232:             return outcome
233:         try:
234:             mapping = load_isin_lei_map(mapping_file)
235:         except Exception as exc:  # noqa: BLE001 — treated as outage (FR-010 AC-2)
236:             outcome["outage"] = f"gleif mapping unreadable: {exc}"
237:             log.warning("esef: %s — resuming next cycle", outcome["outage"])
238:             return outcome
239: 
240:     con = _connect()
241:     try:
242:         con.execute(ESEF_SCHEMA)
243:         companies = [
244:             {"symbol": s, "isin": i}
245:             for s, i in con.execute(
246:                 "SELECT symbol, isin FROM companies WHERE region = 'europe' AND NOT delisted"
247:             ).fetchall()
248:         ]
249:         resolved, unmatched = resolve_leis(companies, mapping)
250:         outcome["unmatched"] = len(unmatched)
251:         # FR-010 AC-4: the unmatched-EU-listings metric is visible in status
252:         update_heartbeat(esef_unmatched=len(unmatched), esef_resolved=len(resolved))
253:         for symbol, lei in resolved.items():
254:             con.execute(
255:                 "INSERT INTO esef_tasks (symbol, lei) VALUES (?, ?) ON CONFLICT (symbol) DO NOTHING",
256:                 [symbol, lei],
257:             )
258:         due = con.execute(
259:             "SELECT symbol, lei FROM esef_tasks WHERE last_fetched_at IS NULL"
260:             " OR last_fetched_at < ? ORDER BY last_fetched_at NULLS FIRST LIMIT ?",
261:             [time.time() - ESEF_REFRESH_SECONDS, limit],
262:         ).fetchall()
263:         if not due:
264:             return outcome
265: 
266:         if client is None:
267:             from crible.providers.esef import EsefClient
268: 
269:             client = EsefClient()
270:         from crible.providers.esef import facts_to_frames
271:         from crible.ingest.raw import write_raw_statement
272: 
273:         for symbol, lei in due:
274:             try:
275:                 filings = client.filings_for_lei(lei)
276:                 if not filings:
277:                     con.execute(
278:                         "UPDATE esef_tasks SET last_fetched_at = ? WHERE symbol = ?",
279:                         [time.time(), symbol],
280:                     )
281:                     continue
282:                 xbrl = client.fetch_xbrl_json(filings[0])
283:                 frames = facts_to_frames(xbrl) if xbrl else {}
284:                 fetched_at = time.time()
285:                 for (statement_type, freq), frame in frames.items():
286:                     write_raw_statement(
287:                         data, symbol=symbol, provider="esef", statement_type=statement_type,
288:                         freq=freq, frame=frame, fetched_at=fetched_at,
289:                     )
290:                 con.execute(
291:                     "UPDATE esef_tasks SET last_fetched_at = ? WHERE symbol = ?",
292:                     [fetched_at, symbol],
293:                 )
294:                 if frames:
295:                     outcome["enriched"].append(symbol)
296:                     log.info("esef: enriched %s (%d statement frame(s)) from filing of LEI %s",
297:                              symbol, len(frames), lei)
298:             except Exception as exc:  # noqa: BLE001 — outage: record, resume next cycle
299:                 outcome["outage"] = f"{symbol}: {exc}"
300:                 log.warning("esef: outage on %s: %s — resuming next cycle", symbol, exc)
301:                 break
302:         return outcome
303:     finally:
304:         con.close()
305: 
306: 
307: EDGAR_REFRESH_SECONDS = 90 * 24 * 3600
308: EDGAR_SCHEMA = """
309: CREATE TABLE IF NOT EXISTS edgar_tasks (
310:     symbol          VARCHAR PRIMARY KEY,
311:     cik             BIGINT NOT NULL,
312:     last_fetched_at DOUBLE
313: )
314: """
315: 
316: 
317: def run_edgar_cycle(limit: int = 5, client=None, ticker_map: dict[str, int] | None = None) -> dict:
318:     """FR-016 — the EDGAR enrichment cycle: US companies whose ticker resolves
319:     in the SEC directory (company_tickers.json) get audited figures pulled
320:     from companyfacts into provider='edgar' raw statements. Outages are
321:     recorded and the cycle resumes next time; unmatched listings are counted,
322:     never errored — symmetric with the ESEF cycle."""
323:     from crible.providers.edgar import facts_to_frames, resolve_ciks
324: 
325:     data = config.data_dir()
326:     outcome: dict = {"enriched": [], "unmatched": 0, "outage": None, "skipped": None}
327: 
328:     con = _connect()
329:     try:
330:         con.execute(EDGAR_SCHEMA)
331:         companies = [
332:             {"symbol": s}
333:             for (s,) in con.execute(
334:                 "SELECT symbol FROM companies WHERE region = 'us' AND NOT delisted"
335:             ).fetchall()
336:         ]
337:         if not companies:
338:             outcome["skipped"] = "no US companies in the universe yet"
339:             return outcome
340:         if ticker_map is None:
341:             if client is None:
342:                 from crible.providers.edgar import EdgarClient
343: 
344:                 client = EdgarClient()
345:             try:
346:                 ticker_map = client.company_tickers()
347:             except Exception as exc:  # noqa: BLE001 — outage: record, resume next cycle
348:                 outcome["outage"] = f"company_tickers.json: {exc}"
349:                 log.warning("edgar: %s — resuming next cycle", outcome["outage"])
350:                 return outcome
351:         resolved, unmatched = resolve_ciks(companies, ticker_map)
352:         outcome["unmatched"] = len(unmatched)
353:         # FR-016: the unmatched-US-listings metric is visible in status
354:         update_heartbeat(edgar_unmatched=len(unmatched), edgar_resolved=len(resolved))
355:         for symbol, cik in resolved.items():
356:             con.execute(
357:                 "INSERT INTO edgar_tasks (symbol, cik) VALUES (?, ?) ON CONFLICT (symbol) DO NOTHING",
358:                 [symbol, cik],
359:             )
360:         due = con.execute(
361:             "SELECT symbol, cik FROM edgar_tasks WHERE last_fetched_at IS NULL"
362:             " OR last_fetched_at < ? ORDER BY last_fetched_at NULLS FIRST LIMIT ?",
363:             [time.time() - EDGAR_REFRESH_SECONDS, limit],
364:         ).fetchall()
365:         if not due:
366:             return outcome
367: 
368:         if client is None:
369:             from crible.providers.edgar import EdgarClient
370: 
371:             client = EdgarClient()
372:         from crible.ingest.raw import write_raw_statement
373: 
374:         for symbol, cik in due:
375:             try:
376:                 frames = facts_to_frames(client.companyfacts(int(cik)))
377:                 fetched_at = time.time()
378:                 for (statement_type, freq), frame in frames.items():
379:                     write_raw_statement(
380:                         data, symbol=symbol, provider="edgar", statement_type=statement_type,
381:                         freq=freq, frame=frame, fetched_at=fetched_at,
382:                     )
383:                 con.execute(
384:                     "UPDATE edgar_tasks SET last_fetched_at = ? WHERE symbol = ?",
385:                     [fetched_at, symbol],
386:                 )
387:                 if frames:
388:                     outcome["enriched"].append(symbol)
389:                     log.info("edgar: enriched %s (%d statement frame(s)) from CIK %010d",
390:                              symbol, len(frames), int(cik))
391:             except Exception as exc:  # noqa: BLE001 — outage: record, resume next cycle
392:                 outcome["outage"] = f"{symbol}: {exc}"
393:                 log.warning("edgar: outage on %s: %s — resuming next cycle", symbol, exc)
394:                 break
395:         return outcome
396:     finally:
397:         con.close()
398: 
399: 
400: def run_edgar_bulk(
401:     zip_path=None, client=None, ticker_map: dict[str, int] | None = None,
402:     download: bool = True, limit: int | None = None,
403: ) -> dict:
404:     """FR-016 / ADR-0005 scale-up — the bulk variant: ONE companyfacts.zip
405:     gives the audited layer for EVERY resolved US listing (~10k issuers),
406:     instead of the per-CIK trickle. The archive is processed member-by-member
407:     (memory-safe) and never committed; a broken filing is skipped, a missing
408:     archive is an outage — recorded, resumed next run."""
409:     from pathlib import Path
410: 
411:     from crible.ingest.raw import write_raw_statement
412:     from crible.providers.edgar import facts_to_frames, iter_bulk_companyfacts, resolve_ciks
413: 
414:     data = config.data_dir()
415:     outcome: dict = {"enriched": 0, "unmatched": 0, "outage": None, "skipped": None}
416: 
417:     con = _connect()
418:     try:
419:         con.execute(EDGAR_SCHEMA)
420:         companies = [
421:             {"symbol": s}
422:             for (s,) in con.execute(
423:                 "SELECT symbol FROM companies WHERE region = 'us' AND NOT delisted"
424:             ).fetchall()
425:         ]
426:         if not companies:
427:             outcome["skipped"] = "no US companies in the universe yet"
428:             return outcome
429:         if ticker_map is None or (download and zip_path is None):
430:             if client is None:
431:                 from crible.providers.edgar import EdgarClient
432: 
433:                 client = EdgarClient()
434:         if ticker_map is None:
435:             try:
436:                 ticker_map = client.company_tickers()
437:             except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
438:                 outcome["outage"] = f"company_tickers.json: {exc}"
439:                 log.warning("edgar bulk: %s", outcome["outage"])
440:                 return outcome
441:         resolved, unmatched = resolve_ciks(companies, ticker_map)
442:         outcome["unmatched"] = len(unmatched)
443:         update_heartbeat(edgar_unmatched=len(unmatched), edgar_resolved=len(resolved))
444: 
445:         archive = Path(zip_path) if zip_path is not None else data / "companyfacts.zip"
446:         if not archive.exists():
447:             if not download:
448:                 outcome["skipped"] = f"no bulk archive at {archive}"
449:                 return outcome
450:             try:
451:                 log.info("edgar bulk: downloading companyfacts.zip (~1.4 GB)")
452:                 client.download_bulk(archive)
453:             except Exception as exc:  # noqa: BLE001
454:                 outcome["outage"] = f"companyfacts.zip download: {exc}"
455:                 log.warning("edgar bulk: %s", outcome["outage"])
456:                 return outcome
457: 
458:         by_cik = {cik: symbol for symbol, cik in resolved.items()}
459:         fetched_at = time.time()
460:         for cik, facts in iter_bulk_companyfacts(archive, set(by_cik)):
461:             frames = facts_to_frames(facts)
462:             if not frames:
463:                 continue
464:             symbol = by_cik[cik]
465:             for (statement_type, freq), frame in frames.items():
466:                 write_raw_statement(
467:                     data, symbol=symbol, provider="edgar", statement_type=statement_type,
468:                     freq=freq, frame=frame, fetched_at=fetched_at,
469:                 )
470:             con.execute(
471:                 "INSERT INTO edgar_tasks (symbol, cik, last_fetched_at) VALUES (?, ?, ?)"
472:                 " ON CONFLICT (symbol) DO UPDATE SET last_fetched_at = excluded.last_fetched_at",
473:                 [symbol, int(cik), fetched_at],
474:             )
475:             outcome["enriched"] += 1
476:             if limit is not None and outcome["enriched"] >= limit:
477:                 break
478:         log.info("edgar bulk: enriched %d US issuers from %s", outcome["enriched"], archive)
479:         return outcome
480:     finally:
481:         con.close()
482: 
483: 
484: def _esef_due(con: duckdb.DuckDBPyConnection, symbol: str, cutoff: float) -> bool:
485:     row = con.execute(
486:         "SELECT last_fetched_at FROM esef_tasks WHERE symbol = ?", [symbol]
487:     ).fetchone()
488:     return row is None or row[0] is None or row[0] < cutoff
489: 
490: 
491: def run_esef_sweep(
492:     limit: int = 100, client=None, mapping: dict[str, str] | None = None,
493:     page_size: int = 100, max_pages: int = 300,
494: ) -> dict:
495:     """FR-010 at index scale: walk filings.xbrl.org's FULL index (newest
496:     first) instead of querying one LEI at a time — every request lands on a
497:     real filing, so the whole EU/EEA ESEF gisement (~25k filings) is
498:     coverable in a few nightly runs. Filers outside the universe are counted
499:     and skipped; dual listings sharing one LEI are all enriched; freshness
500:     (esef_tasks, 90 days) prevents refetching. Outages resume next run."""
501:     from crible.providers.esef import facts_to_frames, filing_lei
502:     from crible.providers.gleif import load_isin_lei_map
503: 
504:     data = config.data_dir()
505:     outcome: dict = {"enriched": [], "skipped_unknown": 0, "outage": None, "skipped": None}
506: 
507:     if mapping is None:
508:         mapping_file = next(
509:             (p for p in (data / "isin-lei.csv", data / "isin-lei.zip") if p.exists()), None
510:         )
511:         if mapping_file is None:
512:             outcome["skipped"] = (
513:                 "no GLEIF mapping file — download the ISIN-LEI relationship file to data/isin-lei.csv"
514:             )
515:             log.info("esef sweep: %s", outcome["skipped"])
516:             return outcome
517:         try:
518:             mapping = load_isin_lei_map(mapping_file)
519:         except Exception as exc:  # noqa: BLE001 — outage (FR-010 AC-2)
520:             outcome["outage"] = f"gleif mapping unreadable: {exc}"
521:             log.warning("esef sweep: %s — resuming next run", outcome["outage"])
522:             return outcome
523: 
524:     con = _connect()
525:     try:
526:         con.execute(ESEF_SCHEMA)
527:         rows = con.execute(
528:             "SELECT symbol, isin FROM companies"
529:             " WHERE region = 'europe' AND NOT delisted AND isin IS NOT NULL"
530:         ).fetchall()
531:         by_lei: dict[str, list[str]] = {}
532:         for symbol, isin in rows:
533:             lei = mapping.get(isin)
534:             if lei:
535:                 by_lei.setdefault(lei, []).append(symbol)
536:         update_heartbeat(
537:             esef_resolved=sum(len(v) for v in by_lei.values()),
538:             esef_unmatched=len(rows) - sum(len(v) for v in by_lei.values()),
539:         )
540: 
541:         if client is None:
542:             from crible.providers.esef import EsefClient
543: 
544:             client = EsefClient()
545:         from crible.ingest.raw import write_raw_statement
546: 
547:         cutoff = time.time() - ESEF_REFRESH_SECONDS
548:         seen_leis: set[str] = set()
549:         page = 1
550:         while len(outcome["enriched"]) < limit and page <= max_pages:
551:             try:
552:                 filings, _total = client.filings_index(page_size=page_size, page_number=page)
553:             except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
554:                 outcome["outage"] = f"index page {page}: {exc}"
555:                 log.warning("esef sweep: %s — resuming next run", outcome["outage"])
556:                 return outcome
557:             if not filings:
558:                 break
559:             page += 1
560:             for filing in filings:
561:                 lei = filing_lei(filing)
562:                 if not lei or lei in seen_leis:
563:                     continue  # newest-first: only the latest filing per filer
564:                 seen_leis.add(lei)
565:                 symbols = by_lei.get(lei)
566:                 if not symbols:
567:                     outcome["skipped_unknown"] += 1
568:                     continue
569:                 due = [s for s in symbols if _esef_due(con, s, cutoff)]
570:                 if not due:
571:                     continue
572:                 try:
573:                     xbrl = client.fetch_xbrl_json(filing)
574:                     frames = facts_to_frames(xbrl) if xbrl else {}
575:                 except Exception as exc:  # noqa: BLE001
576:                     outcome["outage"] = f"{lei}: {exc}"
577:                     log.warning("esef sweep: outage on %s: %s — resuming next run", lei, exc)
578:                     return outcome
579:                 fetched_at = time.time()
580:                 for symbol in due:
581:                     for (statement_type, freq), frame in frames.items():
582:                         write_raw_statement(
583:                             data, symbol=symbol, provider="esef",
584:                             statement_type=statement_type, freq=freq,
585:                             frame=frame, fetched_at=fetched_at,
586:                         )
587:                     con.execute(
588:                         "INSERT INTO esef_tasks (symbol, lei, last_fetched_at) VALUES (?, ?, ?)"
589:                         " ON CONFLICT (symbol) DO UPDATE SET"
590:                         " last_fetched_at = excluded.last_fetched_at",
591:                         [symbol, lei, fetched_at],
592:                     )
593:                     if frames:
594:                         outcome["enriched"].append(symbol)
595:                 if len(outcome["enriched"]) >= limit:
596:                     break
597:         if outcome["enriched"]:
598:             log.info("esef sweep: enriched %d listings (%d filers outside the universe)",
599:                      len(outcome["enriched"]), outcome["skipped_unknown"])
600:         return outcome
601:     finally:
602:         con.close()
603: 
604: 
605: def run_price_refresh(budget: TokenBucket, provider=None) -> dict:
606:     """FR-011 — daily price refresh for the priority set within the budget."""
607:     from crible.ingest.prices import PriceRefresher
608: 
609:     if provider is None:
610:         provider = _YfPriceAdapter()
611:     refresher = PriceRefresher(provider=provider, budget=budget, data_dir=config.data_dir())
612:     outcome = refresher.refresh(bootstrap_sample())
613:     return {"refreshed": len(outcome.refreshed), "skipped": len(outcome.skipped), "aborted": outcome.aborted}
614: 
615: 
616: class _YfPriceAdapter:
617:     id = "yfinance"
618: 
619:     def fetch_prices(self, symbol: str):
620:         import yfinance as yf
621: 
622:         from crible.providers.base import RateLimitedError
623:         from crible.providers.yfinance_provider import RATE_LIMIT_MARKERS
624: 
625:         try:
626:             # one year of daily bars is still ONE request — and FR-015's
627:             # return_6m needs ≥182 days of history to compute (momentum
628:             # pillar); a 5d window left it permanently NaN
629:             bars = yf.Ticker(symbol).history(period="1y", auto_adjust=False)
630:         except Exception as exc:  # noqa: BLE001
631:             if any(m in str(exc).lower() for m in RATE_LIMIT_MARKERS):
632:                 raise RateLimitedError(str(exc)) from exc
633:             raise
634:         return bars.reset_index() if bars is not None and not bars.empty else None
635: 
636: 
637: def run_compute() -> int:
638:     data = config.data_dir()
639:     if not (data / "universe.parquet").exists() and config.database_path().exists():
640:         # self-heal installs bootstrapped before universe export existed
641:         con = _connect()
642:         try:
643:             from crible.universe import export_universe_parquet
644: 
645:             has = con.execute(
646:                 "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
647:             ).fetchone()[0]
648:             if has:
649:                 export_universe_parquet(con, data)
650:                 log.info("compute: exported missing universe.parquet")
651:         finally:
652:             con.close()
653:     snapshot = build_snapshot(data)
654:     if snapshot.empty:
655:         log.info("compute: no raw data yet — skipping publish")
656:         return 0
657:     publish_snapshot(snapshot, data)
658:     log.info("compute: published %d rows × %d columns", len(snapshot), len(snapshot.columns))
659:     return len(snapshot)
660: 
661: 
662: def run_refresh(
663:     deadline_seconds: float = 9000.0,
664:     esef_limit: int = 25,
665:     edgar_limit: int = 25,
666:     *,
667:     edgar_bulk: bool = False,
668:     fetch_universe=None,
669:     provider=None,
670:     price_provider=None,
671:     edgar_client=None,
672:     cycle_limit: int = 10,
673: ) -> dict:
674:     """One bounded, resumable refresh pass — the nightly dataset run.
675: 
676:     Bootstrap (falling back to the last-good universe.parquet when
677:     FinanceDatabase is down) → prioritized crawl on ONE shared token bucket
678:     until the queue drains or the deadline passes (repeated ``ingest --once``
679:     calls would each get a fresh bucket and bust the hourly budget) → ESEF +
680:     EDGAR enrichment → price refresh → prune the raw layer → compute + publish.
681:     """
682:     from crible.ingest.raw import prune_raw
683:     from crible.universe import (
684:         export_universe_parquet,
685:         fetch_financedatabase,
686:         restore_universe_from_parquet,
687:     )
688: 
689:     started = time.monotonic()
690:     deadline = started + deadline_seconds
691:     data = config.data_dir()
692:     result: dict = {"universe_restored": False}
693: 
694:     con = _connect()
695:     try:
696:         try:
697:             report = refresh_universe(con, fetch=fetch_universe or fetch_financedatabase)
698:             result["universe_loaded"] = report.loaded
699:         except UniverseSourceError:
700:             if not (data / "universe.parquet").exists():
701:                 raise
702:             log.warning("universe source down — restoring last-good universe.parquet")
703:             result["universe_loaded"] = restore_universe_from_parquet(
704:                 con, data / "universe.parquet"
705:             )
706:             result["universe_restored"] = True
707:         crawler = _make_crawler(con, provider=provider)  # CrawlQueue() re-seeds
708:         prioritize_sample(con, bootstrap_sample())
709:         # AFTER prioritizing: fresh raw wins over the sample's due-now reset,
710:         # so the nightly advances into new symbols instead of re-crawling
711:         result["queue_restored"] = restore_queue_from_raw(con, data)
712:         export_universe_parquet(con, data)
713: 
714:         fetched = failed = 0
715:         while time.monotonic() < deadline:
716:             outcome = crawler.run_cycle(limit=cycle_limit)
717:             fetched += len(outcome.fetched)
718:             failed += len(outcome.failed)
719:             if not outcome.fetched and not outcome.failed:
720:                 break  # nothing due — the queue is drained for this run
721:         result["fetched"] = fetched
722:         result["failed"] = failed
723:         stats = _queue_stats(con)
724:     finally:
725:         con.close()
726: 
727:     try:
728:         # index sweep, not per-LEI polling: every request lands on a real
729:         # filing, so the nightly covers actual EU filers at full speed
730:         result["esef"] = run_esef_sweep(limit=esef_limit)
731:     except Exception as exc:  # noqa: BLE001 — enrichment never kills the refresh
732:         log.warning("esef sweep failed: %s", exc)
733:         result["esef"] = {"outage": str(exc)}
734:     try:
735:         if edgar_bulk:
736:             # the bulk sweep marks every issuer fetched, so the per-CIK
737:             # cycle below finds nothing due — no double work
738:             result["edgar_bulk"] = run_edgar_bulk(client=edgar_client)
739:         result["edgar"] = run_edgar_cycle(limit=edgar_limit, client=edgar_client)
740:     except Exception as exc:  # noqa: BLE001 — enrichment never kills the refresh
741:         log.warning("edgar cycle failed: %s", exc)
742:         result["edgar"] = {"outage": str(exc)}
743:     try:
744:         result["prices"] = run_price_refresh(crawler.budget, provider=price_provider)
745:     except Exception as exc:  # noqa: BLE001
746:         log.warning("price refresh failed: %s", exc)
747:         result["prices"] = {"error": str(exc)}
748: 
749:     result["pruned"] = prune_raw(data)
750:     result["snapshot_rows"] = run_compute()
751:     result["took_seconds"] = round(time.monotonic() - started, 1)
752:     update_heartbeat(
753:         last_refresh={
754:             k: result[k]
755:             for k in ("fetched", "failed", "pruned", "snapshot_rows",
756:                       "universe_restored", "took_seconds")
757:         },
758:         requests_last_hour=crawler.budget.used_in_window(),
759:         budget_per_hour=crawler.budget.capacity,
760:         last_cycle={"fetched": fetched, "failed": failed},
761:         providers={crawler.provider.id: "healthy"},
762:         **stats,
763:         ts=time.time(),
764:     )
765:     return result
766: 
767: 
768: def run_loop(cycle_limit: int = 40, compute_every_seconds: float = 1800.0) -> None:  # pragma: no cover — long-lived loop
769:     # cycle_limit × ~7 requests must stay under the hourly budget so a cycle
770:     # never stalls mid-way on the token bucket before its compute runs
771:     con = _connect()
772:     has_universe = con.execute(
773:         "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
774:     ).fetchone()[0]
775:     con.close()
776:     if not has_universe:
777:         log.info("first boot — bootstrapping universe")
778:         run_bootstrap()
779: 
780:     first_cycle = not (config.data_dir() / "snapshot").exists()
781:     last_compute = 0.0
782:     last_price_refresh = 0.0
783:     price_budget = TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600)
784:     while True:
785:         # first boot: crawl exactly the bootstrap sample, then publish
786:         # immediately — a first screen must return rows within hours (FR-008)
787:         limit = max(10, len(bootstrap_sample())) if first_cycle else cycle_limit
788:         outcome = run_once(limit=limit)
789:         first_cycle = False
790:         now = time.time()
791: 
792:         # FR-011: daily priority-tier price refresh (shares the request budget)
793:         if now - last_price_refresh >= 20 * 3600:
794:             try:
795:                 log.info("price refresh: %s", run_price_refresh(price_budget))
796:             except Exception as exc:  # noqa: BLE001 — never kills the loop
797:                 log.warning("price refresh failed: %s", exc)
798:             last_price_refresh = now
799: 
800:         # FR-010: audited ESEF enrichment (keyless; idle without a GLEIF file)
801:         try:
802:             esef = run_esef_cycle()
803:             if esef["enriched"] or esef["outage"]:
804:                 log.info("esef cycle: %s", esef)
805:         except Exception as exc:  # noqa: BLE001
806:             log.warning("esef cycle failed: %s", exc)
807: 
808:         # FR-016: audited EDGAR enrichment (keyless; own SEC fair-access pace)
809:         try:
810:             edgar = run_edgar_cycle()
811:             if edgar["enriched"] or edgar["outage"]:
812:                 log.info("edgar cycle: %s", edgar)
813:         except Exception as exc:  # noqa: BLE001
814:             log.warning("edgar cycle failed: %s", exc)
815: 
816:         if outcome.fetched or now - last_compute >= compute_every_seconds:
817:             run_compute()
818:             last_compute = now
819:         if not outcome.fetched and not outcome.failed:
820:             time.sleep(60)  # queue empty or nothing due — idle politely
821: 
```
**Verdict:** ______  ·  **Note:** ______

## F4 · run:analysis.json
**Finding:** service.py is the #1 hotspot at 820 LOC with nesting depth 14 (analysis.json). Last cycle's F2 flagged the same module at 370 LOC; the ESEF/EDGAR/bulk enrichment cycles (run_esef_cycle, run_esef_sweep, run_edgar_cycle, run_edgar_bulk, run_refresh, run_loop) were all added to this one file, so the deferred 'extract collaborators' debt is now materially larger and each cycle duplicates the same GLEIF-file / connection / heartbeat boilerplate.
```
{
  "target": "/Users/maxime/Downloads/crible",
  "files": 110,
  "loc": 12706,
  "languages": {
    ".mjs": 1,
    ".py": 68,
    ".tsx": 21,
    ".ts": 20
  },
  "hotspots": [
    {
```
**Verdict:** ______  ·  **Note:** ______

## F4 · src/crible/ingest/service.py:223-234
**Finding:** service.py is the #1 hotspot at 820 LOC with nesting depth 14 (analysis.json). Last cycle's F2 flagged the same module at 370 LOC; the ESEF/EDGAR/bulk enrichment cycles (run_esef_cycle, run_esef_sweep, run_edgar_cycle, run_edgar_bulk, run_refresh, run_loop) were all added to this one file, so the deferred 'extract collaborators' debt is now materially larger and each cycle duplicates the same GLEIF-file / connection / heartbeat boilerplate.
```
221:     outcome: dict = {"enriched": [], "unmatched": 0, "outage": None, "skipped": None}
222: 
223:     if mapping is None:
224:         mapping_file = next(
225:             (p for p in (data / "isin-lei.csv", data / "isin-lei.zip") if p.exists()), None
226:         )
227:         if mapping_file is None:
228:             outcome["skipped"] = (
229:                 "no GLEIF mapping file — download the ISIN-LEI relationship file to data/isin-lei.csv"
230:             )
231:             log.info("esef: %s", outcome["skipped"])
232:             return outcome
233:         try:
234:             mapping = load_isin_lei_map(mapping_file)
235:         except Exception as exc:  # noqa: BLE001 — treated as outage (FR-010 AC-2)
236:             outcome["outage"] = f"gleif mapping unreadable: {exc}"
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/compute/snapshot.py:171-172
**Finding:** Every compute cycle rebuilds the entire snapshot: run_compute() calls build_snapshot(data) with no symbols, which re-reads every crawled symbol's raw parquet and recomputes all ratios/scores/ranks (snapshot.py:171-172). build_snapshot ALREADY accepts a symbols= argument — the seam exists, the caller just never uses it. Fine at ~500 companies, quadratic pain toward the 150k universe the README advertises.
```
169: 
170: 
171: def build_snapshot(data_dir: Path | str, symbols: list[str] | None = None) -> pd.DataFrame:
172:     todo = symbols if symbols is not None else crawled_symbols(data_dir)
173:     quotes = _price_quotes(data_dir)
174:     parts = []
```
**Verdict:** ______  ·  **Note:** ______

## F7 · src/crible/ingest/service.py:653
**Finding:** Every compute cycle rebuilds the entire snapshot: run_compute() calls build_snapshot(data) with no symbols, which re-reads every crawled symbol's raw parquet and recomputes all ratios/scores/ranks (snapshot.py:171-172). build_snapshot ALREADY accepts a symbols= argument — the seam exists, the caller just never uses it. Fine at ~500 companies, quadratic pain toward the 150k universe the README advertises.
```
651:         finally:
652:             con.close()
653:     snapshot = build_snapshot(data)
654:     if snapshot.empty:
655:         log.info("compute: no raw data yet — skipping publish")
```
**Verdict:** ______  ·  **Note:** ______

## F8 · src/crible/compute/snapshot.py:135-148
**Finding:** Ratios are currency-neutral so the gap is modest, but absolute values (market_cap, revenue) are stored in native currency with no normalized companion columns — grep for frankfurter|market_cap_eur|fx_rate finds nothing. Cross-currency screening on absolute size is therefore misleading. The research doc identifies a keyless source: ECB reference rates via api.frankfurter.dev ([S71][S72]).
```
133: 
134: 
135: UNIVERSE_COLUMNS = [
136:     "name", "country", "country_name", "region", "sector", "industry", "exchange", "currency", "isin",
137: ]
138: 
139: 
140: def attach_universe(snapshot: pd.DataFrame, data_dir: Path | str) -> pd.DataFrame:
141:     """Embed universe metadata so the snapshot is self-contained: readers
142:     (API/CLI) never open the ingest-owned DuckDB file (ADR-0003)."""
143:     universe_path = Path(data_dir) / "universe.parquet"
144:     if snapshot.empty or not universe_path.exists():
145:         return snapshot
146:     universe = pd.read_parquet(universe_path)
147:     keep = ["symbol"] + [c for c in UNIVERSE_COLUMNS if c in universe.columns]
148:     return snapshot.merge(universe[keep], on="symbol", how="left")
149: 
150: 
```
**Verdict:** ______  ·  **Note:** ______

## F8 · docs/research/2026-07-13-data-sources/SUMMARY.md:9
**Finding:** Ratios are currency-neutral so the gap is modest, but absolute values (market_cap, revenue) are stored in native currency with no normalized companion columns — grep for frankfurter|market_cap_eur|fx_rate finds nothing. Cross-currency screening on absolute size is therefore misleading. The research doc identifies a keyless source: ECB reference rates via api.frankfurter.dev ([S71][S72]).
```
7: **Fondamentaux hors US : bons filons keyless, avec pièges.** filings.xbrl.org agrège les dépôts ESEF européens (3 400+ dès 2022, en xBRL-JSON) mais n'est pas exhaustif — il n'existe pas encore de dépôt central officiel européen [S42]. Companies House (UK) offre un Accounts Data Product en ZIP gratuit [S13] ; EDINET couvre toutes les cotées japonaises (API à clé gratuite) [S28] ; SEDAR+ (Canada) bloque l'accès automatisé derrière un CAPTCHA [S50]. Attention à SimFin : la licence FREE est limitée à la recherche personnelle, redistribution interdite [S26].
8: 
9: **Prix : le maillon faible du keyless.** Yahoo a durci ses limites fin 2024 (~429 après quelques centaines de requêtes) [S73] — le crawl budgeté reste la bonne approche. Stooq fournit des CSV historiques mondiaux mais « sans garantie d'API officielle » [S19] et avec des questions d'ajustement des cours [S69]. Pour le change : taux de référence BCE quotidiens [S71] via l'API keyless Frankfurter [S72].
10: 
11: **Technos : edgartools (MIT) pour parser EDGAR [S10], Arelle pour le XBRL brut [S44], Perspective (FINOS) pour la dataviz streaming [S51], OpenBB comme plateforme de référence [S18].** Recommandation n°1 pour crible : un provider `edgar` keyless basé sur companyfacts.zip.
```
**Verdict:** ______  ·  **Note:** ______

## F10 · src/crible/providers/esef.py:22-39
**Finding:** Two distinct IFRS concepts map to the same canonical column (Revenue and RevenueFromContractsWithCustomers → TotalRevenue, esef.py:23-24; ProfitLoss and ProfitLossAttributableToOwnersOfParent → NetIncome, esef.py:27-28). facts_to_frames writes them with last-writer-wins keyed only by (year,column) (esef.py:71), so which concept survives depends on JSON iteration order. For consolidated statements ProfitLoss (group total) and the owners-of-parent figure differ materially (minority interests), yielding a non-deterministic audited NetIncome.
```
20: 
21: # IFRS concept (ifrs-full unless prefixed) → (canonical field, statement type)
22: CONCEPT_MAP: dict[str, tuple[str, str]] = {
23:     "ifrs-full:Revenue": ("TotalRevenue", "income"),
24:     "ifrs-full:RevenueFromContractsWithCustomers": ("TotalRevenue", "income"),
25:     "ifrs-full:GrossProfit": ("GrossProfit", "income"),
26:     "ifrs-full:ProfitLossFromOperatingActivities": ("OperatingIncome", "income"),
27:     "ifrs-full:ProfitLoss": ("NetIncome", "income"),
28:     "ifrs-full:ProfitLossAttributableToOwnersOfParent": ("NetIncome", "income"),
29:     "ifrs-full:Assets": ("TotalAssets", "balance"),
30:     "ifrs-full:CurrentAssets": ("CurrentAssets", "balance"),
31:     "ifrs-full:CurrentLiabilities": ("CurrentLiabilities", "balance"),
32:     "ifrs-full:Equity": ("StockholdersEquity", "balance"),
33:     "ifrs-full:EquityAttributableToOwnersOfParent": ("StockholdersEquity", "balance"),
34:     "ifrs-full:RetainedEarnings": ("RetainedEarnings", "balance"),
35:     "ifrs-full:Inventories": ("Inventory", "balance"),
36:     "ifrs-full:TradeAndOtherCurrentReceivables": ("AccountsReceivable", "balance"),
37:     "ifrs-full:CashAndCashEquivalents": ("CashAndCashEquivalents", "balance"),
38:     "ifrs-full:CashFlowsFromUsedInOperatingActivities": ("OperatingCashFlow", "cashflow"),
39: }
40: 
41: # canonical (yfinance-vocabulary) column → statement type, for frame assembly
```
**Verdict:** ______  ·  **Note:** ______

## F10 · src/crible/providers/esef.py:71
**Finding:** Two distinct IFRS concepts map to the same canonical column (Revenue and RevenueFromContractsWithCustomers → TotalRevenue, esef.py:23-24; ProfitLoss and ProfitLossAttributableToOwnersOfParent → NetIncome, esef.py:27-28). facts_to_frames writes them with last-writer-wins keyed only by (year,column) (esef.py:71), so which concept survives depends on JSON iteration order. For consolidated statements ProfitLoss (group total) and the owners-of-parent figure differ materially (minority interests), yielding a non-deterministic audited NetIncome.
```
69:             continue
70:         column, _ = mapped
71:         values.setdefault(year, {})[column] = value
72: 
73:     frames: dict[tuple[str, str], pd.DataFrame] = {}
```
**Verdict:** ______  ·  **Note:** ______

## F11 · src/crible/ingest/raw.py:51
**Finding:** write_raw_statement stages to '.tmp-{...}.parquet' then renames to the final name (raw.py:51,59), relying on the tmp being invisible to readers. But pathlib's glob('*.parquet') DOES match dotfiles (verified empirically), so prune_raw (raw.py:26) and latest_raw_frames (snapshot.py:121) both enumerate leftover '.tmp-*.parquet' files. A crash between to_parquet(tmp) and rename leaves a partial parquet that a later glob picks up; stem.split('-',2) yields a junk '.tmp' statement_type and pd.read_parquet on the truncated file can raise, breaking the snapshot build for that symbol. The raw layer is documented as 'the durable source of truth any snapshot can be recomputed from' (raw.py:1-6).
```
49:     stamp = f"{int(fetched_at * 1000):015d}"
50:     final = directory / f"{statement_type}-{freq}-{stamp}.parquet"
51:     tmp = directory / f".tmp-{statement_type}-{freq}-{stamp}.parquet"
52:     out = frame.copy()
53:     out["_symbol"] = symbol
```
**Verdict:** ______  ·  **Note:** ______

## F11 · src/crible/ingest/raw.py:26
**Finding:** write_raw_statement stages to '.tmp-{...}.parquet' then renames to the final name (raw.py:51,59), relying on the tmp being invisible to readers. But pathlib's glob('*.parquet') DOES match dotfiles (verified empirically), so prune_raw (raw.py:26) and latest_raw_frames (snapshot.py:121) both enumerate leftover '.tmp-*.parquet' files. A crash between to_parquet(tmp) and rename leaves a partial parquet that a later glob picks up; stem.split('-',2) yields a junk '.tmp' statement_type and pd.read_parquet on the truncated file can raise, breaking the snapshot build for that symbol. The raw layer is documented as 'the durable source of truth any snapshot can be recomputed from' (raw.py:1-6).
```
24:         newest: dict[tuple[str, str], Path] = {}
25:         # zero-padded ms stamps make lexical order chronological
26:         for file in sorted(directory.glob("*.parquet")):
27:             statement_type, freq, _ = file.stem.split("-", 2)
28:             key = (statement_type, freq)
```
**Verdict:** ______  ·  **Note:** ______

## F11 · src/crible/compute/snapshot.py:120-123
**Finding:** write_raw_statement stages to '.tmp-{...}.parquet' then renames to the final name (raw.py:51,59), relying on the tmp being invisible to readers. But pathlib's glob('*.parquet') DOES match dotfiles (verified empirically), so prune_raw (raw.py:26) and latest_raw_frames (snapshot.py:121) both enumerate leftover '.tmp-*.parquet' files. A crash between to_parquet(tmp) and rename leaves a partial parquet that a later glob picks up; stem.split('-',2) yields a junk '.tmp' statement_type and pd.read_parquet on the truncated file can raise, breaking the snapshot build for that symbol. The raw layer is documented as 'the durable source of truth any snapshot can be recomputed from' (raw.py:1-6).
```
118:     frames: dict[tuple[str, str], pd.DataFrame] = {}
119:     root = Path(data_dir) / "raw"
120:     for directory in root.glob(f"provider={provider}/symbol={safe_symbol}"):
121:         for file in sorted(directory.glob("*.parquet")):
122:             statement_type, freq, _ = file.stem.split("-", 2)
123:             frames[(statement_type, freq)] = pd.read_parquet(file)
124:     return frames
125: 
```
**Verdict:** ______  ·  **Note:** ______

## F12 · src/crible/ingest/stooq_fetch.py:61-68
**Finding:** solve_pow (stooq_fetch.py:61-68) brute-forces SHA-256 until the digest starts with `difficulty` hex zeros, with no upper bound and no time budget; `difficulty` comes verbatim from the remote page (parsed at stooq_fetch.py:90 and passed at :93). Each extra hex zero multiplies expected work ~16x, so a changed or hostile value makes the automated bulk-price download spin a core indefinitely — and there is no crawler watchdog to interrupt it (see F2).
```
59: 
60: 
61: def solve_pow(challenge: str, difficulty: int) -> int:
62:     """Return the smallest ``n`` where ``SHA256(challenge + n)`` starts with
63:     ``difficulty`` hex zeros (Stooq's Layer-1 hashcash)."""
64:     target = "0" * difficulty
65:     n = 0
66:     while not hashlib.sha256(f"{challenge}{n}".encode()).hexdigest().startswith(target):
67:         n += 1
68:     return n
69: 
70: 
```
**Verdict:** ______  ·  **Note:** ______

## F12 · src/crible/ingest/stooq_fetch.py:90-93
**Finding:** solve_pow (stooq_fetch.py:61-68) brute-forces SHA-256 until the digest starts with `difficulty` hex zeros, with no upper bound and no time budget; `difficulty` comes verbatim from the remote page (parsed at stooq_fetch.py:90 and passed at :93). Each extra hex zero multiplies expected work ~16x, so a changed or hostile value makes the automated bulk-price download spin a core indefinitely — and there is no crawler watchdog to interrupt it (see F2).
```
88:         """Solve the proof-of-work challenge and earn the session's auth cookie."""
89:         html = self._http.get(DB_PAGE).text
90:         m_c, m_d = _POW_C_RE.search(html), _POW_D_RE.search(html)
91:         if not (m_c and m_d):
92:             return  # no challenge served — already verified
93:         n = solve_pow(m_c.group(1), int(m_d.group(1)))
94:         self._http.post(
95:             VERIFY_URL,
```
**Verdict:** ______  ·  **Note:** ______

## F13 · src/crible/bootstrap.py:148
**Finding:** fetch_and_extract gets the dataset tarball with a non-streaming http.get (bootstrap.py:148) and wraps the full body in io.BytesIO(response.content) (bootstrap.py:153) before tarfile opens it. The whole (multi-hundred-MB and growing) published dataset is held in RAM at once — the opposite of the memory-safe member-by-member handling used for companyfacts.zip — so a small self-hosted box (the target audience) can OOM on the one-command bootstrap.
```
146:     for source, url in attempts:
147:         try:
148:             response = http.get(url)
149:             if response.status_code == 404:
150:                 last_error = f"{source} not published yet ({url})"
```
**Verdict:** ______  ·  **Note:** ______

## F13 · src/crible/bootstrap.py:153
**Finding:** fetch_and_extract gets the dataset tarball with a non-streaming http.get (bootstrap.py:148) and wraps the full body in io.BytesIO(response.content) (bootstrap.py:153) before tarfile opens it. The whole (multi-hundred-MB and growing) published dataset is held in RAM at once — the opposite of the memory-safe member-by-member handling used for companyfacts.zip — so a small self-hosted box (the target audience) can OOM on the one-command bootstrap.
```
151:                 continue
152:             response.raise_for_status()
153:             payload = io.BytesIO(response.content)
154:         except Exception as exc:  # noqa: BLE001 — try the next distribution channel
155:             last_error = f"{source}: {exc}"
```
**Verdict:** ______  ·  **Note:** ______

