# Non-functional requirements

## NFR-001 — performance

Screening is interactive: any valid DSL screen over the full snapshot answers in about a second — the enforceable contract is the NFR-008 CI benchmark; local hardware figures are guidance. [E4][E88]

**Metric:** In the NFR-008 CI benchmark environment: p95 < 1 s end-to-end for any DSL screen over the synthetic full-size snapshot; API POST /screen p95 < 500 ms warm; GET /company/{symbol} p95 < 300 ms.

## NFR-002 — security

No auth by design (single self-hosted operator, ADR-0002); the attack surface is the DSL and the provider keys. DSL input can never become SQL; keys never leave the environment. [E13]

**Metric:** DSL compiles to parametrized SQL over a strict column whitelist (property-tested, see NFR-011); API binds to localhost/compose network by default; provider keys read only from environment/.env — never baked into images, logged, or echoed in errors; Python and npm dependencies audited in CI.

## NFR-003 — reliability

The system degrades gracefully and recovers from transient failures without data loss: the crawler survives kills and rate limits; readers never see partial data. [E82][E36]

**Metric:** Crash-resume without duplicate fetches inside freshness windows; snapshot publication is atomic (write-new-then-swap; a reader never observes a half-written snapshot); raw Parquet writes are write-temp-then-rename; a 24 h crawler soak run completes with zero unhandled exceptions.

## NFR-004 — usability

An operator reaches a first successful screen without reading source code; every error names the next action. [E75]

**Metric:** Clean machine → first successful screen in ≤ 3 commands (docker compose up; wait; run a preset) and ≤ 4 h on first boot with the default bootstrap sample; every CLI/API/UI error message names the failing input or the command to run next; presets give one-click value on first contact.

## NFR-005 — observability

The operator can answer 'what is the crawler doing, how fresh is my data, am I inside the rate budget?' without reading code. [E36]

**Metric:** Structured JSON log line for every provider fetch (symbol, provider, latency, outcome); crible status and GET /status expose universe count, fundamentals coverage %, freshness histogram, rolling req/h and per-provider health; per-symbol consecutive-failure counts are queryable.

## NFR-006 — cost

Data cost is €0 in v1 and can only ever grow by one explicit, documented switch (EODHD). [E111][E112][E115]

**Metric:** Zero paid dependencies in v1 (keyless sources only; EODHD free tier is 20 calls/day with paid plans gated [E111]); the only planned recurring cost is the EODHD Fundamentals feed behind the EODHD_KEY switch, price recorded and re-validated in docs/prds/eodhd.md; infra = any single Docker host.

## NFR-007 — rate-limit compliance

The crawler never exceeds its configured upstream request budget — polite crawling is a hard constraint of the keyless design, because Yahoo demonstrably rate-limits scrapers (429s and YFRateLimitError are endemic in the wild [E105][E107][E108]). [E105][E107][E108]

**Metric:** Rolling 60-minute upstream request count ≤ budget (default 330 — a conservative design choice, configurable), counting every statement/profile/price request individually; enforced by a token bucket and asserted in tests under simulated load; 0 budget violations in a 24 h soak; on HTTP 429 the backoff doubles from 1 min to a 15 min cap with ±20% jitter (design parameters, property-tested).

## NFR-008 — performance (screening engine)

The filter engine keeps its millisecond-class promise as the snapshot grows. [E88]

**Metric:** CI runs the DSL engine against a synthetic full-size snapshot (161k rows × 200 columns): every preset and a battery of generated screens must complete with p95 < 1 s; the DuckDB query plan for any DSL screen touches only the snapshot (no row-by-row Python loop).

## NFR-009 — portability (zero-key contract)

Zero-key operation is a guaranteed, permanent contract — not a degraded mode. Everything core runs from one docker compose up with no accounts and no external services. [E2][E5]

**Metric:** A dedicated CI job runs the full E2E suite with an empty environment (no provider keys) and must pass for every release; docker compose up on a clean machine requires nothing but Docker; removing every key from a configured install returns it to a fully working state.

## NFR-010 — data quality & transparency

Every number can explain itself: formula, source and fetch time. Audited beats scraped. This is the product's moat against closed SaaS ranks [E67]. [E1][E67][E5]

**Metric:** Every snapshot cell is traceable to (provider, fetchedAt) and a published formula (financetoolkit's open implementations [E1] or crible's own tested code); Piotroski/Altman/Beneish are unit-tested against published examples; ESEF audited values override scraped values, with >5% discrepancies logged (FR-010).

## NFR-011 — security (DSL injection)

No DSL input, however hostile, can execute unintended SQL.

**Metric:** Property-based tests feed ≥ 1,000 generated/mutated inputs per run: any input that parses must compile to SQL referencing only whitelisted columns with every literal bound as a parameter; any input that does not parse must execute nothing. A curated corpus of injection payloads is asserted rejected.

## NFR-012 — maintainability

Components stay isolated (universe / ingest / compute / store / api / ui) and the provider seam is the extension point — adding a source never touches the core. [E1][E77]

**Metric:** Adding a data provider = one plugin module implementing the Provider interface + its tests, zero changes to scheduler/compute/API; every FR has at least one test whose name carries the FR id (verified by construct verify --strict); TDD red-green-refactor throughout.

## NFR-013 — privacy

Fully self-hosted: the instance calls data sources, and nothing else. No telemetry, ever. [E58]

**Metric:** Zero outbound requests except to configured data-source endpoints (asserted by an egress test using a recording proxy in CI); no analytics/telemetry libraries in either lockfile; all data lives under the operator's data directory/volume.
