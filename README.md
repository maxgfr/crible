# crible

[![ci](https://github.com/maxgfr/crible/actions/workflows/ci.yml/badge.svg)](https://github.com/maxgfr/crible/actions/workflows/ci.yml)
[![pages](https://github.com/maxgfr/crible/actions/workflows/pages.yml/badge.svg)](https://github.com/maxgfr/crible/actions/workflows/pages.yml)
[![release](https://img.shields.io/github/v/release/maxgfr/crible)](https://github.com/maxgfr/crible/releases)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**The fundamental stock screener that runs on your own machine — zero API keys, zero subscription, forever.**

**[Try the live demo →](https://maxgfr.github.io/crible/)** — the real screener running entirely in your browser (DuckDB-WASM, open data, no backend).

Screen a worldwide universe of ~150k equities (Europe-depth priority) on real fundamentals —
Piotroski F, Altman Z, Beneish M, 150+ transparent ratios — with every number traceable back
to its source. No account, no data vendor, no monthly bill. `docker compose up` and it's yours.

![crible screener](docs/img/screener-dark.png)
<details><summary>More screens (status, providers, light theme)</summary>

![status](docs/img/status-dark.png)
![providers](docs/img/providers-dark.png)
![paper terminal](docs/img/screener-light.png)
</details>

```bash
# same filter DSL in CLI, API and UI — results in milliseconds
crible screen "return_on_equity > 0.15 AND piotroski_f >= 7 AND country IN ('FR','DE')"
```

## Why crible

Serious fundamental screening is otherwise a paid SaaS — Stockopedia runs €550/year for Europe
(€725 with the US), TIKR and Simply Wall St are monthly subscriptions. The open-source
self-hosted tools track portfolios (Ghostfolio) or are research terminals (OpenBB); **none of
them is a turnkey fundamental screener you host yourself.** crible is that missing piece.

| | crible | Stockopedia | TIKR | Simply Wall St | OpenBB | Ghostfolio |
|---|---|---|---|---|---|---|
| Self-hosted | ✅ | ❌ | ❌ | ❌ | terminal only | ✅ |
| No API key / no subscription | ✅ | ❌ €550+/yr | ❌ | ❌ freemium | partial | ✅ |
| Fundamental screener (full universe) | ✅ | ✅ | ✅ | partial | ❌ | ❌ |
| Transparent scores → provenance | ✅ | ✅ | ✅ | ❌ | — | — |
| Your data, your machine | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |

_Honest comparison: the paid tools have deeper history, analyst estimates and polish. crible's
bet is ownership + transparency + zero cost for the fundamental-screening job._

## Quickstart (self-host)

```bash
git clone https://github.com/maxgfr/crible && cd crible
docker compose up          # ingest + api, one shared volume — no keys needed
# open http://localhost:8000  (dense, dark-first grid; light "paper terminal" toggle)
```

Prebuilt multi-arch images (amd64 + arm64 — VPS, Apple Silicon, ARM NAS) ship with every
release; `docker compose pull` fetches them instead of building locally:

```bash
docker pull ghcr.io/maxgfr/crible:latest
```

The first run bootstraps the universe and starts a rate-budgeted, Europe-first crawl; the
screener shows live progress until the first rows land. See the **Status** view for coverage,
freshness and provider health.

### Standalone CLI — no clone needed

crible is a regular Python CLI (`[project.scripts]`); install it as a tool and run it anywhere:

```bash
uv tool install git+https://github.com/maxgfr/crible    # or one-shot: uvx --from git+https://github.com/maxgfr/crible crible …
crible --data-dir ~/crible-data bootstrap                # pull the published dataset
crible --data-dir ~/crible-data screen "price_to_earnings_ratio <= 15 AND region = 'europe'"
crible --data-dir ~/crible-data fields                   # every filterable column + type
```

`--data-dir` (or `CRIBLE_DATA_DIR`) selects the dataset location; the default is `./data`.

### Start with data — zero crawl

The nightly refresh publishes its open dataset twice: as assets on the rolling
[`data-latest` release](https://github.com/maxgfr/crible/releases/tag/data-latest) and on the
`demo-data` branch. A fresh install can pull it and screen immediately:

```bash
uv run crible bootstrap                      # data/ restored from the published dataset
uv run crible screen "piotroski_f >= 7"     # rows, right now — no crawl needed
```

The normal ingest loop then extends the dataset from wherever the bootstrap left it.

**Keeping the data fresh** — pick one:

- `docker compose up` — the `ingest` service is the built-in "cron": a continuous,
  rate-budgeted crawl loop that recomputes and republishes the snapshot after every cycle.
- Your own cron running one bounded pass, e.g. nightly:
  `17 2 * * * cd crible && uv run crible demo-refresh --deadline 9000` (exactly what the
  GitHub Action does).
- Consume-only (no crawling at all): re-pull the published nightly dataset with
  `crible bootstrap --force` on a cron — the `data-latest` release is refreshed every night
  by this repo's Action.

### Running on a NAS (Synology / Docker)

crible is a two-container Compose stack (`ingest` + `api`) sharing one named volume — it drops
straight onto a Synology NAS, Unraid, or any Docker host:

1. Copy the repo (or just `docker-compose.yml` + built image) to the host.
2. `docker compose up -d` — the `api` service listens on `${CRIBLE_PORT:-8000}`; the `crible-data`
   volume persists the Parquet snapshot across restarts.
3. Point your reverse proxy (or the NAS's) at the `api` container.

> **Deploy on a private network.** The API ships **without authentication** — it's designed for
> single-user, private-LAN or reverse-proxied use. Do **not** publish port 8000 straight to the
> public internet; put it behind your reverse proxy / VPN, or bind it to loopback. (OWASP A05.)

## Surfaces

- **CLI** — `crible screen`, `export`, `presets`, `status`, `ingest`, `compute`.
- **HTTP API** — FastAPI; the SPA is served from the same origin in production.
- **SPA** — React/Vite dense grid, a query builder over every snapshot column (typed
  operators, AND/OR groups) that composes the same DSL, company drawer with score
  breakdowns + provenance, theme toggle.

## Data & scores (all keyless)

- **Universe**: [FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) (151,170 equities at the July 2026 refresh, 117 countries).
- **Data**: Yahoo via [yfinance](https://github.com/ranaroussi/yfinance) (rolling, rate-budgeted) ·
  **audited** figures that outrank scraped values at reconciliation — US from
  [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
  companyfacts (public domain) and EU from [filings.xbrl.org](https://filings.xbrl.org)
  (ESEF xBRL-JSON).
- **Ratios & scores**: [financetoolkit](https://github.com/JerBouma/FinanceToolkit) (150+ ratios,
  Piotroski F, Altman Z) + in-house Beneish M-Score (tested against published examples).
- **Engine**: DuckDB over Parquet — full-universe screens in milliseconds.

The full public-data audit — every source, its access mode and license terms, plus the
evaluated-and-rejected candidates (e.g. Google Finance, whose official API shut down in 2012) —
lives in [`docs/DATA-SOURCES.md`](docs/DATA-SOURCES.md).

### How the composite rank is built (FR-015)

`composite_rank` (0-100) blends three percentile pillars, each ranked within the
company's peer group (region×sector when it holds ≥ 5 companies, otherwise the
whole snapshot — the group is named in `rank_peer_group`):

- **quality** = mean pct(`piotroski_f` ↑, `altman_z` ↑)
- **value** = mean pct(`earnings_yield` ↑, `price_to_book_ratio` ↓)
- **momentum** = pct(`return_6m` ↑, trailing 6-month price return)

A pillar with any missing input stays **NULL — never imputed** — and the omission
is recorded in `rank_missing_pillars`; the composite blends the available pillars.
Unlike proprietary StockRanks, every rank decomposes in the company drawer down
to its component values. Ranks are computed at snapshot build time: after
upgrading, run `crible compute` (or wait for the next crawl cycle) to get the
columns.

## The live demo — how it works

The [demo](https://maxgfr.github.io/crible/) is not a video or a mock: it is the real screener
running **entirely in your browser**. The same filter DSL is compiled client-side (a TypeScript
port, golden-locked to the Python compiler by shared test vectors) and executed by
**DuckDB-WASM** over Parquet artifacts fetched with HTTP range requests from GitHub Pages —
there is no backend at all.

- **Open data, nightly**: a GitHub Action refreshes the demo dataset every night from the same
  keyless sources the self-hosted crawl uses — FinanceDatabase (the full ~150k-listing universe,
  searchable), Yahoo via yfinance, SEC EDGAR (audited US statements, public domain) and
  filings.xbrl.org (audited ESEF statements) matched through the GLEIF ISIN→LEI file. No key,
  no account, anywhere. The same dataset is downloadable (`crible bootstrap`).
- **Coverage**: audited fundamentals cover the **entire US market** (~10k issuers via the
  nightly EDGAR bulk sweep — price-free scores only where Yahoo prices are missing) plus the
  crawled European sample (CAC 40 + DAX 40, extended nightly by the crawl + ESEF); the full
  rolling crawl of the whole universe is what self-hosting gives you.
- **Last-good guarantee**: a refresh that fails or covers too few symbols never publishes —
  the demo keeps the previous dataset, and its Status view shows data freshness honestly.

## Status

Built spec-first: the full SRD suite (requirements, ADRs, data model, design system,
evidence-grounded) lives in [`srd/`](srd/). Implementation follows `srd/BUILD-PLAN.json`, TDD,
every test named after the FR it proves. Continuous-improvement cycles (market + evaluation) are
tracked in [`IMPROVE.md`](IMPROVE.md), `docs/market/` and `docs/improve/`.

## Development

```bash
uv sync            # python 3.12 env + deps
uv run pytest      # test suite (FR-tagged)
cd ui && npm i && npm run dev   # SPA dev server on :5173 (proxies /api)
```

## License

MIT
