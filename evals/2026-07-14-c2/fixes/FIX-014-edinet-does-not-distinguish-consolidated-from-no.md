# FIX-014 — EDINET does not distinguish consolidated (連結) from non-consolidated (単体) contexts — parent-only figures can be booked for a group  (P2 · DEFECT)

**Finding F14:** EDINET reports the same jppfs_cor concept twice — consolidated and parent-only — differentiated only by the context's scenario/dimension members. parse_xbrl_instance reads contexts for start/end/instant only and never inspects dimensions (edinet.py:80-93), and the fact loop keeps the first-seen concept per (period,column) (edinet.py:107-119), so document order decides the basis. For a company with subsidiaries this can silently book parent-only revenue/assets instead of the consolidated figure. EDINET is opt-in (off without a key).
**Evidence:** `src/crible/providers/edinet.py:80`, `src/crible/providers/edinet.py:107`
**Why it matters:** A JP holding company's parent-only revenue appears first in the XBRL instance and is booked as the audited consolidated revenue, understating the group.

## RED — write this test first
Write a failing test that reproduces: A JP holding company's parent-only revenue appears first in the XBRL instance and is booked as the audited consolidated revenue, understating the group.

Suggested test file: `tests/test_edinet.FIX-014.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Prefer the consolidated context (ConsolidatedMember / no non-consolidated dimension) explicitly; drop parent-only facts when a consolidated one exists.

Touch only: `src/crible/providers/edinet.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
