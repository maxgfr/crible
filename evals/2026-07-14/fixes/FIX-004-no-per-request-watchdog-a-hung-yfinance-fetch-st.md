# FIX-004 — No per-request watchdog — a hung yfinance fetch stalls the whole long-lived loop; two docstrings claim a watchdog that does not exist  (P1 · DEFECT)

**Finding F2:** Crawler.crawl_symbol calls provider.fetch_statements(symbol) with no hard timeout (crawler.py:70); there is no signal/thread-join/ThreadPoolExecutor timeout anywhere in ingest/ or providers/. Yet prices.py:6-7 says hangs are 'enforced by the crawler's watchdog' and yfinance_provider.py:6 says 'a per-call watchdog is the crawler's job, not ours' — both delegate hang-protection to a watchdog that was never implemented (ADR-0004 promised it per TODO.md:17-22). yfinance owns its own session and has documented hang cases; a single stuck socket blocks the entire single-threaded run_loop indefinitely with no reschedule.
**Evidence:** `src/crible/ingest/crawler.py:60-70`, `src/crible/providers/yfinance_provider.py:6`, `src/crible/ingest/prices.py:6-7`, `TODO.md:17-22`, `src/crible/providers/yfinance_provider.py:36-58`
**Why it matters:** yfinance hangs on one symbol (known upstream behaviour); crawl_symbol never returns, the loop stops advancing, the heartbeat goes stale, and coverage plateaus until an operator restarts the container.

## RED — write this test first
Write a failing test that reproduces: yfinance hangs on one symbol (known upstream behaviour); crawl_symbol never returns, the loop stops advancing, the heartbeat goes stale, and coverage plateaus until an operator restarts the container.

Suggested test file: `tests/test_crawler.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Wrap fetch_statements in a hard deadline (thread + .join(timeout) or a watchdog thread), treat a timeout as a failure → queue.mark_failed + reschedule; then the two docstrings become true.

Touch only: `src/crible/ingest/crawler.py`, `src/crible/providers/yfinance_provider.py`, `src/crible/ingest/prices.py`, `TODO.md`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
