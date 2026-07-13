"""/api/prices/{symbol} — the published daily bars behind the drawer chart."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app

from tests.test_price_series import write_yf_bars, yf_frame


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    write_yf_bars(tmp_path, "ML.PA", yf_frame(days=3, start="2026-03-02"))
    return TestClient(create_app())


def test_prices_returns_bars_sorted_by_date(client) -> None:
    response = client.get("/api/prices/ML.PA")
    assert response.status_code == 200
    bars = response.json()
    assert [b["date"] for b in bars] == ["2026-03-02", "2026-03-03", "2026-03-04"]
    assert bars[0]["close"] == 100.5
    assert bars[0]["source"] == "yfinance"


def test_prices_unknown_symbol_is_empty_never_an_error(client) -> None:
    response = client.get("/api/prices/NOPE")
    assert response.status_code == 200
    assert response.json() == []
