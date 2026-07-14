# FIX-013 — EDINET sweep applies no document-type filter and books interim balance-sheet instants as annual figures  (P2 · DEFECT)

**Finding F13:** run_edinet processes any swept document whose secCode matches, with no docTypeCode/ordinanceCode filter despite the 'annual securities reports' contract (enrichment.py:480-483). A quarterly/semi-annual report thus reaches the parser; the income branch's full-year duration guard drops interim durations, but the balance branch of _period accepts ANY instant and returns its calendar year (edinet.py:60-63), so an interim balance instant (e.g. 2023-09-30) is booked as the '2023' annual balance — the same interim-as-annual class as the prior-cycle ESEF F9. EDINET is opt-in (off without a key).
**Evidence:** `src/crible/ingest/enrichment.py:480`, `src/crible/providers/edinet.py:60`
**Why it matters:** A semi-annual EDINET report for a JP filer is swept; its Sep-30 interim balance-sheet instant is stored as the annual audited TotalAssets for that year.

## RED — write this test first
Write a failing test that reproduces: A semi-annual EDINET report for a JP filer is swept; its Sep-30 interim balance-sheet instant is stored as the annual audited TotalAssets for that year.

Suggested test file: `tests/test_enrichment.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Filter to annual securities-report docTypeCodes in run_edinet, and require the balance instant's month-day to match the entity's fiscal-year-end before tagging it annual.

Touch only: `src/crible/ingest/enrichment.py`, `src/crible/providers/edinet.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
