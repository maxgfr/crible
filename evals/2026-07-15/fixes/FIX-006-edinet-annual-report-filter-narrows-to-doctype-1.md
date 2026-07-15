# FIX-006 — EDINET annual-report filter narrows to docType 120 and also excludes amended annual reports (訂正有報, docType 130)  (P2 · OPPORTUNITY · impact low · effort S)

**Opportunity F6:** The (correct) interim-report fix narrows EDINET ingestion to ANNUAL_DOC_TYPES = {"120"} (src/crible/providers/edinet.py:26, applied at src/crible/ingest/enrich/jp.py:58). docType 120 is the annual securities report (有価証券報告書); 130 is its amendment (訂正有価証券報告書). The base commit processed all docs, so this new filter also drops amended annual figures. This is collateral of an otherwise-correct fix and is strictly better than the base (which mis-booked quarterly/semi-annual figures as annual); EDINET is free-key and OFF by default, so blast radius is minimal. Not a regression from a working state, but a small completeness gap: a company that supersedes its 120 with a 130 correction keeps the pre-correction figures.
**Evidence:** `src/crible/providers/edinet.py:26`, `src/crible/ingest/enrich/jp.py:58`
**Why it matters:** The (correct) interim-report fix narrows EDINET ingestion to ANNUAL_DOC_TYPES = {"120"} (src/crible/providers/edinet.py:26, applied at src/crible/ingest/enrich/jp.py:58). docType 120 is the annual securities report (有価証券報告書); 130 is its amendment (訂正有価証券報告書). The base commit processed all docs, so this new filter also drops amended annual figures. This is collateral of an otherwise-correct fix and is strictly better than the base (which mis-booked quarterly/semi-annual figures as annual); EDINET is free-key and OFF by default, so blast radius is minimal. Not a regression from a working state, but a small completeness gap: a company that supersedes its 120 with a 130 correction keeps the pre-correction figures.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: If corrected annual figures matter, set ANNUAL_DOC_TYPES = {"120", "130"} and add a fixture asserting a 130 amendment is ingested while quarterly (140)/semi-annual (160) stay excluded.

Suggested test file: `tests/test_edinet.FIX-006.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
If corrected annual figures matter, set ANNUAL_DOC_TYPES = {"120", "130"} and add a fixture asserting a 130 amendment is ingested while quarterly (140)/semi-annual (160) stay excluded.

Touch only: `src/crible/providers/edinet.py`, `src/crible/ingest/enrich/jp.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
