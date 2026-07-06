# Functional requirements

## FR-001 — Worldwide universe built from FinanceDatabase _(must)_

Bootstrap the screening universe from FinanceDatabase (160,995 equities, 117 countries, 84 exchanges; Yahoo-suffixed symbols usable directly by yfinance [E2][E16]). Loaded into DuckDB with region tags that drive crawl priority (Europe first). market_cap arrives categorical (Large/Mid/Small) [E17]; numeric market cap is derived later from prices × shares. Known upstream data-quality caveats (CUSIP collisions [E25], stale exchange codes [E27]) are tolerated: the universe is metadata, not valuation input. [E2][E16][E17][E25][E27][E40]

**Acceptance criteria:**
- **Given** a fresh install with no API keys configured **When** the operator runs the universe bootstrap (crible ingest --bootstrap) **Then** a companies table exists in DuckDB with at least 150,000 equity rows spanning at least 100 countries, every row carrying a Yahoo-suffixed symbol, country, region, sector, industry and exchange, and re-running the bootstrap is idempotent (upsert; row count stable)
- **Given** the FinanceDatabase source is unreachable (offline machine, GitHub down) **When** the bootstrap runs **Then** it exits non-zero naming FinanceDatabase as the failed source and the existing universe table is left untouched (no partial load)
- **Given** the universe is loaded **When** region tags are computed **Then** every EU/EEA/UK/CH listing carries region = 'europe' and the highest crawl priority tier, verified by a count per region exposed in crible status

_Traceability — NFRs: NFR-003, NFR-005, NFR-009, NFR-010 · entities: Company · interfaces: CLI_

## FR-002 — Rolling prioritized keyless ingestion (yfinance) _(must)_

A continuous, resumable crawler fetches per-ticker fundamentals (income/balance/cash-flow, ~4 annual periods and 4–5 quarters — Yahoo's ceiling [E98][E99]) and daily prices through yfinance, under a global rate budget with jittered exponential backoff on 429 (Yahoo tolerates roughly 360 req/h and rate-limiting is Yahoo policy, not a library bug [E3][E52]). A priority queue orders work Europe → US large caps → rest of world, revisit driven by expected reporting freshness (quarterly for statements, daily for prices). Raw responses land as versioned Parquet (append-only raw layer). All sources sit behind one Provider interface; a keyed plugin with no key disables itself cleanly (zero-key contract). [E3][E52][E36][E82][E98][E99]

**Acceptance criteria:**
- **Given** the universe is loaded and no API keys are configured **When** the crawler runs for one hour **Then** it fetches statements and prices exclusively via keyless providers, issues at most 330 Yahoo requests in any rolling 60-minute window, persists each fetched company as versioned raw Parquet under the data directory, and updates its crawl queue (lastCrawledAt / nextDue) after every symbol
- **Given** Yahoo answers with HTTP 429 or a crumb/cookie failure **When** the crawler encounters the error **Then** it backs off exponentially with jitter (delay doubling from 1 minute up to a 15-minute cap), never busy-loops, reschedules the failed symbol instead of dropping it, and logs the event with symbol and wait time
- **Given** the crawler process is killed mid-cycle **When** it restarts **Then** it resumes from the persisted queue and does not re-fetch symbols still inside their freshness window (quarterly for fundamentals, daily for prices)
- **Given** a European listing and a rest-of-world listing are both due for crawl **When** the scheduler picks the next symbol **Then** the European listing is fetched first (priority order Europe → US large caps → rest of world)

_Traceability — NFRs: NFR-003, NFR-005, NFR-007, NFR-009 · entities: RawStatement, PriceBar, CrawlTask, Provider · interfaces: CLI, Provider Plugin API_

## FR-003 — Ratio and score computation into a wide snapshot _(must)_

Compute the wide screening snapshot: financetoolkit (with the Yahoo source enforced) supplies 150+ transparently-defined ratios plus Piotroski F-Score and Altman Z-Score [E1][E6][E8]; Beneish M-Score is implemented in-house (absent from financetoolkit — verified by full-source grep) with its 8 components, unit-tested against published examples. Output: one row per company × fiscal period, ~200 columns, written as snapshot Parquet that DuckDB queries. Missing inputs yield NULL cells with provenance, never fabricated values [E30]. [E1][E6][E7][E8][E9][E39][E79][E30]

**Acceptance criteria:**
- **Given** raw statements exist for a sample of at least 100 companies **When** the compute step runs (crible compute) **Then** a snapshot Parquet is produced with one row per company × fiscal period, at least 150 ratio columns plus piotroski_f (0–9), altman_z and beneish_m with their components, and re-running on the same input produces byte-identical output
- **Given** a company lacks a field required by a ratio or score (e.g. no cash-flow statement) **When** the compute step processes it **Then** the affected cells are NULL with a provenance note naming the missing input, the company still appears in the snapshot, and no value is imputed or fabricated
- **Given** the published Beneish test vectors (Beneish 1999 example set) **When** M-Score is computed on them **Then** each of the 8 components (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) and the final M = -4.84 + weighted sum match the published values within 0.01

_Traceability — NFRs: NFR-001, NFR-010, NFR-012 · entities: SnapshotRow · interfaces: CLI_

## FR-004 — Filter DSL compiled to DuckDB SQL _(must)_

A human-readable filter DSL — e.g. roe > 15 AND piotroski >= 7 AND country IN ('FR','DE') AND sector = 'Industrials' — compiled to parametrized DuckDB SQL over the snapshot. Strict column whitelist (parser rejects unknown fields with a hint), values always bound as parameters (injection impossible by construction), sorting and pagination built in. DuckDB over Parquet is the 'ultra-powerful engine': a full 161k × 200 screen runs in milliseconds [E4][E12]; the preset-filtering timeout that hit xang1234/stock-screener under Postgres [E88] is the anti-pattern this design avoids. [E4][E12][E88]

**Acceptance criteria:**
- **Given** the snapshot is loaded **When** a user screens with roe > 15 AND piotroski >= 7 AND country IN ('FR','DE') **Then** the result contains exactly the rows satisfying every clause, respects the requested sort and pagination, and the generated SQL references only whitelisted columns with all values bound as parameters
- **Given** a query names an unknown field (moat > 3) or is malformed (roe >) **When** it is parsed **Then** parsing fails with an error naming the offending token and its position plus the closest valid field name, and nothing is executed against DuckDB
- **Given** a hostile query string (e.g. roe > 15; DROP TABLE companies-- or a value embedding ' OR 1=1) **When** it is parsed **Then** the input is either rejected or treated strictly as a literal value — property-based tests over generated inputs prove non-whitelisted SQL never reaches DuckDB
- **Given** the full ~161k-row snapshot **When** any valid DSL screen runs on a development laptop **Then** the 95th-percentile end-to-end latency is under 1 second

_Traceability — NFRs: NFR-001, NFR-008, NFR-011 · entities: SnapshotRow, Preset · interfaces: CLI, HTTP API_

## FR-005 — CLI (crible) _(must)_

The crible CLI (Typer [E92]): crible screen "<dsl>" with table or CSV output; crible ingest (bootstrap / one cycle / continuous loop); crible compute; crible status (universe size, coverage %, freshness histogram, requests-per-hour, provider health); crible export. Exactly the same DSL and semantics as the API and UI. [E92][E93]

**Acceptance criteria:**
- **Given** a working install with a computed snapshot **When** crible screen "piotroski >= 7" --format csv runs **Then** matching rows stream to stdout as CSV with a header row, the process exits 0, and the same query through the API returns the same rows
- **Given** an invalid DSL string or a missing snapshot **When** any CLI command runs **Then** the process exits non-zero with an actionable stderr message (for a missing snapshot: telling the operator to run crible ingest / crible compute first)
- **Given** the crawler has been running **When** crible status runs **Then** it reports universe row count, fundamentals coverage %, a freshness histogram, the rolling requests-per-hour figure and per-provider health, in under 2 seconds

_Traceability — NFRs: NFR-004, NFR-005 · entities: SnapshotRow · interfaces: CLI_

## FR-006 — HTTP API (FastAPI) _(must)_

The HTTP API (FastAPI [E13]): POST /screen (DSL + sort + pagination → rows, total, tookMs), GET /screen.csv (streaming export), GET /presets, GET /company/{symbol} (profile, statement history, score breakdowns, per-field provenance), GET /status (coverage, freshness, rate budget, provider health), GET /healthz. Serves the built SPA statically at /. No auth by design: single self-hosted operator (ADR-0002), bound to localhost/compose network by default. [E13][E14]

**Acceptance criteria:**
- **Given** the API is running with a snapshot **When** POST /screen receives {"query": "roe > 15", "sort": "-roe", "page": 1} **Then** it returns 200 with rows, total count, page info and tookMs, with p95 latency under 500 ms warm for full-universe screens
- **Given** a DSL error or an unknown company symbol **When** POST /screen or GET /company/{symbol} is called **Then** the API returns 422 (DSL error: message, position, hint) or 404 (unknown symbol) — never a 5xx — and logs the request with its outcome
- **Given** the SPA build exists **When** a browser requests / **Then** the built SPA is served (index.html + hashed assets) and every /api route remains reachable under the same origin

_Traceability — NFRs: NFR-001, NFR-002, NFR-008 · entities: SnapshotRow, Preset, Company · interfaces: HTTP API_

## FR-007 — React/Vite SPA _(must)_

The React 18 + Vite + TypeScript SPA [E18][E21]: a dense, dark-first results grid on TanStack Table [E19] — query bar bound to the DSL, sortable columns, column picker, presets menu, CSV export of the current result set, and a company-detail drawer (statements, score breakdowns, provenance and freshness badges). The table is the hero; screener.in-class information density is the benchmark [E75]. [E18][E19][E20][E21][E100][E75]

**Acceptance criteria:**
- **Given** the SPA is served and a snapshot exists **When** the user runs a DSL query from the query bar **Then** the grid renders the matching rows with sortable columns and a column picker, updates in under 1 second p95 for full-universe screens, and CSV export downloads exactly the rows and columns currently displayed
- **Given** the API is unreachable or returns a DSL error **When** the user runs a query **Then** the UI surfaces the API's error message and hint inline (no blank screen, no console-only failure) and keeps the previous results visible
- **Given** a user opens a company row **When** the detail drawer opens **Then** it shows the statement history, each score with its component breakdown and per-field provenance badges without navigating away from the results

_Traceability — NFRs: NFR-001, NFR-004, NFR-008 · entities: SnapshotRow, Company · interfaces: Web App, HTTP API_

## FR-008 — Docker Compose deployment _(must)_

Docker Compose deployment [E94]: service ingest (continuous crawler) + service api (FastAPI serving the built SPA), a shared volume for Parquet/DuckDB, healthchecks on both, .env consumed for optional phase-2 keys. docker compose up with zero keys yields a fully working system — the zero-key guarantee is exercised in CI. [E94][E49]

**Acceptance criteria:**
- **Given** a machine with only Docker installed and no API keys in the environment **When** docker compose up runs **Then** both services report healthy within 120 seconds, the shared volume holds the DuckDB database and Parquet layers, and a screen executed through the UI or CLI returns rows once the bootstrap sample is ingested
- **Given** the ingest container crashes or is killed **When** compose restarts it **Then** crawling resumes from the persisted queue without re-fetching fresh symbols, and the api service keeps serving the last snapshot uninterrupted throughout
- **Given** an operator provides phase-2 keys via .env **When** the stack restarts **Then** the corresponding plugins activate without any image rebuild, and removing the keys returns the system to keyless operation

_Traceability — NFRs: NFR-003, NFR-006, NFR-009, NFR-013 · entities: Provider · interfaces: HTTP API, CLI_

## FR-009 — Preset screens _(should)_

Preset screens shipped as plain, visible, editable DSL strings — transparency is the product (the closed ranks of Stockopedia [E67] are the counter-model): piotroski-strong (piotroski >= 7 [E39]), altman-safe (altman_z > 2.99), beneish-red-flags (beneish_m > -1.78), classic-value (low EV/EBIT + high ROIC), quality (high ROE + low leverage). Available identically via CLI (--preset), API (GET /presets) and the SPA presets menu. [E39][E67][E63]

**Acceptance criteria:**
- **Given** the presets are shipped **When** GET /presets is called or crible screen --preset piotroski-strong runs **Then** each preset exposes its name, a one-line description and its complete DSL string, and running the preset is byte-for-byte equivalent to running that DSL string directly
- **Given** a user edits a preset's DSL in the UI **When** they run the edited query **Then** it executes as ordinary DSL (presets carry no hidden logic) and the edited text can be saved as a new named preset

_Traceability — NFRs: NFR-004, NFR-010 · entities: Preset · interfaces: HTTP API, Web App, CLI_

## FR-010 — ESEF XBRL Europe enrichment _(should)_

Europe-depth enrichment from filings.xbrl.org — the free, keyless ESEF repository (4,000+ audited annual reports as xBRL-JSON, with a JSON-API; explicitly the interim source until ESAP opens in July 2027 [E5][E15][E74]). Audited annual figures are stored as provider='esef' facts; where an audited value and a scraped Yahoo value coexist for the same field/period, the audited value wins and material discrepancies are logged. Company detail links to the underlying filing. [E5][E15][E74]

**Acceptance criteria:**
- **Given** an EU company whose ESEF annual report exists on filings.xbrl.org **When** the enrichment cycle processes it **Then** audited annual figures parsed from xBRL-JSON are stored as provider='esef' facts for that company, the snapshot marks the enriched fields' provenance as audited, and the company detail view links to the filing URL
- **Given** filings.xbrl.org is unreachable **When** the enrichment cycle runs **Then** yfinance-derived data remains intact, the cycle records the outage and resumes at the next cycle — no partial overwrite of existing facts
- **Given** an audited ESEF value and a Yahoo value differ by more than 5% for the same field and period **When** reconciliation runs **Then** the audited value is used in the snapshot and the discrepancy is logged with both values, the field, the period and the filing reference

_Traceability — NFRs: NFR-003, NFR-005, NFR-010 · entities: RawStatement, Company · interfaces: Provider Plugin API_

## FR-011 — Stooq price fallback _(should)_

Stooq CSV fallback for prices: when Yahoo throttles or hangs (a real, recurring failure mode [E36][E82]), the price refresher falls back to Stooq's keyless CSV endpoints (~21k global tickers, prices only) so valuation ratios (P/E, EV multiples) stay refreshable during Yahoo outages. Fetched bars carry provider='stooq' provenance. [E36][E82][E3]

**Acceptance criteria:**
- **Given** Yahoo price requests are being rate-limited or failing **When** the price refresher runs its fallback path **Then** OHLCV bars for Stooq-covered tickers are updated from Stooq with provider='stooq' provenance and the dependent valuation ratios recompute on the next compute cycle
- **Given** a ticker unknown to Stooq **When** the fallback attempts it **Then** the ticker is skipped with a single log line and remains scheduled for Yahoo on the next cycle — the fallback never blocks the queue

_Traceability — NFRs: NFR-003, NFR-005 · entities: PriceBar, Provider · interfaces: Provider Plugin API_

## FR-012 — Company detail view _(should)_

Company detail (SPA drawer + GET /company/{symbol}): full statement history as far as sources allow, every score with its complete component breakdown (the 9 Piotroski criteria pass/fail, the 8 Beneish components, Altman inputs), per-field provenance (provider + fetchedAt) and freshness. The transparency answer to Simply Wall St's polished-but-closed company pages [E58]. [E58][E75][E1]

**Acceptance criteria:**
- **Given** a company present in the snapshot **When** its detail is opened in the UI or fetched via the API **Then** it shows the held statement history, each score with its full component breakdown (9 Piotroski criteria, 8 Beneish components, Altman inputs), and per-field provenance with provider and fetch timestamp
- **Given** a company in the universe that has not been crawled yet **When** its detail is opened **Then** the view shows the universe metadata (name, country, sector, exchange) plus its queue position / crawl ETA instead of an error

_Traceability — NFRs: NFR-004, NFR-010 · entities: Company, SnapshotRow, RawStatement · interfaces: Web App, HTTP API_

## FR-013 — Phase-2 free-key provider plugins _(could)_

Phase-2 free-key provider plugins behind the same Provider interface: financialreports (FinancialReports.eu — free official MCP server, OAuth, EU filings + normalized financials [E72][E73]), simfin (free bulk US fundamentals, ~12-month delay [E65][E66][E78]), fmp_free and eodhd_free (schema validation against the future paid switch only). Strictly optional: without its key a plugin logs one 'disabled (no key)' line and the system behaves exactly as keyless. [E72][E73][E65][E66][E78][E83]

**Acceptance criteria:**
- **Given** no provider keys are configured **When** the system starts **Then** each keyed plugin logs exactly one 'disabled (no key configured)' line, is reported as disabled in crible status, and every keyless flow behaves identically to a build without the plugins
- **Given** a valid SimFin key is configured **When** the ingest cycle runs **Then** SimFin bulk US fundamentals are stored as provider='simfin' raw facts alongside yfinance data without overwriting fresher facts, and provider health for simfin appears in crible status
- **Given** a configured key is invalid or expired **When** the plugin makes its first API call **Then** the plugin disables itself for the session with a clear log line naming the env var to fix, and the crawler continues keyless without error

_Traceability — NFRs: NFR-006, NFR-009, NFR-012 · entities: Provider, RawStatement · interfaces: Provider Plugin API_

## FR-014 — EODHD paid provider PRD + stub plugin _(could)_

The single planned paid upgrade, specced without paying: docs/prds/eodhd.md — a detailed PRD for EODHD's Fundamentals Data Feed (€59.99/mo, 100k calls/day, worldwide fundamentals; free tier confirmed to exclude fundamentals [E61][E62]) with endpoint schemas validated against the demo tickers using the existing free key, field mapping to crible's raw schema, and the switch plan (set EODHD_KEY → plugin activates). docs/prds/fmp-ultimate.md documents FMP Ultimate ($149/mo) as the evaluated-and-rejected alternative. [E61][E62]

**Acceptance criteria:**
- **Given** the repository is checked out **When** a reader opens docs/prds/eodhd.md **Then** it contains the pricing and quota facts (€59.99/mo, 100k calls/day), recorded sample payloads for the fundamentals and EOD endpoints captured via the free key's demo tickers, a field-by-field mapping to crible's raw schema, and the exact activation steps — and docs/prds/fmp-ultimate.md documents the rejected FMP alternative with its pricing
- **Given** an EODHD key is configured **When** the stub plugin initializes **Then** it validates the key with a single metadata call and reports the detected tier — a free-tier key yields 'insufficient tier for fundamentals' and the plugin stays disabled — proving the switch path end-to-end without a paid subscription

_Traceability — NFRs: NFR-006, NFR-012 · entities: Provider · interfaces: Provider Plugin API_
