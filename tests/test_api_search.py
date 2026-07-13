"""Universe search — GET /api/search makes the 161k-row universe browsable
by symbol or name (case-insensitive substring), profile-drawer deep-linkable.
Same runtime seam as every other read surface: universe.parquet only.
"""

from __future__ import annotations

import duckdb
import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app
from crible.universe import bootstrap_universe, export_universe_parquet

from tests.test_fr001_universe import fixture_frame


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect()
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    return TestClient(create_app())


def test_search_matches_symbol_case_insensitive(client) -> None:
    hits = client.get("/api/search", params={"q": "air"}).json()
    assert [h["symbol"] for h in hits] == ["AIR.PA"]
    assert set(hits[0]) == {"symbol", "name", "country", "sector"}


def test_search_matches_name_substring(client) -> None:
    hits = client.get("/api/search", params={"q": "apple"}).json()
    assert [h["symbol"] for h in hits] == ["AAPL"]


def test_search_orders_by_symbol_and_limits(client) -> None:
    hits = client.get("/api/search", params={"q": "a", "limit": 3}).json()
    assert len(hits) == 3
    assert [h["symbol"] for h in hits] == sorted(h["symbol"] for h in hits)


def test_search_blank_query_is_empty_not_an_error(client) -> None:
    response = client.get("/api/search", params={"q": "  "})
    assert response.status_code == 200
    assert response.json() == []


def test_search_without_universe_is_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path / "empty"))
    response = TestClient(create_app()).get("/api/search", params={"q": "air"})
    assert response.status_code == 200
    assert response.json() == []
