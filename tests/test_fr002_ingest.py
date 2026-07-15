"""FR-002 — Rolling prioritized keyless ingestion.

All tests run offline: providers are fakes, clocks and sleepers are injected.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from crible.compute.snapshot import latest_raw_frames
from crible.ingest.backoff import BackoffPolicy
from crible.ingest.budget import TokenBucket
from crible.ingest.crawler import Crawler
from crible.ingest.queue import CrawlQueue
from crible.ingest.raw import prune_raw, write_raw_statement
from crible.providers.base import (
    FetchResult,
    ProviderRegistry,
    RateLimitedError,
    StatementPayload,
)
from crible.universe import bootstrap_universe

from tests.test_fr001_universe import fixture_frame


# ----------------------------------------------- F11: crashed-write partials


def test_leftover_tmp_partial_is_ignored_by_readers_and_prune(tmp_path) -> None:
    """F11 — a crash mid-write leaves a `.tmp-*.parquet` partial. It must never
    be globbed as a committed raw file: the snapshot reader would otherwise try
    to parse a corrupt partial and crash the whole compute, and prune would
    misparse its stem into a bogus (statement, freq) key."""
    frame = pd.DataFrame({"period": ["2024"], "TotalRevenue": [100.0]})
    write_raw_statement(
        tmp_path, symbol="AIR.PA", provider="yfinance",
        statement_type="income", freq="annual", frame=frame, fetched_at=1000.0,
    )
    sym_dir = tmp_path / "raw" / "provider=yfinance" / "symbol=AIR.PA"
    (sym_dir / ".tmp-income-annual-000000002000000.parquet").write_bytes(b"not a parquet")

    # the reader ignores the partial and returns only the committed frame
    frames = latest_raw_frames(tmp_path, "AIR.PA")
    assert set(frames) == {("income", "annual")}

    # prune ignores the partial (one committed file, nothing to delete)
    assert prune_raw(tmp_path) == 0
    assert (sym_dir / "income-annual-000000001000000.parquet").exists()


# --------------------------------------------------------------------- fakes


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def now(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class FakeProvider:
    """Keyless provider double recording calls; can inject 429s per symbol."""

    id = "fake"
    kind = "keyless"
    requests_per_fetch = 1

    def __init__(self, rate_limited_first_n: dict[str, int] | None = None) -> None:
        self.calls: list[str] = []
        self.call_times: list[float] = []
        self._limited = dict(rate_limited_first_n or {})

    def enabled(self, env: dict[str, str]) -> bool:
        return True

    def fetch_statements(self, symbol: str) -> FetchResult:
        self.calls.append(symbol)
        left = self._limited.get(symbol, 0)
        if left > 0:
            self._limited[symbol] = left - 1
            raise RateLimitedError(f"429 for {symbol}")
        payload = StatementPayload(
            statement_type="income",
            freq="annual",
            frame=pd.DataFrame({"period": ["2025"], "revenue": [100.0]}),
        )
        return FetchResult(symbol=symbol, provider=self.id, statements=[payload], requests_used=1)


class KeyedProvider:
    id = "needs_key"
    kind = "free-key"
    key_env_var = "NEEDS_KEY_TOKEN"
    requests_per_fetch = 1

    def __init__(self) -> None:
        self.calls: list[str] = []

    def enabled(self, env: dict[str, str]) -> bool:
        return bool(env.get(self.key_env_var))

    def fetch_statements(self, symbol: str) -> FetchResult:
        self.calls.append(symbol)
        return FetchResult(symbol=symbol, provider=self.id, statements=[], requests_used=1)


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect()
    bootstrap_universe(c, fixture_frame())
    return c


def make_crawler(con, provider, clock, data_dir, budget_capacity=330, sleeper=None):
    sleeps: list[float] = []
    return (
        Crawler(
            queue=CrawlQueue(con),
            provider=provider,
            budget=TokenBucket(capacity=budget_capacity, window_seconds=3600, now=clock.now),
            backoff=BackoffPolicy(base_seconds=60, cap_seconds=900, jitter=0.2, rng=lambda: 0.5),
            data_dir=data_dir,
            now=clock.now,
            sleep=sleeper if sleeper is not None else sleeps.append,
        ),
        sleeps,
    )


# --------------------------------------------------------------------- tests


def test_fr002_token_bucket_enforces_rolling_hour_budget() -> None:
    clock = FakeClock()
    bucket = TokenBucket(capacity=330, window_seconds=3600, now=clock.now)

    for _ in range(330):
        assert bucket.try_acquire()
    assert not bucket.try_acquire()  # 331st in the same hour is denied
    assert bucket.seconds_until_available() > 0

    clock.advance(3600.01)  # window rolls over
    assert bucket.try_acquire()


def test_fr002_budget_charges_per_upstream_request_not_per_symbol(con, tmp_path) -> None:
    """NFR-007: a 7-requests-per-fetch provider on a 20-token budget fits only
    2 symbols per rolling window; the 3rd waits for the window to roll."""
    clock = FakeClock()

    class ExpensiveProvider(FakeProvider):
        requests_per_fetch = 7

        def fetch_statements(self, symbol: str) -> FetchResult:
            self.call_times.append(clock.now())
            return super().fetch_statements(symbol)

    provider = ExpensiveProvider()
    # sleeper advances the fake clock so budget waits actually release
    crawler, _ = make_crawler(
        con, provider, clock, tmp_path, budget_capacity=20, sleeper=clock.advance
    )
    crawler.run_cycle(limit=3)

    assert len(provider.call_times) == 3
    first_window = [t for t in provider.call_times if t < provider.call_times[0] + 3600]
    assert len(first_window) == 2  # 3 × 7 = 21 > 20 → third fetch waited out the window
    assert provider.call_times[2] >= 3600


def test_fr002_europe_is_crawled_before_us_before_world(con, tmp_path) -> None:
    clock = FakeClock()
    provider = FakeProvider()
    crawler, _ = make_crawler(con, provider, clock, tmp_path)

    crawler.run_cycle(limit=8)

    regions = dict(
        con.execute("SELECT symbol, region FROM companies").fetchall()
    )
    seen_order = [regions[s] for s in provider.calls]
    # all europe first, then us, then world
    assert seen_order == sorted(seen_order, key=["europe", "us", "world"].index)
    # within europe, Large Caps beat the Mid Cap (ABN.AS) — cap-tiered priority
    europe_calls = [s for s in provider.calls if regions[s] == "europe"]
    assert europe_calls.index("ABN.AS") > max(
        europe_calls.index(s) for s in ("AIR.PA", "SAP.DE", "NESN.SW", "BARC.L")
    )


def test_fr002_backoff_doubles_with_cap_and_reschedules(con, tmp_path) -> None:
    clock = FakeClock()
    provider = FakeProvider(rate_limited_first_n={"ABN.AS": 2})
    crawler, sleeps = make_crawler(con, provider, clock, tmp_path)

    crawler.run_cycle(limit=8)

    # two 429s → two backoff sleeps; rng=0.5 makes jitter factor exactly 1.0
    backoff_sleeps = [s for s in sleeps if s >= 60]
    assert backoff_sleeps[:2] == [60.0, 120.0]
    # the symbol was rescheduled, not dropped: eventually fetched
    assert provider.calls.count("ABN.AS") == 3
    status = con.execute(
        "SELECT consecutive_failures FROM crawl_tasks WHERE symbol = 'ABN.AS'"
    ).fetchone()[0]
    assert status == 0  # success reset


def test_fr002_backoff_never_exceeds_cap() -> None:
    policy = BackoffPolicy(base_seconds=60, cap_seconds=900, jitter=0.2, rng=lambda: 1.0)
    delays = [policy.delay(attempt) for attempt in range(1, 12)]
    assert max(delays) <= 900 * 1.2 + 1e-9
    assert delays[0] == pytest.approx(60 * 1.2)


def test_fr002_crash_resume_skips_fresh_symbols(con, tmp_path) -> None:
    clock = FakeClock(start=1_000_000)
    provider = FakeProvider()
    crawler, _ = make_crawler(con, provider, clock, tmp_path)
    crawler.run_cycle(limit=8)
    assert len(provider.calls) == 8

    # a "new process" over the same operational DB shortly after
    clock.advance(3600)
    provider2 = FakeProvider()
    crawler2, _ = make_crawler(con, provider2, clock, tmp_path)
    crawler2.run_cycle(limit=8)

    # everything is inside its quarterly freshness window → nothing re-fetched
    assert provider2.calls == []


def test_fr002_raw_parquet_is_versioned_and_readable(tmp_path) -> None:
    frame = pd.DataFrame({"period": ["2025"], "revenue": [100.0]})
    path1 = write_raw_statement(
        tmp_path, symbol="AIR.PA", provider="yfinance",
        statement_type="income", freq="annual", frame=frame, fetched_at=1_000.0,
    )
    path2 = write_raw_statement(
        tmp_path, symbol="AIR.PA", provider="yfinance",
        statement_type="income", freq="annual", frame=frame, fetched_at=2_000.0,
    )
    assert path1 != path2  # versioned, append-only
    assert path1.exists() and path2.exists()
    assert ".tmp" not in path1.name
    got = duckdb.connect().execute(f"SELECT revenue FROM read_parquet('{path1}')").fetchone()[0]
    assert got == 100.0


def test_fr002_skip_identical_reuses_the_newest_version(tmp_path) -> None:
    """Re-fetch-everything providers (EDGAR bulk, FSDS, ESEF) must not
    re-stamp unchanged data: a fresh stamp marks the symbol dirty and
    degrades incremental compute to a full rebuild."""
    frame = pd.DataFrame({"period": ["2025"], "revenue": [100.0]})
    first = write_raw_statement(
        tmp_path, symbol="AAPL", provider="edgar",
        statement_type="income", freq="annual", frame=frame, fetched_at=1_000.0,
    )
    again = write_raw_statement(
        tmp_path, symbol="AAPL", provider="edgar",
        statement_type="income", freq="annual", frame=frame.copy(), fetched_at=2_000.0,
        skip_identical=True,
    )
    assert again == first  # no new file, no new stamp
    directory = tmp_path / "raw" / "provider=edgar" / "symbol=AAPL"
    assert len(list(directory.glob("*.parquet"))) == 1

    # a changed value DOES write a new version
    changed = frame.assign(revenue=[120.0])
    third = write_raw_statement(
        tmp_path, symbol="AAPL", provider="edgar",
        statement_type="income", freq="annual", frame=changed, fetched_at=3_000.0,
        skip_identical=True,
    )
    assert third != first
    assert len(list(directory.glob("*.parquet"))) == 2
    # a different (statement, freq) key never matches the income file
    other = write_raw_statement(
        tmp_path, symbol="AAPL", provider="edgar",
        statement_type="balance", freq="annual", frame=frame, fetched_at=4_000.0,
        skip_identical=True,
    )
    assert other.name.startswith("balance-annual-")


def test_fr002_keyed_provider_without_key_disables_cleanly(caplog) -> None:
    registry = ProviderRegistry(env={})
    keyed = KeyedProvider()
    with caplog.at_level("INFO"):
        active = registry.activate([FakeProvider(), keyed])

    assert [p.id for p in active] == ["fake"]
    assert keyed.calls == []
    disabled_lines = [r for r in caplog.records if "disabled (no key configured)" in r.message]
    assert len(disabled_lines) == 1 and "needs_key" in disabled_lines[0].message


def test_fr002_keyed_provider_with_key_is_active() -> None:
    registry = ProviderRegistry(env={"NEEDS_KEY_TOKEN": "x"})
    active = registry.activate([KeyedProvider()])
    assert [p.id for p in active] == ["needs_key"]


def test_fr002_run_cycle_persists_raw_parquet_to_disk(con, tmp_path) -> None:
    """FR-002 AC-1: the crawler→raw-layer link itself — files land on disk."""
    clock = FakeClock()
    provider = FakeProvider()
    crawler, _ = make_crawler(con, provider, clock, tmp_path)
    crawler.run_cycle(limit=3)
    files = list(tmp_path.glob("raw/provider=fake/symbol=*/income-annual-*.parquet"))
    assert len(files) == 3


def test_fr002_resume_from_partial_cycle_fetches_only_the_rest(con, tmp_path) -> None:
    """Killed mid-cycle: 4 of 8 crawled → the next process fetches ONLY the
    remaining 4 (fresh ones are skipped)."""
    clock = FakeClock(start=1_000_000)
    first = FakeProvider()
    crawler, _ = make_crawler(con, first, clock, tmp_path)
    crawler.run_cycle(limit=4)  # "killed" after a partial pass
    assert len(first.calls) == 4

    clock.advance(60)
    second = FakeProvider()
    crawler2, _ = make_crawler(con, second, clock, tmp_path)
    crawler2.run_cycle(limit=8)

    assert len(second.calls) == 4  # only the un-crawled half
    assert set(second.calls).isdisjoint(first.calls)
