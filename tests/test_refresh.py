"""The bounded nightly refresh behind `crible refresh` (GitHub Actions).

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


def test_run_refresh_max_seconds_reserves_time_for_compute(refresh_env) -> None:
    """--max-minutes semantics: inside the compute reserve the crawl window
    collapses, enrichment stages yield, the price refresh is skipped — but
    prune + compute still run, so the night always publishes something."""
    result = run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
        max_seconds=1.0,  # far below ENRICH_RESERVE_SECONDS
    )
    assert result["fetched"] == 0  # the crawl window was consumed by the reserve
    # the sweep either stopped on budget or self-skipped (no GLEIF mapping here)
    assert result["esef"].get("stopped") == "budget" or result["esef"].get("skipped")
    assert result["prices"] == {"skipped": "time budget"}
    assert "snapshot_rows" in result  # compute always runs


def test_run_refresh_plumbs_esef_history_to_the_sweep(refresh_env, monkeypatch) -> None:
    import crible.ingest.service as service

    recorded: dict = {}

    def fake_sweep(**kwargs):
        recorded.update(kwargs)
        return {"enriched": [], "skipped": "test", "outage": None}

    monkeypatch.setattr(service, "run_esef_sweep", fake_sweep)
    run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
        esef_history=5,
    )
    assert recorded.get("history") == 5


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


def test_run_refresh_wires_the_orphan_audited_cycles(refresh_env) -> None:
    """run_companies_house existed but was never CALLED (the façade
    re-exported it into the void). The nightly now runs it; it degrades to a
    RECORDED skip — no operator CSV — instead of silently not existing.
    Zero network either way."""
    result = run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
        companies_house_url="https://example.invalid/accounts.zip",
    )
    assert "uk-company-numbers" in result["companies_house"]["skipped"]


def test_run_refresh_restores_queue_from_raw_and_advances(refresh_env) -> None:
    """A nightly Actions run starts from a fresh operational DB (only the raw
    parquet layer travels in the published dataset). The queue freshness must
    be rebuilt from the raw filename stamps — otherwise every night re-crawls
    the same head and coverage plateaus instead of advancing."""
    provider = FakeYfProvider()
    first = run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=provider,
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
    )
    assert first["fetched"] == 8
    calls_after_first = len(provider.calls)

    (refresh_env / "crible.duckdb").unlink()
    result = run_refresh(
        deadline_seconds=60,
        fetch_universe=fixture_frame,
        provider=provider,
        price_provider=FakePriceProvider(),
        edgar_client=FakeEdgarDirectory(),
    )
    assert result["queue_restored"] >= 8
    assert result["fetched"] == 0  # everything fresh in raw — nothing re-crawled
    assert len(provider.calls) == calls_after_first
    # the raw layer stays pruned: at most one file per (provider, symbol, statement, freq)
    for directory in refresh_env.glob("raw/provider=*/symbol=*"):
        keys = ["-".join(p.stem.split("-", 2)[:2]) for p in directory.glob("*.parquet")]
        assert len(keys) == len(set(keys)), directory
