# FIX-001 — REGRESSION from the F6 fix: audited-only periods are appended UNSORTED, so the current price, return_6m and every price-derived ratio land on an OLD period instead of the latest — the flagship deep-history universe is now silently mis-priced  (P1 · DEFECT)

**Finding F1:** The c2 F6 fix stopped reconcile from dropping audited-only periods, but it appends them at the END of the frame without re-sorting: reconcile.py:63 does merged.reindex(list(merged.index) + extra_periods). build_canonical guarantees an ascending period index, and build_symbol_snapshot relies on that invariant — it writes the current close to price.iloc[-1] (snapshot.py:79, comment 'the current price applies to the LATEST fiscal period only') and the 6-month momentum to out.iloc[-1] (snapshot.py:96). After the F6 append, iloc[-1] is the newest-appended audited-only period (the OLDEST deep-history year, e.g. 2022 in the repro / 2010s in production), not the latest. So for any scraped symbol that also has deep FSDS/EDGAR history — exactly the US large/mid caps F6 was meant to serve — the current price, return_6m and all price-derived ratios (P/E, P/B, yields) attach to a stale historical period; the true latest period gets NaN price and NaN momentum, and its value/momentum ranks are wrong. The F6 unit test only asserts values by label (test_fr010_esef.py) and never checks period order, so the suite stayed green.
**Evidence:** `src/crible/compute/reconcile.py:63`, `src/crible/compute/snapshot.py:79`, `src/crible/compute/snapshot.py:96`, `src/crible/compute/canonical.py:104`, `run:runs/regression-price-period.txt#L1`
**Why it matters:** An operator ingests SEC FSDS to get deep history for AAPL (the headline Phase-2 feature). AAPL is yfinance-scraped, so reconcile now appends the pre-2021 audited years at the tail; build_symbol_snapshot writes today's price and the 6-month momentum onto a ~2016 row, leaving the 2024 row with NaN price/return_6m. The screener then ranks AAPL on wrong-period price ratios and a blank momentum — the published output is silently corrupted for precisely the universe the deep-history feature targets.

## RED — write this test first
Write a failing test that reproduces: An operator ingests SEC FSDS to get deep history for AAPL (the headline Phase-2 feature). AAPL is yfinance-scraped, so reconcile now appends the pre-2021 audited years at the tail; build_symbol_snapshot writes today's price and the 6-month momentum onto a ~2016 row, leaving the 2024 row with NaN price/return_6m. The screener then ranks AAPL on wrong-period price ratios and a blank momentum — the published output is silently corrupted for precisely the universe the deep-history feature targets.

Suggested test file: `tests/test_reconcile.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Re-sort the merged frame chronologically after the union (e.g. merged = merged.sort_index() at reconcile.py:63, safe because period labels sort chronologically), or insert extra_periods in sorted position; add a fixture asserting an audited-only period deeper than the scrape ends up BEFORE the latest and that price/return_6m still land on the latest period.

Touch only: `src/crible/compute/reconcile.py`, `src/crible/compute/snapshot.py`, `src/crible/compute/canonical.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
