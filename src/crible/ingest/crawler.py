"""FR-002 — the rolling, resumable, rate-budgeted crawler.

One long-lived polite process: pick the next due symbol (europe → us → world),
spend budget, fetch through the provider, persist raw Parquet, update the
queue. 429s trigger jittered exponential backoff and an in-place retry; other
errors reschedule the symbol. Clock and sleep are injected for testability.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from crible.ingest.backoff import BackoffPolicy
from crible.ingest.budget import TokenBucket
from crible.ingest.queue import CrawlQueue
from crible.ingest.raw import write_raw_statement
from crible.providers.base import Provider, RateLimitedError

log = logging.getLogger("crible.ingest")

MAX_RATE_LIMIT_RETRIES = 6


@dataclass
class CrawlOutcome:
    fetched: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


class Crawler:
    def __init__(
        self,
        *,
        queue: CrawlQueue,
        provider: Provider,
        budget: TokenBucket,
        backoff: BackoffPolicy,
        data_dir: Path | str,
        now: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.queue = queue
        self.provider = provider
        self.budget = budget
        self.backoff = backoff
        self.data_dir = Path(data_dir)
        self.now = now
        self.sleep = sleep

    def _acquire_budget(self, n: int = 1) -> None:
        while not self.budget.try_acquire(n):
            wait = max(self.budget.seconds_until_available(), 1.0)
            log.info("rate budget exhausted — sleeping %.0fs", wait)
            self.sleep(wait)

    def crawl_symbol(self, symbol: str) -> bool:
        """Fetch one symbol with in-place backoff on 429. True on success.

        The budget is charged with the provider's per-fetch request estimate
        BEFORE fetching: every upstream call counts (NFR-007), not every symbol.
        """
        cost = getattr(self.provider, "requests_per_fetch", 1)
        for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
            self._acquire_budget(cost)
            try:
                result = self.provider.fetch_statements(symbol)
            except RateLimitedError as exc:
                delay = self.backoff.delay(attempt)
                log.warning(
                    "rate-limited on %s (attempt %d): %s — backing off %.0fs",
                    symbol, attempt, exc, delay,
                )
                self.sleep(delay)
                continue
            except Exception as exc:  # noqa: BLE001 — a symbol must never kill the loop
                log.error("fetch failed for %s: %s — rescheduled", symbol, exc)
                self.queue.mark_failed(symbol, self.now())
                return False

            fetched_at = self.now()
            for payload in result.statements:
                write_raw_statement(
                    self.data_dir,
                    symbol=symbol,
                    provider=result.provider,
                    statement_type=payload.statement_type,
                    freq=payload.freq,
                    frame=payload.frame,
                    fetched_at=fetched_at,
                )
            self.queue.mark_done(symbol, fetched_at)
            log.info(
                "fetched %s via %s (%d statement(s), budget used %d/h)",
                symbol, result.provider, len(result.statements), self.budget.used_in_window(),
            )
            return True

        log.error("giving up on %s after %d rate-limited attempts", symbol, MAX_RATE_LIMIT_RETRIES)
        self.queue.mark_failed(symbol, self.now())
        return False

    def run_cycle(self, limit: int = 50) -> CrawlOutcome:
        outcome = CrawlOutcome()
        for symbol in self.queue.next_batch(self.now(), limit):
            (outcome.fetched if self.crawl_symbol(symbol) else outcome.failed).append(symbol)
        return outcome
