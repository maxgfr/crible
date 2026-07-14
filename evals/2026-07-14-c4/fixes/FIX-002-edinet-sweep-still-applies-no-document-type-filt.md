# FIX-002 — EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13 / c3 F3, unresolved)  (P2 · DEFECT)

**Finding F1:** list_documents requests all filings for a day with type=2 and no docTypeCode/ordinanceCode filter (edinet.py:197-200), and _period takes a balance instant from any context whose period resolves (edinet.py:59-63) with no guard that the instant belongs to an annual securities report (有価証券報告書). Income/cashflow are protected by the full-year duration check (edinet.py:64-69), but balance instants are NOT, so a quarterly/semi-annual report's period-end instant can be booked as the annual balance. EDINET is opt-in (requires a Subscription-Key, edinet.py:200) so blast radius is limited, but the values are silently wrong when it is enabled.
**Evidence:** `src/crible/providers/edinet.py:197`, `src/crible/providers/edinet.py:60`, `src/crible/providers/edinet.py:90`
**Why it matters:** A JP company's Q2 report lands in the swept day; its mid-year balance instant is booked as the annual TotalAssets/Equity, distorting every balance-derived ratio for that symbol.

## RED — write this test first
Write a failing test that reproduces: A JP company's Q2 report lands in the swept day; its mid-year balance instant is booked as the annual TotalAssets/Equity, distorting every balance-derived ratio for that symbol.

Suggested test file: `tests/test_edinet.FIX-002.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Filter list_documents (or the sweep loop) to the annual securities report docTypeCode (120) and/or require the balance instant to match the annual period end; add a fixture with an interim filing asserting it is skipped.

Touch only: `src/crible/providers/edinet.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
