"""FR-013 — the provider plugin seam: keyless providers are always active;
a keyed provider without its env key disables with exactly one log line.

The bundled keyed providers were removed with the open-data cleanup
(2026-07-13) — the seam stays, proven against an in-test stub so third-party
plugins keep the same contract."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from crible.providers.base import FetchResult, ProviderRegistry
from crible.providers.catalog import default_catalog, inventory


@dataclass
class StubKeyedProvider:
    id: str = "stub"
    kind: str = "free-key"
    key_env_var: str = "STUB_KEY"
    requests_per_fetch: int = 1
    env: dict[str, str] = field(default_factory=dict)

    def enabled(self, env: dict[str, str]) -> bool:
        return bool(env.get(self.key_env_var))

    def fetch_statements(self, symbol: str) -> FetchResult:
        return FetchResult(symbol=symbol, provider=self.id, statements=[])


def test_fr013_no_key_means_keyed_plugin_disables_with_one_log_line(caplog) -> None:
    registry = ProviderRegistry(env={})
    with caplog.at_level(logging.INFO, logger="crible.providers"):
        active = registry.activate([StubKeyedProvider()])
    assert active == []
    disabled = [r for r in caplog.records if "disabled (no key configured)" in r.message]
    assert len(disabled) == 1
    assert "STUB_KEY" in disabled[0].message


def test_fr013_key_present_activates_keyed_plugin() -> None:
    registry = ProviderRegistry(env={"STUB_KEY": "k"})
    active = registry.activate([StubKeyedProvider()])
    assert [p.id for p in active] == ["stub"]


def test_fr013_shipped_catalog_is_keyless_core_with_edinet_opt_in() -> None:
    catalog = default_catalog()
    assert [p.id for p in catalog] == ["yfinance", "edinet"]
    inv = inventory(catalog, env={})
    by_id = {p["id"]: p for p in inv}
    # keyless core is always on
    assert by_id["yfinance"] == {
        "id": "yfinance", "kind": "keyless", "key_env_var": None, "enabled": True,
    }
    # EDINET is the one free-key opt-in — OFF with an empty env, so the published
    # dataset and the CI contract stay keyless (NFR-009)
    assert by_id["edinet"]["kind"] == "free-key"
    assert by_id["edinet"]["key_env_var"] == "CRIBLE_EDINET_KEY"
    assert by_id["edinet"]["enabled"] is False
    # invariant: nothing keyed is enabled without its key
    assert not any(p["enabled"] for p in inv if p["key_env_var"] is not None)


def test_fr013_inventory_reports_keyed_stub_enabled_iff_key_present() -> None:
    stub = StubKeyedProvider()
    assert inventory([stub], env={})[0]["enabled"] is False
    assert inventory([stub], env={"STUB_KEY": "k"})[0]["enabled"] is True


def test_fr013_registry_keeps_keyless_providers_active() -> None:
    keyless = default_catalog()
    active = ProviderRegistry(env={}).activate(keyless)
    assert [p.id for p in active] == ["yfinance"]
