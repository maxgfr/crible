# FIX-008 — attach_ranks fragments the snapshot frame — reproducible PerformanceWarning on the compute hot path  (P2 · DEFECT)

**Finding F3:** attach_ranks adds rank columns one at a time via repeated single-column assignment on the full snapshot frame (ranks.py:96-99: a per-column loop then two more inserts), triggering pandas' 'DataFrame is highly fragmented' PerformanceWarning — reproduced 16x in the test run (tests/test_refresh.py). It runs on the compute write path over the whole assembled universe, so cost scales with universe size exactly where the README targets ~150k rows.
**Evidence:** `src/crible/compute/ranks.py:96-99`, `run:runs/core.md#L11`
**Why it matters:** As the universe grows, the fragmented-frame inserts turn a linear column-attach into repeated full-frame copies, inflating each compute cycle's wall-clock with no functional signal that anything is wrong.

## RED — write this test first
Write a failing test that reproduces: As the universe grows, the fragmented-frame inserts turn a linear column-attach into repeated full-frame copies, inflating each compute cycle's wall-clock with no functional signal that anything is wrong.

Suggested test file: `tests/test_ranks.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Build the rank columns in a dict / separate frame and attach with a single pd.concat(axis=1), or pre-allocate; assert no PerformanceWarning in a focused test.

Touch only: `src/crible/compute/ranks.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
