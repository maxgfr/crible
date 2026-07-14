# FIX-004 — Audited-only symbols still carry no field-level provenance (audited_fields empty) — the c2 F3 gap is unresolved on the production path  (P2 · DEFECT)

**Finding F2:** build_symbol_rows passes audited_frames=audited only when a yfinance scrape exists, else None (snapshot.py:199), while feeding the audited data in as the primary frames (scraped or audited, snapshot.py:197). In build_symbol_snapshot the audited_fields provenance is only populated inside the `if audited_frames:` block (snapshot.py:54, 60) and via reconcile (snapshot.py:65), so an audited-only symbol takes neither branch: every field is audited yet the audited_fields output column (snapshot.py:101-102) is empty. Row-level provider still records the source, so this is a provenance-completeness gap, not a data error — but it is exactly the case (a listing with no yfinance scrape) the audited layers exist to serve.
**Evidence:** `src/crible/compute/snapshot.py:199`, `src/crible/compute/snapshot.py:54`, `src/crible/compute/snapshot.py:101`
**Why it matters:** A JP/UK listing with no yfinance data is enriched purely from EDINET/Companies House; its rows are entirely audited but the audited_fields column is blank, so a user cannot tell the figures are as-filed.

## RED — write this test first
Write a failing test that reproduces: A JP/UK listing with no yfinance data is enriched purely from EDINET/Companies House; its rows are entirely audited but the audited_fields column is blank, so a user cannot tell the figures are as-filed.

Suggested test file: `tests/test_snapshot.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
When canonical is seeded directly from audited (audited-only path), mark all present fields as audited in audited_fields — pass audited_frames through even when scraped is empty, or populate the column in the audited-only branch as done at snapshot.py:60.

Touch only: `src/crible/compute/snapshot.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
