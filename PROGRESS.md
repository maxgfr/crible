# crible — état d'avancement (repris automatiquement par le cron de session)

_Mise à jour : 2026-07-07 ~01:30. Mode autonome (Maxime dort) — décisions consignées ici._

## Où on en est

**SRD (srd/) : TERMINÉ et validé.**
- `construct check` : structurel ✓, grounding 14/14 FR · 11/13 NFR · 4/4 ADR (NFR-011/012 volontairement non cités : engagements de design purs).
- `construct check --semantic` : **PASS** — 40/40 paires adjugées (28 supported, 12 partial, 0 refuted/unsupported), verdicts dans `srd/verdicts.json` + `srd/VERIFY.json`.
- 3 rounds de revue adversariale (agents frais). Round 1 : 11 blockers (arithmétique de crawl impossible, citation-washing massif) → corrigés. Round 2 : 8/11 fermés, 3 rouverts (miroirs) + 2 nouveaux → corrigés au round 3.
- **Découverte importante round 3** : les endpoints CSV de Stooq sont derrière un mur anti-bot JS (proof-of-work SHA-256, vérifié au curl 2026-07-07). Le « chemin prix bulk hors budget » n'existe pas → FR-011 redessiné : les prix partagent le budget Yahoo (tiering priorité, provenance price_asof), Stooq = plugin optionnel désactivé, non porteur.
- Arithmétique honnête (ADR-0004) : 330 req/h ≈ 7 900 req/j ; ~2 000/j prix tier prioritaire + ~5 900/j fondamentaux ≈ 840 sweeps/j → Europe en 5-7 semaines (< trimestre ✓), monde ≈ 2 sweeps/an best-effort ; le remède documenté = switch EODHD (FR-014).

## Build (BUILD-PLAN.json — statuts à jour dedans)

| Tâche | FR | État |
|---|---|---|
| T-000 skeleton (uv/py3.12, pytest) | — | **done** |
| T-001 universe (FinanceDatabase→DuckDB, régions, ISO) | FR-001 | **done** |
| T-002 crawler (budget/req, backoff, queue, raw parquet, gating) | FR-002 | **done** |
| T-003 compute (canonical, 46 ratios ftk auto-câblés, Piotroski¹, Altman, Beneish maison, snapshot 185 col.) | FR-003 | **done** |
| T-004 DSL (parser, whitelist+params, injection property-tested) | FR-004 | **done** |
| T-005 CLI (screen/export/presets/status/ingest/compute) + service loop | FR-005 | **done** |
| T-006 API FastAPI | FR-006 | **en cours** |
| T-007 SPA React/Vite | FR-007 | todo |
| T-008 Docker compose | FR-008 | todo (service.py prêt) |
| T-009 presets | FR-009 | code fait (presets.py), tests FR-009 à taguer |
| T-010 ESEF+GLEIF | FR-010 | todo |
| T-011 prix tiering | FR-011 | todo |
| T-012 company detail | FR-012 | todo |
| T-013 plugins phase 2 | FR-013 | gating fait (base.py), plugins todo |
| T-014 PRDs EODHD/FMP | FR-014 | todo |

¹ Piotroski : critère ΔROA implémenté maison selon la définition publiée (ROA_t > ROA_{t-1}) — le critère ftk compare l'accélération (bug documenté ftk#91 = [E39]).

**56 tests verts** (`uv run pytest`). `construct verify` ✓ après chaque tâche.

## Décisions prises en autonomie (à revalider par Maxime au réveil)

1. **Stooq rétrogradé** (mur anti-bot vérifié) — le SRD et FR-011 assument désormais des prix sous budget Yahoo avec provenance datée.
2. `country` = code ISO-2 (le DSL filtre `country IN ('FR','DE')`), `country_name` = nom FinanceDatabase.
3. Lecteurs (API/CLI screen) ne touchent JAMAIS crible.duckdb (writer = ingest) : univers exporté en `universe.parquet`, snapshot auto-suffisant (métadonnées univers embarquées).
4. Beneish testé contre vecteurs dérivés à la main de la formule publiée 1999 (pas les données du papier, introuvables en accès libre vérifiable).
5. NFR-011/012 sans citations (design commitments, pas des claims factuels).

## Reste à faire (ordre)

1. T-006 API → T-007 SPA (design tokens srd/design/) → T-008 compose + E2E zéro clé (docker compose up sans clés → sample → screen non vide → CSV) → T-009 tags → T-010/T-011/T-012 → T-013 plugins → T-014 PRDs (docs/prds/eodhd.md détaillé avec payloads demo via clé free si dispo en env, sinon schéma documenté ; fmp-ultimate.md sommaire).
2. `construct verify --out srd --run-tests --strict` par milestone (M1 après T-008).
3. Revue milestone M1 (agent frais : un AC sans test réel ?).
4. Fin : PROGRESS.md état FINAL + supprimer le cron (CronList/CronDelete). Repo reste PRIVÉ local.
