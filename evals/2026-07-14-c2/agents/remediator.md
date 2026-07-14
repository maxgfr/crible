# Contract: remediator

Finalize the eval and generate the AI-exploitable fix docs.

1. Ensure `evals/2026-07-14-c2/RESULTS.md` and `SUMMARY.md` are complete and cite `[F#]`; `score` computes the weighted verdict and judge agreement from `judges.jsonl` — do not hand-average.
2. Score: `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs score --run evals/2026-07-14-c2` → `scorecard.json` (weighted 0-100 + meets-expectations, from judges.jsonl).
3. Emit the TDD backlog: `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs backlog --run evals/2026-07-14-c2 --tdd` → `BACKLOG.json`, `REMEDIATION.md`, and one `fixes/FIX-*.md` card per confirmed finding/opportunity (RED failing/spec test → GREEN change → VERIFY).
4. Render the dashboard: `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs render --run evals/2026-07-14-c2` → `index.md` + `index.html` (shows the verdict + opportunities matrix).
5. Re-run `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs check --run evals/2026-07-14-c2 --semantic` and confirm exit 0 (backlog integrity is part of the gate).
6. If `evals/2026-07-14-c2/runs/budget.md` exists (a budgeted run recorded coverage cuts), report EVERY cut in `SUMMARY.md` — `check` warns when the summary omits them; a silent cut reads as full coverage.

Report the verdict, the P0/P1 backlog headline, the top opportunities (impact×effort), and the paths a downstream fix agent should consume.
