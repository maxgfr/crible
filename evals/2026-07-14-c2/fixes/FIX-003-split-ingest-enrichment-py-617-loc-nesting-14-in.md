# FIX-003 — Split ingest/enrichment.py (617 LOC, nesting 14) into per-provider cycle modules  (P2 · OPPORTUNITY · impact med · effort M)

**Opportunity F1:** The F4 refactor correctly halved service.py (820->523 LOC) by extracting the audited enrichment cycles, but they all landed in ONE module: enrichment.py is now the #2 hotspot at 617 LOC with nesting depth 14, holding 9 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep). The seam (AuditedBulkProvider) exists; the cycles could each move beside their provider so a new source stops growing one file.
**Evidence:** `analysis:src/crible/ingest/enrichment.py`, `src/crible/ingest/enrichment.py:43`
**Why it matters:** The F4 refactor correctly halved service.py (820->523 LOC) by extracting the audited enrichment cycles, but they all landed in ONE module: enrichment.py is now the #2 hotspot at 617 LOC with nesting depth 14, holding 9 parallel run_* cycles (ESEF, EDGAR, EDGAR-bulk, FSDS, Companies House, EDINET, ESEF-sweep). The seam (AuditedBulkProvider) exists; the cycles could each move beside their provider so a new source stops growing one file.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Move each run_<source>_cycle next to its provider (or an ingest/cycles/ package), keeping the shared GLEIF/heartbeat helpers in one place; the per-cycle contracts are already clean.

Suggested test file: `tests/test_enrichment.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Move each run_<source>_cycle next to its provider (or an ingest/cycles/ package), keeping the shared GLEIF/heartbeat helpers in one place; the per-cycle contracts are already clean.

Touch only: `src/crible/ingest/enrichment.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
