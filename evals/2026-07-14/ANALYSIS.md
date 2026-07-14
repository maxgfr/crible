# Analysis — /Users/maxime/Downloads/crible

110 files · 12706 LOC · .py 68 · .tsx 21 · .ts 20 · .mjs 1
deps: 72 local import edges, 1 cycle(s) · tests: 37/73 (ratio 0.51) · TODO/FIXME: 0 · docs: README.md, CONTRIBUTING.md, docs

## Hotspots (size + churn)

| file | LOC | churn | note |
|------|-----|-------|------|
| `src/crible/ingest/service.py` | 820 | 11 | large: 820 LOC, 11 commits (churn), nesting depth 14 |
| `src/crible/cli.py` | 313 | 10 | large: 313 LOC, 10 commits (churn) |
| `ui/src/App.tsx` | 275 | 10 | 275 LOC, 10 commits (churn), nesting depth 9 |
| `tests/test_fr010_esef.py` | 307 | 6 | large: 307 LOC, nesting depth 8 |
| `tests/test_fr016_edgar.py` | 340 | 3 | large: 340 LOC, nesting depth 14 |
| `src/crible/compute/snapshot.py` | 218 | 8 | 218 LOC |
| `tests/test_fr002_ingest.py` | 269 | 5 | 269 LOC |
| `src/crible/ingest/price_import.py` | 290 | 3 | 290 LOC, nesting depth 12 |
| `ui/src/components/QueryBuilder.tsx` | 299 | 2 | 299 LOC, nesting depth 9 |
| `src/crible/api/main.py` | 165 | 8 | 165 LOC, nesting depth 8 |
| `src/crible/providers/edgar.py` | 247 | 3 | 247 LOC, nesting depth 10 |
| `src/crible/runtime.py` | 205 | 5 | 205 LOC, nesting depth 12 |

## Import cycles

- ui/src/data/static-client.ts → ui/src/data/duckdb.ts → ui/src/data/static-client.ts
## Source files without an obvious test

- `evals/2026-07-14/eval.workflow.mjs`
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
- `src/crible/ingest/crawler.py`
- `src/crible/ingest/prices.py`
- `src/crible/ingest/queue.py`
- `src/crible/ingest/raw.py`
