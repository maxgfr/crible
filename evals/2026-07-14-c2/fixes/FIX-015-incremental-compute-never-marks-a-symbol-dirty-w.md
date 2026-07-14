# FIX-015 — Incremental compute never marks a symbol dirty when its newest raw file is removed  (P2 · DEFECT)

**Finding F15:** _newest_raw_stamp returns the max fetched-at stamp for a symbol (snapshot.py:239); a deletion can only lower the newest stamp, never raise it above base_mtime, so the dirty test `> base_mtime` (snapshot.py:262) misses a symbol whose latest raw statement was removed — it keeps its stale cached row while a full rebuild would reflect the removal. prune_raw is safe (it only deletes older versions), so this bites only on an out-of-band removal of the newest file; a full-drop of the symbol IS handled (snapshot.py:265-270).
**Evidence:** `src/crible/compute/snapshot.py:239`, `src/crible/compute/snapshot.py:262`
**Why it matters:** An operator manually deletes a corrupt newest raw parquet for one symbol; incremental compute keeps serving the row built from it until an unrelated change dirties the symbol.

## RED — write this test first
Write a failing test that reproduces: An operator manually deletes a corrupt newest raw parquet for one symbol; incremental compute keeps serving the row built from it until an unrelated change dirties the symbol.

Suggested test file: `tests/test_snapshot.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Also treat a drop in a symbol's newest-stamp (or a change in its raw file set) versus a recorded baseline as dirty; or compare a per-symbol raw fingerprint rather than a max stamp.

Touch only: `src/crible/compute/snapshot.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
