"""FIX-004 / F2 — a hard per-fetch watchdog.

`crawl_symbol` called the provider with no hard timeout, trusting yfinance's
own (documented as unreliable — pulls can hang). A single hung fetch froze the
whole rolling crawl. The crawler now runs each fetch under a wall-clock
timeout; a timeout is treated as a failed fetch (rescheduled), never a freeze.
"""

from __future__ import annotations

import time

import pytest

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


# ------------------------------------------------- deadline, breaker, writes


import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from crible.ingest.queue import CrawlQueue  # noqa: E402
from crible.providers.base import FetchResult, RateLimitedError, StatementPayload  # noqa: E402


class _Clock:
    def __init__(self) -> None:
        self.t = 1_000.0
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


class _Provider:
    id = "yfinance"
    kind = "keyless"
    requests_per_fetch = 1

    def __init__(self, *, limited: bool = False, empty: bool = False) -> None:
        self.limited = limited
        self.empty = empty
        self.calls: list[str] = []

    def fetch_statements(self, symbol):
        self.calls.append(symbol)
        if self.limited:
            raise RateLimitedError("429 Too Many Requests")
        statements = (
            []
            if self.empty
            else [
                StatementPayload(
                    "income", "annual", pd.DataFrame({"period": ["2025"], "TotalRevenue": [1.0]})
                )
            ]
        )
        return FetchResult(symbol=symbol, provider=self.id, statements=statements)


def _queue(symbols: list[str]) -> CrawlQueue:
    con = duckdb.connect()
    queue = CrawlQueue(con)
    for i, symbol in enumerate(symbols):
        con.execute("INSERT INTO crawl_tasks (symbol, priority) VALUES (?, ?)", [symbol, i])
    return queue


def _crawler(tmp_path, queue, provider, clock, deadline=None, capacity=100) -> Crawler:
    return Crawler(
        queue=queue,
        provider=provider,
        budget=TokenBucket(capacity=capacity, window_seconds=3600, now=clock.now),
        backoff=BackoffPolicy(base_seconds=60, cap_seconds=900, jitter=0.0),
        data_dir=tmp_path,
        now=clock.now,
        sleep=clock.sleep,
        deadline=deadline,
    )


def test_rate_limits_trip_the_breaker_instead_of_45_minutes_per_symbol(tmp_path) -> None:
    clock = _Clock()
    queue = _queue(["A", "B", "C", "D"])
    crawler = _crawler(tmp_path, queue, _Provider(limited=True), clock)
    outcome = crawler.run_cycle(limit=10)
    assert outcome.aborted
    assert len(crawler.provider.calls) == 3  # three consecutive 429s, then stop
    assert sum(clock.slept) < 600


def test_the_crawler_never_sleeps_past_its_deadline(tmp_path) -> None:
    clock = _Clock()
    queue = _queue(["A", "B"])
    crawler = _crawler(tmp_path, queue, _Provider(limited=True), clock, deadline=clock.t + 90)
    crawler.run_cycle(limit=10)
    assert clock.t <= 1_000.0 + 90
    # an exhausted budget is not waited out past the deadline either
    clock2 = _Clock()
    crawler2 = _crawler(tmp_path, _queue(["A", "B"]), _Provider(), clock2, deadline=clock2.t + 30, capacity=1)
    outcome = crawler2.run_cycle(limit=10)
    assert outcome.fetched == ["A"] and clock2.t <= 1_000.0 + 30


def test_a_raw_write_error_reschedules_the_symbol(tmp_path, monkeypatch) -> None:
    import crible.ingest.crawler as crawler_module

    def disk_full(*args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(crawler_module, "write_raw_statement", disk_full)
    clock = _Clock()
    queue = _queue(["A"])
    outcome = _crawler(tmp_path, queue, _Provider(), clock).run_cycle(limit=5)
    assert outcome.failed == ["A"]
    failures, last = queue.con.execute(
        "SELECT consecutive_failures, last_crawled_at FROM crawl_tasks WHERE symbol = 'A'"
    ).fetchone()
    assert failures == 1 and last is None


def test_an_empty_symbol_leaves_a_marker_the_restore_reads(tmp_path) -> None:
    from crible.ingest.service import restore_queue_from_raw

    clock = _Clock()
    queue = _queue(["DEAD"])
    assert _crawler(tmp_path, queue, _Provider(empty=True), clock).crawl_symbol("DEAD")
    markers = list((tmp_path / "raw" / "provider=yfinance" / "symbol=DEAD").glob("meta-none-*.parquet"))
    assert len(markers) == 1

    fresh = _queue(["DEAD"])  # the nightly starts from a fresh DB
    assert restore_queue_from_raw(fresh.con, tmp_path) == 1
    last = fresh.con.execute("SELECT last_crawled_at FROM crawl_tasks").fetchone()[0]
    assert last == pytest.approx(clock.t)
