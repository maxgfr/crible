# System context

crible serves a fundamental investor and self-hosting tinkerer screening European + worldwide equities. Pipeline: universe (FinanceDatabase CSVs → DuckDB) → ingest (rolling prioritized keyless crawler over yfinance — fundamentals AND prices under one request budget — plus ESEF XBRL audited figures joined via GLEIF ISIN→LEI, behind a Provider plugin seam; raw versioned Parquet) → compute (financetoolkit ratios + Piotroski/Altman + in-house Beneish → wide snapshot Parquet) → store/query (DuckDB over Parquet; DSL → parametrized SQL) → surfaces (Typer CLI, FastAPI HTTP API, React/Vite SPA) — all packaged as two Docker Compose services (ingest, api) sharing one data volume. Keyless external endpoints: FinanceDatabase, Yahoo, filings.xbrl.org, GLEIF (+ optional disabled Stooq fallback). Each external source is isolated behind the Provider Plugin API (ADR-0003, ADR-0004).

```
FinanceDatabase CSVs      Yahoo (yfinance)   filings.xbrl.org   Stooq CSV
        │                        │                  │              │
        ▼                        ▼                  ▼              ▼
  [universe] ──────────► [ingest: priority queue + token bucket ≤330/h]
        │                        │ raw Parquet (versioned, per provider)
        ▼                        ▼
     DuckDB ◄──────────── [compute: financetoolkit + Piotroski/Altman/Beneish]
        │                        │ snapshot Parquet (atomic swap)
        ▼                        ▼
   [CLI crible]          [FastAPI /screen /company /status] ──► [React SPA]

  docker compose: service `ingest` + service `api`, one shared data volume
```

Phase-2 keyed providers (FinancialReports.eu MCP, SimFin, FMP free, EODHD free) and the future paid EODHD plugin all mount behind the same Provider Plugin API — no core changes (NFR-012).
