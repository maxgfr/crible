# crible — TODO

État : v1 zéro clé **publique, testée (227 pytest + 62 vitest), E2E réel validé**.
Sources bulk-first / local-first en place : universe FinanceDatabase, prix bulk
(HuggingFace US + Stooq worldwide), fondamentaux audités SEC (companyfacts +
FSDS), ESEF (EU), Companies House (UK), EDINET (JP, opt-in), FX BCE (`*_eur`).
Le dataset ouvert est republié en nightly. Rien ici n'est bloquant pour utiliser
le screener aujourd'hui — c'est de la dette de qualité et des extensions.

---

## P1 — Quick wins qualité (dette test / maintenabilité)

- [ ] **Parité de la règle « return 6 mois ».** La même règle est réimplémentée à
  trois endroits (`compute/ranks.py`, `ingest/price_import.py` ×2), synchronisée
  seulement par des commentaires. Ajouter un test golden de parité qui casse si
  les trois divergent.
- [ ] **Tester `compute_ratios` directement.** Le plus gros producteur de colonnes
  est câblé par réflexion sous un `except Exception` global (`compute/ratios.py`),
  sans test direct — un mapping cassé passe en silence. Test de caractérisation.
- [ ] **Dé-dupliquer `run_loop` / `run_refresh`** (`ingest/service.py`) : l'entrypoint
  Docker (`# pragma: no cover`) réimplémente la séquence de `run_refresh`. Extraire
  la logique commune et la tester offline.
- [ ] **Découper `build_symbol_snapshot`** (`compute/snapshot.py`, ~70 LOC /
  5 responsabilités) en étapes nommées et testables.
- [ ] **Casser le cycle d'import type-only de l'UI** (`ui/src/data/duckdb.ts` ↔
  `static-client.ts`) — inoffensif au runtime, mais à isoler dans un module de types.
- [ ] **EDINET : garder les rapports annuels rectificatifs** (訂正有報, docType 130) —
  le filtre `{120}` les exclut aujourd'hui (`providers/edinet.py`). Opt-in / OFF par défaut.
- [ ] **Vectoriser `reconcile`** (`compute/reconcile.py`) : la double boucle `.loc`
  cellule-par-cellule fera surface à grande échelle.

## P2 — Robustesse / passage à l'échelle

- [ ] **Refresh périodique de l'univers.** FinanceDatabase n'est chargé qu'au premier
  boot ; `delisted` et nouvelles cotations ne bougent jamais. Ajouter un
  `refresh_universe` hebdo dans la boucle (l'upsert idempotent existe déjà, FR-001).
- [ ] **Query builder : round-trip texte → builder** (aujourd'hui volontairement
  one-way, le DSL reste le langage unique) et un knob de slimming régional de
  l'univers dans `export-site` si le payload publié grossit un jour.
- [ ] **Sortir le sweep Europe complet** (plusieurs semaines au débit keyless —
  c'est le design, visible dans `crible status`). Rien à coder ; laisser tourner.

## P3 — Dette de test résiduelle (assumée)

- [ ] **Rendu du `CompanyDrawer`** (l'API est testée, le JSX ne l'est pas).
- [ ] **Beneish sur un cas réel publié** (type Enron 2000) en plus des vecteurs analytiques.

## P4 — Reporté volontairement (décision explicite requise)

- [ ] **E2E live en nightly CI** — manuel pour l'instant (dépense du vrai budget de scraping) ;
  le gate CI zéro-clé offline tourne à chaque push, NFR-009 est aligné là-dessus.

## Hors scope v1 (non-goals — ne pas faire sans re-spec)

Technique / chartisme · portefeuille · backtesting · exécution d'ordres · temps réel ·
multi-utilisateur / auth · apps mobiles.
