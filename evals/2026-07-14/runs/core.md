# Core run — deterministic evidence (2026-07-14)

Target: `/Users/maxime/Downloads/crible` @ main. Python 3.12 (uv), node v24.

## Test suites

```
$ uv run pytest
181 passed, 29 warnings in 9.58s        # exit 0
```
Warnings of note (real, reproducible): `PerformanceWarning: DataFrame is highly fragmented`
raised from `src/crible/compute/ranks.py:97-103` during `attach_ranks` (per-column
`snapshot[col] = ...` insertions on a wide frame) — seen 16× in `tests/test_refresh.py`.

```
$ (cd ui && npx vitest run)
Test Files  10 passed (10)
Tests       62 passed (62)             # exit 0
```

## Grounding probes (grep, verbatim)

- Universe refresh: `refresh_universe` defined `universe.py:213`; called at
  `service.py:165` (`run_bootstrap`, first boot) and `service.py:697` (`run_refresh`, nightly).
  NOT called anywhere inside `run_loop` (service.py:768-821) after first boot.
- GLEIF auto-fetch: `ISIN_LEI_LATEST_URL` `gleif.py:21` is defined but **never referenced**
  (no downloader). No `fetch_gleif` / `--fetch-gleif` in `cli.py`. ESEF paths skip with a
  "download the ISIN-LEI relationship file to data/isin-lei.csv" message (service.py:229, 513).
- Watchdog: no `signal.`/`.join(timeout`/`ThreadPoolExecutor`/`alarm` in `ingest/` or
  `providers/`. `crawler.crawl_symbol` calls `provider.fetch_statements` (crawler.py:70) with
  no hard timeout. Two docstrings reference a "crawler's watchdog" that does not exist:
  `prices.py:7`, `yfinance_provider.py:6`.
- FX normalization: grep for `frankfurter|market_cap_eur|fx_rate|exchange_rate|forex|ECB` in
  `src/` → **no match**. Absent.
- Self-hosted entrypoint: `docker-compose.yml:8` = `command: ["crible","ingest","--loop"]` →
  `run_loop`. Crawl cost `requests_per_fetch = 7` (yfinance_provider.py:31); budget default 330
  (budget.py:14). `run_once` builds a fresh `TokenBucket` each call (service.py:178,187).
