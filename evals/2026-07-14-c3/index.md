# Evaluation — .

> target `/Users/maxime/Downloads/crible` · codebase · self-hosted fintech tool · 4 findings (P0 0 · P1 1 · P2 3) · 2 opportunities
> engine 1.9.0 · protocol 2 · rubric 1 · target ee2eb09

## Verdict — ❌ BELOW expectations · 77/100

_a judge ruled it does not meet expectations (3 judges)_

_Weight sensitivity: verdict robust to ±0.05 shifts._

| dimension | score | weight | anchored to |
|-----------|-------|--------|-------------|
| Correctness | 3.8/5 | 0.3 | ISO/IEC 25010:2023 — Functional suitability — functional correctness; ISO/IEC 25010:2023 — Reliability — faultlessness |
| Test quality | 3.9/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — testability |
| Security | 3.9/5 | 0.2 | ISO/IEC 25010:2023 — Security — confidentiality, integrity, resistance; OWASP Top 10 (2021) — categories A01–A10 |
| Maintainability | 3.6/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — modularity, analysability, modifiability |
| Performance | 4.2/5 | 0.1 | ISO/IEC 25010:2023 — Performance efficiency — time behaviour, resource utilization, capacity |

## Findings

| id | sev | title | status | evidence |
|----|-----|-------|--------|----------|
| F1 | P1 | REGRESSION from the F6 fix: audited-only periods are appended UNSORTED, so the current price, return_6m and every price-derived ratio land on an OLD period instead of the latest — the flagship deep-history universe is now silently mis-priced | confirmed | `src/crible/compute/reconcile.py:63` `src/crible/compute/snapshot.py:79` `src/crible/compute/snapshot.py:96` `src/crible/compute/canonical.py:104` `run:runs/regression-price-period.txt#L1` |
| F2 | P2 | Audited-only symbols still carry no field-level provenance (audited_fields empty) — the c2 F3 gap is unresolved on the production path | confirmed | `src/crible/compute/snapshot.py:199` `src/crible/compute/snapshot.py:54` `src/crible/compute/snapshot.py:101` |
| F3 | P2 | EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13, unresolved) | confirmed | `src/crible/providers/edinet.py:198` `src/crible/providers/edinet.py:61` `src/crible/providers/edinet.py:107` |
| F4 | P2 | EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14, unresolved) | confirmed | `src/crible/providers/edinet.py:88` `src/crible/providers/edinet.py:116` |

## Opportunities (2) — impact × effort

| id | impact | effort | value | title |
|----|--------|--------|-------|-------|
| F5 | med | M | 1.00 | ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 opportunity still open |
| F6 | low | S | 1.00 | Mirror bulk fetch still has no max-size or total-time cap — c2 F5 opportunity still open |

Quick wins (value ≥ 2): —

## Verification

✅ 17 adjudicated · 17 supported · 0 refuted · 0 unsupported

## Fix backlog (6)

- **FIX-001** (P1) REGRESSION from the F6 fix: audited-only periods are appended UNSORTED, so the current price, return_6m and every price-derived ratio land on an OLD period instead of the latest — the flagship deep-history universe is now silently mis-priced → `tests/test_reconcile.py`
- **FIX-002** (P2) ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 opportunity still open → `tests/test_enrichment.py`
- **FIX-003** (P2) Mirror bulk fetch still has no max-size or total-time cap — c2 F5 opportunity still open → `tests/test_mirror.FIX-003.py`
- **FIX-004** (P2) Audited-only symbols still carry no field-level provenance (audited_fields empty) — the c2 F3 gap is unresolved on the production path → `tests/test_snapshot.py`
- **FIX-005** (P2) EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13, unresolved) → `tests/test_edinet.FIX-005.py`
- **FIX-006** (P2) EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14, unresolved) → `tests/test_edinet.FIX-006.py`
