# FIX-003 — run_loop (106 LOC, # pragma: no cover) hand-rolls six time-gated blocks and duplicates run_refresh's enrichment sequence  (P2 · OPPORTUNITY · impact med · effort M)

**Opportunity F3:** run_loop (src/crible/ingest/service.py:422) is the primary self-hosted deployment entrypoint (the docker ingest service) yet is marked `# pragma: no cover` — zero test coverage. It hand-rolls six near-identical time-gated maintenance blocks (each an `if now - last_X >= INTERVAL: try: ... except Exception: log.warning`), and run_refresh (src/crible/ingest/service.py:281) re-implements the same enrichment sequence with its own parallel try/except-log blocks. test_service.py covers only run_once and maybe_refresh_universe.
**Evidence:** `src/crible/ingest/service.py:422`, `src/crible/ingest/service.py:281`
**Why it matters:** run_loop (src/crible/ingest/service.py:422) is the primary self-hosted deployment entrypoint (the docker ingest service) yet is marked `# pragma: no cover` — zero test coverage. It hand-rolls six near-identical time-gated maintenance blocks (each an `if now - last_X >= INTERVAL: try: ... except Exception: log.warning`), and run_refresh (src/crible/ingest/service.py:281) re-implements the same enrichment sequence with its own parallel try/except-log blocks. test_service.py covers only run_once and maybe_refresh_universe.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Extract a periodic-task table [(name, interval, fn)] driven by a tick(now) helper so run_loop becomes a loop over it (unit-testable without the infinite loop); factor the shared enrichment sequence into one orchestrator both run_loop and run_refresh call.

Suggested test file: `tests/test_service.FIX-003.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Extract a periodic-task table [(name, interval, fn)] driven by a tick(now) helper so run_loop becomes a loop over it (unit-testable without the infinite loop); factor the shared enrichment sequence into one orchestrator both run_loop and run_refresh call.

Touch only: `src/crible/ingest/service.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
