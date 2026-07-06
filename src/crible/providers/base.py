"""Provider Plugin API — the seam every data source implements (FR-002/FR-013).

Keyless providers are always active. A keyed provider is activated only when
its environment key is present; otherwise it logs exactly one
"disabled (no key configured)" line and the system behaves as keyless.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Protocol, Sequence, runtime_checkable

import pandas as pd

log = logging.getLogger("crible.providers")


class RateLimitedError(RuntimeError):
    """The upstream source is rate-limiting us (HTTP 429, crumb failures…)."""


@dataclass(frozen=True)
class StatementPayload:
    statement_type: str  # income | balance | cashflow
    freq: str  # annual | quarterly
    frame: pd.DataFrame


@dataclass(frozen=True)
class FetchResult:
    symbol: str
    provider: str
    statements: Sequence[StatementPayload]
    prices: pd.DataFrame | None = None
    requests_used: int = 1


@runtime_checkable
class Provider(Protocol):
    id: str
    kind: str  # keyless | free-key | paid

    def enabled(self, env: dict[str, str]) -> bool: ...

    def fetch_statements(self, symbol: str) -> FetchResult: ...


@dataclass
class ProviderRegistry:
    env: dict[str, str] = field(default_factory=dict)

    def activate(self, providers: Iterable[Provider]) -> list[Provider]:
        active: list[Provider] = []
        for provider in providers:
            if provider.enabled(self.env):
                active.append(provider)
                continue
            key_var = getattr(provider, "key_env_var", None)
            log.info(
                "provider %s disabled (no key configured)%s",
                provider.id,
                f" — set {key_var} to enable" if key_var else "",
            )
        return active
