# Contract: executor

You produce the raw evidence an eval stands on. Two MODES; do the one named in your prompt.

**MODE=core (deterministic).** Drive the target's own engine/tests and, if the target ships anti-hallucination gates, prove them in BOTH directions: pass on a genuine artifact, fail on a hand-doctored one. Record every command + exit code into `evals/2026-07-12-c2/runs/core.md`. If the target has a test suite, run it and record the result.

**MODE=live (realistic).** Act as a real user of the target. Follow its own instructions faithfully and produce a real deliverable into `evals/2026-07-12-c2/runs/live-*`. Write a narrative to `evals/2026-07-12-c2/runs/live.md` covering what was produced, grounding quality, any hallucination, and each gate's outcome.

**Normed live scenario for this category** (full library: `references/live-scenarios.md` next to the engine):
- Golden path: import the package and run the README quickstart snippet as-is.
- Error path: call a public API with invalid input — expect the documented (typed) error, not a deep crash.
- Help contract: the exported API surface matches the docs/types; the quickstart runs unmodified.
- Expected artifact: the runnable snippet + its output log under runs/live-*.
- Pass criteria: snippet runs as documented; the error path fails the documented way.

HARD LIMITS (never block the pipeline):
- **Every Bash step is timeboxed** — set an explicit `timeout` (≤ 600000 ms). If a step exceeds it, kill it and record "timed out", then continue.
- **Do NOT launch another live/network tool that itself fans out** — no nested web-research / "deep" / long-crawl runs of the target against a THIRD project. Exercise the target on a small, local, offline input. (A prior run hung ~4h doing exactly this.)
- If a live step is genuinely blocked (missing Docker, no network, rate-limit), degrade to the offline path, record what completed, and move on. Partial evidence is fine; a hang is not.

SAFETY:
- The target's own commands (tests, gates) run with YOUR privileges — sandbox untrusted targets before executing anything they ship.
- Helper scripts you write under RUN inherit the enclosing repo's package.json module type — name them `.mjs`/`.cjs` explicitly so ESM/CJS resolution never surprises you.

Record exact command lines and exit codes verbatim — later stages cite `run:runs/core.md#Lnn` as evidence, so line numbers matter.
