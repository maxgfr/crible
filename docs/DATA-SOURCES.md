# Data sources — the public-data audit

Everything crible's core (and its hosted GitHub Pages screener) consumes is
**public, keyless open data**. This page is the audit trail: every source,
what it provides, how it is accessed, and under which terms. The zero-key
contract is CI-enforced (the test suite runs with an empty environment,
NFR-009).

## Sources in the keyless core

| Source | Data | Access | License / terms | Role |
|---|---|---|---|---|
| [FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) | The screening universe: ~150k equities (151,170 at the July 2026 refresh), 117 countries — symbol, name, sector, industry, exchange, currency | Python package (bundled open dataset) | MIT-licensed repository | `crible ingest --bootstrap` / nightly universe refresh (`src/crible/universe.py`) |
| Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) | Fundamentals (income/balance/cashflow, annual + quarterly) and daily prices | Public web endpoints, scraped — **no contractual API** | Public but unofficial; aggressively rate-limited. Hence the polite token-bucket budget (330 req/h default), jittered backoff and rolling crawl (ADR-0004). **Not redistributable** (Yahoo ToS: personal use; exchange-licensed data) — see the caveat below the table | Primary statements + prices provider (`src/crible/providers/yfinance_provider.py`) |
| [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) companyfacts | **Audited** US fundamentals — every XBRL fact from 10-K/20-F/40-F filings | Keyless JSON API (`data.sec.gov`), fair-access: declared User-Agent (`CRIBLE_SEC_USER_AGENT`) + own 5 req/s budget | **US-government work: public domain**, free to access and reuse | Audited US layer — outranks scraped values at reconciliation (`src/crible/providers/edgar.py`, FR-016, ADR-0005) |
| [filings.xbrl.org](https://filings.xbrl.org) | **Audited** EU **and UK-listed** fundamentals from official ESEF xBRL-JSON filings (the index also serves 2,885 GB filings — verified 2026-07-16; the sweep walks it unfiltered and a regression test forbids an EU-only filter) | Keyless public JSON:API | Official public filings repository (XBRL International), "no restrictions" | Audited EU+GB layer — outranks scraped values at reconciliation (`src/crible/providers/esef.py`, FR-010) |
| [GLEIF](https://www.gleif.org) ISIN→LEI mapping | Daily relationship file linking ISINs to LEIs | Keyless public download (refreshed upstream daily; fetched per run, never committed) | GLEIF publishes it as open data (CC0) | Resolves EU listings to their ESEF filer (`src/crible/providers/gleif.py`) |

The hosted screener is built exclusively from this table: the nightly
`refresh-data` workflow (and `scripts/seed-data.sh`) run the same keyless
pipeline and publish Parquet + JSON artifacts as assets on the rolling
[`data-latest` release](https://github.com/maxgfr/crible/releases/tag/data-latest)
(ADR-0006, ADR-0007) — the only distribution channel: `crible bootstrap`
restores `crible-data.tar.gz`, the Pages deploy attaches `site-data.tar.gz`,
and no data ever travels in git (main stays code-only). The site's Providers
view is exported with an empty environment, so it always reports the honest
keyless state.

**The yfinance redistribution caveat, stated plainly.** Yahoo's data is
exchange-licensed and its terms allow personal use only — it is *free to
access*, not *open data*. The published dataset carries the crawled daily
OHLCV **series** for the sampled symbols (ADR-0007, decision 2026-07-13) — an
explicitly assumed, documented redistribution risk. The scraped fundamentals
sample stays deliberately small (~100 companies); everything else in the
dataset (SEC EDGAR, ESEF, GLEIF, FinanceDatabase) is cleanly redistributable.
A fully-redistributable dataset would drop Yahoo — and with it the price
series and all price-based ratios, because **no open OHLCV price source
exists**: exchanges monetize market data, and Yahoo/Google merely sublicense
it.

**Site footprint.** The site ships the full universe parquet (~4 MB — a
one-time, browser-cached fetch that powers search over all 151k listings).
Since the EDGAR bulk sweep (2026-07-13), the snapshot covers the whole US
market (audited fundamentals, 8 fiscal years max) plus the crawled European
sample — tens of MB of parquet, still fetched via HTTP range requests. It also
ships the daily price series as symbol-sorted, size-bounded shards
(`site-data/prices-*.parquet`, ~400-day window; each shard is kept under the
95 MB git wall and the total is watched via the manifest `prices.bytes`). What
Pages serves is only `site-data/`; the rest of the raw layer lives on the
branch/release for bootstrap purposes.

## Bulk-first, local-first additions (2026-07-14)

The 2026-07-14 cycle pushed the design toward **owning the data**: fewer fragile
live per-symbol calls, more keyless bulk downloads crible mirrors locally, and a
**last-good guarantee** on every source. Yahoo shrinks toward a resilient
fallback; the audited, redistributable bulk grows toward the primary layer.

### The local-first data plane (`src/crible/ingest/mirror.py`)

Every bulk archive is fetched **once** into `data/mirror/<source>/`, kept as the
last-good copy, and re-fetched only when stale (ETag/`If-None-Match`, so an
unchanged re-fetch is nearly free). In steady state the ingestion reads the
local mirror, not a live API; on a network failure it serves the last-good copy
so **coverage never regresses**, and a whole `crible refresh` can run offline
from the mirror. This is the "self-hosted at the call level" contract.

### New audited sources

| Source | Data | Access | License / terms | Tier |
|---|---|---|---|---|
| SEC **Financial Statement Data Sets** (FSDS) | Deep 'as-filed' US history (pre-8-year), quarterly `sub.txt`/`num.txt` | Keyless bulk ZIP per quarter, mirrored (`--fsds-quarters N`) | **US-government work: public domain** | **fully-free** |
| **GLEIF ISIN→LEI** auto-fetch | The relationship file that unlocks the audited-EU (ESEF) layer | `crible ingest --fetch-gleif` streams it to the mirror; `crible refresh` self-heals it | Open data (CC0) | **fully-free** |
| **ECB reference rates** via [Frankfurter](https://frankfurter.dev) | Daily FX rates → `*_eur` companion columns for cross-currency size screens | Keyless JSON, mirrored (`--fetch-fx`) | Open source, redistributable | **fully-free** |
| **Companies House** (UK) Accounts Data Product | Audited UK accounts (iXBRL) — the **non-listed / non-IFRS backfill** (listed consolidated IFRS comes from filings.xbrl.org's GB slice, which outranks it at merge) | Keyless ZIP, mirrored; resolution via operator-provided `data/uk-company-numbers.csv` | **No explicit reuse licence** | **assumed-risk** |
| **EDINET** (Japan) | Audited JP filings (XBRL) | **Free-key opt-in** (`CRIBLE_EDINET_KEY`) — API-only, never scraped; OFF by default | PDL1.0 — redistributable **with attribution** | opt-in (keyed) |

All audited sources implement one contract (`src/crible/providers/audited.py`
`AuditedBulkProvider`) and keep only full-year figures with deterministic concept
precedence. `merge_audited` lets companyfacts win recent US periods while FSDS
backfills the deep history.

### Two dataset tiers (redistribution, stated plainly)

- **Fully-free** — SEC EDGAR companyfacts + **FSDS**, ESEF, GLEIF, FinanceDatabase,
  ECB/Frankfurter FX. Public-domain or openly-licensed; republishable without
  permission ("free to access and reuse").
- **Assumed-risk** — Yahoo prices, the Stooq/HuggingFace/defeatbeta dumps, the
  **TradingView scanner snapshots**, and **Companies House** (no licence
  stated). Carried as a documented, deliberate redistribution risk, isolated
  from the fully-free tier.
- **EDINET** (audited Japan) — **policy change 2026-07-16: the project's own
  nightly now opts in** via the `CRIBLE_EDINET_KEY` repository secret, so
  `provider='edinet'` raw ships in the published dataset. Its PDL1.0 licence
  makes that clean — redistributable **with attribution**: *this dataset
  contains data from EDINET, Financial Services Agency of Japan, licensed
  under the Public Data License v1.0.* Closer to fully-free than
  assumed-risk; it keeps its own line because of the attribution duty.

The **zero-key core is unchanged**: EDINET stays the only keyed provider and
the code self-skips without the key — a fork without the secret runs fully
keyless, and the CI test contract (empty environment, NFR-009) is untouched.
Note: the site's `providers.json` is exported with an empty environment by
construction, so it reports EDINET "disabled" even when the dataset carries
its raw — the dataset-content authority is this ledger, not that file.

### Rejected / iceboxed this cycle

- **Deutsche Börse Public Dataset (AWS)** — REJECTED: non-commercial licence and
  the dataset is marked deprecated.
- **NSE/BSE bhavcopy (India)** — ICEBOX: freely downloadable but redistribution
  ToS not established.

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

## Imported price dumps — published series (2026-07-13)

No open-licensed OHLCV source exists (exchanges monetize market data), but
free full-history DUMPS do. Under ADR-0007 (decision 2026-07-13), crible now
publishes the price **series** from these dumps too, an explicitly assumed
redistribution risk — neither dump carries an open license. `crible
import-prices` writes two artifacts per source: the windowed OHLCV series
(last ~400 days) into `data/prices/<source>.parquet`, exported to the site as
`site-data/prices-*.parquet`; and the per-symbol distillate (last close,
as-of date, trailing 6-month return) into `data/prices-latest.parquet`, which
the snapshot still consumes as a valuation/momentum fallback when the crawl
has no bars (staleness stays visible via `price_asof`).

| Dump | Coverage | Access | Freshness | Terms |
|---|---|---|---|---|
| [paperswithbacktest/Stocks-Daily-Price](https://huggingface.co/datasets/paperswithbacktest/Stocks-Daily-Price) | ~7k US listings, daily, full history | 4 parquet shards, plain HTTPS, **no key/API** — pulled weekly by the nightly | Refreshed ~monthly (2026-07-09 at audit time) | License "other" (unspecified) — series published as an assumed risk |
| [Stooq bulk archives](https://stooq.com/db/h/) | Worldwide (US, DE, UK, JP, PL…), daily, decades | **`crible stooq-download <dataset> --import`** clears the two anti-bot layers headlessly (SHA-256 proof-of-work + a 4-char image captcha, OCR'd by the optional `captcha` extra; verified 2026-07-13) — or manual download then `crible import-prices <zip>` | Daily | No published license — series published as an assumed risk. Stooq bars are pre-adjusted, so `adj_close` stays NULL |
| [defeatbeta/yahoo-finance-data](https://huggingface.co/datasets/defeatbeta/yahoo-finance-data) | ~12k US listings (incl. OTC/ETF), daily, full history + dividends/splits/shares outstanding + statements | One parquet per table, plain HTTPS, **no key/API** — `crible import-prices defeatbeta` (weekly in the nightly + Monday workflow) | Refreshed ~weekly (update time in the dataset's `spec.json`; prices to 2026-07-15 at audit time, evaluated 2026-07-16) | Labeled ODC-BY, but the data is **Yahoo-derived, re-scraped by a single maintainer** — that label cannot cleanse Yahoo's exchange-licensed terms, so it lands in the assumed-risk tier like Stooq. Split-adjusted bars only → `adj_close` stays NULL |

The `import-prices` workflow (manual dispatch) forces a HuggingFace refresh +
snapshot recompute + republish anytime; the nightly refresh pulls it weekly
on its own.

### TradingView scanner — whole-market snapshot, assumed-risk (2026-07-16)

`POST scanner.tradingview.com/{country}/scan` — keyless, one request returns a
country's ENTIRE stock list with close, currency and a **numeric market cap**
(verified 2026-07-16: France 598 stocks, Germany 32,944 rows incl. worldwide
cross-listings; ~40 country slugs probed live, ~100k listings total).
`crible import-prices tradingview` runs it daily in the nightly:

- **Terms, stated plainly: TradingView's ToS forbids scraping.** This is an
  explicitly assumed, documented redistribution risk — the same tier as the
  Yahoo crawl and the Stooq/defeatbeta dumps.
- **Snapshot-only limitation**: no history. Never a series source, never a
  momentum source — the column-aware distillate merge records momentum
  provenance so a TradingView close can refresh a quote but never erase a
  dump's `return_6m`. It does not feed the crawl deferral either: the
  yfinance crawl stays the only bar source for EU/world charts.
- **Role**: daily close freshness for listings no dump covers (continental
  Europe, Asia, the long tail) + the **cap census**
  (`data/caps/tradingview.parquet`, published) that ranks the top-10k global
  companies — unmatched listings are kept with `symbol=NULL` so the census
  can reveal what the universe lacks.
- Degradable enrichment: per-country failures are counted and skipped
  (heartbeat `imports.tradingview.countries_failed`), never fatal; last-good
  = the data-latest restore cycle.

### defeatbeta — additional + fallback, never audited-tier (2026-07-16)

The [defeat-beta/defeatbeta-api](https://github.com/defeat-beta/defeatbeta-api)
project's HF dataset was evaluated as a data source and adopted with a strictly
bounded role — **additional + fallback**:

- **Prices + capital events (the real value)** — fills the documented "audited
  US fundamentals but no prices" gap in bulk, without rate limits. Dividends,
  splits and shares outstanding land in `data/events/defeatbeta-*.parquet`
  (published, full history). Every symbol it prices drops out of the Yahoo
  top-up AND defers its marathon slot (`defer_covered_symbols`, 30 days,
  re-applied nightly — self-healing if the dump dies), so the crawl budget
  flows to Europe and the world, which defeatbeta does not cover.
- **Fundamentals (last resort only)** — `crible import-fundamentals defeatbeta`
  fills ONLY symbols with no audited raw and no crawled yfinance statements
  (`fundamentals_gap_symbols`). The snapshot tags them `provider=defeatbeta`;
  audited values still reconcile on top (the reconcile seam is source-agnostic).
- **Bus factor, stated plainly** — a single maintainer re-scraping Yahoo
  ("I will update the data regularly"): treated as a degradable enrichment.
  No mirror; the last-good guarantee is the data-latest restore→publish cycle,
  and the crawl deferral expires on its own within 30 days.
- **Not a dependency** — the tables are read directly over DuckDB httpfs
  (`src/crible/ingest/defeatbeta.py`); the `defeatbeta-api` Python package is
  not installed. Zero-key contract unchanged.

## Removed sources (open-data cleanup, 2026-07-13)

- **Stooq** — the specced *live per-symbol CSV* fallback never became
  load-bearing: those endpoints sit behind a JS proof-of-work wall (verified
  2026-07-07) and no redistribution license is published, so the dead live-CSV
  code paths were removed. The bulk archives stay a supported DUMP source: as of
  2026-07-13 `crible stooq-download` clears that same proof-of-work plus the
  download image captcha headlessly (the captcha is OCR'd by the optional
  `captcha` extra), and its series are published under the ADR-0007 policy.
- **SimFin / FMP / EODHD keyed plugins** — deleted. SimFin's free license is
  personal-research only and even paid tiers bar redistribution; the others
  are commercial services. Keeping crible fully open data means the shipped
  catalog is keyless-only. The provider *seam* remains
  (`src/crible/providers/base.py`): third-party keyed plugins stay possible,
  off by default, never part of the core or the hosted dataset.
