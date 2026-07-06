"""FR-002 — jittered exponential backoff for 429/crumb failures.

Delay doubles from ``base_seconds`` up to ``cap_seconds`` (15 min by default),
with a symmetric jitter of ±``jitter`` around the nominal value. ``rng`` is
injectable for determinism in tests (rng() in [0, 1]; 0.5 → exactly nominal).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

@dataclass(frozen=True)
class BackoffPolicy:
    base_seconds: float = 60.0
    cap_seconds: float = 900.0
    jitter: float = 0.2
    rng: Callable[[], float] = field(default=random.random)

    def delay(self, attempt: int) -> float:
        """Delay before retry ``attempt`` (1-based)."""
        nominal = min(self.base_seconds * (2 ** (attempt - 1)), self.cap_seconds)
        factor = 1.0 + self.jitter * (2.0 * self.rng() - 1.0)
        return nominal * factor
