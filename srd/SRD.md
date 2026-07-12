# Software Requirements Document — crible

_Level: complex · generated: 2026-07-06T21:32:15.981Z_

# Vision

**Product:** crible

## Problem
Serious fundamental screening across ALL of Europe (and the world) is locked behind paid feeds (EODHD gates fundamentals behind paid plans [E111]; FMP's worldwide coverage sits in its top tier — planning-time prices recorded in docs/prds/, re-validated before any purchase); free tools are US-centric (Finviz), shallow, or SaaS with no control over data, formulas or universe. Investors who want transparent, reproducible fundamental screens over European small/mid caps have no self-hosted option.

## Target users
- Individual fundamental investor (Maxime) screening European + worldwide equities with value/quality/forensic criteria
- Technical tinkerer who self-hosts the stack, tunes the crawl priorities and writes custom screens via the DSL or SQL

## Value proposition
A screener you own: worldwide universe with Europe-depth, 100% functional with zero API keys (guaranteed forever), transparent formulas (financetoolkit + published score definitions), audited ESEF figures for EU names, DuckDB-fast filtering, and a single optional paid switch (EODHD) ready when deeper history is wanted — never required.

## Success metrics
- Screen the full worldwide snapshot (~161k equities × ~200 columns) in under 1 second locally — enforced by a CI benchmark on a synthetic full-size snapshot
- Europe as depth priority: European listings are always crawled first and, where an ISIN→LEI mapping resolves, enriched with audited ESEF XBRL figures (coverage partial until ESAP opens)
- Zero-key contract: a dedicated CI job runs the full E2E suite with no API keys configured and must pass for every release
- Rolling keyless crawl under one hard request budget (fundamentals + prices): the Europe tier refreshes within a quarter (~5–7 weeks/sweep), priority symbols get daily prices, worldwide fundamentals complete best-effort (≈ 2 sweeps/year); coverage, freshness and price_asof are always visible in crible status
- One-switch paid upgrade path: the EODHD Fundamentals plugin is specced and stubbed so a single key upgrade replaces the fragile yfinance link without touching the rest

# Scope

## In scope
- Worldwide universe built from FinanceDatabase
- Rolling prioritized keyless ingestion (yfinance)
- Ratio and score computation into a wide snapshot
- Filter DSL compiled to DuckDB SQL
- CLI (crible)
- HTTP API (FastAPI)
- React/Vite SPA
- Docker Compose deployment
- Preset screens
- ESEF XBRL Europe enrichment
- Stooq price fallback
- Company detail view

## Out of scope
- Technical analysis, chart patterns or momentum signals
- Portfolio management, backtesting or performance tracking
- Trade execution or brokerage integration
- Real-time or intraday data
- Multi-user SaaS: no accounts, no auth, single self-hosted operator
- Buying any paid data plan in v1 (paid providers are specced as PRDs only)
- Mobile apps

## Assumptions
- Team: solo developer (Maxime), TDD workflow (red-green-refactor).
- Timeline: v1 zero-key end-to-end first; phase 2 (free-key plugins) after.
- Budget: €0 for data in v1; the zero-key mode is a permanent, CI-enforced contract (empty-env E2E gate), not a marketing absolute.
- Compliance: MIT license; polite crawling under a hard request budget; English codebase and docs.
- Zero-key mode depends on four external keyless endpoints (FinanceDatabase, Yahoo via yfinance, filings.xbrl.org, GLEIF ISIN→LEI mapping files) plus the optional disabled-by-default Stooq fallback; their availability is monitored, an extended outage degrades to serving the last snapshot with staleness visible — fundamentals have no keyless fallback for Yahoo (that is exactly the EODHD switch, FR-014).

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

# Non-functional requirements

## NFR-001 — performance [E4][E88]

Screening is interactive: any valid DSL screen over the full snapshot answers in about a second — the enforceable contract is the NFR-008 CI benchmark; local hardware figures are guidance.

- **Metric:** In the NFR-008 CI benchmark environment: p95 < 1 s end-to-end for any DSL screen over the synthetic full-size snapshot; API POST /screen p95 < 500 ms warm; GET /company/{symbol} p95 < 300 ms.

## NFR-002 — security [E13]

No auth by design (single self-hosted operator, ADR-0002); the attack surface is the DSL and the provider keys. DSL input can never become SQL; keys never leave the environment.

- **Metric:** DSL compiles to parametrized SQL over a strict column whitelist (property-tested, see NFR-011); API binds to localhost/compose network by default; provider keys read only from environment/.env — never baked into images, logged, or echoed in errors; Python and npm dependencies audited in CI.

## NFR-003 — reliability [E82][E36]

The system degrades gracefully and recovers from transient failures without data loss: the crawler survives kills and rate limits; readers never see partial data.

- **Metric:** Crash-resume without duplicate fetches inside freshness windows; snapshot publication is atomic (write-new-then-swap; a reader never observes a half-written snapshot); raw Parquet writes are write-temp-then-rename; a 24 h crawler soak run completes with zero unhandled exceptions.

## NFR-004 — usability [E75]

An operator reaches a first successful screen without reading source code; every error names the next action.

- **Metric:** Clean machine → first successful screen in ≤ 3 commands (docker compose up; wait; run a preset) and ≤ 4 h on first boot with the default bootstrap sample; every CLI/API/UI error message names the failing input or the command to run next; presets give one-click value on first contact.

## NFR-005 — observability [E36]

The operator can answer 'what is the crawler doing, how fresh is my data, am I inside the rate budget?' without reading code.

- **Metric:** Structured JSON log line for every provider fetch (symbol, provider, latency, outcome); crible status and GET /status expose universe count, fundamentals coverage %, freshness histogram, rolling req/h and per-provider health; per-symbol consecutive-failure counts are queryable.

## NFR-006 — cost [E111][E112][E115]

Data cost is €0 in v1 and can only ever grow by one explicit, documented switch (EODHD).

- **Metric:** Zero paid dependencies in v1 (keyless sources only; EODHD free tier is 20 calls/day with paid plans gated [E111]); the only planned recurring cost is the EODHD Fundamentals feed behind the EODHD_KEY switch, price recorded and re-validated in docs/prds/eodhd.md; infra = any single Docker host.

## NFR-007 — rate-limit compliance [E105][E107][E108]

The crawler never exceeds its configured upstream request budget — polite crawling is a hard constraint of the keyless design, because Yahoo demonstrably rate-limits scrapers (429s and YFRateLimitError are endemic in the wild [E105][E107][E108]).

- **Metric:** Rolling 60-minute upstream request count ≤ budget (default 330 — a conservative design choice, configurable), counting every statement/profile/price request individually; enforced by a token bucket and asserted in tests under simulated load; 0 budget violations in a 24 h soak; on HTTP 429 the backoff doubles from 1 min to a 15 min cap with ±20% jitter (design parameters, property-tested).

## NFR-008 — performance (screening engine) [E88]

The filter engine keeps its millisecond-class promise as the snapshot grows.

- **Metric:** CI runs the DSL engine against a synthetic full-size snapshot (161k rows × 200 columns): every preset and a battery of generated screens must complete with p95 < 1 s; the DuckDB query plan for any DSL screen touches only the snapshot (no row-by-row Python loop).

## NFR-009 — portability (zero-key contract) [E2][E5]

Zero-key operation is a guaranteed, permanent contract — not a degraded mode. Everything core runs from one docker compose up with no accounts and no external services.

- **Metric:** The release-gating CI runs the entire offline test suite with NO provider keys configured — the enforced zero-key gate; the live compose E2E (real Yahoo crawl → first screen) is a documented manual/nightly procedure because it spends real request budget (first executed and passed 2026-07-07); docker compose up on a clean machine requires nothing but Docker; removing every key returns a configured install to fully working keyless operation.

## NFR-010 — data quality & transparency [E1][E67][E5]

Every number can explain itself: formula, source and fetch time. Audited beats scraped. This is the product's moat against closed SaaS ranks [E67].

- **Metric:** Every snapshot cell is traceable to (provider, fetchedAt) and a published formula (financetoolkit's open implementations [E1] or crible's own tested code); Piotroski/Altman/Beneish are unit-tested against published examples; ESEF audited values override scraped values, with >5% discrepancies logged (FR-010).

## NFR-011 — security (DSL injection)

No DSL input, however hostile, can execute unintended SQL.

- **Metric:** Property-based tests feed ≥ 1,000 generated/mutated inputs per run: any input that parses must compile to SQL referencing only whitelisted columns with every literal bound as a parameter; any input that does not parse must execute nothing. A curated corpus of injection payloads is asserted rejected.

## NFR-012 — maintainability

Components stay isolated (universe / ingest / compute / store / api / ui) and the provider seam is the extension point — adding a source never touches the core. (A pure design commitment, verified by construct verify --strict and the plugin test suite.)

- **Metric:** Adding a data provider = one plugin module implementing the Provider interface + its tests, zero changes to scheduler/compute/API; every FR has at least one test whose name carries the FR id (verified by construct verify --strict); TDD red-green-refactor throughout.

## NFR-013 — privacy [E58]

Fully self-hosted: the instance calls data sources, and nothing else. No telemetry, ever.

- **Metric:** Zero outbound requests except to configured data-source endpoints (asserted by an egress test using a recording proxy in CI); no analytics/telemetry libraries in either lockfile; all data lives under the operator's data directory/volume.

# System context

crible serves a fundamental investor and self-hosting tinkerer screening European + worldwide equities. Pipeline: universe (FinanceDatabase CSVs → DuckDB) → ingest (rolling prioritized keyless crawler over yfinance — fundamentals AND prices under one request budget — plus ESEF XBRL audited figures joined via GLEIF ISIN→LEI, behind a Provider plugin seam; raw versioned Parquet) → compute (financetoolkit ratios + Piotroski/Altman + in-house Beneish → wide snapshot Parquet) → store/query (DuckDB over Parquet; DSL → parametrized SQL) → surfaces (Typer CLI, FastAPI HTTP API, React/Vite SPA) — all packaged as two Docker Compose services (ingest, api) sharing one data volume. Keyless external endpoints: FinanceDatabase, Yahoo, filings.xbrl.org, GLEIF (+ optional disabled Stooq fallback). Each external source is isolated behind the Provider Plugin API (ADR-0003, ADR-0004).

# Data model

_Seeded by inference from the brief — verify each entity and extend attributes during authoring._

## Company

| Attribute | Type |
|---|---|
| symbol | identifier (Yahoo-suffixed ticker, PK) |
| name | string |
| isin | string (nullable) |
| country | string (ISO-3166 alpha-2 — the DSL filter code) |
| country_name | string (original FinanceDatabase name) |
| region | string (europe \| us \| world — drives crawl priority) |
| sector | string |
| industry | string |
| exchange | string |
| currency | string |
| marketCapClass | string (Large/Mid/Small — categorical from FinanceDatabase) |
| delisted | boolean |
| updatedAt | timestamp |

_Referenced by: FR-001, FR-006, FR-007, FR-010, FR-012_

## RawStatement

| Attribute | Type |
|---|---|
| symbol | ref Company |
| provider | string (yfinance \| esef \| simfin \| financialreports \| …) |
| statementType | enum (income \| balance \| cashflow) |
| freq | enum (annual \| quarterly) |
| period | string (fiscal period end) |
| payload | json (as-fetched fields) |
| fetchedAt | timestamp |
| parquetPath | string (versioned raw layer file) |

_Referenced by: FR-002, FR-010, FR-012, FR-013_

## PriceBar

| Attribute | Type |
|---|---|
| symbol | ref Company |
| date | date |
| open/high/low/close | number |
| volume | number |
| provider | string (yfinance \| stooq) |

_Referenced by: FR-002, FR-011_

## SnapshotRow

| Attribute | Type |
|---|---|
| symbol | ref Company |
| period | string (fiscal period) |
| ratios | ~200 numeric columns (financetoolkit + derived) |
| piotroskiF | int 0–9 (+ 9 criterion booleans) |
| altmanZ | number (+ inputs) |
| beneishM | number (+ 8 components) |
| provenance | json (per-field provider + fetchedAt) |
| computedAt | timestamp |

_Referenced by: FR-003, FR-004, FR-005, FR-006, FR-007, FR-012_

## CrawlTask

| Attribute | Type |
|---|---|
| symbol | ref Company |
| priority | int (0 = europe, 1 = us large caps, 2 = world) |
| nextDue | timestamp (freshness-driven) |
| lastCrawledAt | timestamp |
| consecutiveFailures | int |
| status | enum (pending \| inflight \| done \| parked) |

_Referenced by: FR-002_

## Preset

| Attribute | Type |
|---|---|
| id | identifier (slug) |
| name | string |
| description | string |
| dsl | string (the full, visible query) |

_Referenced by: FR-004, FR-006, FR-009_

## Provider

| Attribute | Type |
|---|---|
| id | identifier (yfinance \| esef \| stooq \| simfin \| financialreports \| fmp_free \| eodhd_free \| eodhd) |
| kind | enum (keyless \| free-key \| paid) |
| enabled | boolean (derived: keyless → true; keyed → key present & valid) |
| keyEnvVar | string (nullable) |
| health | json (last success, error counts, budget usage) |

_Referenced by: FR-002, FR-008, FR-011, FR-013, FR-014_

# Interfaces

_Seeded by inference from the brief — verify each surface and define its contract during authoring._

## CLI _(cli)_

The crible command (Typer): screen (DSL → table/CSV), ingest (bootstrap/once/loop), compute, status, export. Exit codes and stderr messages are part of the contract; same DSL semantics as the API.

_Related: FR-001, FR-002, FR-003, FR-004, FR-005, FR-008, FR-009_

## HTTP API _(api)_

FastAPI: POST /screen, GET /screen.csv, GET /presets, GET /company/{symbol}, GET /status, GET /healthz; serves the built SPA at /. JSON errors carry message + hint; 422 for DSL errors, 404 for unknown symbols, never 5xx for user input.

_Related: FR-004, FR-006, FR-007, FR-008, FR-009, FR-012_

## Web App _(ui)_

React/Vite SPA: query bar (DSL), TanStack results grid (sort, column picker, CSV export), presets menu, company-detail drawer, status view. Talks only to the HTTP API on the same origin.

_Related: FR-007, FR-009, FR-012_

## Provider Plugin API _(api)_

Internal contract every data source implements: capabilities() (statements/prices/coverage), fetch_statements(symbol), fetch_prices(symbols), health(). Keyless providers are always on; keyed providers self-disable without their env key (one log line, no crash). External endpoints behind it — keyless: Yahoo via yfinance, filings.xbrl.org JSON-API, GLEIF ISIN→LEI mapping files, optional Stooq fallback (disabled by default); phase 2 keyed: FinancialReports.eu, SimFin, FMP free, EODHD free; future: EODHD paid.

_Related: FR-002, FR-010, FR-011, FR-013, FR-014_

# Architecture decisions

# 0001. Primary technology stack

- **Status:** accepted

## Context
Solo developer, TDD, zero-ops self-hosting, and a data problem shaped like: a 161k-symbol universe [E2], per-ticker scraping through a fragile rate-limited source [E3], columnar analytics over ~200 ratio columns, and a dense data UI. The stack must minimise moving parts while keeping every layer replaceable.

## Decision
Python 3.12 for universe/ingest/compute/API (the finance OSS ecosystem is Python: financetoolkit [E1][E8], financedatabase [E2], yfinance [E3][E98]); DuckDB over Parquet (pyarrow) as the only datastore — embedded, zero-ops, columnar, millisecond screens [E4][E12][E10]; FastAPI [E13] + Typer [E92] as the two entry points sharing one core; React 18 + Vite + TypeScript with TanStack Table for the SPA [E18][E19][E21]; pytest for TDD [E95]; Docker Compose for deployment [E94]. [E1][E2][E3][E4][E12][E13][E19][E77][E88][E90][E92][E94][E95]

## Consequences
One language for the whole data path; no database server, migrations or queue to operate; the SPA is the only build step. DuckDB is single-writer — the ingest and API processes share data via Parquet files and an atomic snapshot swap rather than concurrent writes. Python-side compute must stay vectorised (pandas/DuckDB) to hold the performance NFRs.

## Alternatives considered
OpenBB Platform as an aggregation façade [E90] — rejected: planning-time verification of its docs showed the free equity-fundamentals path routes through yfinance (same rate limits and shallow history as going direct) and its screener providers (finviz, fmp, nasdaq, yfinance) offer no European-first screening; recorded as a design-time verification, not a dossier citation. Postgres + Celery + React (the xang1234/stock-screener architecture) — rejected: real prior art shows preset-filter timeouts and index churn at exactly this workload [E77][E88]. A Rust custom engine — rejected: re-implements what DuckDB already does in-process.

# 0002. Self-hosting, zero-key contract and data ownership

- **Status:** accepted

## Context
Every credible fundamental screener with European coverage is subscription SaaS with closed formulas (Stockopedia [E67], Simply Wall St [E58], Uncle Stock [E59]); data feeds worth using are pay-gated — EODHD's free tier grants 20 API calls/day with paid plans required for more data [E111], the observed paid pricing being recorded to-revalidate in docs/prds/eodhd.md. The product's reason to exist is owning the screener: data, formulas, universe.

## Decision
Ship as a self-hosted Docker Compose deployment where the host owns all data. The zero-key mode (FinanceDatabase + yfinance + filings.xbrl.org + Stooq) is a permanent, CI-enforced contract — every core flow works with no account, no key, no external service. No auth layer: single operator, bound to the local network; no telemetry. [E58][E59][E61][E67][E98]

## Consequences
Data residency and polite-crawling compliance are the operator's responsibility (documented); the free path accepts Yahoo's shallow statement history (a handful of annual periods — observed behaviour, validated in integration tests, no contractual depth exists for a scraped source) and best-effort worldwide freshness as the price of €0; a hosted multi-tenant SaaS is explicitly out of scope. The zero-key guarantee is expressed as a testable contract: the release-gating CI job runs the E2E suite with no keys configured.

## Alternatives considered
Hosted SaaS — rejected: recreates the incumbents' model and their privacy/lock-in problems [E67][E58]. Mandatory free-tier keys (FMP/EODHD free) in v1 — rejected: their free tiers contribute nothing for Europe (US-only / no fundamentals [E61]) and would break the zero-key promise.

# 0003. Persistence: DuckDB over layered Parquet with atomic snapshot swap

- **Status:** accepted

## Context
Three data shapes coexist: append-heavy raw fetches (per provider, re-parseable), a wide computed snapshot the screener hammers, and small operational state (crawl queue, provider health). Readers (API/CLI) and the writer (ingest/compute) are separate processes [E4].

## Decision
A layered store on one shared volume: (1) raw layer — immutable, versioned Parquet per provider/fetch (write-temp-then-rename), the durable source of truth that survives any recompute; (2) snapshot layer — the wide company × period Parquet, published by atomic swap (write new, fsync, rename; readers re-open on change); (3) operational state — a small DuckDB database owned by the ingest process. The API opens Parquet read-only through DuckDB [E12][E10]; every external integration writes only through its provider adapter into the raw layer. [E4][E10][E11][E12][E88]

## Consequences
No write contention (single-writer per layer); any snapshot is reproducible from the raw layer; corruption recovery = delete snapshot, recompute. Cross-layer consistency is eventual (a screen can lag a fetch by one compute cycle) — acceptable for quarterly-moving fundamentals and surfaced via freshness metadata.

## Alternatives considered
One shared DuckDB database for everything — rejected: concurrent writer/reader processes across containers fight DuckDB's single-writer model. Postgres — rejected: an operational row store doing an analytical job, plus a server to operate (see ADR-0001 and the xang1234 timeout lesson [E88]). Event sourcing — deferred: the raw Parquet layer already gives replayability without the machinery.

# 0004. Keyless ingestion: rolling prioritized crawl under a hard Yahoo rate budget

- **Status:** accepted

## Context
Yahoo has no bulk fundamentals endpoint — statements are per-ticker, per-statement-type calls — and rate-limits scrapers aggressively: bulk downloads trip YFRateLimitError ('Too Many Requests. Rate limited. Try after a while.') [E107][E108], long-running pulls crash or hang [E36][E82], and the core rate-limit issue is documented at length [E105]. yfinance rides curl_cffi with impersonated sessions and must own its session [E52]. No public figure exists for a 'safe' rate — the budget is a deliberately conservative design parameter, not a claimed tolerance. Design-time verification (2026-07-07) also found Stooq's CSV endpoints behind a JavaScript proof-of-work wall: there is NO keyless bulk price alternative, so prices must share the Yahoo budget.

## Decision
A continuous priority-queue crawler with a global token bucket (default 330 upstream requests per rolling hour, configurable), counting every upstream call (a fundamentals sweep ≈ 7 requests per symbol; every price request counts too). Jittered exponential backoff on 429 (1 min → 15 min cap), a per-request watchdog against hangs, persisted queue state for crash-resume, freshness-driven revisits (quarterly statements; daily prices for the priority tier only — FR-011). Priority tiers: Europe → US large caps → rest of world. Europe's cross-sectional depth is compensated by the audited ESEF layer (FR-010) joined via the keyless GLEIF ISIN→LEI mapping [E113][E114]. [E105][E107][E108][E52][E36][E82][E113][E114]

## Consequences
The honest arithmetic at the default budget (7,900 req/day): ~2,000/day reserved for daily priority-tier prices leaves ~5,900/day ≈ 840 fundamentals sweeps/day — the Europe tier (tens of thousands of listings) completes in roughly 5–7 weeks, inside the quarterly contract; the full ~161k worldwide universe takes ≈ 6+ months per sweep, so rest-of-world coverage is explicitly best-effort in zero-key mode. Non-priority valuation ratios may rest on week-old prices — visible via price_asof provenance, never silent. Coverage and freshness are always visible in crible status; the single-switch EODHD upgrade (FR-014) is the documented cure when worldwide freshness is wanted. The crawler is a long-lived, stateful, polite process; an extended Yahoo block degrades to serving the last snapshot with staleness badges, never to hammering.

## Alternatives considered
Parallel scraping with proxy rotation — rejected: hostile, fragile, and the documented blocking [E105] shows how it ends. Paid feed from day one — rejected: breaks the €0 v1 budget and the zero-key contract (ADR-0002). On-demand fetching only (no crawl) — rejected: screening needs the full cross-section precomputed. Stooq as a budget-free bulk price path — rejected after design-time verification (2026-07-07): its endpoints sit behind a JS proof-of-work wall; it survives only as an optional, disabled-by-default, non-load-bearing fallback plugin.

# Design system

# Design principles

- The table is the hero — information density over decoration; every pixel of chrome must earn its place against one more visible row.
- Numbers first: tabular figures, right-aligned, monospaced; color encodes meaning (gain/loss/flag), never mood.
- Dark mode is the primary theme; light is the variant. Both ship, both meet contrast.
- Transparency in the UI itself: every score links to its components, every value to its provenance — no unexplained numbers.
- Consistency over novelty — reuse tokens and components before inventing new ones.
- Accessible by construction: dense ≠ inaccessible; every flow works with keyboard and assistive tech.
- One color means "interactive": forge amber marks actions, focus and selection — semantic colors (gain/loss/warn) encode data meaning, never mood, and never appear on chrome.

## Content & voice

- Voice & tone: sober, precise, numbers-forward; French product name, English UI.
- Label actions with the outcome the user gets, not the system operation behind it.
- Error messages state what happened, why, and the next step — never blame the user.
- Empty states teach the first useful action; success states confirm exactly what changed.

# Design tokens

## color

| Token | Value | Notes |
|---|---|---|
| color.bg | oklch(0.13 0 0) | App background — neutral pure black, never tinted. Light « paper terminal »: oklch(1 0 0). |
| color.bg-raised | oklch(0.17 0 0) | Topbar, panels, drawers, sticky header. Light: oklch(0.955 0.004 75). |
| color.fg | oklch(0.93 0.012 75) | Primary text — warm chalk on slate. Light: oklch(0.25 0.015 60). |
| color.muted | oklch(0.65 0.015 75) | Secondary text, borders, disabled (≥4.5:1). Light: oklch(0.47 0.015 60). |
| color.primary | oklch(0.75 0.15 55) | Forge amber — the ONLY interactive signal: actions, links, focus, selection. Light: oklch(0.55 0.13 55). |
| color.on-primary | oklch(0.15 0.03 55) | Text on amber fill. Light: oklch(1 0 0). |
| color.accent | oklch(0.62 0.1 240) | Cooled steel — provenance, info links, neutral badges. Light: oklch(0.45 0.1 240). |
| color.gain | oklch(0.72 0.15 150) | Positive deltas, passing criteria — never colour alone (sign required). Light: oklch(0.52 0.14 150). |
| color.loss | oklch(0.64 0.2 22) | Negative deltas, failing criteria. Light: oklch(0.52 0.19 25). |
| color.danger | oklch(0.64 0.2 22) | Destructive, errors (= loss). Light: oklch(0.52 0.19 25). |
| color.warn | oklch(0.8 0.13 90) | Stale-data badges, Beneish red flags — yellow, distinct from amber. Light: oklch(0.55 0.12 90). |

## typography

| Token | Value | Notes |
|---|---|---|
| font.sans | system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif | Labels, prose. System stack only — nothing fetched or bundled (NFR-013). |
| font.mono | ui-monospace, 'SF Mono', SFMono-Regular, Menlo, 'Cascadia Mono', Consolas, 'Liberation Mono', monospace | The tool's voice: wordmark, numerals (tabular-nums), DSL query bar, provenance. |
| scale.body | 13px / 1.45 | Dense default; grid cells. |
| scale.h1 | 20px / 1.3 | Screen titles — chrome stays small. |
| scale.small | 11px / 1.35 | Badges, provenance, freshness. |

## spacing

| Token | Value | Notes |
|---|---|---|
| space.1 | 4px |  |
| space.2 | 8px |  |
| space.3 | 12px |  |
| space.4 | 16px |  |
| space.6 | 24px |  |
| space.8 | 32px |  |

## radius

| Token | Value | Notes |
|---|---|---|
| radius.sm | 2px | Inputs, badges — instrument, not toy. |
| radius.md | 4px | Buttons, pills. |
| radius.lg | 8px | Drawers, dialogs only. |

## elevation

| Token | Value | Notes |
|---|---|---|
| shadow.sm | 0 1px 2px rgba(0,0,0,0.4) | Dark; light: rgba(0,0,0,0.06). |
| shadow.md | 0 8px 24px rgba(0,0,0,0.5) | Drawer/dialog; light: rgba(0,0,0,0.12). |
| shadow.glow | 0 0 0 1px var(--color-primary), 0 0 12px color-mix(in oklch, var(--color-primary) 25%, transparent) | Phosphor signature — focus/active states only (query bar, active pill). |

## z

| Token | Value | Notes |
|---|---|---|
| z.sticky | 10 |  |
| z.dropdown | 15 |  |
| z.backdrop | 20 |  |
| z.drawer | 30 |  |
| z.toast | 40 |  |
| z.tooltip | 50 |  |

## motion

| Token | Value | Notes |
|---|---|---|
| motion.fast | 120ms ease-out | Hover, focus, sort, glow-in. |
| motion.base | 200ms ease-out | Drawer; 0ms under prefers-reduced-motion. |

> The machine-readable token set is in `design/design-tokens.json`.

# Components

_Seeded from the functional requirements — verify each component and its states during authoring._

## App Shell & Navigation [E75]

Slim top bar (product name, status pill with coverage/freshness, presets menu, theme toggle) framing the full-height screener.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007

## Query Bar (DSL editor)

Monospaced input for the DSL with syntax-aware validation, inline error (token + position + hint), field autocomplete from the whitelist, and run-on-Enter.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-004, FR-007

## Results Grid [E19][E20]

TanStack Table: virtualised rows, sortable columns, sticky header, tabular-numeral cells with gain/loss coloring, row click → detail drawer.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-004, FR-007

## Column Picker

Searchable multi-select over the ~200 snapshot columns, grouped by family (valuation, profitability, solvency, scores…); persists locally.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007

## Presets Menu [E67]

Named screens with description and the full DSL visible; one click loads the DSL into the query bar for editing (never hidden logic).

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-009, FR-007

## Company Detail Drawer [E58]

Right-side drawer: profile header, statement history table, score cards with component breakdowns (9 Piotroski / 8 Beneish / Altman inputs), provenance + freshness badges, ESEF filing link.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-012, FR-010, FR-007

## Status Dashboard

Coverage %, freshness histogram, rolling req/h vs budget, per-provider health — the operator's window into the rolling crawl.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-002, FR-006, FR-013

## Export Button

Downloads the current result set (rows + visible columns) as CSV via GET /screen.csv; disabled with reason when no results.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007

## Feedback & Notifications

Inline banners and toasts for API errors (with hint), long-running states and export completion; polite live regions.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007, FR-006

## Empty & Error States

First-run (universe loading, crawl progress with ETA), no-match (suggest loosening clauses), API-down and not-yet-crawled company states — each teaches the next action.

- **States:** default, hover, focus, active, disabled, loading, empty, error
- **Realises:** FR-007, FR-012, FR-006

# Screens & flows

## Shell & navigation

One-window shell, no sidebar (the width belongs to the table). Topbar, left to right: wordmark (sieve glyph + « crible » in mono) · view switcher pills Screener / Status / Providers (hash-routed #/, #/status, #/providers) · ingest status pill · theme toggle (dark ⇄ light « paper terminal », persisted in localStorage, initial default from prefers-color-scheme). The company drawer stays an overlay over whichever view is active and keeps its deep-linkable route. Keyboard: `/` focuses the DSL query bar, `Esc` closes the drawer, view pills are tabbable.

## Screens

| Screen | Purpose | Requirements |
|---|---|---|
| Screener | The home screen: query bar + presets + results grid + export. Where 95% of time is spent; everything else is a drawer or a pill away. | FR-004, FR-007, FR-009 |
| Company detail | Drawer (deep-linkable route) over the screener: statements, score breakdowns, provenance, ESEF filing link. | FR-012, FR-010 |
| Ingest & coverage status | The crawl observatory: universe coverage, freshness histogram, rate-budget gauge, provider health, recent failures. | FR-002, FR-006, FR-013 |
| Providers & settings | Read-only provider inventory (keyless / keyed-off / keyed-on with health), pointer to .env configuration and the EODHD upgrade path; theme preference. | FR-013, FR-014 |

## User flows

### First run (zero-key) _(FR-001, FR-002, FR-008, FR-009, FR-007)_

1. docker compose up with no keys
2. The screener never shows a blank grid: its first-run empty state teaches — bootstrap/crawl progress inline (coverage %, ETA) with a link to the Status view
3. Status shows universe bootstrap then Europe-first crawl progress with ETA
4. First preset screen returns rows on the ingested sample
5. Grid renders; the operator saves a first custom DSL screen

### Screen & export _(FR-004, FR-007)_

1. Type or edit DSL in the query bar (autocomplete from whitelist)
2. Run: results in < 1 s, sortable, column picker adjusts the view
3. Export CSV of exactly what is displayed

### Investigate a company _(FR-012, FR-010)_

1. Click a result row — the detail drawer opens without losing the result set
2. Read score component breakdowns and per-field provenance
3. Follow the ESEF filing link for the audited source

### Enable a phase-2 provider _(FR-013, FR-008)_

1. Add the provider key to .env and restart the stack
2. Provider flips to enabled in the status view with live health
3. New facts appear with their provider provenance

### Watch the rolling crawl _(FR-002, FR-006)_

1. Open the status screen
2. Check coverage %, freshness histogram and req/h vs budget
3. Drill into recent failures and parked symbols

# Accessibility

**Target standard:** WCAG 2.2 AA

## A11Y-001 — Every interactive control is fully keyboard operable.

**Acceptance criteria:**
- **Given** a user navigates with the keyboard only **When** they tab through any flow **Then** every interactive control is reachable, operable and follows a logical focus order

## A11Y-002 — Focus is always visible.

**Acceptance criteria:**
- **Given** an element receives keyboard focus **When** the user is navigating **Then** a visible focus indicator is shown and meets the non-text contrast minimum

## A11Y-003 — Colour contrast meets the target standard.

**Acceptance criteria:**
- **Given** any text or essential UI element **When** it is rendered in any supported theme **Then** contrast meets the target (≥ 4.5:1 for body text, ≥ 3:1 for large text and UI)

## A11Y-004 — Every control and image exposes an accessible name.

**Acceptance criteria:**
- **Given** a form control, icon-only button or meaningful image **When** it is read by assistive technology **Then** it exposes a programmatic label/name and images carry meaningful alt text (decorative images are hidden)

## A11Y-005 — Structure and async changes are conveyed semantically.

**Acceptance criteria:**
- **Given** a screen is parsed by a screen reader **When** the user explores it **Then** headings, landmarks and roles convey the structure and live regions announce asynchronous changes

## A11Y-006 — Reduced motion and zoom are respected.

**Acceptance criteria:**
- **Given** a user prefers reduced motion or zooms to 200% **When** they use the product **Then** non-essential motion is reduced or disabled and content reflows without loss of content or function

# Competitive landscape

## Competitors

| Product | Note | Evidence |
|---|---|---|
| Finviz | The reference free screener, US-market presets and thematic filters [E63][E71]; planning research found no European exchange coverage — Europe is exactly the gap crible fills. | [E63][E71] |
| TradingView Stock Screener | Broad multi-market SaaS screener [E76]; subscription-gated depth, closed formulas, not self-hostable (product model, not a snippet claim). | [E76] |
| Simply Wall St | Fundamental-analysis SaaS with praised global coverage for value investors [E58][E64]; a closed subscription product — crible's company detail is the transparent, self-hosted answer. | [E58][E64] |
| Stockopedia | Quality/Value/Momentum ranks over European + global markets, subscription SaaS. Its StockRanks are precisely the kind of closed composite score crible replaces with visible, editable DSL presets. | [E67][E68] |
| Uncle Stock | 'Professional stock screening for DIY investors' — the closest functional cousin for European fundamental screening, with backtesting; subscription, closed, not self-hostable. | [E59][E60] |
| screener.in | India's fundamental screener — the UX benchmark: information-dense tables, transparent query language, fast. crible aims for this feel over a worldwide, Europe-deep universe. | [E75] |
| EODHD Screener API | The data vendor's own screener endpoint. Fundamentals are pay-gated: the free tier grants 20 API calls/day and more data requires a paid plan [E111][E112]; the Fundamentals-feed price observed during planning is recorded to-revalidate in docs/prds/eodhd.md (FR-014) — the single paid upgrade crible keeps on standby, not a v1 dependency. | [E111][E112][E61] |
| Find My Moat | A curated directory of investment research tools [E104] that surfaced FinancialReports.eu in planning research — the pointer to the free EU-filings MCP server crible integrates in phase 2 (FR-013) [E69][E70]. | [E104][E69][E70] |
| OpenBB Platform | Open-source multi-provider financial data platform [E90]. Considered as a foundation and rejected (ADR-0001): planning-time docs verification showed its free fundamentals path is yfinance underneath and its screener providers cannot screen Europe. | [E90] |

## Comparable open-source projects

| Project | Note | Evidence |
|---|---|---|
| [JerBouma/FinanceToolkit](https://github.com/JerBouma/FinanceToolkit) | Core dependency: 200+ transparently-implemented ratios + Piotroski & Altman (Beneish absent — crible implements it). Yahoo backend supported via enforce_source; built for portfolios, so crible owns batching/backoff. | [E1][E6][E7][E8][E9][E39] |
| [JerBouma/FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) | The universe: 160,995 equities across 117 countries as plain CSVs, symbols Yahoo-suffixed. Its issue tracker documents the data-quality caveats crible tolerates (CUSIP collisions, exchange-code drift) and the steady quality PRs that fix them. | [E2][E16][E17][E25][E27][E40][E47][E48] |
| [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) | The fragile-but-free fundamentals link: curl_cffi impersonated sessions [E52], endemic rate limiting (429 / YFRateLimitError on bulk pulls [E105][E107][E108]) and hangs [E36][E82]. Statement depth is shallow (a handful of annual periods — observed behaviour, validated in integration; no contractual depth exists). ADR-0004 designs around every one of these. | [E3][E52][E105][E107][E108][E36][E82] |
| [xang1234/stock-screener](https://github.com/xang1234/stock-screener) | Closest architectural prior art (FastAPI + Postgres + Celery + React, multi-exchange refresh queues). Its preset-filtering timeout fix is the cautionary tale that justified DuckDB-over-Parquet instead of an operational DB. | [E77][E85][E88][E89] |
| [astro30/valinvest](https://github.com/astro30/valinvest) | Clean reference implementation of Piotroski-style fundamental scoring (dead since 2023, FMP-bound) — used as a cross-check for crible's score implementations, not as a dependency. | [E79][E80][E81] |
| [SimFin/simfin](https://github.com/SimFin/simfin) | Official Python client for SimFin's free bulk US fundamentals (5,000 US stocks, 20+ years of history via API/bulk download [E115][E116]; free-tier limitations vs paid re-verified when the phase-2 plugin is built). Library dormant since 2023 → crible's plugin would call the REST API directly. | [E78][E115][E116] |

# Build plan

## M1 — Walking skeleton (must-haves)

A usable end-to-end slice covering every must-have requirement.

- **Requirements:** FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008
- **Risks:**
  - Yahoo rate-limiting/blocking is the dominant hazard: 429s and YFRateLimitError are endemic [E105][E107]; mitigated by the hard token-bucket budget, capped backoff and the degradation path (serve last snapshot).
  - Snapshot atomicity under concurrent reader/writer processes (ADR-0003 write-then-swap) must be proven by tests before the API ships.
  - Keyless throughput arithmetic caps first-boot experience — the bootstrap sample (~100 symbols) is what makes M1 demoable within hours.

## M2 — Rounded product (should-haves)

The product is complete enough for real users.

- **Requirements:** FR-009, FR-010, FR-011, FR-012
- **Risks:**
  - ESEF repository coverage is partial (e.g. German/Irish filings unavailable [E15]) and ISINs are sparse in FinanceDatabase [E35] — ESEF enrichment lands on a subset; the unmatched-EU metric keeps it honest.
  - Stooq has no formal API contract; its CSV endpoints may change without notice — provider isolation keeps the blast radius to one plugin.

## M3 — Enhancements (could-haves)

Nice-to-have capabilities that differentiate the product.

- **Requirements:** FR-013, FR-014
- **Risks:**
  - EODHD paid quotas/pricing recorded at planning time must be re-validated with the free key before any purchase decision [E111][E112].
  - FinancialReports.eu MCP OAuth flow may not suit headless ingestion — evaluate during the plugin spike before committing.

# Traceability matrix

| Requirement | NFRs | ADRs | Entities | Interfaces | Components | Screens |
|---|---|---|---|---|---|---|
| FR-001 | NFR-003, NFR-005, NFR-009, NFR-010 | 0001, 0003 | Company | CLI | — | — |
| FR-002 | NFR-003, NFR-005, NFR-007, NFR-009 | 0001, 0003, 0004 | RawStatement, PriceBar, CrawlTask, Provider | CLI, Provider Plugin API | Status Dashboard | Ingest & coverage status |
| FR-003 | NFR-001, NFR-010, NFR-012 | 0001, 0003 | SnapshotRow | CLI | — | — |
| FR-004 | NFR-001, NFR-008, NFR-011 | 0001, 0003 | SnapshotRow, Preset | CLI, HTTP API | Query Bar (DSL editor), Results Grid | Screener |
| FR-005 | NFR-004, NFR-005 | 0001 | SnapshotRow | CLI | — | — |
| FR-006 | NFR-001, NFR-002, NFR-008 | 0001, 0002 | SnapshotRow, Preset, Company | HTTP API | Status Dashboard, Feedback & Notifications, Empty & Error States | Ingest & coverage status |
| FR-007 | NFR-001, NFR-004, NFR-008 | 0001 | SnapshotRow, Company | Web App, HTTP API | App Shell & Navigation, Query Bar (DSL editor), Results Grid, Column Picker, Presets Menu, Company Detail Drawer, Export Button, Feedback & Notifications, Empty & Error States | Screener |
| FR-008 | NFR-003, NFR-006, NFR-009, NFR-013 | 0001, 0002, 0003 | Provider | HTTP API, CLI | — | — |
| FR-009 | NFR-004, NFR-010 | 0002 | Preset | HTTP API, Web App, CLI | Presets Menu | Screener |
| FR-010 | NFR-003, NFR-005, NFR-010 | 0003, 0004 | RawStatement, Company | Provider Plugin API | Company Detail Drawer | Company detail |
| FR-011 | NFR-003, NFR-005 | 0004 | PriceBar, Provider | Provider Plugin API | — | — |
| FR-012 | NFR-004, NFR-010 | 0002 | Company, SnapshotRow, RawStatement | Web App, HTTP API | Company Detail Drawer, Empty & Error States | Company detail |
| FR-013 | NFR-006, NFR-009, NFR-012 | 0002, 0003 | Provider, RawStatement | Provider Plugin API | Status Dashboard | Ingest & coverage status, Providers & settings |
| FR-014 | NFR-006, NFR-012 | 0002, 0004 | Provider | Provider Plugin API | — | Providers & settings |
| FR-015 | — | 0001 | — | — | — | — |
