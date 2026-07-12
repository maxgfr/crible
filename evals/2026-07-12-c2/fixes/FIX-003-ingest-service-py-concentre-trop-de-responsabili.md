# FIX-003 — ingest/service.py concentre trop de responsabilités (hotspot 370 LOC, nesting 14)  (P2 · DEFECT)

**Finding F2:** Toujours ouvert (porté du run de base, décision « coût > valeur immédiate » documentée dans PRIORITIES) : le service d'ingestion orchestre queue, budget, backoff, crawler, prix et heartbeat dans un seul module de 370 LOC avec une profondeur d'imbrication de 14 — le pire hotspot du dépôt à l'analyse déterministe.
**Evidence:** `src/crible/ingest/service.py:1-370`, `run:analysis.json`
**Why it matters:** Une évolution du budget de crawl (par ex. budget par provider) force à modifier un module qui mélange six responsabilités ; le risque de régression sur le backoff ou le heartbeat est élevé faute de frontières.

## RED — write this test first
Write a failing test that reproduces: Une évolution du budget de crawl (par ex. budget par provider) force à modifier un module qui mélange six responsabilités ; le risque de régression sur le backoff ou le heartbeat est élevé faute de frontières.

Suggested test file: `tests/test_service.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Extraire les collaborateurs (BudgetClock, CrawlLoop, Heartbeat) — déjà planifié en File 1 différée ; à faire quand une évolution touchera le module.

Touch only: `src/crible/ingest/service.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
