# FIX-001 — Periodic universe refresh inside run_loop (the self-hosted service never re-downloads FinanceDatabase)  (P1 · OPPORTUNITY · impact high · effort S)

**Opportunity F5:** refresh_universe already exists (universe.py:213) and the nightly run_refresh calls it (service.py:697), but the long-lived Docker service (docker-compose command `crible ingest --loop`) only bootstraps on first boot (service.py:776-778) and never refreshes again. A self-hoster's delisted flags and new listings freeze forever. The upsert is already idempotent, so this is a scheduler, not new logic.
**Evidence:** `src/crible/ingest/service.py:776-778`, `src/crible/universe.py:213-224`, `docker-compose.yml:8`
**Why it matters:** refresh_universe already exists (universe.py:213) and the nightly run_refresh calls it (service.py:697), but the long-lived Docker service (docker-compose command `crible ingest --loop`) only bootstraps on first boot (service.py:776-778) and never refreshes again. A self-hoster's delisted flags and new listings freeze forever. The upsert is already idempotent, so this is a scheduler, not new logic.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Add a weekly `if now - last_universe_refresh >= 7*86400: refresh_universe(con); queue.seed_from_universe()` branch to run_loop, mirroring the price-refresh cadence already there (service.py:793).

Suggested test file: `tests/test_service.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Add a weekly `if now - last_universe_refresh >= 7*86400: refresh_universe(con); queue.seed_from_universe()` branch to run_loop, mirroring the price-refresh cadence already there (service.py:793).

Touch only: `src/crible/ingest/service.py`, `src/crible/universe.py`, `docker-compose.yml`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
