"""FR-013/FR-014 — the single source of truth for the provider catalog.

Both the API's read-only inventory and any future crawl wiring enumerate the
catalog here rather than re-listing provider classes by hand, and the inventory
reflects each provider's own ``enabled(env)`` rather than a re-derived rule —
so the Providers view can never drift from the actual activation logic.
"""

from __future__ import annotations

from crible.providers.base import Provider
from crible.providers.yfinance_provider import YFinanceProvider


def default_catalog() -> list[Provider]:
    """The providers crible ships with — keyless only since the open-data
    cleanup (2026-07-13); the registry seam still accepts keyed plugins."""
    return [YFinanceProvider()]


def is_configured(prov: Provider, env: dict[str, str]) -> bool:
    """Whether a provider is *configured* to run: keyless is always configured;
    a keyed provider is configured iff its env key is present.

    This is deliberately the offline *configuration* check, not the provider's
    ``enabled(env)`` — the latter may perform live key validation (network I/O),
    which must never happen inside a read-only settings inventory. Centralizing
    the rule here is the single source of truth both the API and any future
    wiring share, so the Providers view cannot drift.
    """
    key_var = getattr(prov, "key_env_var", None)
    return True if key_var is None else bool(env.get(key_var))


def inventory(providers: list[Provider], env: dict[str, str]) -> list[dict]:
    """Read-only, offline inventory: id, kind, key env var, and whether the
    provider is configured (see ``is_configured``)."""
    return [
        {
            "id": prov.id,
            "kind": prov.kind,
            "key_env_var": getattr(prov, "key_env_var", None),
            "enabled": is_configured(prov, env),
        }
        for prov in providers
    ]
