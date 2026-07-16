"""defeatbeta yahoo-finance-data dump — series + distillate from one HF
parquet per table. Yahoo-derived, assumed-risk tier: additional + fallback
only (audited precedence and crawled-bars priority are asserted here)."""

from __future__ import annotations

import pandas as pd
from typer.testing import CliRunner

from crible.cli import app
from crible.ingest.defeatbeta import import_defeatbeta
from crible.ingest.price_import import load_prices_latest
from crible.price_series import _resolve

runner = CliRunner()


def _universe(tmp_path, symbols=("AAPL", "BRK-B")) -> None:
    pd.DataFrame({"symbol": list(symbols)}).to_parquet(tmp_path / "universe.parquet", index=False)


def _prices_table(tmp_path, name="stock_prices.parquet") -> str:
    """defeatbeta's exact schema: report_date is an ISO STRING, no adj_close;
    two symbols with >182 days of history, one unknown to the universe."""
    rows = []
    for symbol, base in (("AAPL", 100.0), ("ZZUNKNOWN", 5.0)):
        for month in range(1, 13):
            rows.append(
                {"symbol": symbol, "report_date": f"2026-{month:02d}-01",
                 "open": base, "close": base + month, "high": base, "low": base,
                 "volume": 1000}
            )
    path = tmp_path / name
    pd.DataFrame(rows).to_parquet(path, index=False)
    return str(path)


def _tables(tmp_path) -> dict[str, str]:
    return {"prices": _prices_table(tmp_path)}


def test_defeatbeta_import_distils_known_symbols(tmp_path) -> None:
    _universe(tmp_path)
    report = import_defeatbeta(tmp_path, tables=_tables(tmp_path))
    assert report.imported == 1 and report.skipped_unknown == 1

    table = load_prices_latest(tmp_path).set_index("symbol")
    row = table.loc["AAPL"]
    assert row["close"] == 112.0  # December close (100 + 12)
    assert row["price_asof"] == "2026-12-01"
    assert round(row["return_6m"], 6) == round(112.0 / 106.0 - 1.0, 6)
    assert row["source"] == "defeatbeta"


def test_defeatbeta_import_persists_the_series_store(tmp_path) -> None:
    """Windowed OHLCV in data/prices/defeatbeta.parquet — universe-filtered,
    adj_close NULL (defeatbeta bars are split-adjusted only, the Stooq rule)."""
    _universe(tmp_path)
    import_defeatbeta(tmp_path, tables=_tables(tmp_path))

    series = pd.read_parquet(tmp_path / "prices" / "defeatbeta.parquet")
    assert set(series["symbol"]) == {"AAPL"}
    assert list(series.columns) == [
        "symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "source",
    ]
    assert (series["source"] == "defeatbeta").all()
    assert series["adj_close"].isna().all()
    assert series["close"].notna().all() and series["volume"].notna().all()


def test_defeatbeta_loses_price_ties_to_the_crawl_but_beats_the_dumps() -> None:
    """Crawled yfinance bars stay canonical on equal dates; among dumps the
    ~weekly defeatbeta outranks the ~monthly huggingface rotation."""
    def bars(source):
        return pd.DataFrame(
            {"symbol": "AAPL", "date": ["2026-07-01"], "open": 1.0, "high": 1.0,
             "low": 1.0, "close": 1.0, "adj_close": float("nan"), "volume": 1.0,
             "source": source}
        )

    against_crawl = _resolve(pd.concat([bars("yfinance"), bars("defeatbeta")]), 400)
    assert set(against_crawl["source"]) == {"yfinance"}

    against_dump = _resolve(pd.concat([bars("huggingface"), bars("defeatbeta")]), 400)
    assert set(against_dump["source"]) == {"defeatbeta"}


def test_import_prices_cli_dispatches_defeatbeta(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    _universe(tmp_path)
    monkeypatch.setattr("crible.ingest.defeatbeta.DB_TABLES", _tables(tmp_path))

    result = runner.invoke(app, ["import-prices", "defeatbeta"])
    assert result.exit_code == 0, result.output
    assert "imported 1 symbols from defeatbeta" in result.output

    # the heartbeat records the import; the per-source age gate holds
    import json

    status = json.loads((tmp_path / "status.json").read_text())
    assert status["imports"]["defeatbeta"]["symbols"] == 1

    again = runner.invoke(app, ["import-prices", "defeatbeta", "--max-age-days", "6"])
    assert "nothing to do" in again.output


def test_defeatbeta_gate_ignores_other_dumps(tmp_path, monkeypatch) -> None:
    """A fresh huggingface import must NOT age-gate the defeatbeta schedule."""
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    _universe(tmp_path)

    hf_shard = tmp_path / "hf.parquet"
    frame = pd.read_parquet(_prices_table(tmp_path, name="src.parquet"))
    frame.assign(date=frame["report_date"], adj_close=frame["close"]).to_parquet(
        hf_shard, index=False
    )
    monkeypatch.setattr("crible.ingest.price_import.HF_SHARDS", [str(hf_shard)])
    monkeypatch.setattr("crible.ingest.defeatbeta.DB_TABLES", _tables(tmp_path))

    assert runner.invoke(app, ["import-prices", "huggingface"]).exit_code == 0
    result = runner.invoke(app, ["import-prices", "defeatbeta", "--max-age-days", "6"])
    assert result.exit_code == 0, result.output
    assert "imported 1 symbols from defeatbeta" in result.output
