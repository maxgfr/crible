# FIX-012 — Stooq solve_pow loops unbounded on a server-supplied difficulty — a raised value pins a CPU core with no time budget or watchdog  (P2 · DEFECT)

**Finding F12:** solve_pow (stooq_fetch.py:61-68) brute-forces SHA-256 until the digest starts with `difficulty` hex zeros, with no upper bound and no time budget; `difficulty` comes verbatim from the remote page (parsed at stooq_fetch.py:90 and passed at :93). Each extra hex zero multiplies expected work ~16x, so a changed or hostile value makes the automated bulk-price download spin a core indefinitely — and there is no crawler watchdog to interrupt it (see F2).
**Evidence:** `src/crible/ingest/stooq_fetch.py:61-68`, `src/crible/ingest/stooq_fetch.py:90-93`
**Why it matters:** Stooq raises the PoW difficulty (or serves a hostile value); the headless bulk import wedges on 100% CPU with no timeout, blocking the price refresh indefinitely.

## RED — write this test first
Write a failing test that reproduces: Stooq raises the PoW difficulty (or serves a hostile value); the headless bulk import wedges on 100% CPU with no timeout, blocking the price refresh indefinitely.

Suggested test file: `tests/test_stooq_fetch.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Bound solve_pow by a max difficulty and a wall-clock/iteration budget; raise StooqError past the budget so the caller degrades to the manual archive path.

Touch only: `src/crible/ingest/stooq_fetch.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
