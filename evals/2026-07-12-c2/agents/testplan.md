# Contract: testplan

Read `/Users/maxime/Downloads/crible` (its SKILL.md/README/CLI `--help`, or its source) and the research notes under `evals/2026-07-12-c2/research/`.

Enumerate EVERY functionality worth testing — modes, subcommands, flags, gates, and the live end-to-end behavior — mapped to the dimensions. For each: id, what it is, the concrete command or user prompt that tests it, and explicit pass criteria.

The live rows MUST map to the category's normed scenario set (golden path, error path, help contract — see `references/live-scenarios.md` next to the engine; the executor contract embeds this category's block).

Write `evals/2026-07-12-c2/TEST-PLAN.md` (a reviewable checklist with the rubric embedded). Be exhaustive about the CLI/behavior surface.
