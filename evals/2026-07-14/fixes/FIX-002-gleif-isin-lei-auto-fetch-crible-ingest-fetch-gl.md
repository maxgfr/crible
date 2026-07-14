# FIX-002 — GLEIF ISIN→LEI auto-fetch (crible ingest --fetch-gleif) — unlock the idle audited-EU layer  (P1 · OPPORTUNITY · impact high · effort M)

**Opportunity F6:** The whole ESEF audited-EU enrichment (run_esef_sweep/run_esef_cycle) is wired but stays idle out-of-the-box: it needs data/isin-lei.csv and nothing downloads it. gleif.py:21 defines ISIN_LEI_LATEST_URL but it is never referenced (dead constant); service.py:229 tells the operator to fetch the ~200 MB file by hand. A self-hoster gets zero audited EU coverage until they discover this. The research doc confirms GLEIF publishes the ISIN↔LEI relationship files as keyless open data ([S12][S53]).
**Evidence:** `src/crible/providers/gleif.py:21`, `src/crible/ingest/service.py:227-232`, `docs/research/2026-07-13-data-sources/SUMMARY.md:5`
**Why it matters:** The whole ESEF audited-EU enrichment (run_esef_sweep/run_esef_cycle) is wired but stays idle out-of-the-box: it needs data/isin-lei.csv and nothing downloads it. gleif.py:21 defines ISIN_LEI_LATEST_URL but it is never referenced (dead constant); service.py:229 tells the operator to fetch the ~200 MB file by hand. A self-hoster gets zero audited EU coverage until they discover this. The research doc confirms GLEIF publishes the ISIN↔LEI relationship files as keyless open data ([S12][S53]).

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Add a downloader (stream ISIN_LEI_LATEST_URL to data/isin-lei.csv, with timeout + size guard) exposed as `crible ingest --fetch-gleif`, and call it from run_refresh so the nightly self-heals the mapping.

Suggested test file: `tests/test_gleif.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Add a downloader (stream ISIN_LEI_LATEST_URL to data/isin-lei.csv, with timeout + size guard) exposed as `crible ingest --fetch-gleif`, and call it from run_refresh so the nightly self-heals the mapping.

Touch only: `src/crible/providers/gleif.py`, `src/crible/ingest/service.py`, `docs/research/2026-07-13-data-sources/SUMMARY.md`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
