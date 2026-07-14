# Comparison — base `evals/2026-07-12-c2` → current `evals/2026-07-14-c2`

- base: engine 1.8.1 · protocol 2 · rubric 1 · target bdad2f7
- current: engine 1.9.0 · protocol 2 · rubric 1 · target 70a3203*

Score: 81 → 73 (-8) · meets-expectations true → false

## Resolved since base (4)

- P2 · ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14)
- P2 · Le preset « Top ranked » échouait sans indice sur un snapshot antérieur à FR-015
- opp · Colonnes de rang visibles par défaut dans la grille + blend documenté dans le README
- opp · Étendre le benchmark NFR-008 au coût de build des rangs

## Introduced in current (16)

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

## Retitled (same evidence, new title) (0)

- none
