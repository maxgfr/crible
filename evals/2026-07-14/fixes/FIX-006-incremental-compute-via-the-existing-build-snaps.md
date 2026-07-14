# FIX-006 — Incremental compute via the existing build_snapshot(symbols=…) seam  (P2 · OPPORTUNITY · impact med · effort M)

**Opportunity F7:** Every compute cycle rebuilds the entire snapshot: run_compute() calls build_snapshot(data) with no symbols, which re-reads every crawled symbol's raw parquet and recomputes all ratios/scores/ranks (snapshot.py:171-172). build_snapshot ALREADY accepts a symbols= argument — the seam exists, the caller just never uses it. Fine at ~500 companies, quadratic pain toward the 150k universe the README advertises.
**Evidence:** `src/crible/compute/snapshot.py:171-172`, `src/crible/ingest/service.py:653`
**Why it matters:** Every compute cycle rebuilds the entire snapshot: run_compute() calls build_snapshot(data) with no symbols, which re-reads every crawled symbol's raw parquet and recomputes all ratios/scores/ranks (snapshot.py:171-172). build_snapshot ALREADY accepts a symbols= argument — the seam exists, the caller just never uses it. Fine at ~500 companies, quadratic pain toward the 150k universe the README advertises.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Track symbols whose raw changed since the last snapshot (fetched_at stamps already exist) and pass them to build_snapshot; ranks stay cross-sectional so recompute ranks over the union, but skip re-parsing unchanged raw.

Suggested test file: `tests/test_snapshot.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Track symbols whose raw changed since the last snapshot (fetched_at stamps already exist) and pass them to build_snapshot; ranks stay cross-sectional so recompute ranks over the union, but skip re-parsing unchanged raw.

Touch only: `src/crible/compute/snapshot.py`, `src/crible/ingest/service.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
