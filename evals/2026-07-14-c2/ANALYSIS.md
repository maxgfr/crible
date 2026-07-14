# Analysis — /Users/maxime/Downloads/crible

130 files · 15427 LOC · .py 87 · .tsx 21 · .ts 20 · .mjs 2
deps: 72 local import edges, 1 cycle(s) · tests: 47/83 (ratio 0.57) · TODO/FIXME: 0 · docs: README.md, CONTRIBUTING.md, docs

## Hotspots (size + churn)

| file | LOC | churn | note |
|------|-----|-------|------|
| `src/crible/ingest/service.py` | 523 | 20 | large: 523 LOC, 20 commits (churn), nesting depth 11 |
| `src/crible/ingest/enrichment.py` | 617 | 3 | large: 617 LOC, nesting depth 14 |
| `src/crible/cli.py` | 341 | 14 | large: 341 LOC, 14 commits (churn) |
| `src/crible/compute/snapshot.py` | 300 | 12 | large: 300 LOC, 12 commits (churn), nesting depth 8 |
| `tests/test_fr010_esef.py` | 371 | 7 | large: 371 LOC, nesting depth 8 |
| `ui/src/App.tsx` | 275 | 10 | 275 LOC, 10 commits (churn), nesting depth 9 |
| `tests/test_fr002_ingest.py` | 295 | 6 | 295 LOC |
| `tests/test_fr016_edgar.py` | 340 | 3 | large: 340 LOC, nesting depth 14 |
| `tests/test_fr003_compute.py` | 296 | 4 | 296 LOC, nesting depth 8 |
| `src/crible/ingest/price_import.py` | 290 | 3 | 290 LOC, nesting depth 12 |
| `ui/src/components/QueryBuilder.tsx` | 299 | 2 | 299 LOC, nesting depth 9 |
| `src/crible/api/main.py` | 165 | 8 | 165 LOC, nesting depth 8 |

## Import cycles

- ui/src/data/static-client.ts → ui/src/data/duckdb.ts → ui/src/data/static-client.ts
## Source files without an obvious test

- `evals/2026-07-14/eval.workflow.mjs`
- `evals/2026-07-14-c2/eval.workflow.mjs`
- `src/crible/api/main.py`
- `src/crible/bootstrap.py`
- `src/crible/cli.py`
- `src/crible/compute/beneish.py`
- `src/crible/compute/canonical.py`
- `src/crible/compute/ranks.py`
- `src/crible/compute/ratios.py`
- `src/crible/compute/reconcile.py`
- `src/crible/compute/scores.py`
- `src/crible/compute/snapshot.py`
- `src/crible/config.py`
- `src/crible/dsl/compiler.py`
- `src/crible/dsl/parser.py`
- `src/crible/ingest/backoff.py`
- `src/crible/ingest/budget.py`
- `src/crible/ingest/enrichment.py`
- `src/crible/ingest/prices.py`
- `src/crible/ingest/queue.py`
