# Comparison — base `evals/2026-07-14-c2` → current `evals/2026-07-14-c3`

- base: engine 1.9.0 · protocol 2 · rubric 1 · target 70a3203*
- current: engine 1.9.0 · protocol 2 · rubric 1 · target ee2eb09

Score: 73 → 77 (+4) · meets-expectations false → false

## Resolved since base (16)

- opp · Split ingest/enrichment.py (617 LOC, nesting 14) into per-provider cycle modules
- opp · Mirror sidecar meta write is non-atomic — a crash mid-write forces a full unconditional re-download
- opp · Audited-only symbols carry no field-level provenance (audited_fields empty)
- opp · EDINET sec_code rejects the new 4-char alphanumeric Tokyo codes (e.g. 130A.T)
- opp · Mirror bulk fetch has no max-size or total-time cap
- P1 · reconcile discards every audited period the scrape lacks — FSDS/EDGAR deep-history backfill is silently truncated to the yfinance window for scraped symbols
- P1 · Companies House _company_number parses the filing DATE, not the company number — the whole UK audited layer silently ingests zero rows on real filenames
- P2 · Incremental compute is blind to price-dump refreshes — published prices, return_6m and value/momentum ranks go stale on the persisted-base path
- P2 · GLEIF ISIN->LEI mapping is fetched once and never refreshed — the weekly self-heal is gated on file ABSENCE, so EU audited coverage freezes
- P2 · FSDS parser ignores the coreg column — a co-registrant/guarantor value can be booked as the consolidated audited figure
- P2 · Bulk archives are read whole into memory (GLEIF ~1GB decompressed, FSDS num.txt hundreds of MB) — OOM risk on the self-hosted target, defeating the mirror's streaming design
- P2 · FX applies the single latest spot rate to every fiscal period — historical *_eur values are silently wrong
- P2 · EDINET sweep applies no document-type filter and books interim balance-sheet instants as annual figures
- P2 · EDINET does not distinguish consolidated (連結) from non-consolidated (単体) contexts — parent-only figures can be booked for a group
- P2 · Incremental compute never marks a symbol dirty when its newest raw file is removed
- P2 · GLEIF CSV is decoded as plain utf-8 (not utf-8-sig) — a BOM in the source file would silently zero the entire mapping

## Introduced in current (6)

- P1 · REGRESSION from the F6 fix: audited-only periods are appended UNSORTED, so the current price, return_6m and every price-derived ratio land on an OLD period instead of the latest — the flagship deep-history universe is now silently mis-priced
- P2 · Audited-only symbols still carry no field-level provenance (audited_fields empty) — the c2 F3 gap is unresolved on the production path
- P2 · EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13, unresolved)
- P2 · EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14, unresolved)
- opp · ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 opportunity still open
- opp · Mirror bulk fetch still has no max-size or total-time cap — c2 F5 opportunity still open

## Retitled (same evidence, new title) (0)

- none
