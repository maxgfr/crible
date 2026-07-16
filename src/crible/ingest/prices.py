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
from crible.ingest.watchdog import call_with_timeout
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
    fetch_timeout: float = 60.0

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
                bars = call_with_timeout(
                    lambda: self.provider.fetch_prices(symbol),
                    self.fetch_timeout,
                    label=f"fetch_prices({symbol})",
                )
            except RateLimitedError:
                consecutive_failures += 1
                outcome.skipped.append(symbol)
                continue
            except Exception as exc:  # noqa: BLE001 — hang (watchdog) or error: skip, never freeze
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


def price_gap_symbols(data_dir: Path | str, limit: int | None = None) -> list[str]:
    """Audited-but-never-priced symbols — the top-up set for leftover budget.

    A symbol is a price gap when the raw layer holds fundamentals for it
    (any non-``prices`` statement, e.g. an ESEF/EDGAR filing) but NO price
    source covers it: no raw ``prices-*`` bars from the crawl and no row in
    the ``prices-latest.parquet`` dump distillate. These are exactly the
    listings whose price ratios stay NULL forever — e.g. the ~1.8k FR
    companies with audited ESEF statements that Stooq's bulk dumps (no
    French dump exists) and the budget-bound crawl never reach.
    """
    root = Path(data_dir) / "raw"
    with_fundamentals: set[str] = set()
    with_raw_prices: set[str] = set()
    for symbol_dir in root.glob("provider=*/symbol=*"):
        if not symbol_dir.is_dir():
            continue
        symbol = symbol_dir.name.split("=", 1)[1]
        for file in symbol_dir.iterdir():
            if file.name.startswith("prices-"):
                with_raw_prices.add(symbol)
            else:
                with_fundamentals.add(symbol)

    dumped: set[str] = set()
    latest = Path(data_dir) / "prices-latest.parquet"
    if latest.exists():
        dumped = set(pd.read_parquet(latest, columns=["symbol"])["symbol"])

    gaps = sorted(with_fundamentals - with_raw_prices - dumped)

    # same ordering contract as the crawl queue: priority ASC, then symbol —
    # Europe-first, so the audited-EU price gap (the FR case) drains first
    universe = Path(data_dir) / "universe.parquet"
    if universe.exists() and gaps:
        frame = pd.read_parquet(universe, columns=["symbol", "crawl_priority"])
        priority = dict(zip(frame["symbol"], frame["crawl_priority"]))
        fallback = max(priority.values(), default=0) + 1
        gaps.sort(key=lambda s: (priority.get(s, fallback), s))

    return gaps[:limit] if limit is not None else gaps
