# Comparison — base `evals/2026-07-12-c2` → current `evals/2026-07-14`

- base: engine 1.8.1 · protocol 2 · rubric 1 · target bdad2f7
- current: engine 1.9.0 · protocol 2 · rubric 1 · target b803a05

Score: 81 → 76 (-5) · meets-expectations true → false

## Resolved since base (4)

- P2 · ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14)
- P2 · Le preset « Top ranked » échouait sans indice sur un snapshot antérieur à FR-015
- opp · Colonnes de rang visibles par défaut dans la grille + blend documenté dans le README
- opp · Étendre le benchmark NFR-008 au coût de build des rangs

## Introduced in current (13)

- P1 · run_loop resets the rate budget every cycle — NFR-007 (330 req/h polite crawl) is silently violated on the self-hosted `ingest --loop` path
- P1 · No per-request watchdog — a hung yfinance fetch stalls the whole long-lived loop; two docstrings claim a watchdog that does not exist
- P2 · attach_ranks fragments the snapshot frame — reproducible PerformanceWarning on the compute hot path
- P2 · ingest/service.py hotspot has more than doubled (820 LOC, nesting 14) — worst module in the repo, up from 370 LOC last cycle
- opp · Periodic universe refresh inside run_loop (the self-hosted service never re-downloads FinanceDatabase)
- opp · GLEIF ISIN→LEI auto-fetch (crible ingest --fetch-gleif) — unlock the idle audited-EU layer
- opp · Incremental compute via the existing build_snapshot(symbols=…) seam
- opp · FX normalization (Frankfurter/ECB, keyless) for cross-currency absolute comparisons
- P1 · ESEF _fiscal_year tags audited facts by end-year with no duration check — an interim/quarterly value can be recorded as the annual audited figure (contradicts the module's own docstring)
- P2 · ESEF concept collisions resolve non-deterministically (last-writer-wins) — e.g. ProfitLoss vs ProfitLossAttributableToOwnersOfParent both map to NetIncome
- P2 · Raw layer glob('*.parquet') matches leftover '.tmp-*.parquet' partials — pathlib includes dotfiles, defeating write-temp-then-rename atomicity
- P2 · Stooq solve_pow loops unbounded on a server-supplied difficulty — a raised value pins a CPU core with no time budget or watchdog
- P2 · bootstrap downloads the published dataset non-streaming and buffers it entirely in memory (io.BytesIO(response.content)) — OOM risk on a small self-hosted host

## Retitled (same evidence, new title) (0)

- none
