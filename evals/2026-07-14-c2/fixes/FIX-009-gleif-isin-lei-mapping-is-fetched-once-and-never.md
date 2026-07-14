# FIX-009 — GLEIF ISIN->LEI mapping is fetched once and never refreshed — the weekly self-heal is gated on file ABSENCE, so EU audited coverage freezes  (P2 · DEFECT)

**Finding F9:** fetch_gleif is correctly staleness-aware (fetch_if_stale with a 7-day max_age, gleif.py:24-35), but both auto-heal callers only invoke it when there is NO mapping at all: run_refresh guards `if load_mapping(data)[0] is None` (service.py:322) and the weekly run_loop timer guards the same (service.py:477). Once isin-lei.zip exists it is never re-fetched, so the 7-day max_age is dead code and new EU ISINs (IPOs, relistings) never resolve to an LEI — those companies get no ESEF audited data, a slow silent coverage regression. Only the manual `ingest --fetch-gleif` bypasses the gate.
**Evidence:** `src/crible/ingest/service.py:322`, `src/crible/ingest/service.py:477`, `src/crible/providers/gleif.py:26`
**Why it matters:** A self-hoster's first refresh downloads the GLEIF file; a year later, dozens of newly-listed EU companies still have no audited figures because the mapping was never refreshed despite the weekly timer firing.

## RED — write this test first
Write a failing test that reproduces: A self-hoster's first refresh downloads the GLEIF file; a year later, dozens of newly-listed EU companies still have no audited figures because the mapping was never refreshed despite the weekly timer firing.

Suggested test file: `tests/test_service.FIX-009.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Call fetch_gleif unconditionally on the weekly timer (let fetch_if_stale decide), dropping the is-None gate; keep the manual command as-is.

Touch only: `src/crible/ingest/service.py`, `src/crible/providers/gleif.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
