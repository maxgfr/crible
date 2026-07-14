# Evaluation — .

> target `/Users/maxime/Downloads/crible` · codebase · self-hosted fintech tool · 11 findings (P0 0 · P1 2 · P2 9) · 5 opportunities
> engine 1.9.0 · protocol 2 · rubric 1 · target 70a3203*

## Verdict — ❌ BELOW expectations · 73/100

_a judge ruled it does not meet expectations (3 judges)_

_Weight sensitivity: verdict robust to ±0.05 shifts._

| dimension | score | weight | anchored to |
|-----------|-------|--------|-------------|
| Correctness | 3.6/5 | 0.3 | ISO/IEC 25010:2023 — Functional suitability — functional correctness; ISO/IEC 25010:2023 — Reliability — faultlessness |
| Test quality | 3.6/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — testability |
| Security | 3.9/5 | 0.2 | ISO/IEC 25010:2023 — Security — confidentiality, integrity, resistance; OWASP Top 10 (2021) — categories A01–A10 |
| Maintainability | 3.5/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — modularity, analysability, modifiability |
| Performance | 3.9/5 | 0.1 | ISO/IEC 25010:2023 — Performance efficiency — time behaviour, resource utilization, capacity |

## Findings

| id | sev | title | status | evidence |
|----|-----|-------|--------|----------|
| F6 | P1 | reconcile discards every audited period the scrape lacks — FSDS/EDGAR deep-history backfill is silently truncated to the yfinance window for scraped symbols | confirmed | `src/crible/compute/reconcile.py:56` `src/crible/compute/reconcile.py:65` `src/crible/providers/audited.py:44` `src/crible/ingest/enrichment.py:307` |
| F7 | P1 | Companies House _company_number parses the filing DATE, not the company number — the whole UK audited layer silently ingests zero rows on real filenames | confirmed | `src/crible/providers/companies_house.py:197` `src/crible/providers/companies_house.py:198` `src/crible/providers/companies_house.py:211` |
| F8 | P2 | Incremental compute is blind to price-dump refreshes — published prices, return_6m and value/momentum ranks go stale on the persisted-base path | confirmed | `src/crible/compute/snapshot.py:262` `src/crible/compute/snapshot.py:236` `src/crible/compute/snapshot.py:194` `src/crible/ingest/price_import.py:37` |
| F9 | P2 | GLEIF ISIN->LEI mapping is fetched once and never refreshed — the weekly self-heal is gated on file ABSENCE, so EU audited coverage freezes | confirmed | `src/crible/ingest/service.py:322` `src/crible/ingest/service.py:477` `src/crible/providers/gleif.py:26` |
| F10 | P2 | FSDS parser ignores the coreg column — a co-registrant/guarantor value can be booked as the consolidated audited figure | confirmed | `src/crible/providers/edgar_fsds.py:67` `src/crible/providers/edgar_fsds.py:80` `src/crible/providers/edgar_fsds.py:97` |
| F11 | P2 | Bulk archives are read whole into memory (GLEIF ~1GB decompressed, FSDS num.txt hundreds of MB) — OOM risk on the self-hosted target, defeating the mirror's streaming design | confirmed | `src/crible/providers/gleif.py:43` `src/crible/providers/gleif.py:47` `src/crible/providers/edgar_fsds.py:131` |
| F12 | P2 | FX applies the single latest spot rate to every fiscal period — historical *_eur values are silently wrong | confirmed | `src/crible/providers/fx.py:26` `src/crible/providers/fx.py:94` |
| F13 | P2 | EDINET sweep applies no document-type filter and books interim balance-sheet instants as annual figures | confirmed | `src/crible/ingest/enrichment.py:480` `src/crible/providers/edinet.py:60` |
| F14 | P2 | EDINET does not distinguish consolidated (連結) from non-consolidated (単体) contexts — parent-only figures can be booked for a group | confirmed | `src/crible/providers/edinet.py:80` `src/crible/providers/edinet.py:107` |
| F15 | P2 | Incremental compute never marks a symbol dirty when its newest raw file is removed | confirmed | `src/crible/compute/snapshot.py:239` `src/crible/compute/snapshot.py:262` |
| F16 | P2 | GLEIF CSV is decoded as plain utf-8 (not utf-8-sig) — a BOM in the source file would silently zero the entire mapping | confirmed | `src/crible/providers/gleif.py:49` `src/crible/providers/gleif.py:52` |

## Opportunities (5) — impact × effort

| id | impact | effort | value | title |
|----|--------|--------|-------|-------|
| F1 | med | M | 1.00 | Split ingest/enrichment.py (617 LOC, nesting 14) into per-provider cycle modules |
| F2 | low | S | 1.00 | Mirror sidecar meta write is non-atomic — a crash mid-write forces a full unconditional re-download |
| F3 | low | S | 1.00 | Audited-only symbols carry no field-level provenance (audited_fields empty) |
| F4 | low | S | 1.00 | EDINET sec_code rejects the new 4-char alphanumeric Tokyo codes (e.g. 130A.T) |
| F5 | low | M | 0.50 | Mirror bulk fetch has no max-size or total-time cap |

Quick wins (value ≥ 2): —

## Verification

✅ 39 adjudicated · 36 supported · 0 refuted · 0 unsupported

## Fix backlog (16)

- **FIX-001** (P1) reconcile discards every audited period the scrape lacks — FSDS/EDGAR deep-history backfill is silently truncated to the yfinance window for scraped symbols → `tests/test_reconcile.py`
- **FIX-002** (P1) Companies House _company_number parses the filing DATE, not the company number — the whole UK audited layer silently ingests zero rows on real filenames → `tests/test_companies_house.FIX-002.py`
- **FIX-003** (P2) Split ingest/enrichment.py (617 LOC, nesting 14) into per-provider cycle modules → `tests/test_enrichment.py`
- **FIX-004** (P2) Mirror sidecar meta write is non-atomic — a crash mid-write forces a full unconditional re-download → `tests/test_mirror.FIX-004.py`
- **FIX-005** (P2) Audited-only symbols carry no field-level provenance (audited_fields empty) → `tests/test_snapshot.py`
- **FIX-006** (P2) EDINET sec_code rejects the new 4-char alphanumeric Tokyo codes (e.g. 130A.T) → `tests/test_edinet.FIX-006.py`
- **FIX-007** (P2) Mirror bulk fetch has no max-size or total-time cap → `tests/test_mirror.FIX-007.py`
- **FIX-008** (P2) Incremental compute is blind to price-dump refreshes — published prices, return_6m and value/momentum ranks go stale on the persisted-base path → `tests/test_snapshot.py`
- **FIX-009** (P2) GLEIF ISIN->LEI mapping is fetched once and never refreshed — the weekly self-heal is gated on file ABSENCE, so EU audited coverage freezes → `tests/test_service.FIX-009.py`
- **FIX-010** (P2) FSDS parser ignores the coreg column — a co-registrant/guarantor value can be booked as the consolidated audited figure → `tests/test_edgar_fsds.py`
- **FIX-011** (P2) Bulk archives are read whole into memory (GLEIF ~1GB decompressed, FSDS num.txt hundreds of MB) — OOM risk on the self-hosted target, defeating the mirror's streaming design → `tests/test_gleif.FIX-011.py`
- **FIX-012** (P2) FX applies the single latest spot rate to every fiscal period — historical *_eur values are silently wrong → `tests/test_fx.FIX-012.py`
- **FIX-013** (P2) EDINET sweep applies no document-type filter and books interim balance-sheet instants as annual figures → `tests/test_enrichment.py`
- **FIX-014** (P2) EDINET does not distinguish consolidated (連結) from non-consolidated (単体) contexts — parent-only figures can be booked for a group → `tests/test_edinet.FIX-014.py`
- **FIX-015** (P2) Incremental compute never marks a symbol dirty when its newest raw file is removed → `tests/test_snapshot.py`
- **FIX-016** (P2) GLEIF CSV is decoded as plain utf-8 (not utf-8-sig) — a BOM in the source file would silently zero the entire mapping → `tests/test_gleif.FIX-016.py`
