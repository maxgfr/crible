# FIX-002 — ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 opportunity still open  (P2 · OPPORTUNITY · impact med · effort M)

**Opportunity F5:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep) at reconcile.py:43-513. The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
**Evidence:** `src/crible/ingest/enrichment.py:43`, `src/crible/ingest/enrichment.py:513`
**Why it matters:** The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep) at reconcile.py:43-513. The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Move each run_<source>_cycle next to its provider (or an ingest/cycles/ package), keeping the shared GLEIF/heartbeat helpers in one place.

Suggested test file: `tests/test_enrichment.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Move each run_<source>_cycle next to its provider (or an ingest/cycles/ package), keeping the shared GLEIF/heartbeat helpers in one place.

Touch only: `src/crible/ingest/enrichment.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
