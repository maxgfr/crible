# FIX-010 — FSDS parser ignores the coreg column — a co-registrant/guarantor value can be booked as the consolidated audited figure  (P2 · DEFECT)

**Finding F10:** SEC FSDS num.txt carries a coreg column (present in the test header, tests/test_fsds.py) where empty = the consolidated registrant and non-empty = a co-registrant/parent/guarantor (common on bond-issuer 10-Ks). parse_fsds_quarter filters rows on tag, uom, qtrs and ddate but never on coreg (edgar_fsds.py:71-92), and cells are first-writer-wins at equal concept rank (edgar_fsds.py:96-99), so whichever num.txt row appears first wins with no guarantee it is the consolidated one. companyfacts (edgar.py) is immune because its units arrays hold only default-member values — this is an FSDS-format-specific risk. (Blast radius is reduced by F6, which drops FSDS-only periods for scraped symbols.)
**Evidence:** `src/crible/providers/edgar_fsds.py:67`, `src/crible/providers/edgar_fsds.py:80`, `src/crible/providers/edgar_fsds.py:97`
**Why it matters:** A guarantor-subsidiary 10-K's co-registrant revenue appears before the consolidated row in num.txt; it is booked as the audited annual Revenue for that CIK.

## RED — write this test first
Write a failing test that reproduces: A guarantor-subsidiary 10-K's co-registrant revenue appears before the consolidated row in num.txt; it is booked as the audited annual Revenue for that CIK.

Suggested test file: `tests/test_edgar_fsds.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Skip rows where coreg is non-empty (consolidated registrant only); add a fixture with a co-registrant row asserting it is dropped.

Touch only: `src/crible/providers/edgar_fsds.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
