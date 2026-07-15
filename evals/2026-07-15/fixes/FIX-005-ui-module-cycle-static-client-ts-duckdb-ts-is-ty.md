# FIX-005 — UI module cycle static-client.ts <-> duckdb.ts is type-only (harmless at runtime) but a cheap-to-clear coupling smell  (P2 · OPPORTUNITY · impact low · effort S)

**Opportunity F5:** The analyzer-flagged cycle is real to the graph but type-only at runtime: ui/src/data/duckdb.ts:11 does `import type { QueryRunner } from './static-client'` (erased at build) while ui/src/data/static-client.ts:74 reaches back via a lazy dynamic import('./duckdb') (intentional code-split to keep duckdb-wasm out of the initial bundle). No runtime defect, but the QueryRunner interface could live where the other shared contracts already do (ui/src/data/types.ts).
**Evidence:** `ui/src/data/duckdb.ts:11`, `ui/src/data/static-client.ts:74`
**Why it matters:** The analyzer-flagged cycle is real to the graph but type-only at runtime: ui/src/data/duckdb.ts:11 does `import type { QueryRunner } from './static-client'` (erased at build) while ui/src/data/static-client.ts:74 reaches back via a lazy dynamic import('./duckdb') (intentional code-split to keep duckdb-wasm out of the initial bundle). No runtime defect, but the QueryRunner interface could live where the other shared contracts already do (ui/src/data/types.ts).

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Move the QueryRunner interface into ui/src/data/types.ts and import it from there in both files. Zero runtime cost; clears the flagged cycle; matches where shared types already live.

Suggested test file: `ui/src/data/__tests__/duckdb.test.ts`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Move the QueryRunner interface into ui/src/data/types.ts and import it from there in both files. Zero runtime cost; clears the flagged cycle; matches where shared types already live.

Touch only: `ui/src/data/duckdb.ts`, `ui/src/data/static-client.ts`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
