# Contributing to crible

Thanks for helping! crible is small and spec-driven; this page is everything
you need.

## Ground rules

1. **Zero-key is the contract, not a default.** Every core flow must work with
   an empty environment — no API key, no account, ever. CI enforces this: the
   Python job runs with no secrets configured. A change that makes a core flow
   require a key will not be merged. Third-party keyed provider plugins must
   stay optional and off by default. New data sources must clear
   the public-data audit in [DATA-SOURCES.md](DATA-SOURCES.md) —
   public, keyless, ToS-respecting — and be added to that table.
2. **The DSL has two implementations that may never drift.** The Python
   compiler (`src/crible/dsl/`) and the TypeScript port (`ui/src/dsl/`) are
   locked together by shared golden vectors (`ui/src/dsl/golden.json`),
   asserted by both pytest and vitest. If you change the grammar, change both
   sides and regenerate the golden file — the parity tests will hold you to it.
3. **Tests first.** The suite is FR-tagged (`tests/test_fr004_dsl.py` proves
   FR-004, and so on — the FR id is the requirement label). New behavior comes
   with a test that fails without it.

## Development setup

```bash
uv sync                          # Python 3.12 env + deps
uv run pytest                    # backend suite
uv run ruff check src tests     # lint

npm --prefix ui install
npm --prefix ui run test -- --run   # vitest suite
npm --prefix ui run dev             # SPA on :5173, proxies /api to :8000
```

Run the full stack locally with `docker compose up`, or the API alone with
`uv run uvicorn crible.api.main:app --reload`.

The GitHub Pages build (the hosted screener) is a separate mode of the same SPA:

```bash
VITE_DATA_MODE=static VITE_BASE=/crible/ npm --prefix ui run build
```

### Seeding the published dataset (maintainers)

The dataset normally refreshes nightly via the `refresh-data` workflow.
To seed it upfront — or rescue it when Yahoo rate-limits the GitHub runners —
run the same keyless pipeline from your own machine:

```bash
DEADLINE=7200 bash scripts/seed-data.sh   # crawl budget in seconds
```

It restores the last-good dataset, crawls politely (~47 symbols/hour at the
default budget), refuses to publish under 50 covered symbols, uploads the
`data-latest` release assets and triggers the Pages deploy. Re-running resumes
instead of starting over.

## Pull requests

- Keep PRs focused; one concern per PR.
- `uv run pytest && uv run ruff check src tests` and
  `npm --prefix ui run test -- --run` must pass (CI runs both, plus the
  static demo build and `docker compose build`).
- Follow the existing commit style: `type(scope): summary` (`feat(dsl): …`,
  `fix(ingest): …`, `docs: …`).
- Data sources must be open data / keyless to qualify for the core; keyed
  sources go through the provider plugin seam (`src/crible/providers/`).

## Releases

Code releases are fully automated (`.github/workflows/release.yml`): after every
green `ci` run on `main`, python-semantic-release reads the conventional commits
since the last `vX.Y.Z` tag and decides the bump — `feat` → minor, `fix`/`perf` →
patch, `docs`/`ci`/`chore`/`refactor`/`test` → no release (while the project is
0.x, breaking changes also bump the minor: `major_on_zero = false`). A release
bumps `pyproject.toml` + `crible.__version__` (`chore(release): vX.Y.Z` commit),
tags, publishes a GitHub Release with generated notes and pushes the multi-arch
image to `ghcr.io/maxgfr/crible` (`:vX.Y.Z` + `:latest`). Nothing to do by hand —
your commit type IS the release decision.

`docs/CHANGELOG.md` stays hand-written (narrative), and the rolling `data-latest`
release is the separate data channel — semantic-release never touches either.

## Reporting bugs / proposing features

Use the issue templates. For security issues, see [SECURITY.md](SECURITY.md) —
please do not open a public issue.
