# FIX-010 — ESEF concept collisions resolve non-deterministically (last-writer-wins) — e.g. ProfitLoss vs ProfitLossAttributableToOwnersOfParent both map to NetIncome  (P2 · DEFECT)

**Finding F10:** Two distinct IFRS concepts map to the same canonical column (Revenue and RevenueFromContractsWithCustomers → TotalRevenue, esef.py:23-24; ProfitLoss and ProfitLossAttributableToOwnersOfParent → NetIncome, esef.py:27-28). facts_to_frames writes them with last-writer-wins keyed only by (year,column) (esef.py:71), so which concept survives depends on JSON iteration order. For consolidated statements ProfitLoss (group total) and the owners-of-parent figure differ materially (minority interests), yielding a non-deterministic audited NetIncome.
**Evidence:** `src/crible/providers/esef.py:22-39`, `src/crible/providers/esef.py:71`
**Why it matters:** An IFRS filing tags both ProfitLoss and ProfitLossAttributableToOwnersOfParent; the audited NetIncome depends on JSON key order, so two runs (or two filers) disagree on the 'audited' bottom line.

## RED — write this test first
Write a failing test that reproduces: An IFRS filing tags both ProfitLoss and ProfitLossAttributableToOwnersOfParent; the audited NetIncome depends on JSON key order, so two runs (or two filers) disagree on the 'audited' bottom line.

Suggested test file: `tests/test_esef.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Give colliding concepts an explicit precedence (prefer the whole-group total, or the most-specific) and only overwrite when the incoming concept ranks higher; unit-test the collision.

Touch only: `src/crible/providers/esef.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
