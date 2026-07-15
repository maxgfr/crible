# FIX-004 — build_symbol_snapshot is a 70-line, five-concern function (the depth-8 hotspot) — invariants only reachable through the whole body  (P2 · OPPORTUNITY · impact med · effort M)

**Opportunity F4:** build_symbol_snapshot (src/crible/compute/snapshot.py:42) interleaves five distinct rules in one body: audited reconcile+alignment, the crawled-vs-imported price fallback (src/crible/compute/snapshot.py:76, 'current price applies to the LATEST fiscal period only'), ratios/scores/growth assembly, momentum resolution, and three provenance columns via positional .iloc writes. Each rule is individually testable but currently reachable only through the whole function.
**Evidence:** `src/crible/compute/snapshot.py:42`, `src/crible/compute/snapshot.py:76`
**Why it matters:** build_symbol_snapshot (src/crible/compute/snapshot.py:42) interleaves five distinct rules in one body: audited reconcile+alignment, the crawled-vs-imported price fallback (src/crible/compute/snapshot.py:76, 'current price applies to the LATEST fiscal period only'), ratios/scores/growth assembly, momentum resolution, and three provenance columns via positional .iloc writes. Each rule is individually testable but currently reachable only through the whole function.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Extract _merge_audited, _apply_price_fallback and _provenance_columns helpers so each load-bearing invariant gets a direct test; the top function then reads as a pipeline.

Suggested test file: `tests/test_snapshot.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Extract _merge_audited, _apply_price_fallback and _provenance_columns helpers so each load-bearing invariant gets a direct test; the top function then reads as a pipeline.

Touch only: `src/crible/compute/snapshot.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
