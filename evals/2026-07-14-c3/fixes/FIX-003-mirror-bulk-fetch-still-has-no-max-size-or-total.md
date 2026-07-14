# FIX-003 — Mirror bulk fetch still has no max-size or total-time cap — c2 F5 opportunity still open  (P2 · OPPORTUNITY · impact low · effort S)

**Opportunity F6:** fetch_if_stale streams response.iter_bytes to disk with no byte ceiling (mirror.py:102) under an httpx timeout that is per-operation, not total (mirror.py:88). URLs are hardcoded/trusted (no SSRF), but a misbehaving or hostile mirror could fill the disk or keep a slow ~200MB GLEIF download alive indefinitely on the auto-heal path.
**Evidence:** `src/crible/ingest/mirror.py:102`, `src/crible/ingest/mirror.py:88`
**Why it matters:** fetch_if_stale streams response.iter_bytes to disk with no byte ceiling (mirror.py:102) under an httpx timeout that is per-operation, not total (mirror.py:88). URLs are hardcoded/trusted (no SSRF), but a misbehaving or hostile mirror could fill the disk or keep a slow ~200MB GLEIF download alive indefinitely on the auto-heal path.

## RED — write this test first
Write a spec/characterization test that pins the desired behavior: Add a byte ceiling while streaming (abort past N bytes) and a wall-clock deadline for the whole transfer.

Suggested test file: `tests/test_mirror.FIX-003.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Add a byte ceiling while streaming (abort past N bytes) and a wall-clock deadline for the whole transfer.

Touch only: `src/crible/ingest/mirror.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
