"""FR-002 / NFR-007 — the global rate budget as a rolling-window token bucket.

Default budget is 330 requests per rolling hour: ~10% headroom under the
~360 req/h Yahoo is known to tolerate. Staying under budget is a hard
constraint of the keyless design, not an optimisation.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable

DEFAULT_CAPACITY = 330
DEFAULT_WINDOW_SECONDS = 3600


class TokenBucket:
    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.capacity = capacity
        self.window = window_seconds
        self._now = now
        self._stamps: deque[float] = deque()

    def _evict(self) -> None:
        horizon = self._now() - self.window
        while self._stamps and self._stamps[0] <= horizon:
            self._stamps.popleft()

    def try_acquire(self, n: int = 1) -> bool:
        """Atomically reserve ``n`` upstream requests (all or nothing)."""
        self._evict()
        if len(self._stamps) + n > self.capacity:
            return False
        stamp = self._now()
        for _ in range(n):
            self._stamps.append(stamp)
        return True

    def seconds_until_available(self) -> float:
        self._evict()
        if len(self._stamps) < self.capacity:
            return 0.0
        return max(0.0, self._stamps[0] + self.window - self._now())

    def used_in_window(self) -> int:
        self._evict()
        return len(self._stamps)
