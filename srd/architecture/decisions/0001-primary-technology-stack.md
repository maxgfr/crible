# ADR 0001 — Primary technology stack

**Status:** accepted

## Context

Solo developer, TDD, zero-ops self-hosting, and a data problem shaped like: a 161k-symbol universe [E2], per-ticker scraping through a fragile rate-limited source [E3], columnar analytics over ~200 ratio columns, and a dense data UI. The stack must minimise moving parts while keeping every layer replaceable.

## Decision

Python 3.12 for universe/ingest/compute/API (the finance OSS ecosystem is Python: financetoolkit [E1][E8], financedatabase [E2], yfinance [E3][E98]); DuckDB over Parquet (pyarrow) as the only datastore — embedded, zero-ops, columnar, millisecond screens [E4][E12][E10]; FastAPI [E13] + Typer [E92] as the two entry points sharing one core; React 18 + Vite + TypeScript with TanStack Table for the SPA [E18][E19][E21]; pytest for TDD [E95]; Docker Compose for deployment [E94].

## Consequences

One language for the whole data path; no database server, migrations or queue to operate; the SPA is the only build step. DuckDB is single-writer — the ingest and API processes share data via Parquet files and an atomic snapshot swap rather than concurrent writes. Python-side compute must stay vectorised (pandas/DuckDB) to hold the performance NFRs.

## Alternatives considered

OpenBB Platform as an aggregation façade [E90] — rejected: planning-time verification of its docs showed the free equity-fundamentals path routes through yfinance (same rate limits and shallow history as going direct) and its screener providers (finviz, fmp, nasdaq, yfinance) offer no European-first screening; recorded as a design-time verification, not a dossier citation. Postgres + Celery + React (the xang1234/stock-screener architecture) — rejected: real prior art shows preset-filter timeouts and index churn at exactly this workload [E77][E88]. A Rust custom engine — rejected: re-implements what DuckDB already does in-process.

**Evidence:** [E1][E2][E3][E4][E12][E13][E19][E77][E88][E90][E92][E94][E95]
