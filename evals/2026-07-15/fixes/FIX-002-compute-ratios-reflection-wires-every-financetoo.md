# FIX-002 — compute_ratios reflection-wires every financetoolkit get_* and swallows every exception, with no direct test  (P2 · OPPORTUNITY · impact med · effort S)

**Opportunity F2:** compute_ratios (src/crible/compute/ratios.py:109) is the snapshot's widest column producer: it reflection-wires every get_* across financetoolkit's ratio modules, each guarded by a blanket `except Exception: continue` (src/crible/compute/ratios.py:123). It has no direct test (only indirect exercise via snapshot building). If financetoolkit renames a parameter or adds a get_* with an unresolvable required arg, the affected ratio columns silently vanish from the snapshot with zero signal — degrading the core product output.
**Evidence:** `src/crible/compute/ratios.py:109`, `src/crible/compute/ratios.py:123`
**Why it matters:** compute_ratios (src/crible/compute/ratios.py:109) is the snapshot's widest column producer: it reflection-wires every get_* across financetoolkit's ratio modules, each guarded by a blanket `except Exception: continue` (src/crible/compute/ratios.py:123). It has no direct test (only indirect exercise via snapshot building). If financetoolkit renames a parameter or adds a get_* with an unresolvable required arg, the affected ratio columns silently vanish from the snapshot with zero signal — degrading the core product output.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Add a wired-ratio inventory golden test: over a fixed canonical frame, assert the expected set of produced ratio column names (and a couple of known values). Silent column loss then fails CI.

Suggested test file: `tests/test_ratios.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Add a wired-ratio inventory golden test: over a fixed canonical frame, assert the expected set of produced ratio column names (and a couple of known values). Silent column loss then fails CI.

Touch only: `src/crible/compute/ratios.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
