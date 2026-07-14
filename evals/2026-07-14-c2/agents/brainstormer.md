# Contract: brainstormer

Discover grounded improvement leads (both internal health AND product/capability) — be divergent, then keep the grounded ones.

1. `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs brainstorm --run evals/2026-07-14-c2` → emits `BRAINSTORM.todo.md` (lenses + hotspots).
2. Work every lens against the hotspots in `ANALYSIS.md` and the code. Generate MANY candidates, then write `evals/2026-07-14-c2/opportunities.json`: each `{ dimension?, impact: high|med|low, effort: S|M|L, title, statement, recommendation, evidence:[{ref}] }`. Every opportunity MUST anchor to a real `file:line` in the target or `analysis:<file>` — no ungrounded "rewrite everything". Rate impact/effort honestly (quick wins = high/S).
3. `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs brainstorm --run evals/2026-07-14-c2 --rank` → folds ranked opportunities into `findings.json` as kind:opportunity. The Gate stage then `check`s them; drop any that do not resolve.
