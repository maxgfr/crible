# FIX-011 — Raw layer glob('*.parquet') matches leftover '.tmp-*.parquet' partials — pathlib includes dotfiles, defeating write-temp-then-rename atomicity  (P2 · DEFECT)

**Finding F11:** write_raw_statement stages to '.tmp-{...}.parquet' then renames to the final name (raw.py:51,59), relying on the tmp being invisible to readers. But pathlib's glob('*.parquet') DOES match dotfiles (verified empirically), so prune_raw (raw.py:26) and latest_raw_frames (snapshot.py:121) both enumerate leftover '.tmp-*.parquet' files. A crash between to_parquet(tmp) and rename leaves a partial parquet that a later glob picks up; stem.split('-',2) yields a junk '.tmp' statement_type and pd.read_parquet on the truncated file can raise, breaking the snapshot build for that symbol. The raw layer is documented as 'the durable source of truth any snapshot can be recomputed from' (raw.py:1-6).
**Evidence:** `src/crible/ingest/raw.py:51`, `src/crible/ingest/raw.py:26`, `src/crible/compute/snapshot.py:120-123`
**Why it matters:** An ingest container is killed mid-write; the leftover '.tmp-income-annual-<stamp>.parquet' is later read by the compute step and raises on the truncated parquet, silently dropping that symbol from the snapshot until an operator cleans up.

## RED — write this test first
Write a failing test that reproduces: An ingest container is killed mid-write; the leftover '.tmp-income-annual-<stamp>.parquet' is later read by the compute step and raises on the truncated parquet, silently dropping that symbol from the snapshot until an operator cleans up.

Suggested test file: `tests/test_raw.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Write the tmp OUTSIDE the globbed tree or name it without a '.parquet' suffix, and filter '.tmp-*' in prune_raw/latest_raw_frames; sweep stale tmp files on startup.

Touch only: `src/crible/ingest/raw.py`, `src/crible/compute/snapshot.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
