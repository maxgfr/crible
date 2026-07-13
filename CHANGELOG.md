# Changelog

## v0.1.0 — 2026-07-13

First public release.

**crible is a self-hosted fundamental stock screener — zero API keys, zero
subscription, forever.** That zero-key contract is CI-enforced: the whole test
suite runs with an empty environment, and every core flow works without any
account or key.

- **Universe**: ~161k equities / 117 countries from FinanceDatabase, searchable
  by symbol or name.
- **Data (all keyless)**: Yahoo via yfinance (rolling, rate-budgeted crawl,
  Europe-first), audited EU figures from filings.xbrl.org (ESEF xBRL-JSON,
  matched through the GLEIF ISIN→LEI file) — audited values outrank scraped
  ones at reconciliation.
- **Scores**: Piotroski F, Altman Z, Beneish M and 150+ ratios, every number
  traceable to its inputs; composite quality/value/momentum percentile ranks
  with peer groups, never imputed.
- **Screening**: one filter DSL compiled to parametrized DuckDB SQL, shared by
  the CLI, the HTTP API and the React SPA — full-universe screens in
  milliseconds.
- **In-browser demo**: the GitHub Pages demo runs the real screener entirely
  client-side — the DSL compiled in TypeScript (golden-locked to the Python
  compiler) executing on DuckDB-WASM over Parquet published by a nightly
  open-data refresh with a last-good guarantee.
- **Deploy**: two-container Docker Compose (`ingest` + `api`), multi-arch
  images (amd64/arm64) on GHCR. Designed for private-LAN self-hosting.

## Earlier

Pre-release development is documented spec-first in `srd/` and the improvement
cycles in `IMPROVE.md`.
