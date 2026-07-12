# Functional requirements

## FR-001 — Worldwide universe built from FinanceDatabase _(must)_ [E109][E110][E2][E16][E25][E27][E35][E40]

Bootstrap the screening universe from FinanceDatabase — its README statistics table counts 160,995 equities across 117 countries and 84 exchanges [E109][E110]; symbols are Yahoo-suffixed tickers usable directly by yfinance [E2][E16]. Loaded into DuckDB with region tags that drive crawl priority (Europe first). market_cap arrives as a categorical class (Large/Mid/Small); numeric market cap is derived later from prices × shares. Known upstream data-quality caveats (CUSIP collisions [E25], stale exchange codes [E27], sparse ISINs [E35]) are tolerated: the universe is metadata, not valuation input. Universe refreshes also update the delisted flag from the source.

**Acceptance criteria:**
- **Given** a fresh install with no API keys configured **When** the operator runs the universe bootstrap (crible ingest --bootstrap) **Then** a companies table exists in DuckDB with at least 150,000 equity rows spanning at least 100 countries, every row carrying a Yahoo-suffixed symbol, country, region, sector, industry and exchange, and re-running the bootstrap is idempotent (upsert; row count stable)
- **Given** the FinanceDatabase source is unreachable (offline machine, GitHub down) **When** the bootstrap runs **Then** it exits non-zero naming FinanceDatabase as the failed source and the existing universe table is left untouched (no partial load)
- **Given** the universe is loaded **When** region tags are computed **Then** every EU/EEA/UK/CH listing carries region = 'europe' and the highest crawl priority tier, verified by a count per region exposed in crible status

_Traceability — NFRs: NFR-003, NFR-005, NFR-009, NFR-010 · entities: Company · interfaces: CLI_

## FR-002 — Rolling prioritized keyless ingestion (yfinance) _(must)_ [E105][E107][E108][E52][E36][E82]

A continuous, resumable crawler fetches per-ticker fundamentals AND prices through yfinance under one hard, configurable request budget (default 330 upstream requests per rolling hour — a deliberately conservative crawl rate chosen because Yahoo aggressively rate-limits scrapers: 429s and YFRateLimitError are endemic [E105][E107][E108]). Every upstream call counts: a fundamentals sweep costs ~7 requests per symbol (3 statement types × 2 frequencies + profile/price). Honest throughput at default budget ≈ 7,900 requests/day: with ~2,000/day reserved for daily priority-tier prices (FR-011), ~5,900/day remain for fundamentals ≈ 840 symbols/day — the Europe tier cycles in roughly 5–7 weeks (inside the quarterly freshness contract) and the worldwide tail is explicitly best-effort (ADR-0004 states the full arithmetic). A priority queue orders work Europe → US large caps → rest of world; statement revisits are freshness-driven (quarterly). Raw responses land as versioned Parquet (append-only raw layer). All sources sit behind one Provider interface; a keyed plugin with no key disables itself cleanly (zero-key contract). If Yahoo blocks for an extended period, the crawler parks politely and retries with capped backoff; the API keeps serving the last snapshot with staleness visible (degradation path).

**Acceptance criteria:**
- **Given** the universe is loaded and no API keys are configured **When** the crawler runs for one hour **Then** it fetches statements exclusively via keyless providers, counts every upstream request (each statement/profile call individually) against the budget, never exceeds 330 upstream requests in any rolling 60-minute window, persists each fetched company as versioned raw Parquet under the data directory, and updates its crawl queue (lastCrawledAt / nextDue) after every symbol
- **Given** Yahoo answers with HTTP 429 or a crumb/cookie failure **When** the crawler encounters the error **Then** it backs off exponentially with jitter (delay doubling from 1 minute up to a 15-minute cap), never busy-loops, reschedules the failed symbol instead of dropping it, and logs the event with symbol and wait time
- **Given** the crawler process is killed mid-cycle **When** it restarts **Then** it resumes from the persisted queue and does not re-fetch symbols still inside their freshness window (quarterly for fundamentals)
- **Given** a European listing and a rest-of-world listing are both due for crawl **When** the scheduler picks the next symbol **Then** the European listing is fetched first (priority order Europe → US large caps → rest of world)

_Traceability — NFRs: NFR-003, NFR-005, NFR-007, NFR-009 · entities: RawStatement, PriceBar, CrawlTask, Provider · interfaces: CLI, Provider Plugin API_

## FR-003 — Ratio and score computation into a wide snapshot _(must)_ [E1][E6][E7][E8][E9][E39][E79][E30]

Compute the wide screening snapshot: financetoolkit (with the Yahoo source enforced) supplies 150+ transparently-defined ratios plus Piotroski F-Score and Altman Z-Score [E1][E6][E8]; Beneish M-Score is implemented in-house (absent from financetoolkit — verified by full-source grep) with its 8 components, unit-tested against published examples. Output: one row per company × fiscal period, ~200 columns, written as snapshot Parquet that DuckDB queries. Missing inputs yield NULL cells with provenance, never fabricated values [E30].

**Acceptance criteria:**
- **Given** raw statements exist for a sample of at least 100 companies **When** the compute step runs (crible compute) **Then** a snapshot Parquet is produced with one row per company × fiscal period, at least 150 value columns (canonical fields, financetoolkit ratios, growth series) plus piotroski_f (0–9), altman_z and beneish_m with their components, and re-running on the same input yields identical values for every column except computed_at (file-level metadata excluded from the comparison)
- **Given** a company lacks a field required by a ratio or score (e.g. no cash-flow statement) **When** the compute step processes it **Then** the affected cells are NULL with a provenance note naming the missing input, the company still appears in the snapshot, and no value is imputed or fabricated
- **Given** the Beneish reference vectors (hand-derived from the published 1999 formula: an all-flat company and a fully worked example with analytically exact components) **When** M-Score is computed on them **Then** each of the 8 components (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) matches its analytic value within 1e-6 and the final M = -4.84 + weighted sum matches within 0.01

_Traceability — NFRs: NFR-001, NFR-010, NFR-012 · entities: SnapshotRow · interfaces: CLI_

## FR-004 — Filter DSL compiled to DuckDB SQL _(must)_ [E4][E12][E88]

A human-readable filter DSL — e.g. roe > 15 AND piotroski >= 7 AND country IN ('FR','DE') — compiled to parametrized DuckDB SQL over the snapshot. Strict column whitelist (parser rejects unknown fields with a hint), values always bound as parameters (injection impossible by construction), sorting and pagination built in. DuckDB is an in-process columnar analytics engine [E4]; the enforceable speed contract is NFR-008's CI benchmark on a synthetic full-size snapshot — not vendor copy. The preset-filtering timeout that hit xang1234/stock-screener on an operational database [E88] is the anti-pattern this design avoids.

**Acceptance criteria:**
- **Given** the snapshot is loaded **When** a user screens with roe > 15 AND piotroski >= 7 AND country IN ('FR','DE') **Then** the result contains exactly the rows satisfying every clause, respects the requested sort and pagination, and the generated SQL references only whitelisted columns with all values bound as parameters
- **Given** a query names an unknown field (moat > 3) or is malformed (roe >) **When** it is parsed **Then** parsing fails with an error naming the offending token and its position plus the closest valid field name, and nothing is executed against DuckDB
- **Given** a hostile query string (e.g. roe > 15; DROP TABLE companies-- or a value embedding ' OR 1=1) **When** it is parsed **Then** the input is either rejected or treated strictly as a literal value — property-based tests over generated inputs prove non-whitelisted SQL never reaches DuckDB
- **Given** the synthetic full-size snapshot used by the NFR-008 CI benchmark (~161k rows × ~200 columns) **When** any valid DSL screen runs in the benchmark environment **Then** the 95th-percentile end-to-end latency is under 1 second (this CI benchmark is the single normative performance environment; laptop figures are guidance)

_Traceability — NFRs: NFR-001, NFR-008, NFR-011 · entities: SnapshotRow, Preset · interfaces: CLI, HTTP API_

## FR-005 — CLI (crible) _(must)_ [E92][E93]

The crible CLI (Typer [E92]): crible screen "<dsl>" with table or CSV output; crible ingest (bootstrap / one cycle / continuous loop); crible compute; crible status (universe size, coverage %, freshness histogram, requests-per-hour, provider health, unmatched-EU-listings count); crible export "<dsl>" --out file.csv (writes the FULL result set of the query — identical rows to GET /screen.csv). Exactly the same DSL and semantics as the API and UI.

**Acceptance criteria:**
- **Given** a working install with a computed snapshot **When** crible screen "piotroski >= 7" --format csv runs **Then** matching rows stream to stdout as CSV with a header row, the process exits 0, and the same query through the API returns the same rows
- **Given** an invalid DSL string or a missing snapshot **When** any CLI command runs **Then** the process exits non-zero with an actionable stderr message (for a missing snapshot: telling the operator to run crible ingest / crible compute first)
- **Given** the crawler has been running **When** crible status runs **Then** it reports universe row count, fundamentals coverage %, a freshness histogram, the rolling requests-per-hour figure and per-provider health, in under 2 seconds

_Traceability — NFRs: NFR-004, NFR-005 · entities: SnapshotRow · interfaces: CLI_

## FR-006 — HTTP API (FastAPI) _(must)_ [E13][E14]

The HTTP API (FastAPI [E13]): POST /screen (DSL + sort + pagination → rows, total, tookMs), GET /screen.csv (streaming export), GET /presets, GET /company/{symbol} (profile, statement history, score breakdowns, per-field provenance), GET /status (coverage, freshness, rate budget, provider health), GET /healthz. Serves the built SPA statically at /. No auth by design: single self-hosted operator (ADR-0002), bound to localhost/compose network by default.

**Acceptance criteria:**
- **Given** the API is running with a snapshot **When** POST /screen receives {"query": "roe > 15", "sort": "-roe", "page": 1} **Then** it returns 200 with rows, total count, page info and tookMs, with p95 latency under 500 ms warm for full-universe screens
- **Given** a DSL error or an unknown company symbol **When** POST /screen or GET /company/{symbol} is called **Then** the API returns 422 (DSL error: message, position, hint) or 404 (unknown symbol) — never a 5xx — and logs the request with its outcome
- **Given** the SPA build exists **When** a browser requests / **Then** the built SPA is served (index.html + hashed assets) and every /api route remains reachable under the same origin
- **Given** a fresh install where no snapshot has been computed yet **When** POST /screen or GET /presets is called **Then** the API returns 200 with an empty row set and a hint naming the ingest/compute progress (never a 5xx), and GET /status reports the bootstrap state

_Traceability — NFRs: NFR-001, NFR-002, NFR-008 · entities: SnapshotRow, Preset, Company · interfaces: HTTP API_

## FR-007 — React/Vite SPA _(must)_ [E18][E19][E20][E21][E100][E75]

The React 18 + Vite + TypeScript SPA [E18][E21]: a dense, dark-first results grid on TanStack Table [E19] — query bar bound to the DSL, sortable columns, column picker, presets menu, CSV export of the current result set, and a company-detail drawer (statements, score breakdowns, provenance and freshness badges). The table is the hero; screener.in-class information density is the benchmark [E75].

**Acceptance criteria:**
- **Given** the SPA is served and a snapshot exists **When** the user runs a DSL query from the query bar **Then** the grid renders the matching rows with sortable columns and a column picker; the export button (labelled 'Export all results') downloads the FULL result set of the current query (all pages, currently visible columns) via GET /screen.csv
- **Given** the API is unreachable or returns a DSL error **When** the user runs a query **Then** the UI surfaces the API's error message and hint inline (no blank screen, no console-only failure) and keeps the previous results visible
- **Given** a user opens a company row **When** the detail drawer opens **Then** it shows the statement history, each score with its component breakdown and per-field provenance badges without navigating away from the results

_Traceability — NFRs: NFR-001, NFR-004, NFR-008 · entities: SnapshotRow, Company · interfaces: Web App, HTTP API_

## FR-008 — Docker Compose deployment _(must)_ [E94][E49]

Docker Compose deployment [E94]: service ingest (continuous loop: universe bootstrap if empty → crawl cycle → compute → atomic snapshot publish, repeating; compute runs after every crawl cycle and at least every 30 minutes) + service api (FastAPI serving the built SPA), a shared volume for Parquet/DuckDB, healthchecks on both, .env consumed for optional phase-2 keys. On first boot the crawler front-loads the bootstrap sample — a built-in list of ~100 liquid symbols (CAC 40 + DAX 40 + 20 US mega-caps), overridable via CRIBLE_BOOTSTRAP_SAMPLE — so a first screen returns rows within hours, not weeks. docker compose up with zero keys yields a fully working system — the zero-key contract is exercised in CI.

**Acceptance criteria:**
- **Given** a machine with only Docker installed and no API keys in the environment **When** docker compose up runs **Then** both services report healthy within 120 seconds, the shared volume holds the DuckDB database and Parquet layers, and — with the default bootstrap sample (~100 symbols ≈ 700 budgeted requests) — a valid DSL screen (e.g. piotroski_f >= 0) returns at least one row through UI or CLI within 4 hours of first boot
- **Given** the ingest container crashes or is killed **When** compose restarts it **Then** crawling resumes from the persisted queue without re-fetching fresh symbols, and the api service keeps serving the last snapshot uninterrupted throughout
- **Given** an operator provides phase-2 keys via .env **When** the stack restarts **Then** the corresponding plugins activate without any image rebuild, and removing the keys returns the system to keyless operation

_Traceability — NFRs: NFR-003, NFR-006, NFR-009, NFR-013 · entities: Provider · interfaces: HTTP API, CLI_

## FR-009 — Preset screens _(should)_ [E67][E63]

Preset screens shipped as plain, visible, editable DSL strings — transparency is the product (the closed ranks of Stockopedia [E67] are the counter-model). Shipped presets with their exact DSL: piotroski-strong (piotroski_f >= 7), altman-safe (altman_z > 2.99), beneish-red-flags (beneish_m > -1.78), classic-value (price_to_earnings_ratio < 12 AND price_to_book < 1.5), quality (return_on_equity > 0.15 AND debt_to_equity < 1). Thresholds are visible in the DSL and editable — they are starting points, not hidden judgments. Available identically via CLI (--preset), API (GET /presets) and the SPA presets menu.

**Acceptance criteria:**
- **Given** the presets are shipped **When** GET /presets is called or crible screen --preset piotroski-strong runs **Then** each preset exposes its name, a one-line description and its complete DSL string, and running the preset is byte-for-byte equivalent to running that DSL string directly
- **Given** a user edits a preset's DSL in the UI **When** they run the edited query **Then** it executes as ordinary DSL (presets carry no hidden logic) and the edited text can be saved as a new named preset

_Traceability — NFRs: NFR-004, NFR-010 · entities: Preset · interfaces: HTTP API, Web App, CLI_

## FR-010 — ESEF XBRL Europe enrichment _(should)_ [E5][E15][E74][E113][E114][E35]

Europe-depth enrichment from filings.xbrl.org — the free, keyless ESEF repository (audited annual reports as xBRL-JSON with a JSON-API; explicitly an interim measure until ESAP, and NOT complete: some jurisdictions' filings, e.g. Germany and Ireland, are unavailable [E5][E15][E74]). Identity resolution: filings are indexed by LEI, the universe by Yahoo symbol + (sparse) ISIN — so enrichment applies to EU companies whose ISIN resolves to an LEI via GLEIF's free ISIN-to-LEI relationship files [E113][E114]; ISIN sparsity in FinanceDatabase is a known limitation [E35]. Audited figures are stored as provider='esef' facts; where audited and scraped values coexist for the same field/period, the audited value wins and material discrepancies are logged. Company detail links to the filing.

**Acceptance criteria:**
- **Given** an EU company whose universe ISIN resolves to an LEI (GLEIF mapping) with an ESEF annual report on filings.xbrl.org **When** the enrichment cycle processes it **Then** audited annual figures parsed from xBRL-JSON are stored as provider='esef' facts for that company, the snapshot marks the enriched fields' provenance as audited, and the company detail view links to the filing URL
- **Given** filings.xbrl.org or the GLEIF mapping is unreachable **When** the enrichment cycle runs **Then** yfinance-derived data remains intact, the cycle records the outage and resumes at the next cycle — no partial overwrite of existing facts
- **Given** an audited ESEF value and a Yahoo value differ by more than 5% (relative to the audited value) for the same field and period **When** reconciliation runs **Then** the audited value is used in the snapshot and the discrepancy is logged with both values, the field, the period and the filing reference
- **Given** an EU company with no ISIN or no ISIN→LEI resolution **When** the enrichment cycle considers it **Then** it is counted in an 'unmatched EU listings' metric visible in crible status (never an error) — making ESEF coverage honest and observable

_Traceability — NFRs: NFR-003, NFR-005, NFR-010 · entities: RawStatement, Company · interfaces: Provider Plugin API_

## FR-011 — Price freshness tiering (budget-aware, provenance-dated) _(should)_ [E36][E82][E105]

Prices ride the SAME Yahoo request budget as fundamentals — there is no free lunch: design-time verification (2026-07-07) found Stooq's CSV endpoints behind a JavaScript proof-of-work anti-bot wall, so no keyless bulk price path exists and none is assumed. Tiering: symbols in the priority price set (default: the bootstrap sample + European large caps, configurable size ~2,000) get daily price refreshes; all other symbols refresh opportunistically with leftover budget (weekly best-effort). Every price carries its as-of date; valuation ratios computed from a stale price expose price_asof provenance rather than pretending freshness. An optional stooq fallback plugin exists but ships DISABLED and is explicitly non-load-bearing (its wall may break it at any time). Yahoo price failures degrade politely (skip, keep last price, staleness visible) — the recurring hang/throttle failure modes are documented [E36][E82][E105].

**Acceptance criteria:**
- **Given** the priority price set is configured (default bootstrap sample + European large caps) **When** the price refresher runs its daily cycle within the global budget **Then** priority symbols end the cycle with prices at most one trading day old, non-priority symbols are refreshed only with leftover budget, and every snapshot valuation ratio exposes the price_asof date it was computed from
- **Given** Yahoo price fetches fail (3 consecutive rate-limit errors or a 30-second hang) **When** the price refresher encounters the failures **Then** it skips politely for the remainder of the cycle, affected symbols keep their last known price with staleness visible in provenance and status, and nothing busy-loops — the optional stooq plugin, if explicitly enabled, may be tried but its failure never blocks the cycle

_Traceability — NFRs: NFR-003, NFR-005 · entities: PriceBar, Provider · interfaces: Provider Plugin API_

## FR-012 — Company detail view _(should)_ [E58][E75][E1]

Company detail (SPA drawer + GET /company/{symbol}): full statement history as far as sources allow, every score with its complete component breakdown (the 9 Piotroski criteria pass/fail, the 8 Beneish components, Altman inputs), per-field provenance (provider + fetchedAt) and freshness. The transparency answer to Simply Wall St's polished-but-closed company pages [E58].

**Acceptance criteria:**
- **Given** a company present in the snapshot **When** its detail is opened in the UI or fetched via the API **Then** it shows the held statement history, each score with its full component breakdown (9 Piotroski criteria, 8 Beneish components, Altman inputs), and per-field provenance with provider and fetch timestamp
- **Given** a company in the universe that has not been crawled yet **When** its detail is opened **Then** the view shows the universe metadata (name, country, sector, exchange) plus its queue position / crawl ETA instead of an error

_Traceability — NFRs: NFR-004, NFR-010 · entities: Company, SnapshotRow, RawStatement · interfaces: Web App, HTTP API_

## FR-013 — Phase-2 free-key provider plugins _(could)_ [E72][E73][E115][E116][E65][E78]

Phase-2 free-key provider plugins behind the same Provider interface: financialreports (FinancialReports.eu — free official MCP server, OAuth, EU filings + normalized financials [E72][E73]), simfin (free bulk fundamentals for ~5,000 US stocks with 20+ years of history via API/bulk download [E115][E116]; free-tier data is delayed relative to paid — exact lag re-verified when the plugin is built), fmp_free and eodhd_free (schema validation against the future paid switch only). Strictly optional: without its key a plugin logs one 'disabled (no key configured)' line and the system behaves exactly as keyless.

**Acceptance criteria:**
- **Given** no provider keys are configured **When** the system starts **Then** each keyed plugin logs exactly one 'disabled (no key configured)' line, is reported as disabled in crible status, and every keyless flow behaves identically to a build without the plugins
- **Given** a valid SimFin key is configured **When** the ingest cycle runs **Then** SimFin bulk US fundamentals are stored as provider='simfin' raw facts alongside yfinance data without overwriting fresher facts, and provider health for simfin appears in crible status
- **Given** a configured key is invalid or expired **When** the plugin makes its first API call **Then** the plugin disables itself for the session with a clear log line naming the env var to fix, and the crawler continues keyless without error

_Traceability — NFRs: NFR-006, NFR-009, NFR-012 · entities: Provider, RawStatement · interfaces: Provider Plugin API_

## FR-014 — EODHD paid provider PRD + stub plugin _(could)_ [E111][E112][E61][E62]

The single planned paid upgrade, specced without paying: docs/prds/eodhd.md — a detailed PRD for EODHD's Fundamentals Data Feed. Grounded facts: the free tier grants 20 API calls/day and paid plans are required for more data [E111]; the pricing table is tier-based (free → paid, yearly discount) [E112]. The exact paid price/quota observed during planning (€59.99/mo, 100k calls/day on the 2026 pricing page) is recorded in the PRD as TO-REVALIDATE at purchase time, with endpoint schemas validated against the demo tickers using the existing free key, a field-by-field mapping to crible's raw schema, and the switch plan (set EODHD_KEY → plugin activates). docs/prds/fmp-ultimate.md documents FMP Ultimate as the evaluated-and-rejected alternative.

**Acceptance criteria:**
- **Given** the repository is checked out **When** a reader opens docs/prds/eodhd.md **Then** it contains the grounded free-tier facts (20 calls/day, paid upgrade required), the planning-time paid price/quota clearly marked to-revalidate, recorded sample payloads for the fundamentals and EOD endpoints captured via the free key's demo tickers, a field-by-field mapping to crible's raw schema, and the exact activation steps — and docs/prds/fmp-ultimate.md documents the rejected FMP alternative
- **Given** an EODHD key is configured **When** the stub plugin initializes **Then** it validates the key with a single metadata call and reports the detected tier — a free-tier key yields 'insufficient tier for fundamentals' and the plugin stays disabled — proving the switch path end-to-end without a paid subscription

_Traceability — NFRs: NFR-006, NFR-012 · entities: Provider · interfaces: Provider Plugin API_

## FR-015 — Composite quality/value/momentum rank across the universe _(could)_ [S21][S22]

Rank the screening universe on a single composite score built from the fundamentals crible already computes (Piotroski F, Altman Z, per-share value ratios, price momentum), in the spirit of Stockopedia's StockRanks — the paid market's headline differentiator [S21][S22] (see docs/market/2026-07-12/REPORT.md). Each pillar (Quality / Value / Momentum) is a percentile rank within a peer group (e.g. region×sector) over the existing snapshot columns; the composite is a documented, transparent blend. No new data source and no API key — computed from the wide snapshot in DuckDB. Every rank links back to its component values (provenance-consistent with FR-003/FR-012). GATED: market-evidenced, spec-first; implementation awaits explicit go-ahead.

**Acceptance criteria:**
- **Given** a published snapshot with the quality/value/momentum input columns for a peer group **When** the rank step runs over the universe **Then** each company receives quality_rank, value_rank, momentum_rank (0–100 percentiles within its peer group) and a composite_rank blending them by a documented, reproducible formula; re-running on the same snapshot yields identical ranks
- **Given** a company is missing an input for one pillar **When** ranks are computed **Then** that pillar's rank is NULL (never imputed) and the composite is computed from the available pillars with the omission recorded in provenance — no fabricated rank
- **Given** a rank is shown in the UI **When** the user opens the company drawer **Then** each pillar rank links to the underlying component values, consistent with the score-breakdown transparency of FR-012

_Traceability — NFRs: — · entities: — · interfaces: —_
