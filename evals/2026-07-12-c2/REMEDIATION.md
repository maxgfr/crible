# Remediation plan — .

Target: `/Users/maxime/Downloads/crible` · 4 fix task(s), most impactful first.
Each task has a matching TDD card under `fixes/` (RED failing test → GREEN change → VERIFY).

## P2 — Minor: polish, consistency, or documentation drift; no scored dimension materially degraded (4)

- **FIX-001** Colonnes de rang visibles par défaut dans la grille + blend documenté dans le README — FR-015 est livré (composite_rank + piliers, preset Top ranked, décomposition dans le drawer) mais la grille par défaut n'affiche pas composite_rank et le README ne documente pas la formule du blend — or la transparence du rang est l'argument face aux StockRanks propriétaires ([S21]).
  - fix: Ajouter composite_rank aux colonnes par défaut du ColumnPicker et une section « How the rank is built » dans le README (formule, peer group, sémantique NULL jamais imputée).
  - targets: ui/src/App.tsx, docs/market/2026-07-12/REPORT.md
- **FIX-002** Étendre le benchmark NFR-008 au coût de build des rangs — Les rangs FR-015 sont calculés côté write (attach_ranks sur ~161k lignes, groupby percentile). Le chemin de lecture est benchmarké (p95 < 1s, inchangé) mais le surcoût de build n'a pas de garde-fou chiffré — une régression du compute passerait inaperçue jusqu'au crawl suivant.
  - fix: Ajouter un micro-benchmark attach_ranks sur le snapshot synthétique 161k (budget indicatif < 5s) dans test_nfr008 ou un test dédié.
  - targets: src/crible/compute/ranks.py, tests/test_nfr008_benchmark.py
- **FIX-003** ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14) — Une évolution du budget de crawl (par ex. budget par provider) force à modifier un module qui mélange six responsabilités ; le risque de régression sur le backoff ou le heartbeat est élevé faute de frontières.
  - fix: Extraire les collaborateurs (BudgetClock, CrawlLoop, Heartbeat) — déjà planifié en File 1 différée ; à faire quand une évolution touchera le module.
  - targets: src/crible/ingest/service.py
- **FIX-004** Le preset « Top ranked » échouait sans indice sur un snapshot antérieur à FR-015 — Un utilisateur existant met à jour crible, clique le preset « Top ranked » : avant le fix il obtenait une erreur de champ inconnu sans remède ; après le fix l'erreur explique qu'un `crible compute` ajoute la colonne.
  - fix: Corrigé dans le cycle (hint de recompute) ; à généraliser si d'autres colonnes build-time apparaissent (le set BUILD_TIME_COLUMNS est la source unique).
  - targets: src/crible/presets.py, src/crible/store.py, src/crible/dsl/compiler.py, tests/test_fr015_ranks.py
