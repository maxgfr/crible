# FIX-007 — FX normalization (Frankfurter/ECB, keyless) for cross-currency absolute comparisons  (P2 · OPPORTUNITY · impact med · effort M)

**Opportunity F8:** Ratios are currency-neutral so the gap is modest, but absolute values (market_cap, revenue) are stored in native currency with no normalized companion columns — grep for frankfurter|market_cap_eur|fx_rate finds nothing. Cross-currency screening on absolute size is therefore misleading. The research doc identifies a keyless source: ECB reference rates via api.frankfurter.dev ([S71][S72]).
**Evidence:** `src/crible/compute/snapshot.py:135-148`, `docs/research/2026-07-13-data-sources/SUMMARY.md:9`
**Why it matters:** Ratios are currency-neutral so the gap is modest, but absolute values (market_cap, revenue) are stored in native currency with no normalized companion columns — grep for frankfurter|market_cap_eur|fx_rate finds nothing. Cross-currency screening on absolute size is therefore misleading. The research doc identifies a keyless source: ECB reference rates via api.frankfurter.dev ([S71][S72]).

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Store daily ECB rates (Frankfurter, keyless, cite source), add companion columns (market_cap_eur, revenue_eur…) at snapshot build, expose via whitelist/UI.

Suggested test file: `tests/test_snapshot.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Store daily ECB rates (Frankfurter, keyless, cite source), add companion columns (market_cap_eur, revenue_eur…) at snapshot build, expose via whitelist/UI.

Touch only: `src/crible/compute/snapshot.py`, `docs/research/2026-07-13-data-sources/SUMMARY.md`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
