# crible

**The fundamental stock screener that runs on your own machine — zero API keys, zero subscription, forever.**

Screen a worldwide universe of ~161k equities (Europe-depth priority) on real fundamentals —
Piotroski F, Altman Z, Beneish M, 150+ transparent ratios — with every number traceable back
to its source. No account, no data vendor, no monthly bill. `docker compose up` and it's yours.

```bash
# same filter DSL in CLI, API and UI — results in milliseconds
crible screen "roe > 15 AND piotroski >= 7 AND country IN ('FR','DE')"
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

The first run bootstraps the universe and starts a rate-budgeted, Europe-first crawl; the
screener shows live progress until the first rows land. See the **Status** view for coverage,
freshness and provider health.

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
- **SPA** — React/Vite dense grid, company drawer with score breakdowns + provenance, theme toggle.

## Data & scores (all keyless)

- **Universe**: [FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) (160,995 equities, 117 countries).
- **Data**: Yahoo via [yfinance](https://github.com/ranaroussi/yfinance) (rolling, rate-budgeted) ·
  audited EU figures from [filings.xbrl.org](https://filings.xbrl.org) (ESEF xBRL-JSON) ·
  [Stooq](https://stooq.com) price fallback.
- **Ratios & scores**: [financetoolkit](https://github.com/JerBouma/FinanceToolkit) (150+ ratios,
  Piotroski F, Altman Z) + in-house Beneish M-Score (tested against published examples).
- **Engine**: DuckDB over Parquet — full-universe screens in milliseconds.

Phase-2 providers (SimFin / FMP / EODHD) are **optional** and off by default: add a key to `.env`
to enable one, and it shows up as enabled in the **Providers** view. crible stays fully keyless
without them.

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
