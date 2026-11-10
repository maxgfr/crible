"""FIX-004 / F2 (price path) — the price refresh must be watchdog-protected too.

PriceRefresher.refresh called the provider with no hard timeout even though the
module docstring promised watchdog protection. A hung yfinance price pull froze
the whole price cycle. Same wall-clock watchdog as the statement crawler,
sharing one helper: a timeout is a skipped symbol, never a freeze.
"""

from __future__ import annotations

import time

from crible.ingest.budget import TokenBucket
from crible.ingest.prices import PriceRefresher


class HungPriceProvider:
    id = "yfinance"

    def fetch_prices(self, symbol):
        time.sleep(2)  # never returns inside the watchdog window
        raise AssertionError("unreachable — the watchdog should have fired")


def test_price_refresh_times_out_on_a_hung_fetch(tmp_path) -> None:
    refresher = PriceRefresher(
        provider=HungPriceProvider(),
        budget=TokenBucket(capacity=100, window_seconds=3600),
        data_dir=tmp_path,
        fetch_timeout=0.1,
    )

    start = time.monotonic()
    outcome = refresher.refresh(["AIR.PA"])
    elapsed = time.monotonic() - start

    assert outcome.refreshed == []
    assert outcome.skipped == ["AIR.PA"]  # skipped, not frozen
    assert elapsed < 1.0


def test_three_hung_fetches_in_a_row_end_the_refresh(tmp_path) -> None:
    """The switch rule covers hangs too: when Yahoo stops answering, the
    refresh ends after three watchdog timeouts — it used to wait out the full
    timeout for every remaining symbol (hundreds of minutes on a nightly)."""
    calls: list[str] = []

    class Hung(HungPriceProvider):
        def fetch_prices(self, symbol):
            calls.append(symbol)
            return super().fetch_prices(symbol)

    refresher = PriceRefresher(
        provider=Hung(),
        budget=TokenBucket(capacity=100, window_seconds=3600),
        data_dir=tmp_path,
        fetch_timeout=0.05,
    )
    outcome = refresher.refresh(["A", "B", "C", "D", "E"])
    assert outcome.aborted
    assert calls == ["A", "B", "C"]
    assert outcome.skipped == ["A", "B", "C", "D", "E"] and outcome.refreshed == []
