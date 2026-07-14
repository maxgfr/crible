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
