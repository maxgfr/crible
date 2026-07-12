# Evaluation — .

> target `/Users/maxime/Downloads/crible` · codebase · self-hosted fintech tool · 2 findings (P0 0 · P1 0 · P2 2) · 2 opportunities
> engine 1.8.1 · protocol 2 · rubric 1 · target bdad2f7

## Verdict — ✅ MEETS expectations · 81/100

_no P0, judges agree, score 81 >= 80 (3 judges)_

_Weight sensitivity: verdict robust to ±0.05 shifts._

| dimension | score | weight | anchored to |
|-----------|-------|--------|-------------|
| Correctness | 4.2/5 | 0.3 | ISO/IEC 25010:2023 — Functional suitability — functional correctness; ISO/IEC 25010:2023 — Reliability — faultlessness |
| Test quality | 4.2/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — testability |
| Security | 4.0/5 | 0.2 | ISO/IEC 25010:2023 — Security — confidentiality, integrity, resistance; OWASP Top 10 (2021) — categories A01–A10 |
| Maintainability | 3.5/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — modularity, analysability, modifiability |
| Performance | 4.5/5 | 0.1 | ISO/IEC 25010:2023 — Performance efficiency — time behaviour, resource utilization, capacity |

## Findings

| id | sev | title | status | evidence |
|----|-----|-------|--------|----------|
| F2 | P2 | ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14) | confirmed | `src/crible/ingest/service.py:1-370` `run:analysis.json` |
| F8 | P2 | Le preset « Top ranked » échouait sans indice sur un snapshot antérieur à FR-015 | confirmed | `src/crible/presets.py:52-57` `src/crible/store.py:42-44` `src/crible/dsl/compiler.py:18-31` `tests/test_fr015_ranks.py:128-141` |

## Opportunities (2) — impact × effort

| id | impact | effort | value | title |
|----|--------|--------|-------|-------|
| F9 | med | S | 2.00 | Colonnes de rang visibles par défaut dans la grille + blend documenté dans le README |
| F10 | med | S | 2.00 | Étendre le benchmark NFR-008 au coût de build des rangs |

Quick wins (value ≥ 2): F9, F10

## Verification

✅ 10 adjudicated · 9 supported · 0 refuted · 0 unsupported

## Fix backlog (4)

- **FIX-001** (P2) Colonnes de rang visibles par défaut dans la grille + blend documenté dans le README → `ui/src/__tests__/App.test.tsx`
- **FIX-002** (P2) Étendre le benchmark NFR-008 au coût de build des rangs → `tests/test_ranks.py`
- **FIX-003** (P2) ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14) → `tests/test_service.py`
- **FIX-004** (P2) Le preset « Top ranked » échouait sans indice sur un snapshot antérieur à FR-015 → `tests/test_presets.py`
