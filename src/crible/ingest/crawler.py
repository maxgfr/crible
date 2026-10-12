"""FR-002 — the rolling, resumable, rate-budgeted crawler.

One long-lived polite process: pick the next due symbol (europe → us → world),
spend budget, fetch through the provider, persist raw Parquet, update the
queue. 429s trigger jittered exponential backoff and an in-place retry; other
errors (fetch or raw write) reschedule the symbol. Three rate limits in a row
trip a breaker that ends the cycle, and no sleep — budget wait or backoff —
ever crosses the caller's ``deadline``. A symbol Yahoo returns nothing for
leaves a ``meta-none`` marker so the nightly restore does not re-crawl it.
Clock and sleep are injected for testability.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from crible.ingest.backoff import BackoffPolicy
from crible.ingest.budget import TokenBucket
from crible.ingest.queue import CrawlQueue
from crible.ingest.raw import write_raw_statement
from crible.ingest.watchdog import call_with_timeout
from crible.providers.base import Provider, RateLimitedError

log = logging.getLogger("crible.ingest")

MAX_RATE_LIMIT_RETRIES = 6
# the price refresher's switch rule: this many 429s in a row end the cycle —
# each symbol otherwise burns ~45 min of backoff (60+120+…+900 s)
MAX_CONSECUTIVE_RATE_LIMITS = 3
# statement_type of the marker written for a symbol that returned nothing
EMPTY_MARKER = ("meta", "none")


@dataclass
class CrawlOutcome:
    fetched: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    # why the cycle stopped early ("deadline" / "rate-limited"), else None
    aborted: str | None = None


class _Stop(Exception):
    """End the cycle without charging the symbol a failure."""


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
        fetch_timeout: float = 60.0,
        deadline: float | None = None,
    ) -> None:
        self.queue = queue
        self.provider = provider
        self.budget = budget
        self.backoff = backoff
        self.data_dir = Path(data_dir)
        self.now = now
        self.sleep = sleep
        self.fetch_timeout = fetch_timeout
        # absolute, on the ``now`` clock — None = unbounded
        self.deadline = deadline
        self.stopped: str | None = None
        self._consecutive_limits = 0
        # an external stop request (the loop's SIGTERM), checked per symbol
        self.should_stop: Callable[[], bool] | None = None

    def _sleep_within_deadline(self, seconds: float) -> None:
        if self.deadline is not None and self.now() + seconds > self.deadline:
            raise _Stop("deadline")
        self.sleep(seconds)

    def _acquire_budget(self, n: int = 1) -> None:
        while not self.budget.try_acquire(n):
            wait = max(self.budget.seconds_until_available(n), 1.0)
            log.info("rate budget exhausted — sleeping %.0fs", wait)
            self._sleep_within_deadline(wait)

    def _fetch_with_timeout(self, symbol: str):
        """Run one provider fetch under the shared wall-clock watchdog so a hung
        upstream can never freeze the rolling loop (ADR-0004)."""
        return call_with_timeout(
            lambda: self.provider.fetch_statements(symbol),
            self.fetch_timeout,
            label=f"fetch_statements({symbol})",
        )

    def crawl_symbol(self, symbol: str) -> bool:
        """Fetch one symbol with in-place backoff on 429. True on success.

        The budget is charged with the provider's per-fetch request estimate
        BEFORE fetching: every upstream call counts (NFR-007), not every symbol.
        A deadline or a tripped breaker returns False with ``self.stopped``
        set and the symbol left due — never charged a failure.
        """
        try:
            return self._crawl(symbol)
        except _Stop as stop:
            self.stopped = str(stop)
            log.warning("crawl stopped before %s: %s", symbol, self.stopped)
            return False

    def _crawl(self, symbol: str) -> bool:
        cost = getattr(self.provider, "requests_per_fetch", 1)
        for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
            self._acquire_budget(cost)
            try:
                result = self._fetch_with_timeout(symbol)
            except RateLimitedError as exc:
                self._consecutive_limits += 1
                if self._consecutive_limits >= MAX_CONSECUTIVE_RATE_LIMITS:
                    raise _Stop("rate-limited") from exc
                delay = self.backoff.delay(attempt)
                log.warning(
                    "rate-limited on %s (attempt %d): %s — backing off %.0fs",
                    symbol,
                    attempt,
                    exc,
                    delay,
                )
                self._sleep_within_deadline(delay)
                continue
            except Exception as exc:  # noqa: BLE001 — a symbol must never kill the loop
                log.error("fetch failed for %s: %s — rescheduled", symbol, exc)
                self.queue.mark_failed(symbol, self.now())
                return False
            self._consecutive_limits = 0

            fetched_at = self.now()
            try:
                self._persist(symbol, result, fetched_at)
            except Exception as exc:  # noqa: BLE001 — a full disk or an odd frame must not crash-loop
                log.error("writing raw for %s failed: %s — rescheduled", symbol, exc)
                self.queue.mark_failed(symbol, self.now())
                return False
            self.queue.mark_done(symbol, fetched_at)
            log.info(
                "fetched %s via %s (%d statement(s), budget used %d/h)",
                symbol,
                result.provider,
                len(result.statements),
                self.budget.used_in_window(),
            )
            return True

        log.error("giving up on %s after %d rate-limited attempts", symbol, MAX_RATE_LIMIT_RETRIES)
        self.queue.mark_failed(symbol, self.now())
        return False

    def _persist(self, symbol: str, result, fetched_at: float) -> None:
        priced = result.prices is not None and len(result.prices)
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
        if priced:
            write_raw_statement(
                self.data_dir,
                symbol=symbol,
                provider=result.provider,
                statement_type="prices",
                freq="daily",
                frame=result.prices,
                fetched_at=fetched_at,
            )
        if not result.statements and not priced:
            # a delisted / empty ticker: the marker carries the crawl stamp
            # through the published raw layer (the queue DB does not travel)
            statement_type, freq = EMPTY_MARKER
            write_raw_statement(
                self.data_dir,
                symbol=symbol,
                provider=result.provider,
                statement_type=statement_type,
                freq=freq,
                frame=pd.DataFrame({"period": pd.Series(dtype="string")}),
                fetched_at=fetched_at,
            )

    def run_cycle(self, limit: int = 50) -> CrawlOutcome:
        outcome = CrawlOutcome()
        for symbol in self.queue.next_batch(self.now(), limit):
            if self.deadline is not None and self.now() >= self.deadline:
                self.stopped = "deadline"
            if self.should_stop is not None and self.should_stop():
                self.stopped = "stop requested"
            if self.stopped is None and self.crawl_symbol(symbol):
                outcome.fetched.append(symbol)
            elif self.stopped is None:
                outcome.failed.append(symbol)
            if self.stopped is not None:
                outcome.aborted = self.stopped
                break
        return outcome
