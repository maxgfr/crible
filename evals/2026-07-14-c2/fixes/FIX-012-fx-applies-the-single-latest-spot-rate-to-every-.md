# FIX-012 — FX applies the single latest spot rate to every fiscal period — historical *_eur values are silently wrong  (P2 · DEFECT)

**Finding F12:** fetch_rates pulls Frankfurter's /latest endpoint (fx.py:26) and attach_fx converts every row (all fiscal periods) with that one rate map (fx.py:94-95), so 2015 revenue and 2024 revenue are both normalized at today's EUR rate. The docstring documents the listing-vs-reporting currency approximation but not this temporal one; historical revenue_eur / total_assets_eur look precise but are wrong for cross-period comparison.
**Evidence:** `src/crible/providers/fx.py:26`, `src/crible/providers/fx.py:94`
**Why it matters:** A user screens revenue_eur across years for a USD filer; the older years are converted at today's USD/EUR rate, distorting a multi-year EUR trend.

## RED — write this test first
Write a failing test that reproduces: A user screens revenue_eur across years for a USD filer; the older years are converted at today's USD/EUR rate, distorting a multi-year EUR trend.

Suggested test file: `tests/test_fx.FIX-012.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Fetch dated ECB rates (Frankfurter supports /<date>) and convert each period at its period-end rate; or scope *_eur to the latest period only and document it.

Touch only: `src/crible/providers/fx.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
