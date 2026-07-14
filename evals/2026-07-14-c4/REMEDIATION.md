# Remediation plan — .

Target: `/Users/maxime/Downloads/crible` · 3 fix task(s), most impactful first.
Each task has a matching TDD card under `fixes/` (RED failing test → GREEN change → VERIFY).

## P2 — Minor: polish, consistency, or documentation drift; no scored dimension materially degraded (3)

- **FIX-001** ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 / c3 F5 opportunity still open — The audited enrichment cycles all still live in one module: enrichment.py is 617 LOC holding 7 parallel run_* cycles (ESEF enrichment.py:43, EDGAR :131, EDGAR-bulk :214, FSDS :301, Companies House :396, EDINET :437, ESEF-sweep :513). The per-cycle contracts are already clean, so each could move beside its provider (or an ingest/cycles/ package) to stop one file growing with every new source.
  - fix: Move each run_<source>_cycle next to its provider (or an ingest/cycles/ package), keeping the shared GLEIF/heartbeat helpers in one place.
  - targets: src/crible/ingest/enrichment.py
- **FIX-002** EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13 / c3 F3, unresolved) — A JP company's Q2 report lands in the swept day; its mid-year balance instant is booked as the annual TotalAssets/Equity, distorting every balance-derived ratio for that symbol.
  - fix: Filter list_documents (or the sweep loop) to the annual securities report docTypeCode (120) and/or require the balance instant to match the annual period end; add a fixture with an interim filing asserting it is skipped.
  - targets: src/crible/providers/edinet.py
- **FIX-003** EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14 / c3 F4, unresolved) — A group whose non-consolidated (単体) Revenue context is parsed before the consolidated (連結) one books parent-only revenue as the audited group figure.
  - fix: Capture the consolidated/non-consolidated member per context and prefer the consolidated one (or drop non-consolidated when a consolidated exists); add a fixture with both contexts asserting the consolidated value wins.
  - targets: src/crible/providers/edinet.py
