# FIX-004 — Le preset « Top ranked » échouait sans indice sur un snapshot antérieur à FR-015  (P2 · DEFECT)

**Finding F8:** Le preset livré `composite_rank >= 80` référence une colonne qui n'existe que dans les snapshots recalculés après l'upgrade FR-015. Sur une installation existante (snapshot pré-upgrade), la whitelist dérivée de snapshot_latest ne contient pas la colonne et le DSL levait « unknown field 'composite_rank' … no similar field exists » — un preset livré ne doit jamais échouer sans expliquer le remède. Reproduit puis corrigé dans ce cycle : les colonnes build-time portent désormais un hint « recompute the snapshot (`crible compute`) after upgrading » (commit b97193e, test test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint).
**Evidence:** `src/crible/presets.py:52-57`, `src/crible/store.py:42-44`, `src/crible/dsl/compiler.py:18-31`, `tests/test_fr015_ranks.py:128-141`
**Why it matters:** Un utilisateur existant met à jour crible, clique le preset « Top ranked » : avant le fix il obtenait une erreur de champ inconnu sans remède ; après le fix l'erreur explique qu'un `crible compute` ajoute la colonne.

## RED — write this test first
Write a failing test that reproduces: Un utilisateur existant met à jour crible, clique le preset « Top ranked » : avant le fix il obtenait une erreur de champ inconnu sans remède ; après le fix l'erreur explique qu'un `crible compute` ajoute la colonne.

Suggested test file: `tests/test_presets.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Corrigé dans le cycle (hint de recompute) ; à généraliser si d'autres colonnes build-time apparaissent (le set BUILD_TIME_COLUMNS est la source unique).

Touch only: `src/crible/presets.py`, `src/crible/store.py`, `src/crible/dsl/compiler.py`, `tests/test_fr015_ranks.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
