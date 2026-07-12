# Contract: analyzer

Produce deterministic signal for the brainstorm stage.

Run `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs analyze --run evals/2026-07-12-c2` → writes `analysis.json` + `ANALYSIS.md` (size/complexity hotspots, import graph + cycles, git churn, test/doc gaps). Then read `ANALYSIS.md` and note the 5-8 highest-signal hotspots the brainstorm should anchor on. This stage is deterministic — do not invent metrics; report what the tool found.
