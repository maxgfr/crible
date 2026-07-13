"""FR-011 — price freshness tiering: budget-aware refresh, the 3-consecutive-
failures switch rule, and price_asof provenance in the snapshot."""

from __future__ import annotations

import pandas as pd
import pytest

from crible.compute.snapshot import build_symbol_snapshot
from crible.ingest.budget import TokenBucket
from crible.ingest.prices import PriceRefresher
from crible.providers.base import RateLimitedError

from tests.test_fr003_compute import IMPROVING, income_frame


class FakePriceProvider:
    id = "yfinance"

    def __init__(self, limited: set[str] | None = None) -> None:
        self.limited = limited or set()
        self.calls: list[str] = []

    def fetch_prices(self, symbol: str) -> pd.DataFrame | None:
        self.calls.append(symbol)
        if symbol in self.limited:
            raise RateLimitedError("429")
        return pd.DataFrame({"Date": ["2026-07-04"], "Close": [100.0]})


def test_fr011_priority_symbols_refresh_within_budget(tmp_path) -> None:
    provider = FakePriceProvider()
    refresher = PriceRefresher(
        provider=provider, budget=TokenBucket(capacity=10), data_dir=tmp_path, now=lambda: 1000.0
    )
    outcome = refresher.refresh(["AIR.PA", "SAP.DE", "AAPL"])
    assert outcome.refreshed == ["AIR.PA", "SAP.DE", "AAPL"]
    assert not outcome.aborted
    # raw price bars landed with provenance
    files = list(tmp_path.glob("raw/provider=yfinance/symbol=*/prices-daily-*.parquet"))
    assert len(files) == 3


def test_fr011_three_consecutive_rate_limits_abort_politely(tmp_path) -> None:
    provider = FakePriceProvider(limited={"A", "B", "C"})
    refresher = PriceRefresher(
        provider=provider, budget=TokenBucket(capacity=100), data_dir=tmp_path, now=lambda: 1000.0
    )
    outcome = refresher.refresh(["A", "B", "C", "D", "E"])
    assert outcome.aborted
    assert outcome.refreshed == []
    # D and E were never attempted — the cycle ended politely, nothing busy-looped
    assert provider.calls == ["A", "B", "C"]
    assert set(outcome.skipped) == {"A", "B", "C", "D", "E"}


def test_fr011_budget_exhaustion_skips_instead_of_blocking(tmp_path) -> None:
    provider = FakePriceProvider()
    refresher = PriceRefresher(
        provider=provider, budget=TokenBucket(capacity=1), data_dir=tmp_path, now=lambda: 1000.0
    )
    outcome = refresher.refresh(["AIR.PA", "SAP.DE"])
    assert outcome.refreshed == ["AIR.PA"]
    assert outcome.skipped == ["SAP.DE"]  # leftover-budget rule: skip, never block


def test_fr011_snapshot_exposes_price_asof_and_prices_latest_period_only(tmp_path) -> None:
    frames = {
        (s, "annual"): income_frame(dict(rows), ["2023", "2024", "2025"])
        for s, rows in IMPROVING.items()
    }
    # add share count so price-dependent ratios compute to exact values
    frames[("income", "annual")]["BasicAverageShares"] = [10.0, 10.0, 10.0]
    frames[("prices", "daily")] = pd.DataFrame(
        {"Date": ["2026-07-03", "2026-07-04"], "Close": [95.0, 100.0]}
    )
    snapshot = build_symbol_snapshot("TEST.PA", frames, computed_at=1000.0)
    assert (snapshot["price_asof"] == "2026-07-04").all()
    # exact valuation from the latest close: PE = (100 × 10 shares) / NI 120
    latest = snapshot.iloc[-1]
    assert latest["market_cap"] == 1000.0
    assert latest["price_to_earnings_ratio"] == pytest.approx(1000.0 / 120.0)
    # latest period only — historical prices are never faked
    assert snapshot["price_to_earnings_ratio"].iloc[:-1].isna().all()


def test_fr011_snapshot_without_prices_has_null_price_asof(tmp_path) -> None:
    frames = {(s, "annual"): income_frame(rows, ["2023", "2024", "2025"]) for s, rows in IMPROVING.items()}
    snapshot = build_symbol_snapshot("TEST.PA", frames, computed_at=1000.0)
    assert snapshot["price_asof"].isna().all()


def test_fr011_price_adapter_fetches_a_full_year_for_momentum(monkeypatch) -> None:
    """FR-015 regression: return_6m needs ≥182 days of daily bars — a 5d
    fetch window left the momentum pillar permanently NaN. One year of bars
    still costs exactly one Yahoo request."""
    import sys
    import types

    calls: dict = {}

    class FakeTicker:
        def __init__(self, symbol: str) -> None:
            calls["symbol"] = symbol

        def history(self, period=None, auto_adjust=None):
            calls["period"] = period
            return pd.DataFrame()

    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker))
    from crible.ingest.service import _YfPriceAdapter

    assert _YfPriceAdapter().fetch_prices("AIR.PA") is None  # empty history → None
    assert calls["period"] == "1y"
