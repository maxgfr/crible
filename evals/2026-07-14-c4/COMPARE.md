# Comparison — base `evals/2026-07-14-c3` → current `evals/2026-07-14-c4`

- base: engine 1.9.0 · protocol 2 · rubric 1 · target ee2eb09
- current: engine 1.9.0 · protocol 2 · rubric 1 · target 1206fad

Score: 77 → 82 (+5) · meets-expectations false → true

## Resolved since base (4)

- P1 · REGRESSION from the F6 fix: audited-only periods are appended UNSORTED, so the current price, return_6m and every price-derived ratio land on an OLD period instead of the latest — the flagship deep-history universe is now silently mis-priced
- P2 · Audited-only symbols still carry no field-level provenance (audited_fields empty) — the c2 F3 gap is unresolved on the production path
- P2 · EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13, unresolved)
- opp · Mirror bulk fetch still has no max-size or total-time cap — c2 F5 opportunity still open

## Introduced in current (1)

- P2 · EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13 / c3 F3, unresolved)

## Retitled (same evidence, new title) (2)

- EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14, unresolved) → EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14 / c3 F4, unresolved)
- ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 opportunity still open → ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 / c3 F5 opportunity still open
