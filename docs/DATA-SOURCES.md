# Data sources — the public-data audit

Everything crible's core (and its GitHub Pages demo) consumes is **public,
keyless open data**. This page is the audit trail: every source, what it
provides, how it is accessed, and under which terms. The zero-key contract is
CI-enforced (the test suite runs with an empty environment, NFR-009).

## Sources in the keyless core

| Source | Data | Access | License / terms | Role |
|---|---|---|---|---|
| [FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) | The screening universe: ~161k equities, 117 countries — symbol, name, sector, industry, exchange, currency | Python package (bundled open dataset) | MIT-licensed repository | `crible ingest --bootstrap` / nightly universe refresh (`src/crible/universe.py`) |
| Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) | Fundamentals (income/balance/cashflow, annual + quarterly) and daily prices | Public web endpoints, scraped — **no contractual API** | Public but unofficial; aggressively rate-limited. Hence the polite token-bucket budget (330 req/h default), jittered backoff and rolling crawl (ADR-0004) | Primary statements + prices provider (`src/crible/providers/yfinance_provider.py`) |
| [filings.xbrl.org](https://filings.xbrl.org) | **Audited** EU fundamentals from official ESEF xBRL-JSON filings | Keyless public JSON:API | Official public filings repository (XBRL International) | Audited layer — outranks scraped values at reconciliation (`src/crible/providers/esef.py`, FR-010) |
| [GLEIF](https://www.gleif.org) ISIN→LEI mapping | Daily relationship file linking ISINs to LEIs | Keyless public download (refreshed upstream daily; fetched per run, never committed) | GLEIF publishes it as open data (CC0) | Resolves EU listings to their ESEF filer (`src/crible/providers/gleif.py`) |
| [Stooq](https://stooq.com) | Worldwide EOD prices | CSV endpoints — currently behind a JS proof-of-work wall (verified 2026-07-07) | No formal API contract | Specced price fallback, **ships disabled / non-load-bearing** (ADR-0004) |

The GitHub Pages demo is built exclusively from this table: the nightly
`refresh-data` workflow (and `scripts/seed-demo-data.sh`) run the same keyless
pipeline and publish Parquet + JSON artifacts to the `demo-data` branch. The
demo's Providers view is exported with an empty environment, so it always
reports the honest keyless state.

## Google Finance — evaluated and rejected (2026-07-13)

Asked for explicitly, investigated, and rejected:

- Google's official Finance API was deprecated on 2011-05-26 and **shut down
  permanently on 2012-10-20**. There has been no official API since.
- The only surviving official surface is the `GOOGLEFINANCE()` function inside
  Google Sheets — an internal mechanism (not an API), delayed 15–20 minutes,
  unusable for headless ingestion.
- Everything marketed as a "Google Finance API" in 2026 is a **third-party
  paid scraper** (Apify and similar), and scraping google.com/finance directly
  is both bot-protected and against Google's Terms of Service.

Any of those paths would break at least one core contract (zero-key,
zero-cost, public data, ToS-respecting). The role Google Finance would have
filled is already covered by yfinance + ESEF, with Stooq as the specced price
fallback.

## Optional keyed providers (NOT part of the core)

SimFin (`SIMFIN_KEY`), FMP free tier (`FMP_KEY`) and EODHD (`EODHD_KEY`) are
opt-in plugins, off by default, documented in `docs/prds/`. They never
participate in the demo pipeline and no core flow depends on them — a provider
without a key simply logs one `disabled (no key configured)` line and stays
off (`src/crible/providers/base.py`).
