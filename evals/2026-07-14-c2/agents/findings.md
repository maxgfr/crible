# Contract: findings

Consolidate the test-plan results and the run logs into `evals/2026-07-14-c2/findings.json` following `evals/2026-07-14-c2/findings.schema.json`.

RULES (the grounding gate will enforce these):
- Every finding MUST carry at least one resolvable `evidence.ref`:
  - `path:line` or `path:start-end` — a real location IN THE TARGET (`/Users/maxime/Downloads/crible`).
  - `run:relpath#Lnn` — a line in a log this run produced.
- Do NOT invent line numbers. If you cite `src/x.ts:42`, line 42 must exist and support the claim.
- `severity`: P0 (Critical: breaks trust, correctness, safety, or data integrity of the primary deliverable; the documented main path fails) · P1 (Major: materially degrades a scored dimension (fidelity, coverage, robustness); a workaround or secondary path exists) · P2 (Minor: polish, consistency, or documentation drift; no scored dimension materially degraded).
- `status`: `confirmed` (evidence holds) or `open` (needs verification). Never keep a finding you cannot ground — delete it.

Also draft `evals/2026-07-14-c2/RESULTS.md` (per-functionality results, every claim citing `[F#]`) and `evals/2026-07-14-c2/SUMMARY.md` (scorecard + headline). Flag any narrative sentence that is not a finding with `[M]`.
