# FIX-005 — ESEF _fiscal_year tags audited facts by end-year with no duration check — an interim/quarterly value can be recorded as the annual audited figure (contradicts the module's own docstring)  (P1 · DEFECT)

**Finding F9:** facts_to_frames promises 'Only full-year instant/duration facts ... are kept' (esef.py:48), but _fiscal_year (esef.py:87-103) derives the fiscal year purely from the period's END date and never validates that a duration spans a full year (contrast EDGAR, which checks a ~full-year span). A duration fact like 2024-07-01/2024-12-31 (an interim period ending Dec 31) is therefore tagged year '2024' and, at esef.py:71 (values.setdefault(year,{})[column]=value, last-writer-wins), can overwrite the true annual value for the same concept/year. Because audited ESEF values OUTRANK scraped Yahoo values at reconciliation (reconcile.py:1-6, 84), a mis-tagged interim number silently corrupts the flagship 'audited & traceable' figure.
**Evidence:** `src/crible/providers/esef.py:87-103`, `src/crible/providers/esef.py:45-51`, `src/crible/providers/esef.py:71`, `src/crible/compute/reconcile.py:84`
**Why it matters:** A filer's latest ESEF document (picked by sort -date_added) carries an interim duration fact ending Dec 31; it is stored as the annual audited Revenue/NetIncome, overrides the correct scraped value, and the screener ranks the company on a wrong 'audited' number.

## RED — write this test first
Write a failing test that reproduces: A filer's latest ESEF document (picked by sort -date_added) carries an interim duration fact ending Dec 31; it is stored as the annual audited Revenue/NetIncome, overrides the correct scraped value, and the screener ranks the company on a wrong 'audited' number.

Suggested test file: `tests/test_esef.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
In _fiscal_year (or facts_to_frames) require duration facts to span ~360-372 days before accepting them as annual; keep instants as period-end snapshots. Add a fixture with an interim duration asserting it is dropped.

Touch only: `src/crible/providers/esef.py`, `src/crible/compute/reconcile.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
