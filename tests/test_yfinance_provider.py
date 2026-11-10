"""The crawl's yfinance provider: statements tagged with the currency they
are reported in, best effort."""

from __future__ import annotations

import pandas as pd
import pytest

from crible.providers.yfinance_provider import YFinanceProvider


class _Ticker:
    def __init__(self, info=None, info_error: Exception | None = None) -> None:
        self._info = info
        self._error = info_error

    def _frame(self, freq="yearly"):
        return pd.DataFrame({pd.Timestamp("2025-12-31"): [100.0]}, index=["TotalRevenue"])

    get_income_stmt = get_balance_sheet = get_cash_flow = _frame

    def history(self, period="1y", auto_adjust=False):
        return pd.DataFrame({"Close": [6810.0]}, index=pd.Index([pd.Timestamp("2026-10-09")], name="Date"))

    def get_info(self):
        if self._error:
            raise self._error
        return self._info


def test_statements_carry_the_financial_currency(monkeypatch) -> None:
    import yfinance

    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: _Ticker(info={"financialCurrency": "USD"}))
    result = YFinanceProvider().fetch_statements("BREN.JK")
    assert result.statements
    assert all(set(p.frame["_currency"]) == {"USD"} for p in result.statements)


def test_an_unavailable_profile_never_fails_the_fetch(monkeypatch) -> None:
    import yfinance

    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: _Ticker(info_error=RuntimeError("401 crumb")))
    result = YFinanceProvider().fetch_statements("X")
    assert result.statements and all("_currency" not in p.frame.columns for p in result.statements)


def test_the_snapshot_converts_with_the_crawled_currency(tmp_path) -> None:
    """BREN.JK: statements in USD, quote in IDR — the P/E was ~2.7 million."""
    from crible.compute.snapshot import build_snapshot
    from crible.ingest.raw import write_raw_statement

    pd.DataFrame({"symbol": ["BREN.JK"], "currency": ["IDR"]}).to_parquet(tmp_path / "universe.parquet")
    (tmp_path / "mirror" / "fx").mkdir(parents=True)
    (tmp_path / "mirror" / "fx" / "rates.json").write_text('{"rates": {"USD": 1.1, "IDR": 18000.0}}')
    frames = {
        "income": {"TotalRevenue": [1000.0], "NetIncome": [100.0], "BasicAverageShares": [100.0]},
        "balance": {"StockholdersEquity": [500.0], "TotalAssets": [900.0]},
    }
    for stmt, values in frames.items():
        write_raw_statement(
            tmp_path,
            symbol="BREN.JK",
            provider="yfinance",
            statement_type=stmt,
            freq="annual",
            frame=pd.DataFrame({"period": ["2025-12-31"], **values, "_currency": "USD"}),
            fetched_at=1.0,
        )
    write_raw_statement(
        tmp_path,
        symbol="BREN.JK",
        provider="yfinance",
        statement_type="prices",
        freq="daily",
        frame=pd.DataFrame({"Date": ["2026-10-09"], "Close": [16364.0]}),
        fetched_at=1.0,
    )
    row = build_snapshot(tmp_path).iloc[-1]
    assert row["reporting_currency"] == "USD"
    # 16364 IDR ≈ 1.0 USD; EPS 1.0 USD → P/E ≈ 1, not 16 364
    assert abs(row["price_to_earnings_ratio"] - 16364.0 / 18000.0 * 1.1) < 1e-6


def test_bars_carry_the_quote_currency(monkeypatch) -> None:
    import yfinance

    info = {"financialCurrency": "EUR", "currency": "GBp"}
    monkeypatch.setattr(yfinance, "Ticker", lambda symbol: _Ticker(info=info))
    result = YFinanceProvider().fetch_statements("CCEP.L")
    assert set(result.prices["_quote_currency"]) == {"GBp"}


def test_the_crawled_quote_currency_beats_the_listed_one(tmp_path) -> None:
    """CCEP.L: listed EUR (the currency it reports in), trades in pence —
    a 3.5 T market cap and a P/E of 1,815."""
    from crible.compute.snapshot import build_snapshot
    from crible.ingest.raw import write_raw_statement

    pd.DataFrame({"symbol": ["CCEP.L"], "currency": ["EUR"]}).to_parquet(tmp_path / "universe.parquet")
    (tmp_path / "mirror" / "fx").mkdir(parents=True)
    (tmp_path / "mirror" / "fx" / "rates.json").write_text('{"rates": {"GBP": 0.85}}')
    frames = {
        "income": {"TotalRevenue": [20e9], "NetIncome": [1.7e9], "BasicAverageShares": [456e6]},
        "balance": {"StockholdersEquity": [8e9], "TotalAssets": [30e9]},
    }
    for stmt, values in frames.items():
        write_raw_statement(
            tmp_path,
            symbol="CCEP.L",
            provider="yfinance",
            statement_type=stmt,
            freq="annual",
            frame=pd.DataFrame({"period": ["2025-12-31"], **values, "_currency": "EUR"}),
            fetched_at=1.0,
        )
    write_raw_statement(
        tmp_path,
        symbol="CCEP.L",
        provider="yfinance",
        statement_type="prices",
        freq="daily",
        frame=pd.DataFrame({"Date": ["2026-10-09"], "Close": [6810.0], "_quote_currency": ["GBp"]}),
        fetched_at=1.0,
    )
    row = build_snapshot(tmp_path).iloc[-1]
    # 6810p = £68.10 = €80.12; × 456 M shares
    assert row["market_cap"] == pytest.approx(68.10 / 0.85 * 456e6)


class _Failing(_Ticker):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self._raise = error

    def _frame(self, freq="yearly"):
        raise self._raise

    get_income_stmt = get_balance_sheet = get_cash_flow = _frame

    def history(self, period="1y", auto_adjust=False):
        raise self._raise


@pytest.mark.parametrize("symbol", ["4290.T", "1429.HK", "600429.SS"])
def test_a_symbol_holding_429_is_not_a_rate_limit(monkeypatch, symbol) -> None:
    """An error that merely names the ticker (4290.T: possibly delisted) was
    classified as a 429: six backed-off retries (~45 min) per such symbol, and
    three in a row tripped the breaker."""
    import yfinance

    from crible.ingest.service import _YfPriceAdapter
    from crible.providers.base import RateLimitedError

    delisted = RuntimeError(f"${symbol}: possibly delisted; no price data found")
    monkeypatch.setattr(yfinance, "Ticker", lambda s: _Failing(delisted))
    with pytest.raises(RuntimeError) as crawl:
        YFinanceProvider().fetch_statements(symbol)
    assert not isinstance(crawl.value, RateLimitedError)
    with pytest.raises(RuntimeError) as refresh:
        _YfPriceAdapter().fetch_prices(symbol)
    assert not isinstance(refresh.value, RateLimitedError)

    throttled = RuntimeError(f"429 Client Error: Too Many Requests for url: …/chart/{symbol}")
    monkeypatch.setattr(yfinance, "Ticker", lambda s: _Failing(throttled))
    with pytest.raises(RateLimitedError):
        YFinanceProvider().fetch_statements(symbol)
    with pytest.raises(RateLimitedError):
        _YfPriceAdapter().fetch_prices(symbol)


def test_a_price_refresh_keeps_the_crawled_quote_currency(tmp_path) -> None:
    """The daily refresh fetches bars only (one request, no profile): its
    newer file used to drop the GBp the crawl had recorded, and the snapshot
    — which reads the newest bars — priced CCEP.L in its listed EUR again."""
    from crible.compute.snapshot import build_snapshot
    from crible.ingest.budget import TokenBucket
    from crible.ingest.prices import PriceRefresher
    from crible.ingest.raw import write_raw_statement

    pd.DataFrame({"symbol": ["CCEP.L"], "currency": ["EUR"]}).to_parquet(tmp_path / "universe.parquet")
    (tmp_path / "mirror" / "fx").mkdir(parents=True)
    (tmp_path / "mirror" / "fx" / "rates.json").write_text('{"rates": {"GBP": 0.85}}')
    frames = {
        "income": {"TotalRevenue": [20e9], "NetIncome": [1.7e9], "BasicAverageShares": [456e6]},
        "balance": {"StockholdersEquity": [8e9], "TotalAssets": [30e9]},
    }
    for stmt, values in frames.items():
        write_raw_statement(
            tmp_path,
            symbol="CCEP.L",
            provider="yfinance",
            statement_type=stmt,
            freq="annual",
            frame=pd.DataFrame({"period": ["2025-12-31"], **values, "_currency": "EUR"}),
            fetched_at=1.0,
        )
    write_raw_statement(
        tmp_path,
        symbol="CCEP.L",
        provider="yfinance",
        statement_type="prices",
        freq="daily",
        frame=pd.DataFrame({"Date": ["2026-10-09"], "Close": [6700.0], "_quote_currency": ["GBp"]}),
        fetched_at=1.0,
    )

    class BarsOnly:
        id = "yfinance"

        def fetch_prices(self, symbol):
            return pd.DataFrame({"Date": ["2026-10-12"], "Close": [6810.0]})

    outcome = PriceRefresher(
        provider=BarsOnly(), budget=TokenBucket(capacity=10), data_dir=tmp_path, now=lambda: 2.0
    ).refresh(["CCEP.L", "NEW.L"])
    assert outcome.refreshed == ["CCEP.L", "NEW.L"]  # nothing to carry for NEW.L: still written
    row = build_snapshot(tmp_path, ["CCEP.L"]).iloc[-1]
    assert row["price_asof"] == "2026-10-12"
    assert row["market_cap"] == pytest.approx(68.10 / 0.85 * 456e6)
