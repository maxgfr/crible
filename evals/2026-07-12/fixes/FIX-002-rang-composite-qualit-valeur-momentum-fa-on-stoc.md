# FIX-002 — Rang composite qualité/valeur/momentum (façon StockRanks) — GATÉ marché  (P1 · OPPORTUNITY · impact high · effort M)

**Opportunity F7:** Le différenciateur n°1 du leader payant Stockopedia est le StockRank composite (qualité/valeur/momentum), cité par les reviews comme la raison d'abonnement. crible a déjà les scores en base (Piotroski, Altman, ratios) pour le calculer, sans clé.
**Evidence:** `src/crible/compute/scores.py:1`, `docs/market/2026-07-12/REPORT.md:1`
**Why it matters:** Le différenciateur n°1 du leader payant Stockopedia est le StockRank composite (qualité/valeur/momentum), cité par les reviews comme la raison d'abonnement. crible a déjà les scores en base (Piotroski, Altman, ratios) pour le calculer, sans clé.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Spécifier via construct (FR + acceptance) un rang composite classant l'univers ; NE PAS développer avant la spec. Évidence marché forte → passe le gate, dev cycle 2.

Suggested test file: `tests/test_scores.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Spécifier via construct (FR + acceptance) un rang composite classant l'univers ; NE PAS développer avant la spec. Évidence marché forte → passe le gate, dev cycle 2.

Touch only: `src/crible/compute/scores.py`, `docs/market/2026-07-12/REPORT.md`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
