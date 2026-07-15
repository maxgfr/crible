# Evaluation — .

> target `/Users/maxime/Downloads/crible` · codebase · self-hosted fintech tool · 0 findings (P0 0 · P1 0 · P2 0) · 7 opportunities
> engine 1.9.0 · protocol 2 · rubric 1 · target 0f9921b

## Verdict — ✅ MEETS expectations · 83/100

_no P0, judges agree, score 83 >= 80 (3 judges)_

_Weight sensitivity: verdict robust to ±0.05 shifts._

| dimension | score | weight | anchored to |
|-----------|-------|--------|-------------|
| Correctness | 4.3/5 | 0.3 | ISO/IEC 25010:2023 — Functional suitability — functional correctness; ISO/IEC 25010:2023 — Reliability — faultlessness |
| Test quality | 4.2/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — testability |
| Security | 4.0/5 | 0.2 | ISO/IEC 25010:2023 — Security — confidentiality, integrity, resistance; OWASP Top 10 (2021) — categories A01–A10 |
| Maintainability | 3.9/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — modularity, analysability, modifiability |
| Performance | 4.2/5 | 0.1 | ISO/IEC 25010:2023 — Performance efficiency — time behaviour, resource utilization, capacity |

## Findings

| id | sev | title | status | evidence |
|----|-----|-------|--------|----------|
| — | — | none | — | — |

## Opportunities (7) — impact × effort

| id | impact | effort | value | title |
|----|--------|--------|-------|-------|
| F1 | high | S | 3.00 | The trailing-6-month-return rule is implemented three times (two languages), kept in sync only by comments |
| F2 | med | S | 2.00 | compute_ratios reflection-wires every financetoolkit get_* and swallows every exception, with no direct test |
| F3 | med | M | 1.00 | run_loop (106 LOC, # pragma: no cover) hand-rolls six time-gated blocks and duplicates run_refresh's enrichment sequence |
| F4 | med | M | 1.00 | build_symbol_snapshot is a 70-line, five-concern function (the depth-8 hotspot) — invariants only reachable through the whole body |
| F5 | low | S | 1.00 | UI module cycle static-client.ts <-> duckdb.ts is type-only (harmless at runtime) but a cheap-to-clear coupling smell |
| F6 | low | S | 1.00 | EDINET annual-report filter narrows to docType 120 and also excludes amended annual reports (訂正有報, docType 130) |
| F7 | low | M | 0.50 | reconcile writes scalars into a DataFrame inside a double loop — per-cell .loc on deep-history symbols |

Quick wins (value ≥ 2): F1, F2

## Verification

✅ 14 adjudicated · 14 supported · 0 refuted · 0 unsupported

## Fix backlog (7)

- **FIX-001** (P1) The trailing-6-month-return rule is implemented three times (two languages), kept in sync only by comments → `tests/test_ranks.py`
- **FIX-002** (P2) compute_ratios reflection-wires every financetoolkit get_* and swallows every exception, with no direct test → `tests/test_ratios.py`
- **FIX-003** (P2) run_loop (106 LOC, # pragma: no cover) hand-rolls six time-gated blocks and duplicates run_refresh's enrichment sequence → `tests/test_service.FIX-003.py`
- **FIX-004** (P2) build_symbol_snapshot is a 70-line, five-concern function (the depth-8 hotspot) — invariants only reachable through the whole body → `tests/test_snapshot.py`
- **FIX-005** (P2) UI module cycle static-client.ts <-> duckdb.ts is type-only (harmless at runtime) but a cheap-to-clear coupling smell → `ui/src/data/__tests__/duckdb.test.ts`
- **FIX-006** (P2) EDINET annual-report filter narrows to docType 120 and also excludes amended annual reports (訂正有報, docType 130) → `tests/test_edinet.FIX-006.py`
- **FIX-007** (P2) reconcile writes scalars into a DataFrame inside a double loop — per-cell .loc on deep-history symbols → `tests/test_reconcile.py`
