# FIX-004 — Mirror sidecar meta write is non-atomic — a crash mid-write forces a full unconditional re-download  (P2 · OPPORTUNITY · impact low · effort S)

**Opportunity F2:** fetch_if_stale writes the data file atomically (temp-then-rename, mirror.py:92-96) but the .meta.json sidecar is a plain write_text (mirror.py:89, 98-100). A crash mid-write corrupts the sidecar; _read_meta then returns {} (mirror.py:47), losing the stored ETag and forcing a full unconditional re-download of the ~200MB GLEIF file next time. Fails safe (never serves stale data) but wastes bandwidth.
**Evidence:** `src/crible/ingest/mirror.py:98`, `src/crible/ingest/mirror.py:47`
**Why it matters:** fetch_if_stale writes the data file atomically (temp-then-rename, mirror.py:92-96) but the .meta.json sidecar is a plain write_text (mirror.py:89, 98-100). A crash mid-write corrupts the sidecar; _read_meta then returns {} (mirror.py:47), losing the stored ETag and forcing a full unconditional re-download of the ~200MB GLEIF file next time. Fails safe (never serves stale data) but wastes bandwidth.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Write the meta sidecar through the same temp-then-rename path as the data file.

Suggested test file: `tests/test_mirror.FIX-004.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Write the meta sidecar through the same temp-then-rename path as the data file.

Touch only: `src/crible/ingest/mirror.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
