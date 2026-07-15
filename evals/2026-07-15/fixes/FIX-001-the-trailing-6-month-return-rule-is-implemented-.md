# FIX-001 — The trailing-6-month-return rule is implemented three times (two languages), kept in sync only by comments  (P1 · OPPORTUNITY · impact high · effort S)

**Opportunity F1:** The same financial invariant — return = lastClose / (last close at or before asof-182d) - 1, never extrapolated — is coded three independent times: compute.ranks.price_return (src/crible/compute/ranks.py:36, pandas, crawl path), _distill (src/crible/ingest/price_import.py:112, pandas, Stooq path) and a DuckDB SQL variant (src/crible/ingest/price_import.py:168, HuggingFace path). They stay consistent only via cross-referencing comments; the window constant RETURN_WINDOW_DAYS is redeclared at price_import.py:38 separately from ranks.price_return(days=182). A future change (trading vs calendar days, dividend handling, window) must be edited in three places and the imported-dump paths would silently diverge from the crawl path by data source.
**Evidence:** `src/crible/compute/ranks.py:36`, `src/crible/ingest/price_import.py:112`, `src/crible/ingest/price_import.py:168`
**Why it matters:** The same financial invariant — return = lastClose / (last close at or before asof-182d) - 1, never extrapolated — is coded three independent times: compute.ranks.price_return (src/crible/compute/ranks.py:36, pandas, crawl path), _distill (src/crible/ingest/price_import.py:112, pandas, Stooq path) and a DuckDB SQL variant (src/crible/ingest/price_import.py:168, HuggingFace path). They stay consistent only via cross-referencing comments; the window constant RETURN_WINDOW_DAYS is redeclared at price_import.py:38 separately from ranks.price_return(days=182). A future change (trading vs calendar days, dividend handling, window) must be edited in three places and the imported-dump paths would silently diverge from the crawl path by data source.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Add one shared golden fixture (a bar series -> one expected return_6m) asserted against all three paths (a parity test locks the SQL path). Optionally collapse _distill and price_return onto a single helper.

Suggested test file: `tests/test_ranks.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Add one shared golden fixture (a bar series -> one expected return_6m) asserted against all three paths (a parity test locks the SQL path). Optionally collapse _distill and price_return onto a single helper.

Touch only: `src/crible/compute/ranks.py`, `src/crible/ingest/price_import.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
