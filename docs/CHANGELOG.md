# Changelog

## Unreleased — 2026-07-15

- **Release-only dataset distribution** — the orphan `data` branch is retired;
  the rolling `data-latest` release is now the only channel. `refresh-data`,
  `import-prices` and `seed-data.sh` restore/publish release assets, the Pages
  deploy attaches the new `site-data.tar.gz` asset, and `crible bootstrap`
  drops its branch fallback. One branch (`main`), no data in git history.
  `publish-data.sh` and the caller-less `publish-prices.sh` are removed —
  `publish-data-release.sh` is the single publisher.
- **Blank query = no filter** — clearing the query (UI, API, CLI) screens the
  full snapshot instead of erroring with `empty query (at position 0)`; the
  DSL grammar itself still rejects empty input (golden-locked).
- **Full indicator preset coverage** — 11 new presets (zmijewski-safe,
  ohlson-safe, montier-clean, top-quality/value/momentum, greenblatt-factors,
  graham-defensive, cash-quality, dividend-safety, all-indicators) so every
  published indicator is one click away; a coverage test locks it in.

## Unreleased — 2026-07-13 (open-data hardening)

- **Automated Stooq bulk download (`crible stooq-download`)** — clears Stooq's
  two anti-bot layers headlessly so the CAPTCHA-gated worldwide price archives
  can be fetched in CI: a pure-Python SHA-256 proof-of-work solver for the
  "verify your browser" wall, then a lightweight ONNX OCR model (`ddddocr`,
  ~85 % first-try, retried) for the 4-char image captcha, validated against
  Stooq's own endpoint. Ships a reusable `crible solve-captcha <img>` command,
  an optional `captcha` extra (keeps core ML-free), a `stooq-download` proof
  workflow, and network-free orchestration tests. `--import` chains straight
  into the existing derived-values distillation. **Wired into the
  `import-prices` workflow**: it now fetches the Stooq worldwide dump
  (`d_world_txt`, best-effort) alongside HuggingFace before recompute/publish,
  so the pipeline gains worldwide coverage in CI.
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
- **Price dumps, distilled (`crible import-prices`)** — no open-licensed
  OHLCV exists, but free dumps do: the HuggingFace daily-price shards (plain
  HTTPS, ~7k US listings, pulled weekly by the nightly) and Stooq bulk
  archives (manual download, worldwide). Only DERIVED values are stored and
  published — close, as-of, 6-month return per symbol — never the series;
  the snapshot falls back to them where the crawl has no bars, giving
  EDGAR-only issuers real P/E, market cap and momentum.
- **ESEF index sweep** — filings.xbrl.org's full index (~25k filings) is
  walked newest-first instead of polling one LEI at a time: every request
  lands on a real audited filing; the EU gisement becomes coverable in weeks.
- **Nightly coverage plateau fixed** — the crawl queue is rebuilt from raw
  filename stamps each run (only raw/ travels in the published dataset), so
  nightlies advance into new symbols instead of re-crawling the same head.
- **SEC 403 on runners fixed** — www.sec.gov requires a contact email in the
  User-Agent; the nightly UA now carries one.
- **EDGAR bulk — the whole US market on the demo (ADR-0005 update)** — the
  nightly now downloads `companyfacts.zip` (1.4 GB, public domain) and ingests
  the audited layer for every resolved US listing (~10k issuers, 8 fiscal
  years of history), instead of 25 per night. Issuers without a Yahoo price
  carry the price-free indicators (Piotroski, Beneish, margins, growth) with
  NULL valuation ratios — never imputed. `crible refresh --edgar-bulk`.
- **Starter filter chips** — the classic screener criteria (market cap, P/E,
  P/B, dividend yield, ROE, debt/equity, margins, growth, scores, ranks,
  region/sector/country) pinned as one-click editable chips on the builder.
- **Auto theme** — the preference becomes auto|dark|light (default auto,
  follows the OS live); the header control cycles flip → back-to-auto.
- **Momentum fix** — the price refresh now fetches one year of daily bars
  (same single request); `return_6m` was permanently NaN on a 5-day window,
  so the momentum rank pillar never computed.
- **Standalone CLI** — `uv tool install git+…` documented and verified, new
  global `--data-dir` option, new `crible fields` command; the repo ships a
  `crible-cli` agent skill (`.claude/skills/`).
- **CI** — the docker job now boots the real image: CLI, `crible bootstrap`
  against the published dataset, and API screening are smoke-tested per push.
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

Pre-release development followed a test-first, FR-tagged discipline.
