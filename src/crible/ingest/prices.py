"""FR-011 — price freshness tiering, budget-aware and provenance-dated.

Prices share the ONE Yahoo request budget — yfinance is the only price
source in the keyless core (no redistributable bulk price feed exists).
The priority set gets daily refreshes; everything else rides leftover
budget. Switch rule: 3 consecutive rate-limit failures (or a hang,
enforced by the crawler's watchdog) end the cycle politely — symbols keep
their last price, staleness stays visible via price_asof.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import pandas as pd

from crible.ingest.budget import TokenBucket
from crible.ingest.raw import write_raw_statement
from crible.providers.base import RateLimitedError

log = logging.getLogger("crible.ingest.prices")

MAX_CONSECUTIVE_FAILURES = 3


class PriceProvider(Protocol):
    id: str

    def fetch_prices(self, symbol: str) -> pd.DataFrame | None: ...


@dataclass
class PriceRefreshOutcome:
    refreshed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    aborted: bool = False


@dataclass
class PriceRefresher:
    provider: PriceProvider
    budget: TokenBucket
    data_dir: Path
    now: Callable[[], float] = time.time

    def refresh(self, symbols: list[str]) -> PriceRefreshOutcome:
        outcome = PriceRefreshOutcome()
        consecutive_failures = 0
        for symbol in symbols:
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                outcome.aborted = True
                outcome.skipped.extend(symbols[len(outcome.refreshed) + len(outcome.skipped):])
                log.warning(
                    "price refresh aborted after %d consecutive rate-limits — "
                    "remaining symbols keep their last price (visible via price_asof)",
                    consecutive_failures,
                )
                break
            if not self.budget.try_acquire():
                outcome.skipped.append(symbol)
                continue
            try:
                bars = self.provider.fetch_prices(symbol)
            except RateLimitedError:
                consecutive_failures += 1
                outcome.skipped.append(symbol)
                continue
            except Exception as exc:  # noqa: BLE001 — one symbol never kills the cycle
                log.info("price fetch failed for %s: %s — skipped", symbol, exc)
                outcome.skipped.append(symbol)
                continue
            consecutive_failures = 0
            if bars is None or not len(bars):
                outcome.skipped.append(symbol)
                continue
            write_raw_statement(
                self.data_dir,
                symbol=symbol,
                provider=self.provider.id,
                statement_type="prices",
                freq="daily",
                frame=bars,
                fetched_at=self.now(),
            )
            outcome.refreshed.append(symbol)
        return outcome
