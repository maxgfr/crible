# Comparison — base `evals/2026-07-14-c4` → current `evals/2026-07-15`

- base: engine 1.9.0 · protocol 2 · rubric 1 · target 1206fad
- current: engine 1.9.0 · protocol 2 · rubric 1 · target 0f9921b

Score: 82 → 83 (+1) · meets-expectations true → true

## Resolved since base (3)

- P2 · EDINET sweep still applies no document-type filter — an interim (quarterly) filing's balance-sheet instant can be booked as the annual figure (c2 F13 / c3 F3, unresolved)
- P2 · EDINET context parsing still drops the consolidated/non-consolidated dimension — a parent-only (単体) figure can be booked for the group (c2 F14 / c3 F4, unresolved)
- opp · ingest/enrichment.py remains the top hotspot (617 LOC, 7 run_* cycles in one module) — c2 F1 / c3 F5 opportunity still open

## Introduced in current (7)

- opp · The trailing-6-month-return rule is implemented three times (two languages), kept in sync only by comments
- opp · compute_ratios reflection-wires every financetoolkit get_* and swallows every exception, with no direct test
- opp · run_loop (106 LOC, # pragma: no cover) hand-rolls six time-gated blocks and duplicates run_refresh's enrichment sequence
- opp · build_symbol_snapshot is a 70-line, five-concern function (the depth-8 hotspot) — invariants only reachable through the whole body
- opp · UI module cycle static-client.ts <-> duckdb.ts is type-only (harmless at runtime) but a cheap-to-clear coupling smell
- opp · EDINET annual-report filter narrows to docType 120 and also excludes amended annual reports (訂正有報, docType 130)
- opp · reconcile writes scalars into a DataFrame inside a double loop — per-cell .loc on deep-history symbols

## Retitled (same evidence, new title) (0)

- none
