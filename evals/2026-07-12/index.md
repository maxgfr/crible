# Evaluation — .

> target `/Users/maxime/Downloads/crible` · codebase · self-hosted fintech tool · 3 findings (P0 0 · P1 0 · P2 3) · 4 opportunities
> engine 1.8.1 · protocol 2 · rubric 1 · target 286c7c4*

## Verdict — ❌ BELOW expectations · 74/100

_weighted score 74 is below the 80 bar (3 judges)_

_Weight sensitivity: verdict robust to ±0.05 shifts._

| dimension | score | weight | anchored to |
|-----------|-------|--------|-------------|
| Correctness | 4.0/5 | 0.3 | ISO/IEC 25010:2023 — Functional suitability — functional correctness; ISO/IEC 25010:2023 — Reliability — faultlessness |
| Test quality | 3.0/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — testability |
| Security | 4.0/5 | 0.2 | ISO/IEC 25010:2023 — Security — confidentiality, integrity, resistance; OWASP Top 10 (2021) — categories A01–A10 |
| Maintainability | 3.3/5 | 0.2 | ISO/IEC 25010:2023 — Maintainability — modularity, analysability, modifiability |
| Performance | 4.3/5 | 0.1 | ISO/IEC 25010:2023 — Performance efficiency — time behaviour, resource utilization, capacity |

## Findings

| id | sev | title | status | evidence |
|----|-----|-------|--------|----------|
| F1 | P2 | L'inventaire /api/providers réimplémente la règle d'activation du registre | confirmed | `src/crible/api/main.py:119-145` `src/crible/providers/base.py:54-60` |
| F2 | P2 | ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14) | confirmed | `src/crible/ingest/service.py:1` `run:analysis.json` |
| F3 | P2 | compose expose l'API sans auth ni avertissement « réseau privé » | confirmed | `docker-compose.yml:28` |

## Opportunities (4) — impact × effort

| id | impact | effort | value | title |
|----|--------|--------|-------|-------|
| F4 | high | S | 3.00 | README go-to-market : pitch, comparatif honnête, listing awesome-selfhosted |
| F5 | med | S | 2.00 | Guide d'install self-host NAS/Synology |
| F6 | med | S | 2.00 | Dériver /api/providers du registre (résout F1) |
| F7 | high | M | 1.50 | Rang composite qualité/valeur/momentum (façon StockRanks) — GATÉ marché |

Quick wins (value ≥ 2): F4, F5, F6

## Verification

✅ 13 adjudicated · 13 supported · 0 refuted · 0 unsupported

## Fix backlog (7)

- **FIX-001** (P1) README go-to-market : pitch, comparatif honnête, listing awesome-selfhosted → `tests/readme-go-to-market-pitch-comparatif-honn-te-lis.test.ts`
- **FIX-002** (P1) Rang composite qualité/valeur/momentum (façon StockRanks) — GATÉ marché → `tests/test_scores.py`
- **FIX-003** (P2) Guide d'install self-host NAS/Synology → `tests/guide-d-install-self-host-nas-synology.test.ts`
- **FIX-004** (P2) Dériver /api/providers du registre (résout F1) → `tests/test_main.py`
- **FIX-005** (P2) L'inventaire /api/providers réimplémente la règle d'activation du registre → `tests/test_main.py`
- **FIX-006** (P2) ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14) → `tests/test_service.py`
- **FIX-007** (P2) compose expose l'API sans auth ni avertissement « réseau privé » → `tests/compose-expose-l-api-sans-auth-ni-avertissement-.test.ts`
