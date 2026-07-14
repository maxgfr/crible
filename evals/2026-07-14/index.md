# Evaluation — .

> target `/Users/maxime/Downloads/crible` · codebase · self-hosted fintech tool · 9 findings (P0 0 · P1 3 · P2 6) · 4 opportunities
> engine 1.9.0 · protocol 2 · rubric 1 · target b803a05

## Verdict — ❌ BELOW expectations · 76/100

_a judge ruled it does not meet expectations (3 judges)_

_Weight sensitivity: verdict robust to ±0.05 shifts._

| dimension | score | weight | anchored to |
|-----------|-------|--------|-------------|
| Correctness | 3.7/5 | 0.3 | ISO/IEC 25010:2023 — Functional suitability — functional correctness; ISO/IEC 25010:2023 — Reliability — faultlessness |
| Test quality | 3.9/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — testability |
| Security | 4.0/5 | 0.2 | ISO/IEC 25010:2023 — Security — confidentiality, integrity, resistance; OWASP Top 10 (2021) — categories A01–A10 |
| Maintainability | 3.4/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — modularity, analysability, modifiability |
| Performance | 4.1/5 | 0.1 | ISO/IEC 25010:2023 — Performance efficiency — time behaviour, resource utilization, capacity |

## Findings

| id | sev | title | status | evidence |
|----|-----|-------|--------|----------|
| F1 | P1 | run_loop resets the rate budget every cycle — NFR-007 (330 req/h polite crawl) is silently violated on the self-hosted `ingest --loop` path | confirmed | `src/crible/ingest/service.py:788` `src/crible/ingest/service.py:184-199` `src/crible/ingest/service.py:174-181` `src/crible/ingest/service.py:678-680` `src/crible/ingest/budget.py:35-43` `docker-compose.yml:8` |
| F2 | P1 | No per-request watchdog — a hung yfinance fetch stalls the whole long-lived loop; two docstrings claim a watchdog that does not exist | confirmed | `src/crible/ingest/crawler.py:60-70` `src/crible/providers/yfinance_provider.py:6` `src/crible/ingest/prices.py:6-7` `TODO.md:17-22` `src/crible/providers/yfinance_provider.py:36-58` |
| F3 | P2 | attach_ranks fragments the snapshot frame — reproducible PerformanceWarning on the compute hot path | confirmed | `src/crible/compute/ranks.py:96-99` `run:runs/core.md#L11` |
| F4 | P2 | ingest/service.py hotspot has more than doubled (820 LOC, nesting 14) — worst module in the repo, up from 370 LOC last cycle | confirmed | `src/crible/ingest/service.py:1-820` `run:analysis.json` `src/crible/ingest/service.py:223-234` |
| F9 | P1 | ESEF _fiscal_year tags audited facts by end-year with no duration check — an interim/quarterly value can be recorded as the annual audited figure (contradicts the module's own docstring) | confirmed | `src/crible/providers/esef.py:87-103` `src/crible/providers/esef.py:45-51` `src/crible/providers/esef.py:71` `src/crible/compute/reconcile.py:84` |
| F10 | P2 | ESEF concept collisions resolve non-deterministically (last-writer-wins) — e.g. ProfitLoss vs ProfitLossAttributableToOwnersOfParent both map to NetIncome | confirmed | `src/crible/providers/esef.py:22-39` `src/crible/providers/esef.py:71` |
| F11 | P2 | Raw layer glob('*.parquet') matches leftover '.tmp-*.parquet' partials — pathlib includes dotfiles, defeating write-temp-then-rename atomicity | confirmed | `src/crible/ingest/raw.py:51` `src/crible/ingest/raw.py:26` `src/crible/compute/snapshot.py:120-123` |
| F12 | P2 | Stooq solve_pow loops unbounded on a server-supplied difficulty — a raised value pins a CPU core with no time budget or watchdog | confirmed | `src/crible/ingest/stooq_fetch.py:61-68` `src/crible/ingest/stooq_fetch.py:90-93` |
| F13 | P2 | bootstrap downloads the published dataset non-streaming and buffers it entirely in memory (io.BytesIO(response.content)) — OOM risk on a small self-hosted host | confirmed | `src/crible/bootstrap.py:148` `src/crible/bootstrap.py:153` |

## Opportunities (4) — impact × effort

| id | impact | effort | value | title |
|----|--------|--------|-------|-------|
| F5 | high | S | 3.00 | Periodic universe refresh inside run_loop (the self-hosted service never re-downloads FinanceDatabase) |
| F6 | high | M | 1.50 | GLEIF ISIN→LEI auto-fetch (crible ingest --fetch-gleif) — unlock the idle audited-EU layer |
| F7 | med | M | 1.00 | Incremental compute via the existing build_snapshot(symbols=…) seam |
| F8 | med | M | 1.00 | FX normalization (Frankfurter/ECB, keyless) for cross-currency absolute comparisons |

Quick wins (value ≥ 2): F5

## Verification

✅ 39 adjudicated · 39 supported · 0 refuted · 0 unsupported

## Fix backlog (13)

- **FIX-001** (P1) Periodic universe refresh inside run_loop (the self-hosted service never re-downloads FinanceDatabase) → `tests/test_service.py`
- **FIX-002** (P1) GLEIF ISIN→LEI auto-fetch (crible ingest --fetch-gleif) — unlock the idle audited-EU layer → `tests/test_gleif.py`
- **FIX-003** (P1) run_loop resets the rate budget every cycle — NFR-007 (330 req/h polite crawl) is silently violated on the self-hosted `ingest --loop` path → `tests/test_service.py`
- **FIX-004** (P1) No per-request watchdog — a hung yfinance fetch stalls the whole long-lived loop; two docstrings claim a watchdog that does not exist → `tests/test_crawler.py`
- **FIX-005** (P1) ESEF _fiscal_year tags audited facts by end-year with no duration check — an interim/quarterly value can be recorded as the annual audited figure (contradicts the module's own docstring) → `tests/test_esef.py`
- **FIX-006** (P2) Incremental compute via the existing build_snapshot(symbols=…) seam → `tests/test_snapshot.py`
- **FIX-007** (P2) FX normalization (Frankfurter/ECB, keyless) for cross-currency absolute comparisons → `tests/test_snapshot.py`
- **FIX-008** (P2) attach_ranks fragments the snapshot frame — reproducible PerformanceWarning on the compute hot path → `tests/test_ranks.py`
- **FIX-009** (P2) ingest/service.py hotspot has more than doubled (820 LOC, nesting 14) — worst module in the repo, up from 370 LOC last cycle → `tests/test_service.py`
- **FIX-010** (P2) ESEF concept collisions resolve non-deterministically (last-writer-wins) — e.g. ProfitLoss vs ProfitLossAttributableToOwnersOfParent both map to NetIncome → `tests/test_esef.py`
- **FIX-011** (P2) Raw layer glob('*.parquet') matches leftover '.tmp-*.parquet' partials — pathlib includes dotfiles, defeating write-temp-then-rename atomicity → `tests/test_raw.py`
- **FIX-012** (P2) Stooq solve_pow loops unbounded on a server-supplied difficulty — a raised value pins a CPU core with no time budget or watchdog → `tests/test_stooq_fetch.py`
- **FIX-013** (P2) bootstrap downloads the published dataset non-streaming and buffers it entirely in memory (io.BytesIO(response.content)) — OOM risk on a small self-hosted host → `tests/test_bootstrap.py`
