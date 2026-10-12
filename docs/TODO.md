# crible — TODO

État : v1 zéro clé **publique, testée (549 pytest + 213 vitest), E2E réel validé**.
Sources bulk-first / local-first en place : universe FinanceDatabase, prix bulk
(HuggingFace US + Stooq worldwide), fondamentaux audités SEC (companyfacts +
FSDS), ESEF (EU), Companies House (UK), CVM (BR), TWSE (TW), FX BCE (`*_eur`).
Le dataset ouvert est republié en nightly. Rien ici n'est bloquant pour utiliser
le screener aujourd'hui — c'est de la dette de qualité et des extensions.

---

## P1 — Quick wins qualité (dette test / maintenabilité)

- [x] **Parité de la règle « return 6 mois ».** ~~Réimplémentée à trois endroits~~ —
  résolu : la règle vit dans `compute/momentum.py` (unique implémentation),
  `ranks.price_return` et les distillats délèguent, et un golden de parité
  (`tests/test_momentum.py`) casse si un chemin diverge.
- [x] **Tester `compute_ratios` directement.** ~~Câblé par réflexion sans test~~ —
  résolu : l'ensemble exact des colonnes est figé (`tests/test_fr003_compute.py`),
  chaque champ de preset est vérifié sur un snapshot réellement calculé
  (`tests/test_fr009_presets.py`), les fonctions sautées ou qui lèvent sont
  loguées, et les faux ratios (ROIC & co) sont en denylist.
- [x] **Dé-dupliquer `run_loop` / `run_refresh`** — résolu : étapes partagées
  (`sync_universe`, `_stage`, `_self_heal_reference_data`, `_publish_heartbeat`),
  `run_loop` est un ordonnanceur sur une table de tâches, testé hors ligne
  (`tests/test_loop.py`), sans `pragma: no cover`.
- [x] **Découper `build_symbol_snapshot`** — résolu : `_merge_audited`,
  `_resolve_price`, `_period_blocks`, `_overlay_latest`, `_provenance`.
- [x] **Casser le cycle d'import type-only de l'UI** — résolu : `QueryRunner` vit
  dans `ui/src/data/types.ts`.
- [x] **Vectoriser `reconcile`** — résolu : version alignée, sortie identique à la
  boucle d'origine (test de propriété, `tests/test_reconcile.py`).

## P2 — Robustesse / passage à l'échelle

- [x] **Refresh périodique de l'univers.** — résolu : tâche hebdo de la boucle via
  `sync_universe`, qui réexporte aussi `universe.parquet` pour tous les lecteurs.
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
