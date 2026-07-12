> Plan réutilisé du run de base `evals/2026-07-12`, étendu : FR-015 (ranks.py, presets, drawer) entre dans le périmètre de test.

# Test plan — crible (self-hosted fintech tool)

Target: `/Users/maxime/Downloads/crible` · kind: codebase · category: self-hosted fintech tool

## Rubric & dimensions
- correctness (0.3) — scores exacts vs définitions publiées, fidélité DSL→SQL, agrégats full-univers, chemins d'erreur.
- tests (0.2) — les tests tombent quand le code ment (assertions substantielles, pas smoke).
- security (0.2) — pas de source→sink exploitable ; entrées validées ; défauts de déploiement documentés.
- maintainability (0.2) — frontières = SRD, hotspots limités, pas de logique dupliquée.
- performance (0.1) — NFR-008 (161k×200 p95<1s) tenu ; chemin chaud UI fluide.

## Functionalities to test
| id | functionality | how tested | pass criteria |
|----|---------------|------------|---------------|
| T1 | Suite pytest FR-taggée | `uv run pytest -q` | 100% verte |
| T2 | Injection DSL→SQL | 3 payloads hostiles via compile_query | tous REJECTED, jamais compilés |
| T3 | Chemin d'erreur snapshot manquant | POST /api/screen sans snapshot | 200 + rows:[] + hint (pas de 500) |
| T4 | Inventaire providers /api/providers | comparer sortie vs providers/ + registry | doit refléter l'ensemble réel actif |
| T5 | Perf NFR-008 | benchmark existant | p95 < 1s à univers complet |
| T6 | Thème + routing UI | vitest ui | verts |

## Gate exercises (anti-hallucination)
- [x] genuine artifact → gate PASS (findings groundés file:line réels)
- [x] doctored artifact (honeypot) → gate FAIL
