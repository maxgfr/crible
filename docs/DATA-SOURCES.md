# Data sources — the public-data audit

Everything crible's core (and its GitHub Pages demo) consumes is **public,
keyless open data**. This page is the audit trail: every source, what it
provides, how it is accessed, and under which terms. The zero-key contract is
CI-enforced (the test suite runs with an empty environment, NFR-009).

## Sources in the keyless core

| Source | Data | Access | License / terms | Role |
|---|---|---|---|---|
| [FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) | The screening universe: ~150k equities (151,170 at the July 2026 refresh), 117 countries — symbol, name, sector, industry, exchange, currency | Python package (bundled open dataset) | MIT-licensed repository | `crible ingest --bootstrap` / nightly universe refresh (`src/crible/universe.py`) |
| Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) | Fundamentals (income/balance/cashflow, annual + quarterly) and daily prices | Public web endpoints, scraped — **no contractual API** | Public but unofficial; aggressively rate-limited. Hence the polite token-bucket budget (330 req/h default), jittered backoff and rolling crawl (ADR-0004). **Not redistributable** (Yahoo ToS: personal use; exchange-licensed data) — see the caveat below the table | Primary statements + prices provider (`src/crible/providers/yfinance_provider.py`) |
| [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) companyfacts | **Audited** US fundamentals — every XBRL fact from 10-K/20-F/40-F filings | Keyless JSON API (`data.sec.gov`), fair-access: declared User-Agent (`CRIBLE_SEC_USER_AGENT`) + own 5 req/s budget | **US-government work: public domain**, free to access and reuse | Audited US layer — outranks scraped values at reconciliation (`src/crible/providers/edgar.py`, FR-016, ADR-0005) |
| [filings.xbrl.org](https://filings.xbrl.org) | **Audited** EU fundamentals from official ESEF xBRL-JSON filings | Keyless public JSON:API | Official public filings repository (XBRL International) | Audited EU layer — outranks scraped values at reconciliation (`src/crible/providers/esef.py`, FR-010) |
| [GLEIF](https://www.gleif.org) ISIN→LEI mapping | Daily relationship file linking ISINs to LEIs | Keyless public download (refreshed upstream daily; fetched per run, never committed) | GLEIF publishes it as open data (CC0) | Resolves EU listings to their ESEF filer (`src/crible/providers/gleif.py`) |

The GitHub Pages demo is built exclusively from this table: the nightly
`refresh-data` workflow (and `scripts/seed-demo-data.sh`) run the same keyless
pipeline and publish Parquet + JSON artifacts to the `demo-data` branch and
the rolling [`data-latest` release](https://github.com/maxgfr/crible/releases/tag/data-latest)
(ADR-0006 — what `crible bootstrap` restores). The demo's Providers view is
exported with an empty environment, so it always reports the honest keyless
state.

**The yfinance redistribution caveat, stated plainly.** Yahoo's data is
exchange-licensed and its terms allow personal use only — it is *free to
access*, not *open data*. The published dataset therefore keeps the scraped
sample deliberately small (~100 companies), an assumed and documented risk;
everything else in it (SEC EDGAR, ESEF, GLEIF, FinanceDatabase) is cleanly
redistributable. A fully-redistributable dataset would drop Yahoo — and with
it all price-based ratios, because **no open OHLCV price source exists**:
exchanges monetize market data, and Yahoo/Google merely sublicense it.

**Demo footprint.** The demo ships the full universe parquet (~4 MB — a
one-time, browser-cached fetch that powers search over all 151k listings).
Since the EDGAR bulk sweep (2026-07-13), the snapshot covers the whole US
market (audited fundamentals, 8 fiscal years max) plus the crawled European
sample — tens of MB of parquet, still fetched via HTTP range requests. What
Pages serves is only `site-data/`; the raw layer lives on the branch/release
for bootstrap purposes and never reaches the browser.

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
filled is already covered by yfinance + ESEF.

## Removed sources (open-data cleanup, 2026-07-13)

- **Stooq** — the specced price fallback never became load-bearing: its CSV
  endpoints sit behind a JS proof-of-work wall (verified 2026-07-07) and no
  redistribution license is published. The dead code paths were removed.
- **SimFin / FMP / EODHD keyed plugins** — deleted. SimFin's free license is
  personal-research only and even paid tiers bar redistribution; the others
  are commercial services. Keeping crible fully open data means the shipped
  catalog is keyless-only. The provider *seam* remains
  (`src/crible/providers/base.py`): third-party keyed plugins stay possible,
  off by default, never part of the core or the demo.
