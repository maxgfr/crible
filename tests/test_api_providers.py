"""T-020 — /api/providers: read-only inventory derived from the shared
catalog. The shipped catalog is keyless-only since the open-data cleanup
(2026-07-13); the endpoint must still derive everything from the catalog
rather than re-enumerating providers by hand (FR-013)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    return TestClient(create_app())


def test_fr013_inventory_exposes_the_keyless_core(client):
    body = client.get("/api/providers").json()
    by_id = {p["id"]: p for p in body}
    assert by_id["yfinance"] == {
        "id": "yfinance", "kind": "keyless", "key_env_var": None, "enabled": True,
    }
    # keyless-only contract (2026-07-17): no keyed provider ships at all
    assert all(p["key_env_var"] is None for p in body)


def test_fr013_inventory_is_derived_from_the_shared_catalog(client):
    """F1/F6 — the endpoint must not re-enumerate providers or re-implement the
    enablement rule; it derives both from the single catalog + provider.enabled()."""
    from crible.providers.catalog import default_catalog, inventory

    catalog = default_catalog()
    body = client.get("/api/providers").json()
    # ids come from the catalog, in catalog order (no hand-maintained list drift)
    assert [p["id"] for p in body] == [prov.id for prov in catalog]
    # enabled mirrors each provider's own enabled(env), not a re-derived rule
    assert body == inventory(catalog, env={})
