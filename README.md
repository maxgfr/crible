# crible

Self-hosted fundamental stock screener. Worldwide universe (~161k equities), Europe-depth
priority, **zero API keys required — by contract, forever**.

- **Universe**: [FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) (160,995 equities, 117 countries)
- **Data (keyless)**: Yahoo via [yfinance](https://github.com/ranaroussi/yfinance) (rolling, rate-budgeted crawl) ·
  audited EU figures from [filings.xbrl.org](https://filings.xbrl.org) (ESEF xBRL-JSON) ·
  [Stooq](https://stooq.com) price fallback
- **Ratios & scores**: [financetoolkit](https://github.com/JerBouma/FinanceToolkit) (150+ transparent ratios,
  Piotroski F, Altman Z) + in-house Beneish M-Score (tested against published examples)
- **Engine**: DuckDB over Parquet — full-universe screens in milliseconds
- **Surfaces**: `crible` CLI · FastAPI HTTP API · React/Vite SPA (dense, dark-first grid)
- **Deploy**: `docker compose up` (services `ingest` + `api`, one shared volume)

```bash
# screen with the filter DSL — same language in CLI, API and UI
crible screen "roe > 15 AND piotroski >= 7 AND country IN ('FR','DE')"
```

## Status

Built spec-first: the full SRD suite (requirements, ADRs, data model, design system,
evidence-grounded) lives in [`srd/`](srd/). Implementation follows `srd/BUILD-PLAN.json`,
TDD, every test named after the FR it proves.

## Development

```bash
uv sync            # python 3.12 env + deps
uv run pytest      # test suite (FR-tagged)
```

## License

MIT
