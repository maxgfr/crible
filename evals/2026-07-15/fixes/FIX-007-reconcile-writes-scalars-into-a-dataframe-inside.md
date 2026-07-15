# FIX-007 — reconcile writes scalars into a DataFrame inside a double loop — per-cell .loc on deep-history symbols  (P2 · OPPORTUNITY · impact low · effort M)

**Opportunity F7:** reconcile (src/crible/compute/reconcile.py:72) does `merged.loc[period, column] = audited_value` inside `for period: for column:`, resolving the label pair on every cell. With deep-history backfill (FSDS/EDGAR add many periods) times ~25 canonical columns this is O(periods x columns) chained .loc scalar assignments per symbol — a real (if bounded) slow path on the flagship deep-history universe.
**Evidence:** `src/crible/compute/reconcile.py:72`
**Why it matters:** reconcile (src/crible/compute/reconcile.py:72) does `merged.loc[period, column] = audited_value` inside `for period: for column:`, resolving the label pair on every cell. With deep-history backfill (FSDS/EDGAR add many periods) times ~25 canonical columns this is O(periods x columns) chained .loc scalar assignments per symbol — a real (if bounded) slow path on the flagship deep-history universe.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Build the audited values as an overlay frame and apply once (merged.update / masked vectorized assign), keeping the >5% discrepancy logging as a separate masked pass. Behaviour identical.

Suggested test file: `tests/test_reconcile.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Build the audited values as an overlay frame and apply once (merged.update / masked vectorized assign), keeping the >5% discrepancy logging as a separate masked pass. Behaviour identical.

Touch only: `src/crible/compute/reconcile.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
