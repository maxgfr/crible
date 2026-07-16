"""Price-gap top-up: audited symbols (ESEF/EDGAR fundamentals) that no price
source covers ride the leftover Yahoo budget after the priority sample.

The gap class this closes (diagnosed 2026-07-16): ~1,861 FR listings carry
ESEF audited fundamentals but never get a price — Stooq publishes no French
bulk dump and the 7-requests-per-symbol crawl reaches ~100 symbols/night —
so price_to_earnings_ratio stays NULL for nearly the whole French universe.
"""

from __future__ import annotations

import pandas as pd

from crible.ingest.prices import price_gap_symbols
from crible.ingest.raw import write_raw_statement

INCOME = pd.DataFrame({"period": ["2024", "2025"], "TotalRevenue": [90.0, 100.0]})
BARS = pd.DataFrame({"Date": ["2026-07-10"], "Close": [42.0]})


def _fundamentals(data_dir, symbol: str, provider: str = "esef") -> None:
    write_raw_statement(
        data_dir, symbol=symbol, provider=provider, statement_type="income",
        freq="annual", frame=INCOME, fetched_at=1000.0,
    )


def _raw_prices(data_dir, symbol: str) -> None:
    write_raw_statement(
        data_dir, symbol=symbol, provider="yfinance", statement_type="prices",
        freq="daily", frame=BARS, fetched_at=1000.0,
    )


def test_price_gap_lists_audited_symbols_no_price_source_covers(tmp_path) -> None:
    _fundamentals(tmp_path, "OVH.PA")            # audited, never priced → the gap
    _fundamentals(tmp_path, "AIR.PA", provider="yfinance")
    _raw_prices(tmp_path, "AIR.PA")              # crawl already bars it → covered
    _fundamentals(tmp_path, "COV.PA")
    pd.DataFrame({"symbol": ["COV.PA"], "close": [10.0], "price_asof": ["2026-07-15"]}).to_parquet(
        tmp_path / "prices-latest.parquet"
    )                                            # dump distillate covers it

    assert price_gap_symbols(tmp_path) == ["OVH.PA"]


def test_price_gap_orders_by_universe_crawl_priority_and_caps(tmp_path) -> None:
    for symbol in ("ZZZ.US", "OVH.PA", "MMM.T"):
        _fundamentals(tmp_path, symbol)
    # same ordering contract as the crawl queue: priority ASC, then symbol
    pd.DataFrame(
        {"symbol": ["ZZZ.US", "OVH.PA", "MMM.T"], "crawl_priority": [9, 2, 17]}
    ).to_parquet(tmp_path / "universe.parquet")

    assert price_gap_symbols(tmp_path) == ["OVH.PA", "ZZZ.US", "MMM.T"]
    assert price_gap_symbols(tmp_path, limit=2) == ["OVH.PA", "ZZZ.US"]


class RecordingPriceProvider:
    id = "yfinance"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_prices(self, symbol: str) -> pd.DataFrame | None:
        self.calls.append(symbol)
        return BARS


def test_run_price_refresh_tops_up_the_gap_after_the_sample(tmp_path, monkeypatch) -> None:
    from crible.ingest.budget import TokenBucket
    from crible.ingest.service import run_price_refresh

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CRIBLE_BOOTSTRAP_SAMPLE", "AIR.PA")
    _fundamentals(tmp_path, "OVH.PA")  # audited, never priced

    provider = RecordingPriceProvider()
    result = run_price_refresh(TokenBucket(capacity=10), provider=provider)

    # the priority sample keeps its daily slot; the gap rides what is left
    assert provider.calls == ["AIR.PA", "OVH.PA"]
    assert result["refreshed"] == 2
    assert result["topup_candidates"] == 1


def test_run_price_refresh_gap_never_starves_the_sample(tmp_path, monkeypatch) -> None:
    """Budget for one fetch only: the sample symbol gets it, the gap waits."""
    from crible.ingest.budget import TokenBucket
    from crible.ingest.service import run_price_refresh

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CRIBLE_BOOTSTRAP_SAMPLE", "AIR.PA")
    _fundamentals(tmp_path, "OVH.PA")

    provider = RecordingPriceProvider()
    result = run_price_refresh(TokenBucket(capacity=1), provider=provider)

    assert provider.calls == ["AIR.PA"]
    assert result["refreshed"] == 1
    assert result["skipped"] == 1  # the gap symbol stays visible as skipped
