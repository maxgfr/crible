"""TradingView scanner — whole-market quote snapshots + the cap census.

Snapshot-only, quote-layer: these tests pin the two load-bearing rules —
a TV quote never clobbers a dump's momentum, and the census keeps the
listings the universe does not know (symbol=NULL)."""

from __future__ import annotations

import pandas as pd
from typer.testing import CliRunner

from crible.cli import app
from crible.ingest.price_import import load_prices_latest
from crible.ingest.tradingview import (
    TradingViewError,
    TradingViewReport,
    import_tradingview,
    map_tv_symbol,
)

runner = CliRunner()


def _universe(tmp_path, rows=None) -> None:
    rows = rows if rows is not None else [
        {"symbol": "AI.PA", "isin": "FR0000120073", "country": "FR"},
        {"symbol": "SAP.DE", "isin": "DE0007164600", "country": "DE"},
        {"symbol": "005930.KS", "isin": "KR7005930003", "country": "KR"},
        {"symbol": "0700.HK", "isin": "KYG875721634", "country": "HK"},
        {"symbol": "ODD.PA", "isin": "FR9999999999", "country": "FR"},
    ]
    pd.DataFrame(rows).to_parquet(tmp_path / "universe.parquet", index=False)


def _row(country, exchange, ticker, *, close=10.0, cap=1e9, isin=None,
         type_="stock", subtype="common", currency="EUR"):
    return {
        "name": ticker, "description": f"{ticker} Corp", "close": close,
        "currency": currency, "market_cap_basic": cap, "volume": 1000.0,
        "exchange": exchange, "type": type_, "subtype": subtype, "isin": isin,
        "tv_symbol": f"{exchange}:{ticker}", "tv_exchange": exchange,
        "tv_ticker": ticker, "country": country,
    }


def test_map_tv_symbol_covers_the_venue_table() -> None:
    assert map_tv_symbol("france", "EURONEXT", "AI") == ("AI.PA",)
    assert map_tv_symbol("germany", "XETR", "SAP") == ("SAP.DE",)
    assert map_tv_symbol("america", "NYSE", "BRK.B") == ("BRK-B",)
    assert map_tv_symbol("sweden", "OMXSTO", "VOLV_B") == ("VOLV-B.ST",)
    assert map_tv_symbol("korea", "KRX", "005930") == ("005930.KS", "005930.KQ")
    assert map_tv_symbol("hongkong", "HKEX", "700") == ("0700.HK",)
    assert map_tv_symbol("germany", "GETTEX", "SAP") == ()  # deliberately unmapped


def test_import_matches_censuses_and_distills(tmp_path) -> None:
    _universe(tmp_path)
    rows = {
        "france": [
            _row("france", "EURONEXT", "AI", close=180.0, cap=1e11, isin="FR0000120073"),
            _row("france", "EURONEXT", "ETF1", type_="fund"),  # response-side re-check
            # unmapped venue but ISIN → exactly one FR universe symbol
            _row("france", "TRADEGATE", "ODD", close=5.0, cap=1e8, isin="FR9999999999"),
            _row("france", "EURONEXT", "ZZZ", close=1.0, cap=1e7, isin="FR0000000000"),
        ],
        "korea": [_row("korea", "KRX", "005930", close=60000.0, cap=4e11, currency="KRW",
                       isin="KR7005930003")],
    }
    report = import_tradingview(tmp_path, countries=("france", "korea"),
                                fetch=lambda c: rows[c], jitter=(0, 0))
    assert isinstance(report, TradingViewReport)
    assert report.countries_ok == 2 and report.countries_failed == ()
    assert report.imported == 3  # AI.PA (ticker), ODD.PA (isin), 005930.KS (candidate)

    census = pd.read_parquet(tmp_path / "caps" / "tradingview.parquet")
    assert len(census) == 4  # the fund row dropped, the unmatched ZZZ kept
    unmatched = census[census["symbol"].isna()]
    assert list(unmatched["tv_symbol"]) == ["EURONEXT:ZZZ"]
    by_symbol = census.dropna(subset=["symbol"]).set_index("symbol")
    assert by_symbol.loc["AI.PA", "match_method"] == "ticker"
    assert by_symbol.loc["ODD.PA", "match_method"] == "isin"
    assert by_symbol.loc["005930.KS", "market_cap"] == 4e11
    assert by_symbol.loc["005930.KS", "currency"] == "KRW"

    table = load_prices_latest(tmp_path).set_index("symbol")
    assert table.loc["AI.PA", "close"] == 180.0
    assert table.loc["AI.PA", "source"] == "tradingview"


def test_quote_survives_but_momentum_stays_with_the_dump(tmp_path, monkeypatch) -> None:
    """End-to-end anti-clobber: defeatbeta first (features), TV after."""
    from crible.ingest.defeatbeta import import_defeatbeta

    _universe(tmp_path, rows=[{"symbol": "AAPL", "isin": None, "country": "US"}])
    bars = [
        {"symbol": "AAPL", "report_date": f"2026-{m:02d}-01", "open": 1.0,
         "close": 100.0 + m, "high": 1.0, "low": 1.0, "volume": 10}
        for m in range(1, 13)
    ]
    prices = tmp_path / "stock_prices.parquet"
    pd.DataFrame(bars).to_parquet(prices, index=False)
    import_defeatbeta(tmp_path, tables={"prices": str(prices)})

    monkeypatch.setattr("crible.ingest.tradingview._price_asof", lambda: "2026-12-31")
    import_tradingview(
        tmp_path, countries=("america",), jitter=(0, 0),
        fetch=lambda c: [_row("america", "NASDAQ", "AAPL", close=250.0, cap=4e12,
                              currency="USD")],
    )
    row = load_prices_latest(tmp_path).set_index("symbol").loc["AAPL"]
    assert row["close"] == 250.0 and row["source"] == "tradingview"
    assert pd.notna(row["return_6m"])  # dump momentum intact
    assert row["momentum_source"] == "defeatbeta"


def test_one_failed_country_is_isolated_all_failed_raises(tmp_path) -> None:
    _universe(tmp_path)

    def flaky(country):
        if country == "france":
            raise RuntimeError("blocked")
        return [_row("germany", "XETR", "SAP", isin="DE0007164600")]

    report = import_tradingview(tmp_path, countries=("france", "germany"),
                                fetch=flaky, jitter=(0, 0))
    assert report.countries_failed == ("france",)
    assert report.imported == 1

    def dead(country):
        raise RuntimeError("blocked")

    try:
        import_tradingview(tmp_path, countries=("france",), fetch=dead, jitter=(0, 0))
        raise AssertionError("expected TradingViewError")
    except TradingViewError:
        pass


def test_cli_dispatch_and_heartbeat(tmp_path, monkeypatch) -> None:
    import json

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    _universe(tmp_path)
    monkeypatch.setattr(
        "crible.ingest.tradingview._default_fetch",
        lambda c: [_row("france", "EURONEXT", "AI", isin="FR0000120073")]
        if c == "france" else [],
    )
    monkeypatch.setattr("crible.ingest.tradingview.TV_COUNTRIES", ("france",))
    monkeypatch.setattr("crible.ingest.tradingview.REQUEST_JITTER_S", (0, 0))

    result = runner.invoke(app, ["import-prices", "tradingview"])
    assert result.exit_code == 0, result.output
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["imports"]["tradingview"]["countries_ok"] == 1
    assert status["imports"]["tradingview"]["symbols"] == 1
