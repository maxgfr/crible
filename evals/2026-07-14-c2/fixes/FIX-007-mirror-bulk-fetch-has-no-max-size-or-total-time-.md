# FIX-007 — Mirror bulk fetch has no max-size or total-time cap  (P2 · OPPORTUNITY · impact low · effort M)

**Opportunity F5:** fetch_if_stale streams response.iter_bytes to disk with no size ceiling (mirror.py:93-95) and an httpx timeout that is per-operation, not total (mirror.py:80). URLs are hardcoded and trusted (GLEIF, Frankfurter) so there is no SSRF, but a misbehaving/hostile server could fill the disk or keep a slow download alive indefinitely — the ~200MB GLEIF fetch on the auto-heal path is the exposure.
**Evidence:** `src/crible/ingest/mirror.py:93`, `src/crible/ingest/mirror.py:80`
**Why it matters:** fetch_if_stale streams response.iter_bytes to disk with no size ceiling (mirror.py:93-95) and an httpx timeout that is per-operation, not total (mirror.py:80). URLs are hardcoded and trusted (GLEIF, Frankfurter) so there is no SSRF, but a misbehaving/hostile server could fill the disk or keep a slow download alive indefinitely — the ~200MB GLEIF fetch on the auto-heal path is the exposure.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Add a byte ceiling while streaming (raise past N bytes) and a wall-clock deadline for the whole transfer.

Suggested test file: `tests/test_mirror.FIX-007.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Add a byte ceiling while streaming (raise past N bytes) and a wall-clock deadline for the whole transfer.

Touch only: `src/crible/ingest/mirror.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
