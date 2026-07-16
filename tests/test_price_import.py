"""import-prices — dump imports (no API): HuggingFace parquet shards and
Stooq bulk archives yield the windowed OHLCV series (data/prices/<source>.parquet,
published — ADR-0007) plus ONE derived row per symbol (close, as-of,
return_6m) in prices-latest.parquet; the snapshot falls back to the latter
when the crawl has no bars."""

from __future__ import annotations

import zipfile

import pandas as pd
from typer.testing import CliRunner

from crible.cli import app
from crible.compute.snapshot import build_snapshot
from crible.ingest.price_import import (
    import_huggingface,
    import_stooq,
    load_prices_latest,
    map_stooq_symbol,
)
from crible.ingest.raw import write_raw_statement

runner = CliRunner()


def _universe(tmp_path, symbols=("AAPL", "BMW.DE")) -> None:
    pd.DataFrame({"symbol": list(symbols)}).to_parquet(tmp_path / "universe.parquet", index=False)


def _shard(tmp_path, name="shard.parquet") -> str:
    """Two symbols with >182 days of history, one unknown to the universe."""
    rows = []
    for symbol, base in (("AAPL", 100.0), ("ZZUNKNOWN", 5.0)):
        for month in range(1, 13):
            rows.append(
                {"symbol": symbol, "date": f"2026-{month:02d}-01",
                 "open": base, "high": base, "low": base,
                 "close": base + month, "volume": 1000, "adj_close": base + month}
            )
    path = tmp_path / name
    pd.DataFrame(rows).to_parquet(path, index=False)
    return str(path)


def test_huggingface_import_distils_known_symbols(tmp_path) -> None:
    _universe(tmp_path)
    report = import_huggingface(tmp_path, shards=[_shard(tmp_path)])
    assert report.imported == 1 and report.skipped_unknown == 1

    table = load_prices_latest(tmp_path).set_index("symbol")
    row = table.loc["AAPL"]
    assert row["close"] == 112.0  # December close (100 + 12)
    assert row["price_asof"] == "2026-12-01"
    # base = last close at or before 2026-12-01 − 182d (June 1st) → 106
    assert round(row["return_6m"], 6) == round(112.0 / 106.0 - 1.0, 6)
    assert row["source"] == "huggingface"


def test_huggingface_import_persists_the_series_store(tmp_path) -> None:
    """The windowed OHLCV series lands in data/prices/ (ADR-0007), filtered
    to the universe like the distillate."""
    _universe(tmp_path)
    import_huggingface(tmp_path, shards=[_shard(tmp_path)])

    series = pd.read_parquet(tmp_path / "prices" / "huggingface.parquet")
    assert set(series["symbol"]) == {"AAPL"}  # ZZUNKNOWN dropped
    assert list(series.columns) == [
        "symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "source",
    ]
    assert (series["source"] == "huggingface").all()
    assert series["close"].notna().all()


def test_stooq_maps_hong_kong_with_zero_padding() -> None:
    # Stooq drops leading zeros ('700.hk'); the universe keeps them ('0700.HK')
    assert map_stooq_symbol("data/daily/hk/hkex stocks/7/700.hk.txt") == "0700.HK"
    assert map_stooq_symbol("1.hk.txt") == "0001.HK"
    assert map_stooq_symbol("9988.hk.txt") == "9988.HK"  # already 4 digits


def test_stooq_import_maps_exchange_suffixes(tmp_path) -> None:
    assert map_stooq_symbol("data/us/aapl.us.txt") == "AAPL"
    assert map_stooq_symbol("bmw.de.txt") == "BMW.DE"
    assert map_stooq_symbol("weird.xx.txt") is None

    _universe(tmp_path)
    body = "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>,<OPENINT>\n"
    body += "".join(
        f"BMW.DE,D,2026{month:02d}01,000000,50,51,49,{50 + month},1000,0\n"
        for month in range(1, 13)
    )
    archive = tmp_path / "d_de_txt.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("data/daily/de/bmw.de.txt", body)
        bundle.writestr("data/daily/de/weird.xx.txt", body)

    report = import_stooq(tmp_path, archive)
    assert report.imported == 1
    table = load_prices_latest(tmp_path).set_index("symbol")
    assert table.loc["BMW.DE", "close"] == 62.0
    assert table.loc["BMW.DE", "source"] == "stooq"

    # the series store: OHLCV kept, adj_close NULL (Stooq is pre-adjusted)
    series = pd.read_parquet(tmp_path / "prices" / "stooq.parquet")
    assert set(series["symbol"]) == {"BMW.DE"}
    assert series["adj_close"].isna().all()
    assert series["open"].notna().all() and series["volume"].notna().all()


def test_merge_keeps_the_newest_asof_per_symbol(tmp_path) -> None:
    _universe(tmp_path)
    import_huggingface(tmp_path, shards=[_shard(tmp_path)])  # asof 2026-12-01

    stale = tmp_path / "stale.parquet"
    pd.DataFrame(
        [{"symbol": "AAPL", "date": "2025-01-01", "open": 1, "high": 1, "low": 1,
          "close": 1.0, "volume": 1, "adj_close": 1.0}]
    ).to_parquet(stale, index=False)
    import_huggingface(tmp_path, shards=[str(stale)])  # older asof — must lose

    table = load_prices_latest(tmp_path).set_index("symbol")
    assert len(table) == 1
    assert table.loc["AAPL", "close"] == 112.0


def test_snapshot_falls_back_to_the_distilled_quote(tmp_path) -> None:
    """An EDGAR-only issuer (no crawled bars) gets valuation + momentum from
    the imported dump — price_asof carries the staleness honestly."""
    _universe(tmp_path)
    import_huggingface(tmp_path, shards=[_shard(tmp_path)])
    frame = pd.DataFrame(
        {"period": ["2025-12-31"], "TotalRevenue": [400.0], "NetIncome": [56.0],
         "BasicAverageShares": [10.0]}
    )
    write_raw_statement(
        tmp_path, symbol="AAPL", provider="edgar", statement_type="income",
        freq="annual", frame=frame, fetched_at=1_000.0,
    )
    snapshot = build_snapshot(tmp_path, symbols=["AAPL"]).set_index("period")
    row = snapshot.loc["2025-12-31"]
    assert row["price_asof"] == "2026-12-01"
    assert row["market_cap"] == 1120.0  # 112 × 10 shares
    assert round(row["price_to_earnings_ratio"], 4) == round(1120.0 / 56.0, 4)
    assert round(row["return_6m"], 6) == round(112.0 / 106.0 - 1.0, 6)


def test_import_prices_cli_age_gate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    _universe(tmp_path)
    shard = _shard(tmp_path)
    monkeypatch.setattr("crible.ingest.price_import.HF_SHARDS", [shard])

    first = runner.invoke(app, ["import-prices", "huggingface"])
    assert first.exit_code == 0, first.output
    assert "imported 1 symbols" in first.output

    again = runner.invoke(app, ["import-prices", "huggingface", "--max-age-days", "6"])
    assert again.exit_code == 0
    assert "nothing to do" in again.output


def test_age_gate_is_per_source(tmp_path) -> None:
    """A fresh import from ONE dump must not age-gate the others."""
    from crible.ingest.price_import import latest_import_age_days

    _universe(tmp_path)
    import_huggingface(tmp_path, shards=[_shard(tmp_path)])

    assert latest_import_age_days(tmp_path, "huggingface") is not None
    assert latest_import_age_days(tmp_path, "stooq") is None  # never imported
    assert latest_import_age_days(tmp_path) is not None  # global view unchanged


def test_import_prices_cli_missing_archive_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    result = runner.invoke(app, ["import-prices", str(tmp_path / "nope.zip")])
    assert result.exit_code == 1
    assert "stooq.com/db/h" in result.output
