# Changelog

## Unreleased — 2026-07-13 (open-data hardening)

- **SEC EDGAR provider (FR-016, ADR-0005)** — audited US fundamentals from the
  public-domain companyfacts API, keyless, on its own SEC fair-access budget
  (declared `CRIBLE_SEC_USER_AGENT`, 5 req/s, never the Yahoo bucket). Audited
  US values now outrank scraped ones at reconciliation, symmetric with ESEF.
- **Reconciliation fix** — audited periods are now aligned to the scraped
  period labels of the same fiscal year (`align_periods`). Previously ESEF's
  year labels ("2024") never matched yfinance's dated periods ("2024-12-31"),
  so the audited layer silently never overrode anything; audited-only symbols
  also carried the wrong `provider` provenance. Both fixed, with tests.
- **100 % keyless catalog** — the optional keyed providers (SimFin, FMP,
  EODHD) and the dead Stooq fallback paths were removed (their licenses are
  not open-data compatible; Stooq sits behind an anti-bot wall). The plugin
  seam remains for third-party providers. `docker-compose.yml` now passes no
  key env vars at all — enforced by test.
- **`crible bootstrap` + rolling `data-latest` release (ADR-0006)** — the
  nightly refresh now also uploads the dataset as GitHub Release assets, and
  a new CLI command initializes a self-hosted `data/` from it (release asset
  first, `demo-data` branch fallback; safe tar extraction; never clobbers an
  existing dataset without `--force`). Fresh installs screen with zero crawl.
- **Full query builder in the SPA** — any snapshot column (live schema via the
  new `GET /api/fields`, one shared DESCRIBE in the browser demo), operators
  constrained by field type, AND/OR groups, enum dropdowns for region/sector —
  all composing the same plain, editable DSL into the query bar. Replaces the
  fixed six-filter bar; the grammar and the Python/TS golden parity are
  untouched.
- **Docs** — `docs/DATA-SOURCES.md` gains the SEC EDGAR row, the explicit
  yfinance redistribution caveat and the demo-footprint decision; Google
  Finance stays rejected (no API since 2012, redistribution forbidden);
  ADR-0005/0006 added.

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
