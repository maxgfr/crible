# FIX-001 — reconcile discards every audited period the scrape lacks — FSDS/EDGAR deep-history backfill is silently truncated to the yfinance window for scraped symbols  (P1 · DEFECT)

**Finding F6:** merge_audited correctly assembles deep audited history (companyfacts primary + FSDS backfill) into the audited frames (audited.py:48-58), but for any symbol that ALSO has a yfinance scrape, build_symbol_snapshot reconciles the audited frame INTO the scraped canonical (snapshot.py:63) and reconcile only OVERRIDES periods already present: merged is seeded from scraped (reconcile.py:56) and audited-only periods are skipped, never appended (reconcile.py:65-66). align_periods (reconcile.py:20-45) only relabels an audited period onto a same-year scraped label. So every audited period older than yfinance's ~4-year window is dropped for scraped symbols — i.e. essentially all US large/mid caps. This directly contradicts the stated purpose of the Phase-2 FSDS source.
**Evidence:** `src/crible/compute/reconcile.py:56`, `src/crible/compute/reconcile.py:65`, `src/crible/providers/audited.py:44`, `src/crible/ingest/enrichment.py:307`
**Why it matters:** A self-hoster ingests SEC FSDS to get 15+ years of as-filed history for AAPL; because AAPL is yfinance-scraped, reconcile truncates the audited history back to ~4 years and the deep backfill never reaches the snapshot — the headline feature is silently inert for its target universe.

## RED — write this test first
Write a failing test that reproduces: A self-hoster ingests SEC FSDS to get 15+ years of as-filed history for AAPL; because AAPL is yfinance-scraped, reconcile truncates the audited history back to ~4 years and the deep backfill never reaches the snapshot — the headline feature is silently inert for its target universe.

Suggested test file: `tests/test_reconcile.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
In reconcile, union periods: append audited-only periods to merged (marking every field audited) instead of skipping them; add a fixture with an audited period outside the scraped index asserting it survives.

Touch only: `src/crible/compute/reconcile.py`, `src/crible/providers/audited.py`, `src/crible/ingest/enrichment.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
