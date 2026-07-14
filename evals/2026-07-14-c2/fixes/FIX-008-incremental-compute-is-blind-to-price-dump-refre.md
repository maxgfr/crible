# FIX-008 — Incremental compute is blind to price-dump refreshes — published prices, return_6m and value/momentum ranks go stale on the persisted-base path  (P2 · DEFECT)

**Finding F8:** build_snapshot_incremental derives its dirty set solely from raw-layer fetch stamps under data/raw (snapshot.py:262 via _newest_raw_stamp snapshot.py:230-242), but the imported price dump lives in data/prices-latest.parquet (price_import.py) OUTSIDE data/raw and is baked into each symbol's cached per-symbol row (snapshot.py:194-202, 161-170). After `crible import-prices` refreshes the dump, `crible compute` recomputes nothing for symbols whose fundamentals did not change, so their close, return_6m and the value/momentum ranks derived from them stay stale — diverging from a full build_snapshot. Production uses the incremental path (service.py:269, cli.py compute); build_snapshot is test-only and no periodic full rebuild self-heals. (Crawled yfinance price bars DO write to raw and self-heal; the gap is specific to the import-dump price path.)
**Evidence:** `src/crible/compute/snapshot.py:262`, `src/crible/compute/snapshot.py:236`, `src/crible/compute/snapshot.py:194`, `src/crible/ingest/price_import.py:37`
**Why it matters:** The hosted nightly runs import-prices (fresh Stooq closes) then incremental compute on a persisted base.parquet; no fundamentals changed that day, so the published snapshot keeps yesterday's (or last filing's) prices and momentum until the symbol is next dirtied by a filing.

## RED — write this test first
Write a failing test that reproduces: The hosted nightly runs import-prices (fresh Stooq closes) then incremental compute on a persisted base.parquet; no fundamentals changed that day, so the published snapshot keeps yesterday's (or last filing's) prices and momentum until the symbol is next dirtied by a filing.

Suggested test file: `tests/test_snapshot.py`
Run it and watch it FAIL before you touch the implementation.

## GREEN — make it pass
Treat prices-latest.parquet's mtime as a global change signal (mark all symbols dirty, or recompute the price/return_6m columns in finalize), or force a periodic full rebuild.

Touch only: `src/crible/compute/snapshot.py`, `src/crible/ingest/price_import.py`

## VERIFY
`pytest`
The RED test now passes and no existing test regresses.
