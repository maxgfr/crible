"""FIX-004 / F2 — a hard per-fetch watchdog.

`crawl_symbol` called the provider with no hard timeout, trusting yfinance's
own (documented as unreliable — pulls can hang). A single hung fetch froze the
whole rolling crawl. The crawler now runs each fetch under a wall-clock
timeout; a timeout is treated as a failed fetch (rescheduled), never a freeze.
"""

from __future__ import annotations

import time

from crible.ingest.backoff import BackoffPolicy
from crible.ingest.budget import TokenBucket
from crible.ingest.crawler import Crawler


class HungProvider:
    id = "yfinance"
    kind = "keyless"
    requests_per_fetch = 1

    def fetch_statements(self, symbol):
        time.sleep(2)  # never returns inside the watchdog window
        raise AssertionError("unreachable — the watchdog should have fired")


class RecordingQueue:
    def __init__(self) -> None:
        self.failed: list[str] = []

    def next_batch(self, now, limit):
        return []

    def mark_failed(self, symbol, now):
        self.failed.append(symbol)

    def mark_done(self, symbol, now):
        raise AssertionError("a hung fetch must not be marked done")


def test_crawl_symbol_times_out_on_a_hung_fetch(tmp_path) -> None:
    queue = RecordingQueue()
    crawler = Crawler(
        queue=queue,
        provider=HungProvider(),
        budget=TokenBucket(capacity=100, window_seconds=3600),
        backoff=BackoffPolicy(),
        data_dir=tmp_path,
        fetch_timeout=0.1,
    )

    start = time.monotonic()
    ok = crawler.crawl_symbol("AIR.PA")
    elapsed = time.monotonic() - start

    assert ok is False
    assert queue.failed == ["AIR.PA"]  # rescheduled, not frozen
    assert elapsed < 1.0  # returned on the watchdog, not after the 2s hang
