# FIX-005 — Audited-only symbols carry no field-level provenance (audited_fields empty)  (P2 · OPPORTUNITY · impact low · effort S)

**Opportunity F3:** In build_symbol_snapshot, when a symbol has no yfinance scrape, audited_frames is passed as None (snapshot.py:200) so the reconcile path that populates the audited_fields provenance column never runs — every field is audited yet audited_fields is empty (snapshot.py:101-103). Row-level provider still records the source, so this is a provenance-completeness gap, not a data error.
**Evidence:** `src/crible/compute/snapshot.py:200`, `src/crible/compute/snapshot.py:101`
**Why it matters:** In build_symbol_snapshot, when a symbol has no yfinance scrape, audited_frames is passed as None (snapshot.py:200) so the reconcile path that populates the audited_fields provenance column never runs — every field is audited yet audited_fields is empty (snapshot.py:101-103). Row-level provider still records the source, so this is a provenance-completeness gap, not a data error.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: When canonical is seeded directly from audited (snapshot.py:60), mark all present fields as audited in audited_fields (already done there for the empty-canonical branch — verify it reaches the output column).

Suggested test file: `tests/test_snapshot.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
When canonical is seeded directly from audited (snapshot.py:60), mark all present fields as audited in audited_fields (already done there for the empty-canonical branch — verify it reaches the output column).

Touch only: `src/crible/compute/snapshot.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
