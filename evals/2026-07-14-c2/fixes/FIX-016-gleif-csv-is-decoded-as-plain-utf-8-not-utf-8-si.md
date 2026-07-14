# FIX-016 — GLEIF CSV is decoded as plain utf-8 (not utf-8-sig) — a BOM in the source file would silently zero the entire mapping  (P2 · DEFECT)

**Finding F16:** load_isin_lei_map decodes the CSV with utf-8, not utf-8-sig (gleif.py:49). If the GLEIF relationship CSV ships with a UTF-8 BOM, the first header key becomes '\ufeffLEI', so lower.get('lei') returns None for every row (gleif.py:52), the `if isin and lei` guard is always false, and the mapping loads 0 relationships — logged as a benign 'loaded 0', silently disabling all audited-EU coverage. Whether it triggers depends on the live file carrying a BOM (not verified here); the unit fixture has none so the test cannot see it.
**Evidence:** `src/crible/providers/gleif.py:49`, `src/crible/providers/gleif.py:52`
**Why it matters:** GLEIF publishes the file with a BOM; the auto-fetched mapping parses to zero relationships and every EU listing lands in 'unmatched', with only an info-level 'loaded 0' to signal it.

## RED — write this test first
Write a failing test that reproduces: GLEIF publishes the file with a BOM; the auto-fetched mapping parses to zero relationships and every EU listing lands in 'unmatched', with only an info-level 'loaded 0' to signal it.

Suggested test file: `tests/test_gleif.FIX-016.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Decode with utf-8-sig (or strip a leading BOM); add a BOM'd fixture asserting the mapping still loads.

Touch only: `src/crible/providers/gleif.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
