# Contract: gate

Run the target's grounding gate over the eval artifacts and iterate until green:

- `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs check --run evals/2026-07-12` — structural grounding gate (every finding must resolve to a real file:line in the target, or a run: artifact). Exit 0 = grounded.
- `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs verify --run evals/2026-07-12` — writes VERIFY.todo.json (claim↔evidence). Fill each verdict honestly: `supported`/`partial`/`refuted`/`unsupported`.
- `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs verify --run evals/2026-07-12 --apply <verdicts.json>` — reduces to VERIFY.json.
- `node /Users/maxime/.agents/skills/ultraeval/scripts/ultraeval.mjs check --run evals/2026-07-12 --semantic --require-verify` — folds verdicts in; the exit gate.

If `check` fails, FIX `findings.json` (remove/repair ungrounded findings — do not weaken the gate) and re-run. If a finding is `refuted` by verification, set its status to `dismissed`. Report the final exit codes of `check --run evals/2026-07-12 --semantic --require-verify` — it MUST be 0 before results.
