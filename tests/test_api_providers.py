"""T-020 — /api/providers: read-only inventory (keyless / free-key / paid),
enabled iff the key env var is set; keyless always on. FR-013 / FR-014."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    for var in ("SIMFIN_KEY", "FMP_KEY", "EODHD_KEY"):
        monkeypatch.delenv(var, raising=False)
    return TestClient(create_app())


def test_fr013_inventory_lists_all_plugins_keyless_on(client):
    body = client.get("/api/providers").json()
    by_id = {p["id"]: p for p in body}
    assert set(by_id) == {"yfinance", "simfin", "fmp_free", "eodhd"}
    assert by_id["yfinance"]["kind"] == "keyless"
    assert by_id["yfinance"]["enabled"] is True
    assert by_id["yfinance"]["key_env_var"] is None
    assert by_id["simfin"] == {
        "id": "simfin", "kind": "free-key", "key_env_var": "SIMFIN_KEY", "enabled": False,
    }
    assert by_id["eodhd"]["kind"] == "paid"
    assert by_id["eodhd"]["enabled"] is False


def test_fr013_key_in_env_flips_provider_on(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EODHD_KEY", "sk-test")
    monkeypatch.delenv("SIMFIN_KEY", raising=False)
    monkeypatch.delenv("FMP_KEY", raising=False)
    client = TestClient(create_app())
    by_id = {p["id"]: p for p in client.get("/api/providers").json()}
    assert by_id["eodhd"]["enabled"] is True
    assert by_id["simfin"]["enabled"] is False
