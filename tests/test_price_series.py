"""The published OHLCV series (ADR-0007): normalization, per-symbol source
resolution (whole series wins — adjustment bases never mix), window trim, and
the symbol-sorted, size-bounded shard export with its manifest block."""

from __future__ import annotations

import pandas as pd
import pytest

from crible.ingest.raw import write_raw_statement
from crible.price_series import (
    ShardSizeError,
    export_price_shards,
    load_all_series,
    load_symbol_series,
    normalize_yf_bars,
    write_series,
)


def yf_frame(days: int, start: str = "2026-01-05", tz: str = "Europe/Paris") -> pd.DataFrame:
    dates = pd.date_range(start, periods=days, freq="D", tz=tz)
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": [100.0 + i for i in range(days)],
            "High": [101.0 + i for i in range(days)],
            "Low": [99.0 + i for i in range(days)],
            "Close": [100.5 + i for i in range(days)],
            "Adj Close": [100.4 + i for i in range(days)],
            "Volume": [1000 + i for i in range(days)],
            "Dividends": [0.0] * days,
            "Stock Splits": [0.0] * days,
        }
    )


def store_frame(symbol: str, days: int, start: str, close0: float = 50.0) -> pd.DataFrame:
    dates = pd.date_range(start, periods=days, freq="D")
    return pd.DataFrame(
        {
            "symbol": symbol,
            "date": dates,
            "open": close0,
            "high": close0 + 1,
            "low": close0 - 1,
            "close": [close0 + i for i in range(days)],
            "adj_close": float("nan"),
            "volume": 500.0,
            "source": "stooq",
        }
    )


def write_yf_bars(data_dir, symbol: str, frame: pd.DataFrame, fetched_at: float = 1_000.0) -> None:
    write_raw_statement(
        data_dir, symbol=symbol, provider="yfinance", statement_type="prices",
        freq="daily", frame=frame, fetched_at=fetched_at,
    )


def test_normalize_keeps_the_exchange_local_date() -> None:
    """A Paris midnight bar is 23:00 UTC the day BEFORE — the local calendar
    date must survive normalization, not the UTC one."""
    bars = yf_frame(days=1, start="2026-03-02", tz="Europe/Paris")
    out = normalize_yf_bars(bars, "ML.PA")
    assert str(out["date"].iloc[0])[:10] == "2026-03-02"


def test_normalize_maps_columns_to_the_lean_schema() -> None:
    out = normalize_yf_bars(yf_frame(days=2), "ML.PA")
    assert list(out.columns) == [
        "symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "source",
    ]
    assert out["adj_close"].iloc[0] == 100.4  # "Adj Close" → adj_close
    assert (out["source"] == "yfinance").all()


def test_resolution_never_mixes_sources_per_symbol(tmp_path) -> None:
    # yfinance ends 2026-01-14; the stooq store ends LATER → stooq wins whole
    write_yf_bars(tmp_path, "BMW.DE", yf_frame(days=10, start="2026-01-05"))
    write_series(tmp_path, "stooq", store_frame("BMW.DE", days=10, start="2026-02-01"))

    series = load_symbol_series(tmp_path, "BMW.DE")
    assert set(series["source"]) == {"stooq"}
    assert len(series) == 10
    assert series["adj_close"].isna().all()  # stooq has no adjusted close


def test_resolution_prefers_the_crawled_bars_on_a_tie(tmp_path) -> None:
    write_yf_bars(tmp_path, "BMW.DE", yf_frame(days=10, start="2026-02-01"))
    write_series(tmp_path, "stooq", store_frame("BMW.DE", days=10, start="2026-02-01"))

    series = load_symbol_series(tmp_path, "BMW.DE")
    assert set(series["source"]) == {"yfinance"}


def test_window_trims_to_the_last_400_days(tmp_path) -> None:
    write_yf_bars(tmp_path, "AAPL", yf_frame(days=500, start="2025-01-01"))
    series = load_symbol_series(tmp_path, "AAPL")
    assert len(series) == 400
    assert series["date"].max() - series["date"].min() < pd.Timedelta(days=400)


def test_export_packs_whole_symbols_into_sorted_disjoint_shards(tmp_path, tmp_path_factory) -> None:
    for symbol in ("AAPL", "BMW.DE", "ML.PA"):
        write_yf_bars(tmp_path, symbol, yf_frame(days=10))
    out = tmp_path_factory.mktemp("site")

    block = export_price_shards(tmp_path, out, max_rows_per_shard=12)
    assert [s["file"] for s in block["shards"]] == [
        "prices-00.parquet", "prices-01.parquet", "prices-02.parquet",
    ]
    assert block["symbols"] == 3 and block["bars"] == 30 and block["window_days"] == 400
    # whole symbols per shard, symbol-sorted and disjoint
    seen: list[str] = []
    for shard in block["shards"]:
        table = pd.read_parquet(out / shard["file"])
        symbols = sorted(table["symbol"].unique())
        assert symbols[0] == shard["min_symbol"] and symbols[-1] == shard["max_symbol"]
        assert shard["rows"] == len(table) == 10
        seen.extend(symbols)
    assert seen == sorted(seen) == ["AAPL", "BMW.DE", "ML.PA"]


def test_export_returns_none_and_sweeps_stale_shards_when_no_series(tmp_path, tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("site")
    (out / "prices-00.parquet").write_bytes(b"stale")
    assert export_price_shards(tmp_path, out) is None
    assert not list(out.glob("prices-*.parquet"))


def test_export_refuses_a_shard_past_the_git_wall(tmp_path, tmp_path_factory, monkeypatch) -> None:
    monkeypatch.setattr("crible.price_series.MAX_SHARD_BYTES", 10)
    write_yf_bars(tmp_path, "AAPL", yf_frame(days=10))
    with pytest.raises(ShardSizeError, match="100 MB"):
        export_price_shards(tmp_path, tmp_path_factory.mktemp("site"))


def test_load_all_series_resolves_every_symbol(tmp_path) -> None:
    write_yf_bars(tmp_path, "AAPL", yf_frame(days=5))
    write_series(tmp_path, "stooq", store_frame("BMW.DE", days=5, start="2026-01-05"))
    series = load_all_series(tmp_path)
    assert sorted(series["symbol"].unique()) == ["AAPL", "BMW.DE"]
