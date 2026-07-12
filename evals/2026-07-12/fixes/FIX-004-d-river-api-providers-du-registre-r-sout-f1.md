# FIX-004 — Dériver /api/providers du registre (résout F1)  (P2 · OPPORTUNITY · impact med · effort S)

**Opportunity F6:** Transformer la duplication F1 en amélioration : l'endpoint consomme le registre au lieu de réénumérer et recalculer, supprimant le risque de dérive UI↔réalité.
**Evidence:** `src/crible/api/main.py:119-145`, `src/crible/providers/base.py:54`
**Why it matters:** Transformer la duplication F1 en amélioration : l'endpoint consomme le registre au lieu de réénumérer et recalculer, supprimant le risque de dérive UI↔réalité.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Refactor de l'endpoint pour itérer les providers enregistrés et appeler enabled(env).

Suggested test file: `tests/test_main.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Refactor de l'endpoint pour itérer les providers enregistrés et appeler enabled(env).

Touch only: `src/crible/api/main.py`, `src/crible/providers/base.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
