# FIX-013 — bootstrap downloads the published dataset non-streaming and buffers it entirely in memory (io.BytesIO(response.content)) — OOM risk on a small self-hosted host  (P2 · DEFECT)

**Finding F13:** fetch_and_extract gets the dataset tarball with a non-streaming http.get (bootstrap.py:148) and wraps the full body in io.BytesIO(response.content) (bootstrap.py:153) before tarfile opens it. The whole (multi-hundred-MB and growing) published dataset is held in RAM at once — the opposite of the memory-safe member-by-member handling used for companyfacts.zip — so a small self-hosted box (the target audience) can OOM on the one-command bootstrap.
**Evidence:** `src/crible/bootstrap.py:148`, `src/crible/bootstrap.py:153`
**Why it matters:** A self-hoster on a 512MB-1GB VPS runs the bootstrap; the dataset has grown past available RAM and the process is OOM-killed before extraction, with no partial-progress fallback.

## RED — write this test first
Write a failing test that reproduces: A self-hoster on a 512MB-1GB VPS runs the bootstrap; the dataset has grown past available RAM and the process is OOM-killed before extraction, with no partial-progress fallback.

Suggested test file: `tests/test_bootstrap.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Stream the download to a temp file (http.stream / iter_bytes) and open tarfile from the file, or extract members incrementally; cap peak memory independent of dataset size.

Touch only: `src/crible/bootstrap.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
