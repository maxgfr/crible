# FIX-001 — Colonnes de rang visibles par défaut dans la grille + blend documenté dans le README  (P2 · OPPORTUNITY · impact med · effort S)

**Opportunity F9:** FR-015 est livré (composite_rank + piliers, preset Top ranked, décomposition dans le drawer) mais la grille par défaut n'affiche pas composite_rank et le README ne documente pas la formule du blend — or la transparence du rang est l'argument face aux StockRanks propriétaires ([S21]).
**Evidence:** `ui/src/App.tsx:29-33`, `docs/market/2026-07-12/REPORT.md:5`
**Why it matters:** FR-015 est livré (composite_rank + piliers, preset Top ranked, décomposition dans le drawer) mais la grille par défaut n'affiche pas composite_rank et le README ne documente pas la formule du blend — or la transparence du rang est l'argument face aux StockRanks propriétaires ([S21]).

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Ajouter composite_rank aux colonnes par défaut du ColumnPicker et une section « How the rank is built » dans le README (formule, peer group, sémantique NULL jamais imputée).

Suggested test file: `ui/src/__tests__/App.test.tsx`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Ajouter composite_rank aux colonnes par défaut du ColumnPicker et une section « How the rank is built » dans le README (formule, peer group, sémantique NULL jamais imputée).

Touch only: `ui/src/App.tsx`, `docs/market/2026-07-12/REPORT.md`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
