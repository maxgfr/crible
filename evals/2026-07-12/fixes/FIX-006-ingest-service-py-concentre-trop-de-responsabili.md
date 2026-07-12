# FIX-006 — ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14)  (P2 · DEFECT)

**Finding F2:** Le service d'ingestion est le plus gros fichier source (370 LOC) avec la profondeur d'imbrication la plus élevée du repo (14), churn 5 — signal d'un module qui orchestre bootstrap, crawl budgété, prix et reconciliation dans une seule unité. Analysable mais coûteux à faire évoluer sans régression.
**Evidence:** `src/crible/ingest/service.py:1`, `run:analysis.json`
**Why it matters:** Ajouter un provider de prix impose de modifier une fonction profondément imbriquée ; un cas d'erreur non couvert passe entre les branches.

## RED — write this test first
Write a failing test that reproduces: Ajouter un provider de prix impose de modifier une fonction profondément imbriquée ; un cas d'erreur non couvert passe entre les branches.

Suggested test file: `tests/test_service.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Extraire les étapes (bootstrap / crawl / prix / reconcile) en collaborateurs testables ; le SRD décrit déjà ces frontières.

Touch only: `src/crible/ingest/service.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
