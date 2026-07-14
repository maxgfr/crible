# FIX-009 — ingest/service.py hotspot has more than doubled (820 LOC, nesting 14) — worst module in the repo, up from 370 LOC last cycle  (P2 · DEFECT)

**Finding F4:** service.py is the #1 hotspot at 820 LOC with nesting depth 14 (analysis.json). Last cycle's F2 flagged the same module at 370 LOC; the ESEF/EDGAR/bulk enrichment cycles (run_esef_cycle, run_esef_sweep, run_edgar_cycle, run_edgar_bulk, run_refresh, run_loop) were all added to this one file, so the deferred 'extract collaborators' debt is now materially larger and each cycle duplicates the same GLEIF-file / connection / heartbeat boilerplate.
**Evidence:** `src/crible/ingest/service.py:1-820`, `run:analysis.json`, `src/crible/ingest/service.py:223-234`
**Why it matters:** Adding the next data source (e.g. a GLEIF fetcher or a universe-refresh scheduler) means editing an 820-LOC module that mixes queue, budget, ESEF, EDGAR, prices, compute and heartbeat — high regression surface, no boundaries.

## RED — write this test first
Write a failing test that reproduces: Adding the next data source (e.g. a GLEIF fetcher or a universe-refresh scheduler) means editing an 820-LOC module that mixes queue, budget, ESEF, EDGAR, prices, compute and heartbeat — high regression surface, no boundaries.

Suggested test file: `tests/test_service.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Extract the enrichment cycles (EsefCycle, EdgarCycle) and shared helpers (GLEIF mapping loader, _connect/heartbeat) into their own modules; the per-cycle contracts are already clear.

Touch only: `src/crible/ingest/service.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
