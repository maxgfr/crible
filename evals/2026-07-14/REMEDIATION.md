# Remediation plan — .

Target: `/Users/maxime/Downloads/crible` · 13 fix task(s), most impactful first.
Each task has a matching TDD card under `fixes/` (RED failing test → GREEN change → VERIFY).

## P1 — Major: materially degrades a scored dimension (fidelity, coverage, robustness); a workaround or secondary path exists (5)

- **FIX-001** Periodic universe refresh inside run_loop (the self-hosted service never re-downloads FinanceDatabase) — refresh_universe already exists (universe.py:213) and the nightly run_refresh calls it (service.py:697), but the long-lived Docker service (docker-compose command `crible ingest --loop`) only bootstraps on first boot (service.py:776-778) and never refreshes again. A self-hoster's delisted flags and new listings freeze forever. The upsert is already idempotent, so this is a scheduler, not new logic.
  - fix: Add a weekly `if now - last_universe_refresh >= 7*86400: refresh_universe(con); queue.seed_from_universe()` branch to run_loop, mirroring the price-refresh cadence already there (service.py:793).
  - targets: src/crible/ingest/service.py, src/crible/universe.py, docker-compose.yml
- **FIX-002** GLEIF ISIN→LEI auto-fetch (crible ingest --fetch-gleif) — unlock the idle audited-EU layer — The whole ESEF audited-EU enrichment (run_esef_sweep/run_esef_cycle) is wired but stays idle out-of-the-box: it needs data/isin-lei.csv and nothing downloads it. gleif.py:21 defines ISIN_LEI_LATEST_URL but it is never referenced (dead constant); service.py:229 tells the operator to fetch the ~200 MB file by hand. A self-hoster gets zero audited EU coverage until they discover this. The research doc confirms GLEIF publishes the ISIN↔LEI relationship files as keyless open data ([S12][S53]).
  - fix: Add a downloader (stream ISIN_LEI_LATEST_URL to data/isin-lei.csv, with timeout + size guard) exposed as `crible ingest --fetch-gleif`, and call it from run_refresh so the nightly self-heals the mapping.
  - targets: src/crible/providers/gleif.py, src/crible/ingest/service.py, docs/research/2026-07-13-data-sources/SUMMARY.md
- **FIX-003** run_loop resets the rate budget every cycle — NFR-007 (330 req/h polite crawl) is silently violated on the self-hosted `ingest --loop` path — A self-hoster runs the shipped `docker compose up`; during backlog burn-down the ingest loop issues ~280 requests every few seconds — thousands/hour — blowing past the 330/h politeness budget and getting the IP rate-limited or banned by Yahoo, contradicting the keyless design's central promise.
  - fix: Build the crawler + one TokenBucket once outside the loop (as run_refresh does) and reuse crawler.run_cycle across iterations; or hold the bucket in run_loop and inject it into run_once. Add a regression test asserting cumulative acquisitions across N cycles stay ≤ capacity per rolling hour.
  - targets: src/crible/ingest/service.py, src/crible/ingest/budget.py, docker-compose.yml
- **FIX-004** No per-request watchdog — a hung yfinance fetch stalls the whole long-lived loop; two docstrings claim a watchdog that does not exist — yfinance hangs on one symbol (known upstream behaviour); crawl_symbol never returns, the loop stops advancing, the heartbeat goes stale, and coverage plateaus until an operator restarts the container.
  - fix: Wrap fetch_statements in a hard deadline (thread + .join(timeout) or a watchdog thread), treat a timeout as a failure → queue.mark_failed + reschedule; then the two docstrings become true.
  - targets: src/crible/ingest/crawler.py, src/crible/providers/yfinance_provider.py, src/crible/ingest/prices.py, TODO.md
- **FIX-005** ESEF _fiscal_year tags audited facts by end-year with no duration check — an interim/quarterly value can be recorded as the annual audited figure (contradicts the module's own docstring) — A filer's latest ESEF document (picked by sort -date_added) carries an interim duration fact ending Dec 31; it is stored as the annual audited Revenue/NetIncome, overrides the correct scraped value, and the screener ranks the company on a wrong 'audited' number.
  - fix: In _fiscal_year (or facts_to_frames) require duration facts to span ~360-372 days before accepting them as annual; keep instants as period-end snapshots. Add a fixture with an interim duration asserting it is dropped.
  - targets: src/crible/providers/esef.py, src/crible/compute/reconcile.py

## P2 — Minor: polish, consistency, or documentation drift; no scored dimension materially degraded (8)

- **FIX-006** Incremental compute via the existing build_snapshot(symbols=…) seam — Every compute cycle rebuilds the entire snapshot: run_compute() calls build_snapshot(data) with no symbols, which re-reads every crawled symbol's raw parquet and recomputes all ratios/scores/ranks (snapshot.py:171-172). build_snapshot ALREADY accepts a symbols= argument — the seam exists, the caller just never uses it. Fine at ~500 companies, quadratic pain toward the 150k universe the README advertises.
  - fix: Track symbols whose raw changed since the last snapshot (fetched_at stamps already exist) and pass them to build_snapshot; ranks stay cross-sectional so recompute ranks over the union, but skip re-parsing unchanged raw.
  - targets: src/crible/compute/snapshot.py, src/crible/ingest/service.py
- **FIX-007** FX normalization (Frankfurter/ECB, keyless) for cross-currency absolute comparisons — Ratios are currency-neutral so the gap is modest, but absolute values (market_cap, revenue) are stored in native currency with no normalized companion columns — grep for frankfurter|market_cap_eur|fx_rate finds nothing. Cross-currency screening on absolute size is therefore misleading. The research doc identifies a keyless source: ECB reference rates via api.frankfurter.dev ([S71][S72]).
  - fix: Store daily ECB rates (Frankfurter, keyless, cite source), add companion columns (market_cap_eur, revenue_eur…) at snapshot build, expose via whitelist/UI.
  - targets: src/crible/compute/snapshot.py, docs/research/2026-07-13-data-sources/SUMMARY.md
- **FIX-008** attach_ranks fragments the snapshot frame — reproducible PerformanceWarning on the compute hot path — As the universe grows, the fragmented-frame inserts turn a linear column-attach into repeated full-frame copies, inflating each compute cycle's wall-clock with no functional signal that anything is wrong.
  - fix: Build the rank columns in a dict / separate frame and attach with a single pd.concat(axis=1), or pre-allocate; assert no PerformanceWarning in a focused test.
  - targets: src/crible/compute/ranks.py
- **FIX-009** ingest/service.py hotspot has more than doubled (820 LOC, nesting 14) — worst module in the repo, up from 370 LOC last cycle — Adding the next data source (e.g. a GLEIF fetcher or a universe-refresh scheduler) means editing an 820-LOC module that mixes queue, budget, ESEF, EDGAR, prices, compute and heartbeat — high regression surface, no boundaries.
  - fix: Extract the enrichment cycles (EsefCycle, EdgarCycle) and shared helpers (GLEIF mapping loader, _connect/heartbeat) into their own modules; the per-cycle contracts are already clear.
  - targets: src/crible/ingest/service.py
- **FIX-010** ESEF concept collisions resolve non-deterministically (last-writer-wins) — e.g. ProfitLoss vs ProfitLossAttributableToOwnersOfParent both map to NetIncome — An IFRS filing tags both ProfitLoss and ProfitLossAttributableToOwnersOfParent; the audited NetIncome depends on JSON key order, so two runs (or two filers) disagree on the 'audited' bottom line.
  - fix: Give colliding concepts an explicit precedence (prefer the whole-group total, or the most-specific) and only overwrite when the incoming concept ranks higher; unit-test the collision.
  - targets: src/crible/providers/esef.py
- **FIX-011** Raw layer glob('*.parquet') matches leftover '.tmp-*.parquet' partials — pathlib includes dotfiles, defeating write-temp-then-rename atomicity — An ingest container is killed mid-write; the leftover '.tmp-income-annual-<stamp>.parquet' is later read by the compute step and raises on the truncated parquet, silently dropping that symbol from the snapshot until an operator cleans up.
  - fix: Write the tmp OUTSIDE the globbed tree or name it without a '.parquet' suffix, and filter '.tmp-*' in prune_raw/latest_raw_frames; sweep stale tmp files on startup.
  - targets: src/crible/ingest/raw.py, src/crible/compute/snapshot.py
- **FIX-012** Stooq solve_pow loops unbounded on a server-supplied difficulty — a raised value pins a CPU core with no time budget or watchdog — Stooq raises the PoW difficulty (or serves a hostile value); the headless bulk import wedges on 100% CPU with no timeout, blocking the price refresh indefinitely.
  - fix: Bound solve_pow by a max difficulty and a wall-clock/iteration budget; raise StooqError past the budget so the caller degrades to the manual archive path.
  - targets: src/crible/ingest/stooq_fetch.py
- **FIX-013** bootstrap downloads the published dataset non-streaming and buffers it entirely in memory (io.BytesIO(response.content)) — OOM risk on a small self-hosted host — A self-hoster on a 512MB-1GB VPS runs the bootstrap; the dataset has grown past available RAM and the process is OOM-killed before extraction, with no partial-progress fallback.
  - fix: Stream the download to a temp file (http.stream / iter_bytes) and open tarfile from the file, or extract members incrementally; cap peak memory independent of dataset size.
  - targets: src/crible/bootstrap.py
