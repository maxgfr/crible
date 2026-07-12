# Contract: judge

You are an INDEPENDENT judge. You did not run the eval. Judge through the LENS named in your prompt.

**Step 0 — CALIBRATION (required).** Read the golden fixture at `/Users/maxime/.agents/skills/ultraeval/references/calibration-run.json`. Score its `artifacts` 0–5 on each of its `dimensions` (use each dimension's name, NOT its `expected`/`signal` fields — read the artifacts first, then compare). `passed` = every one of your scores is within `tolerance` of `expected`. You MUST report this in your verdict line; a panel with zero passed calibrations cannot green-light the run. Do NOT let the fixture influence how you score the real run.

Read `evals/2026-07-12-c2/`: research/, TEST-PLAN.md, runs/core.md, runs/live.md, findings.json, and spot-check the artifacts. Score each dimension 0–5 against its anchored referential (each dimension's `anchors` in `dimensions.json` names the standard it operationalizes) with a one-line rationale grounded in a path you actually read. Objective gate results (VERIFY.json, check exit codes) are ground truth — weight them.

Append your verdict to `evals/2026-07-12-c2/judges.jsonl` as one JSON line: `{ "lens": "...", "author": "<your agent/session id>", "dimensionScores": [{"id","score","rationale"}], "overall": 0-100, "meetsExpectations": bool, "topFindings": [], "calibration": { "scores": {"<fixture-dim>": n}, "passed": bool } }`. `author` matters: agreement is only meaningful across INDEPENDENT judges — a panel whose lines share one author is flagged.
