# FIX-002 — Companies House _company_number parses the filing DATE, not the company number — the whole UK audited layer silently ingests zero rows on real filenames  (P1 · DEFECT)

**Finding F7:** The real Accounts Data Product names files Prod<nnn>_<batch>_<companynumber>_<yyyymmdd>.<ext> (e.g. Prod223_2138_08094273_20230331.html). _company_number does re.findall(r'\d{6,8}', ...) then takes digits[-1] (companies_house.py:197-198), which picks the trailing 8-digit DATE (20230331), not the company number (08094273). Verified empirically: findall -> ['08094273','20230331'], digits[-1]='20230331'. That never matches a wanted company number, so iter_accounts yields nothing and the UK layer ingests zero rows. The unit test masks it: its fixture Prod223_1234567.html has a single digit-run so digits[-1]==digits[0] (tests/test_companies_house.py:62).
**Evidence:** `src/crible/providers/companies_house.py:197`, `src/crible/providers/companies_house.py:198`, `src/crible/providers/companies_house.py:211`
**Why it matters:** An operator enables the UK Companies House tier and points it at a real Accounts Data Product ZIP; every filename resolves to a date, no company matches, and the sweep completes 'successfully' with zero UK companies enriched and no error.

## RED — write this test first
Write a failing test that reproduces: An operator enables the UK Companies House tier and points it at a real Accounts Data Product ZIP; every filename resolves to a date, no company matches, and the sweep completes 'successfully' with zero UK companies enriched and no error.

Suggested test file: `tests/test_companies_house.FIX-002.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Take the company-number token by position/pattern (digits[0], or the token before the yyyymmdd), and handle SC/NI/OC alphanumeric prefixes; add a fixture in the real Prod<nnn>_<batch>_<number>_<date> format.

Touch only: `src/crible/providers/companies_house.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
