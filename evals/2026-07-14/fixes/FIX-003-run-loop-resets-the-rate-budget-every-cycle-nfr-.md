# FIX-003 — run_loop resets the rate budget every cycle — NFR-007 (330 req/h polite crawl) is silently violated on the self-hosted `ingest --loop` path  (P1 · DEFECT)

**Finding F1:** The shipped self-hosted service runs `crible ingest --loop` (docker-compose.yml:8) → run_loop, which calls run_once once per cycle (service.py:788). run_once builds a FRESH crawler with a FRESH TokenBucket every call (service.py:187 → _make_crawler service.py:178). TokenBucket state is per-instance (budget.py:28), so each cycle starts with a full 330-token budget. With cycle_limit=40 and yfinance requests_per_fetch=7 (yfinance_provider.py:31), one cycle spends 280 < 330 and never throttles, then returns and the loop immediately starts another full-budget cycle (no inter-cycle sleep unless the queue is drained, service.py:819-820). Steady-state crawl therefore issues far more than 330 requests/rolling-hour. run_refresh's own docstring documents exactly this hazard and fixes it by sharing ONE bucket across cycles (service.py:678-680, crawler built once service.py:707) — run_loop never received that fix. budget.py:3-5 calls staying under budget 'a hard constraint of the keyless design, not an optimisation' (NFR-007).
**Evidence:** `src/crible/ingest/service.py:788`, `src/crible/ingest/service.py:184-199`, `src/crible/ingest/service.py:174-181`, `src/crible/ingest/service.py:678-680`, `src/crible/ingest/budget.py:35-43`, `docker-compose.yml:8`
**Why it matters:** A self-hoster runs the shipped `docker compose up`; during backlog burn-down the ingest loop issues ~280 requests every few seconds — thousands/hour — blowing past the 330/h politeness budget and getting the IP rate-limited or banned by Yahoo, contradicting the keyless design's central promise.

## RED — write this test first
Write a failing test that reproduces: A self-hoster runs the shipped `docker compose up`; during backlog burn-down the ingest loop issues ~280 requests every few seconds — thousands/hour — blowing past the 330/h politeness budget and getting the IP rate-limited or banned by Yahoo, contradicting the keyless design's central promise.

Suggested test file: `tests/test_service.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Build the crawler + one TokenBucket once outside the loop (as run_refresh does) and reuse crawler.run_cycle across iterations; or hold the bucket in run_loop and inject it into run_once. Add a regression test asserting cumulative acquisitions across N cycles stay ≤ capacity per rolling hour.

Touch only: `src/crible/ingest/service.py`, `src/crible/ingest/budget.py`, `docker-compose.yml`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
