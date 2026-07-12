# FIX-002 — Étendre le benchmark NFR-008 au coût de build des rangs  (P2 · OPPORTUNITY · impact med · effort S)

**Opportunity F10:** Les rangs FR-015 sont calculés côté write (attach_ranks sur ~161k lignes, groupby percentile). Le chemin de lecture est benchmarké (p95 < 1s, inchangé) mais le surcoût de build n'a pas de garde-fou chiffré — une régression du compute passerait inaperçue jusqu'au crawl suivant.
**Evidence:** `src/crible/compute/ranks.py:91-122`, `tests/test_nfr008_benchmark.py:57-65`
**Why it matters:** Les rangs FR-015 sont calculés côté write (attach_ranks sur ~161k lignes, groupby percentile). Le chemin de lecture est benchmarké (p95 < 1s, inchangé) mais le surcoût de build n'a pas de garde-fou chiffré — une régression du compute passerait inaperçue jusqu'au crawl suivant.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Ajouter un micro-benchmark attach_ranks sur le snapshot synthétique 161k (budget indicatif < 5s) dans test_nfr008 ou un test dédié.

Suggested test file: `tests/test_ranks.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Ajouter un micro-benchmark attach_ranks sur le snapshot synthétique 161k (budget indicatif < 5s) dans test_nfr008 ou un test dédié.

Touch only: `src/crible/compute/ranks.py`, `tests/test_nfr008_benchmark.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
