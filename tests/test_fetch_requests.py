"""FR-012 — on-demand fetch: the API drops a request FILE (it stays a
reader, ADR-0003); the ingest loop picks pending requests up, crawls them
budget-charged and clears the files."""

from __future__ import annotations

import duckdb
import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app
from crible.ingest.requests import clear_request, pending_requests, request_fetch
from crible.universe import bootstrap_universe, export_universe_parquet

from tests.test_fr001_universe import fixture_frame


def test_request_roundtrip_is_idempotent_and_ordered(tmp_path) -> None:
    assert pending_requests(tmp_path) == []
    assert request_fetch(tmp_path, "AAPL")
    assert request_fetch(tmp_path, "BRK/B")  # '/' never escapes the directory
    assert request_fetch(tmp_path, "AAPL")  # re-request refreshes, no duplicate
    pending = pending_requests(tmp_path)
    assert set(pending) == {"AAPL", "BRK/B"}  # the ORIGINAL symbol travels
    clear_request(tmp_path, "BRK/B")
    assert pending_requests(tmp_path) == ["AAPL"]
    assert not (tmp_path / "fetch-requests" / "BRK_B.req").exists()


def test_request_queue_is_capped(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("crible.ingest.requests.MAX_PENDING", 2)
    assert request_fetch(tmp_path, "A") and request_fetch(tmp_path, "B")
    assert not request_fetch(tmp_path, "C")  # full → caller reports, nothing breaks
    assert request_fetch(tmp_path, "A")  # refreshing an existing one still works


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect()
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    return TestClient(create_app())


def test_post_fetch_queues_a_universe_symbol(client, tmp_path) -> None:
    response = client.post("/api/fetch/AIR.PA")
    assert response.status_code == 202
    body = response.json()
    assert body["queued"] is True and body["symbol"] == "AIR.PA"
    assert pending_requests(tmp_path) == ["AIR.PA"]


def test_post_fetch_rejects_unknown_symbols(client, tmp_path) -> None:
    assert client.post("/api/fetch/NOPE").status_code == 404
    assert pending_requests(tmp_path) == []
