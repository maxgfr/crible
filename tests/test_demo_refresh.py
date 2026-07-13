"""The bounded nightly refresh behind `crible demo-refresh` (GitHub Actions).

One-shot, deadline-bounded: bootstrap (with a last-good universe.parquet
fallback when FinanceDatabase is down), crawl the prioritized sample on ONE
shared token bucket, prune the raw layer to the newest file per key, compute,
publish. All tests run offline with injected fakes.
"""

from __future__ import annotations

import json

import duckdb
import pandas as pd
import pytest

from crible.compute.snapshot import latest_raw_frames
from crible.ingest.raw import prune_raw, write_raw_statement
from crible.ingest.service import run_refresh
from crible.providers.base import FetchResult, StatementPayload
from crible.universe import (
    UniverseSourceError,
    bootstrap_universe,
    export_universe_parquet,
    restore_universe_from_parquet,
)

from tests.test_fr001_universe import fixture_frame


class FakeYfProvider:
    """Statement provider double writing under provider='yfinance' so the
    snapshot builder (which only reads yfinance/esef) picks it up."""

    id = "yfinance"
    kind = "keyless"
    requests_per_fetch = 1

    def __init__(self) -> None:
        self.calls: list[str] = []

    def enabled(self, env: dict[str, str]) -> bool:
        return True

    def fetch_statements(self, symbol: str) -> FetchResult:
        self.calls.append(symbol)
        payload = StatementPayload(
            statement_type="income",
            freq="annual",
            frame=pd.DataFrame({"period": ["2024", "2025"], "TotalRevenue": [90.0, 100.0]}),
        )
        return FetchResult(symbol=symbol, provider=self.id, statements=[payload], requests_used=1)


class FakePriceProvider:
    id = "yfinance"

    def fetch_prices(self, symbol: str) -> pd.DataFrame | None:
        return pd.DataFrame({"Date": ["2026-07-10"], "Close": [42.0]})


class FakeEdgarDirectory:
    """EDGAR client double: an empty SEC directory keeps the cycle offline."""

    def company_tickers(self):
        return {}

    def companyfacts(self, cik):
        raise AssertionError("no CIK resolves — companyfacts is never fetched")


# ------------------------------------------------------------------- restore


def test_restore_universe_preserves_regions_and_iso_codes(tmp_path) -> None:
    source = duckdb.connect()
    bootstrap_universe(source, fixture_frame())
    export_universe_parquet(source, tmp_path)
    expected = source.execute(
        "SELECT symbol, country, country_name, region, crawl_priority FROM companies ORDER BY symbol"
    ).fetchall()
    source.close()

    fresh = duckdb.connect()
    restored = restore_universe_from_parquet(fresh, tmp_path / "universe.parquet")
    got = fresh.execute(
        "SELECT symbol, country, country_name, region, crawl_priority FROM companies ORDER BY symbol"
    ).fetchall()

    assert restored == 8
    assert got == expected  # ISO codes and regions survive — no world remap
    by_symbol = {r[0]: r for r in got}
    assert by_symbol["AIR.PA"][1] == "FR"
    assert by_symbol["AIR.PA"][3] == "europe"


def test_restore_universe_is_idempotent(tmp_path) -> None:
    source = duckdb.connect()
    bootstrap_universe(source, fixture_frame())
    export_universe_parquet(source, tmp_path)
    source.close()

    fresh = duckdb.connect()
    restore_universe_from_parquet(fresh, tmp_path / "universe.parquet")
    restore_universe_from_parquet(fresh, tmp_path / "universe.parquet")
    assert fresh.execute("SELECT count(*) FROM companies").fetchone()[0] == 8


# --------------------------------------------------------------------- prune


def test_prune_raw_keeps_only_newest_per_key(tmp_path) -> None:
    frame = pd.DataFrame({"period": ["2025"], "TotalRevenue": [100.0]})
    for fetched_at in (1_000.0, 2_000.0, 3_000.0):
        write_raw_statement(
            tmp_path, symbol="AIR.PA", provider="yfinance",
            statement_type="income", freq="annual", frame=frame, fetched_at=fetched_at,
        )
    write_raw_statement(
        tmp_path, symbol="AIR.PA", provider="yfinance",
        statement_type="prices", freq="daily", frame=frame, fetched_at=1_500.0,
    )
    before = latest_raw_frames(tmp_path, "AIR.PA")

    deleted = prune_raw(tmp_path)

    assert deleted == 2  # the two older income-annual versions
    remaining = sorted(p.name for p in tmp_path.glob("raw/provider=*/symbol=*/*.parquet"))
    assert len(remaining) == 2
    after = latest_raw_frames(tmp_path, "AIR.PA")
    assert set(before) == set(after)
    for key in before:
        pd.testing.assert_frame_equal(
            before[key].reset_index(drop=True), after[key].reset_index(drop=True)
        )


def test_prune_raw_empty_data_dir_is_a_noop(tmp_path) -> None:
    assert prune_raw(tmp_path) == 0


# ------------------------------------------------------------------- refresh


@pytest.fixture()
def refresh_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CRIBLE_BOOTSTRAP_SAMPLE", "AIR.PA,SAP.DE")
    return tmp_path


def test_run_refresh_crawls_computes_and_publishes(refresh_env) -> None:
    provider = FakeYfProvider()
    result = run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=provider,
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
    )

    assert result["universe_loaded"] == 8
    assert result["universe_restored"] is False
    assert result["fetched"] == 8  # the whole fixture universe fits the budget
    assert result["snapshot_rows"] > 0
    # sample symbols were crawled first (priority -1 front-loading)
    assert set(provider.calls[:2]) == {"AIR.PA", "SAP.DE"}
    assert (refresh_env / "universe.parquet").exists()
    assert (refresh_env / "snapshot" / "snapshot.parquet").exists()
    heartbeat = json.loads((refresh_env / "status.json").read_text())
    assert heartbeat["last_refresh"]["fetched"] == 8


def test_run_refresh_falls_back_to_last_good_universe(refresh_env) -> None:
    # a previous successful run left a universe.parquet behind
    seed = duckdb.connect()
    bootstrap_universe(seed, fixture_frame())
    export_universe_parquet(seed, refresh_env)
    seed.close()

    def failing_fetch():
        raise UniverseSourceError("FinanceDatabase download failed: offline")

    result = run_refresh(
        deadline_seconds=60,
        fetch_universe=failing_fetch,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
    )

    assert result["universe_restored"] is True
    assert result["universe_loaded"] == 8
    assert result["fetched"] == 8
    assert result["snapshot_rows"] > 0


def test_run_refresh_without_universe_source_or_last_good_fails(refresh_env) -> None:
    def failing_fetch():
        raise UniverseSourceError("FinanceDatabase download failed: offline")

    with pytest.raises(UniverseSourceError):
        run_refresh(
            deadline_seconds=60,
            fetch_universe=failing_fetch,
            provider=FakeYfProvider(),
            price_provider=FakePriceProvider(),
        )


def test_run_refresh_prunes_raw_versions(refresh_env) -> None:
    provider = FakeYfProvider()
    run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=provider,
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
    )
    # a nightly Actions run starts from a fresh operational DB (only the raw
    # parquet layer is restored from the demo-data branch) → full re-crawl
    (refresh_env / "crible.duckdb").unlink()
    result = run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=provider,
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
    )
    assert result["pruned"] >= 8  # older income versions for the 8 re-crawled symbols
    # after pruning: at most one file per (provider, symbol, statement, freq)
    for directory in refresh_env.glob("raw/provider=*/symbol=*"):
        keys = ["-".join(p.stem.split("-", 2)[:2]) for p in directory.glob("*.parquet")]
        assert len(keys) == len(set(keys)), directory
