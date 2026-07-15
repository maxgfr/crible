"""compute.momentum — the ONE trailing-return/momentum rule.

Hand-computed vectors (calendar-daily linear closes make every base exact)
plus the parity golden the TODO asked for: the three historical call paths
(ranks.price_return, price_import._distill, the HuggingFace import) must
agree to 1e-12 on the same series.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from crible.compute.momentum import momentum_features, trailing_return


def daily_bars(n: int = 400, start: str = "2025-06-01", base: float = 100.0, step: float = 0.5) -> pd.DataFrame:
    dates = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"date": dates, "close": [base + i * step for i in range(n)]})


def test_momentum_features_hand_computed_vectors() -> None:
    n, base, step = 400, 100.0, 0.5
    feats = momentum_features(daily_bars(n)["date"], daily_bars(n)["close"])

    close = base + (n - 1) * step
    assert feats["close"] == close
    # calendar-daily bars: the base k days back is exactly (n−1−k) steps up
    assert feats["return_6m"] == pytest.approx(close / (base + (n - 1 - 182) * step) - 1)
    recent = base + (n - 1 - 30) * step
    base_12m = base + (n - 1 - 365) * step
    assert feats["return_12_1"] == pytest.approx(recent / base_12m - 1)
    # a rising series sits AT its 52-week high
    assert feats["high_52w_proximity"] == pytest.approx(1.0)
    assert feats["volatility_1y"] > 0 and math.isfinite(feats["volatility_1y"])


def test_momentum_features_short_history_is_nan_never_extrapolated() -> None:
    bars = daily_bars(100)  # reaches neither the 182d nor the 365d base
    feats = momentum_features(bars["date"], bars["close"])
    assert pd.isna(feats["return_6m"])
    assert pd.isna(feats["return_12_1"])
    assert pd.isna(feats["volatility_1y"])  # same full-year reach rule
    assert feats["high_52w_proximity"] == pytest.approx(1.0)  # high of what exists


def test_momentum_features_declining_series_sits_below_its_high() -> None:
    bars = daily_bars(400, step=-0.1, base=200.0)
    feats = momentum_features(bars["date"], bars["close"])
    assert feats["high_52w_proximity"] < 1.0
    assert feats["return_12_1"] < 0


def test_momentum_features_flat_series_has_zero_volatility() -> None:
    bars = daily_bars(400, step=0.0)
    feats = momentum_features(bars["date"], bars["close"])
    assert feats["volatility_1y"] == pytest.approx(0.0)
    assert feats["return_6m"] == pytest.approx(0.0)


def test_trailing_return_matches_features() -> None:
    bars = daily_bars(400)
    feats = momentum_features(bars["date"], bars["close"])
    assert trailing_return(bars["date"], bars["close"], 182) == pytest.approx(
        feats["return_6m"], abs=1e-12
    )


def test_parity_across_the_three_historical_paths(tmp_path) -> None:
    """The golden the TODO asked for: crawl path (ranks.price_return), Stooq
    distillate (_distill) and the HuggingFace import produce the SAME
    return_6m for one series — the rule lives in one place now."""
    from crible.compute.ranks import price_return
    from crible.ingest.price_import import _distill, import_huggingface, load_prices_latest

    # end the series today so the HF import's 400-day window keeps every bar
    end = pd.Timestamp.today().normalize()
    dates = pd.date_range(end=end, periods=397, freq="D")
    closes = [100.0 + i * 0.5 for i in range(len(dates))]
    bars = pd.DataFrame({"date": dates, "close": closes})

    via_ranks = price_return(bars.rename(columns={"date": "Date", "close": "Close"}))
    via_distill = _distill(bars.assign(date=bars["date"].astype(str)))["return_6m"]

    pd.DataFrame({"symbol": ["AAPL"]}).to_parquet(tmp_path / "universe.parquet", index=False)
    shard = tmp_path / "shard.parquet"
    pd.DataFrame(
        {
            "symbol": "AAPL", "date": dates.astype(str),
            "open": closes, "high": closes, "low": closes,
            "close": closes, "adj_close": closes, "volume": 1000,
        }
    ).to_parquet(shard, index=False)
    import_huggingface(tmp_path, shards=[str(shard)])
    via_hf = float(load_prices_latest(tmp_path).set_index("symbol").loc["AAPL", "return_6m"])

    assert via_ranks == pytest.approx(via_distill, abs=1e-12)
    assert via_ranks == pytest.approx(via_hf, abs=1e-12)
    # the new features ride the same distillate row
    row = load_prices_latest(tmp_path).set_index("symbol").loc["AAPL"]
    assert row["high_52w_proximity"] == pytest.approx(1.0)
    assert not pd.isna(row["return_12_1"]) and not pd.isna(row["volatility_1y"])
