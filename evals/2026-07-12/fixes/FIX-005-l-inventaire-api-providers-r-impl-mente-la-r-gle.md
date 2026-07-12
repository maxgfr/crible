# FIX-005 — L'inventaire /api/providers réimplémente la règle d'activation du registre  (P2 · DEFECT)

**Finding F1:** L'endpoint /api/providers code en dur la liste des 4 classes provider et recalcule l'activation avec `True if key_var is None else bool(env)`, au lieu de consommer ProviderRegistry.activate / provider.enabled(env) qui est la source de vérité. Sa propre docstring dit « mirrors ProviderRegistry.activate ». Toute évolution de la règle d'activation (provider à deux clés, keyed avec repli keyless) fait diverger silencieusement l'écran Providers de la réalité.
**Evidence:** `src/crible/api/main.py:119-145`, `src/crible/providers/base.py:54-60`
**Why it matters:** Un provider futur exige deux variables d'env ; activate() gère les deux, l'endpoint continue de tester une seule → l'UI affiche « enabled » alors que le provider est inactif.

## RED — write this test first
Write a failing test that reproduces: Un provider futur exige deux variables d'env ; activate() gère les deux, l'endpoint continue de tester une seule → l'UI affiche « enabled » alors que le provider est inactif.

Suggested test file: `tests/test_main.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Dériver l'inventaire depuis le registre (itérer les providers enregistrés, appeler enabled(env)) plutôt que de réénumérer et recalculer côté API.

Touch only: `src/crible/api/main.py`, `src/crible/providers/base.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
