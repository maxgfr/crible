## What & why

<!-- One paragraph: the problem and how this PR solves it. Link the issue. -->

## Checklist

- [ ] `uv run pytest` and `uv run ruff check src tests` pass
- [ ] `npm --prefix ui run test -- --run` passes
- [ ] Zero-key contract holds: no core flow gained a key/account requirement
- [ ] If the DSL grammar changed: both compilers updated **and**
      `ui/src/dsl/golden.json` regenerated (parity tests pass on both sides)
- [ ] New behavior is covered by a test named after its requirement where applicable
