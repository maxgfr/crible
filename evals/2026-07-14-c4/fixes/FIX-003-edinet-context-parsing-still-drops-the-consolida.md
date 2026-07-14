# FIX-003 — EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14 / c3 F4, unresolved)  (P2 · DEFECT)

**Finding F2:** parse_xbrl_instance records only start/end/instant from each context (edinet.py:88-93) and never the explicit member that marks 連結 (Consolidated) vs 単体 (NonConsolidated). When both a consolidated and a non-consolidated context exist for the same concept and period, the winner is decided purely by concept rank / first-writer (edinet.py:114-119) with no preference for the consolidated member, so a parent-only figure can be booked as the group's audited value. Opt-in (Subscription-Key) so limited blast radius.
**Evidence:** `src/crible/providers/edinet.py:88`, `src/crible/providers/edinet.py:116`
**Why it matters:** A group whose non-consolidated (単体) Revenue context is parsed before the consolidated (連結) one books parent-only revenue as the audited group figure.

## RED — write this test first
Write a failing test that reproduces: A group whose non-consolidated (単体) Revenue context is parsed before the consolidated (連結) one books parent-only revenue as the audited group figure.

Suggested test file: `tests/test_edinet.FIX-003.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Capture the consolidated/non-consolidated member per context and prefer the consolidated one (or drop non-consolidated when a consolidated exists); add a fixture with both contexts asserting the consolidated value wins.

Touch only: `src/crible/providers/edinet.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
