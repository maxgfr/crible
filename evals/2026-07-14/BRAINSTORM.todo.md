# Brainstorm worklist — .

Generate MANY candidate improvement leads (be divergent), then keep the grounded ones. Target: `/Users/maxime/Downloads/crible`.

## Hotspots to anchor on
- `src/crible/ingest/service.py` (large: 820 LOC, 11 commits (churn), nesting depth 14)
- `src/crible/cli.py` (large: 313 LOC, 10 commits (churn))
- `ui/src/App.tsx` (275 LOC, 10 commits (churn), nesting depth 9)
- `tests/test_fr010_esef.py` (large: 307 LOC, nesting depth 8)
- `tests/test_fr016_edgar.py` (large: 340 LOC, nesting depth 14)
- `src/crible/compute/snapshot.py` (218 LOC)
- `tests/test_fr002_ingest.py` (269 LOC)
- `src/crible/ingest/price_import.py` (290 LOC, nesting depth 12)

## Dimensions
- correctness: Correctness
- tests: Test quality
- security: Security
- maintainability: Maintainability
- performance: Performance

## Lenses — internal health
- **simplify** — What could be simpler or removed — dead code, duplication, over-abstraction?
- **performance** — What does needless work on a hot path or at scale?
- **security** — What untrusted input reaches a sink unvalidated; what secret/authz risk?
- **testability** — What is untested or hard to test; what characterization test is missing?
- **dx** — What confuses a contributor — an error message, flag, default, or unclear name?
- **architecture** — What boundary is muddy; which hotspot module does too much and should split?

## Lenses — product / capability
- **feature-gap** — What capability would a user reasonably expect that is missing?
- **new-mode** — What new command/flag/mode would multiply the tool's value?
- **adjacent** — What adjacent use-case is one small step away?

## Output: write `opportunities.json`

`{ "opportunities": [ { "dimension"?, "impact": "high|med|low", "effort": "S|M|L", "title", "statement", "recommendation", "evidence": [ { "ref": "src/x.ts:42" | "analysis:src/x.ts" } ] } ] }`

Rules (the gate enforces them after `brainstorm --rank`):
- Every opportunity MUST cite a resolvable anchor — a real `file:line` in the target, or `analysis:<file>` for a metric-driven one. No ungrounded "rewrite everything".
- Rate impact (value) and effort (cost) honestly; quick wins are high-impact + low-effort.
- Then run `brainstorm --rank` to fold them into findings.json (ranked by impact/effort) and `check` to gate them.
