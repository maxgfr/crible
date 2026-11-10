# Code audit — November 2026

Scope: the whole repository at `4eecd5f` (v0.17.0) — the Python package (`src/crible`, ~13,400
lines), the React SPA (`ui/src`, ~9,000 lines), tests, scripts and workflows. Every finding
below was read in the code before it was acted on, and every fix started from a test that
failed on the old code.

## Summary

1. **The codebase is in good shape.** The baseline was fully green (559 pytest, 215 vitest,
   ruff, both UI builds) and the security-sensitive paths were already hardened: parametrized
   SQL over a schema-derived field whitelist, guarded tar extraction, symbol-derived paths
   that cannot escape their directory. **No SQL injection, XSS, path traversal, unsafe
   deserialization or hardcoded secret was found.**
2. **14 bugs fixed**, each with a regression test: 8 in ingestion (rate-limit handling,
   shutdown, atomic state, price currency), 1 in compute, 5 in the SPA (DSL parity, races,
   crash on corrupt storage).
3. **3 optimizations**, measured: a full screen page ~16× faster to serve, `stats` ~2.3×
   faster, and a quadratic step of the incremental compute removed.
4. **Nothing critical is left open.** Three important issues are documented rather than
   fixed because they need a design decision (incremental compute vs reference data, ESEF
   re-fetches, concurrent computes).
5. **Four questions need your call** (Ohlson size term, a price-gated ratio, the default
   sort of a permalink, the live quote in API mode) — see the last section.

After the audit: 571 pytest (1 skipped: the optional `captcha` extra), 220 vitest, ruff check
and format clean, both UI builds pass.

## Behavior changes to know about

Bug fixes change behavior by definition; these are the ones a user or operator can observe.

- **`shareholder_yield` is now NULL across a split or unit change** (fix 9). It follows the
  bound `net_share_issuance` already had. `ENGINE_SCHEMA_VERSION` goes 11 → 12, the
  repository's convention for value-changing fixes: **the next compute rebuilds every base
  row once** instead of an incremental pass.
- **The price refresh ends after three hung fetches in a row** (fix 5), like three rate
  limits. It used to wait the full timeout on every remaining symbol.
- **A hand-edited URL runs even after a first screen that failed** (fix 12).
- **`stats` means can differ in their last digits** (~1e-15 relative): the sum is folded in a
  different order by the single query. Counts, min/max, quantiles and percentiles are
  identical on a 40-field before/after dump.
- **Releases**: the commits are `fix:`/`perf:`, so this push cuts one patch release
  (image, wheel, Homebrew formula) through `release.yml`.

## Bugs fixed

| # | File | Issue | Fix | Test added |
|---|---|---|---|---|
| 1 | `src/crible/ingest/service.py` (`run_once`) | A targeted crawl (on-demand fetch requests) ignored the 429 breaker and the deadline: it called Yahoo once more per remaining symbol, counted them as failed, and their request files were deleted unserved. The heartbeat said "healthy". Reproduced: 7 upstream calls where the breaker allows 3. | The batch stops where the crawler stopped, sets `aborted`, and leaves the unserved requests pending. | `tests/test_loop.py::test_a_rate_limited_on_demand_batch_stops_and_keeps_its_requests` |
| 2 | `src/crible/ingest/budget.py` (`save_bucket`) | `budget-state.json` was written in place. A crash mid-write left a truncated file, read back as an empty bucket: the next run double-spent the hourly request budget. | Temp file + rename, like the heartbeat. | `tests/test_budget_state.py::test_a_save_that_dies_mid_write_keeps_the_previous_state` |
| 3 | `src/crible/ingest/crawler.py` | Backoff (up to 900 s) and budget waits (up to an hour) were one `time.sleep`, which a SIGTERM handler does not interrupt. `docker compose stop` hit its 1-minute grace period, the container was SIGKILLed and the loop's `finally` never saved the budget window. | With a stop callback set, waits run in 1 s slices and end the cycle as `stop requested`. Unchanged without a callback. | `tests/test_crawler.py::test_a_stop_request_interrupts_a_backoff_sleep` |
| 4 | `src/crible/providers/yfinance_provider.py`, `service.py` (`_YfPriceAdapter`) | The rate-limit markers were matched as substrings of the error text, so an ordinary error naming `4290.T`, `1429.HK` or `600429.SS` ("possibly delisted") counted as a 429: six retries with backoff (~45 min) per such symbol, and three in a row tripped the breaker. | One shared `is_rate_limited(exc, symbol)` that removes the symbol from the message first. | `tests/test_yfinance_provider.py::test_a_symbol_holding_429_is_not_a_rate_limit` (3 symbols, both code paths) |
| 5 | `src/crible/ingest/prices.py` | A watchdog timeout was only a skipped symbol, although the module docstring lists hangs in the switch rule. With Yahoo not answering, the refresh waited the full timeout for every symbol the budget allowed, and `run_refresh` only checks its time budget before the stage. | Timeouts count toward the same 3-in-a-row rule as rate limits. | `tests/test_price_refresh.py::test_three_hung_fetches_in_a_row_end_the_refresh` |
| 6 | `src/crible/ingest/prices.py` (`PriceRefresher`) | The daily refresh writes bars without `_quote_currency` (one request, no profile). The snapshot reads only the newest price file, so a refreshed listing fell back to its listed currency. Reproduced on the CCEP.L fixture: market cap 3.1 T instead of 36.5 B (85×). | The refresher carries the recorded quote currency over from the symbol's previous bars. | `tests/test_yfinance_provider.py::test_a_price_refresh_keeps_the_crawled_quote_currency` |
| 7 | `src/crible/ingest/price_import.py` (`import_stooq`) | `float(close)` raised on the first non-numeric close (`N/D`) and aborted the whole archive. | The close goes through the tolerant parser the other columns use; a row without one is skipped. | `tests/test_price_import.py::test_a_stooq_row_without_a_numeric_close_is_skipped_not_fatal` |
| 8 | `src/crible/ingest/enrich/br.py` (`run_cvm`) | When this year's FCA register is missing and last year's serves (every January), the first failure stayed recorded as the stage's outage: CVM showed as down although the stage ran. | A successful fallback clears it. No register at all is still an outage. | `tests/test_cvm.py::test_run_cvm_register_fallback_is_not_an_outage` |
| 9 | `src/crible/compute/extras.py` | `shareholder_yield` valued any share-count decline at the current price. An unrestated 1:10 reverse split read as a 905 % yield (and a 10:1 split as −90 %) and topped the `shareholder-yield` preset. | Same (0.5, 2) bound as `net_share_issuance`. Documented in `docs/INDICATORS.md`; engine schema 12. | `tests/test_fr003_compute.py::test_fr003_shareholder_yield_undefined_across_a_split_or_unit_change` |
| 10 | `ui/src/dsl/parser.ts` | Keywords were looked up in an object literal, so `constructor`, `toString`, `__proto__`… resolved through `Object.prototype` and were not tokenized as fields. The in-browser screener answered "expected FIELD" where Python answers "unknown field" — a DSL parity break. | Keyword lookup is a `Map`. | 5 new error vectors in `tests/test_dsl_parity.py`, `ui/src/dsl/golden.json` regenerated from Python, asserted by `ui/src/__tests__/dsl.test.ts` |
| 11 | `ui/src/components/CompanyDrawer.tsx` | Switching company while a poll or a "Fetch this company now" request was in flight let the late answer land on the new one: A's periods under B's title, or B shown as queued. | The poll effect carries a `live` flag like the initial load; the button handler checks the symbol it served is still on screen. | `ui/src/__tests__/drawer.test.tsx` — "on-demand fetch races" (2 tests) |
| 12 | `ui/src/App.tsx` | The effect that re-runs a hand-edited or Back/Forward URL compared it with the last screen that *succeeded* and did nothing while there was none. After a permalink with an unknown field, or the API down at load, fixing the URL left the error on screen. | It compares with the URL the app already acted on. | `ui/src/__tests__/ux.test.tsx` — "a corrected URL re-runs the screen after the first one failed" |
| 13 | `ui/src/dsl/explain.ts` | The clause serializer escaped quotes but not backslashes. A value ending in `\` was written back as an unterminated string, the funnel threw and the zero-result diagnosis rendered nothing. | One `quote()` next to the parser, shared with the query builder; out-of-range numbers round-trip too. | `ui/src/__tests__/zero-diagnosis.test.tsx` — "every serialised clause parses back…" |
| 14 | `ui/src/presets-store.ts` | Any truthy stored entry with an `id` and a `dsl` was accepted. A non-string `id` (hand-edited storage, or another app on the shared `maxgfr.github.io` origin) threw in the presets menu on mount and the root error boundary replaced the whole app. | Entries are validated (string `id`, `name`, `dsl`) or dropped. | `ui/src/__tests__/ux.test.tsx` — "survives saved presets that are not presets" |

## Optimizations

Measured on this machine (Apple Silicon, noisy: best of 15 is quoted) against a synthetic
snapshot of the NFR-008 size: 161,000 rows × 189 columns.

| # | File | What cost time | Change | Measured |
|---|---|---|---|---|
| A | `src/crible/api/main.py` (`POST /api/screen`) | Rows were serialized by pandas, parsed back into Python objects, then walked and re-encoded cell by cell by FastAPI. | The JSON pandas wrote is sent as is. A contract test pins the payload (NaN/inf → null, non-ASCII intact, typed ints and booleans). | 1000-row page (4.9 MB): **~660 ms → ~40 ms**. Default 100-row page: ~53 ms → ~32 ms. |
| B | `src/crible/store.py` (`stats`) | One aggregate query per field (up to 40 scans), each with five separate quantile aggregates. | One query for all fields, one list-quantile per field. | 40 fields over the universe: **~640 ms → ~275 ms**. Over a region×sector group: ~170 ms → ~100 ms. |
| C | `src/crible/compute/snapshot.py` (`_incremental_rows`, `build_symbol_snapshot`), `service.py` (`run_price_refresh`) | `s in set(dirty)` inside a comprehension rebuilt the set per symbol (O(symbols × dirty)). Momentum features were computed, then discarded and recomputed, on the build path. | The set is built once; the features are computed only where they are used. | Selection alone, 30k symbols / 10k dirty: **3–7 s → ~1 ms**. Features: one ~0.66 ms call less per symbol (~1.5 % of a symbol's build, ~20 s on a 30k-symbol rebuild). |

Also removed: `EsefClient.filing_page_url` (no caller anywhere), and the `publish_snapshot`
docstring no longer claims an fsync that does not happen.

## Issues found, not fixed

### Critical

None.

### Important

1. **Incremental compute does not rebuild rows when reference data changes.**
   `src/crible/compute/snapshot.py` (`_incremental_rows`): a row is rebuilt only when its raw
   files or its price distillate row change, but the per-symbol stage also reads the ECB
   rates, the listing currencies, split events and the SEC statement-currency mirror. A
   base built before the FX mirror exists keeps NULL multiples on every cross-currency
   listing until each symbol is crawled again. *Recommendation:* record a fingerprint of
   those inputs with the base and mark the affected symbols dirty when it moves. Rates
   change daily, so it must be per-currency, not all-or-nothing, or every night becomes a
   full rebuild.
2. **An ESEF filing that fails with a 4xx is fetched again on every run when a deeper
   history is requested.** `src/crible/ingest/enrich/eu.py`: the skip path stamps
   `last_fetched_at` only, while the due check also tests `coalesce(history_depth, 1) <
   history`. With `history > 1` a broken filer stays due forever. *Recommendation:* stamp
   the requested depth on the skip path too.
3. **`publish_snapshot` and the base cache use fixed temp names.** Two computes on one data
   directory (the ingest loop and a manual `crible compute`) can rename each other's
   half-written file into place. *Recommendation:* a lock file in `snapshot/`, or
   per-process temp names.

### Minor

4. `CRIBLE_BUDGET_PER_HOUR` below the per-symbol cost (8) makes the crawl raise
   `ValueError` out of `run_refresh` (`crawler.py`, `budget.py`). Validate at startup.
5. `prune_raw` (`ingest/raw.py`) raises on a `.parquet` file whose name has no `-`, and is
   called unguarded by `run_refresh`.
6. CVM (`providers/cvm.py`, `enrich/br.py`): a refiled statement keeps the first version
   seen (`VERSAO` is ignored); `years=N` walks N+1 years, and a missing DFP year is recorded
   as an outage even when the others loaded.
7. `crible clean` (`cli.py`): a `data` directory that is a symlink ends in a traceback, and
   `universe.parquet` alone marks a directory as a dataset — a file the hosted site lets
   anyone download, so `--data-dir ~/Downloads clean -y` would pass the guard.
8. Split events are de-duplicated by exact date (`snapshot.py`): the same split dated one
   day apart by two sources is applied twice.
9. `latest_close` (`snapshot.py`) takes the last bar without the `close > 0` filter and
   date sort the momentum code applies, so the price and `return_6m` can come from
   different bars.
10. CSV export, API mode (`App.tsx`): `window.location.assign` on a 4xx navigates the SPA
    to a raw JSON error page, and the `X-Crible-Truncated` header is never read. Static mode
    (`static-client.ts`) cuts the export at 10,000 rows without saying so.
11. EDGAR per-CIK cycle (`enrich/us.py`): `companyfacts` is fetched once per symbol, so two
    share classes of one CIK (GOOG, GOOGL) fetch the same document twice.
12. Static mode (`ui/src/data/duckdb.ts`): `universe` and `snapshot_all` are views over
    remote Parquet, so each search and each drawer re-reads over HTTP.
13. `CoverageBanner.tsx` throws (and takes the app down) if a manifest lacks
    `generated_at`.
14. `.github/workflows/crawl-marathon.yml` interpolates a step output into a `run:` block
    (`--deadline "${{ needs.guard.outputs.deadline }}"`); the value derives from a
    `workflow_dispatch` input. Pass it through `env:` like `import-prices.yml` does.
    Not changed: deployment config was out of scope.
15. Bulk downloads without a byte ceiling (`EdgarClient.download_bulk`,
    `bootstrap._download_and_extract`); `mirror.py` has one (4 GiB).
16. Helpers referenced only by tests (`ranks.price_return`, `ttm.ttm_from_quarterly`,
    `snapshot.read_snapshot`, `snapshot.build_snapshot`, `ProviderRegistry`, the `ui/src/api.ts`
    shim) and a few triplicated ones (`_full_year` in three providers).
17. Dependencies: `npm audit` reports 0 vulnerabilities. Majors are available and left to
    dependabot: DuckDB 2, MCP 2, React 19, TypeScript 7, `@tanstack/react-table` 9. The
    test client warns that `httpx` with `starlette.testclient` is deprecated.

## Open questions

1. **Ohlson O-score size term.** `scores.py` uses `log(total_assets)` in raw currency
   units. The 1980 model was fitted on assets deflated by a price index, in far smaller
   units: for $1 bn of assets the term is about 5.6 points lower than with assets in
   millions, so `O < 0` (the `ohlson-safe` preset) passes almost everyone, and a JPY filer
   scores about 2 points lower than a USD filer of the same size. `INDICATORS.md` documents
   dropping the index, not the unit. Keep as is, rescale, or convert to one currency first?
2. **`net_debt_to_ebitda_ratio` exists only when a price does.** `ratios.py` builds
   `net_debt` inside the price block although it needs no price, and a test pins that
   ("price-gated but full-series"). Audited-only listings without a quote get NULL.
   Intended?
3. **Default sort of a permalink.** `#/?q=…` without `sort` is ordered by `-composite_rank`
   on a cold load, and unsorted when reached by editing the hash of an open app. Which one
   is the contract?
4. **Live quote in API mode.** `ui/src/data/live-quote.ts` always tries Yahoo directly from
   the browser. In API mode that request cannot succeed (no CORS headers) but still tells
   Yahoo which ticker a self-hosted user opened. Keep it, or drop the direct route outside
   the static build?

## How this was checked

- Baseline and final runs: `uv run pytest`, `uv run ruff check src tests`,
  `uv run ruff format --check src tests`, `npm --prefix ui run test -- --run`,
  `npm --prefix ui run build`, and the static build (`VITE_DATA_MODE=static
  VITE_BASE=/crible/`).
- **Not run locally:** the Docker build and compose smoke test (CI runs them), and anything
  that talks to Yahoo, the SEC or another live source — every fix is proven offline with the
  repository's fakes.
- All 14 fixes were reproduced by a failing test on the old code first. The unfixed items
  were confirmed by reading the code; none of them has a test yet.
