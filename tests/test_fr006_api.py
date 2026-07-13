"""FR-006 — the HTTP API (offline, fixture-backed)."""

from __future__ import annotations

import time

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app
from crible.compute.snapshot import publish_snapshot
from crible.universe import bootstrap_universe, export_universe_parquet

from tests.test_fr001_universe import fixture_frame


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    snapshot = pd.DataFrame(
        {
            "symbol": ["AIR.PA", "SAP.DE", "AAPL", "7203.T"],
            "period": ["2025"] * 4,
            "piotroski_f": [8, 7, 9, 5],
            "altman_z": [3.2, 4.1, 6.0, 2.2],
            "beneish_m": [-2.5, -2.9, -2.7, -2.1],
            "return_on_equity": [0.18, 0.22, 0.45, 0.11],
            "country": ["FR", "DE", "US", "JP"],
            "name": ["Airbus", "SAP", "Apple", "Toyota"],
            "computed_at": [time.time()] * 4,
        }
    )
    publish_snapshot(snapshot, tmp_path)
    return TestClient(create_app())


def test_fr006_post_screen_returns_rows_total_and_timing(client) -> None:
    response = client.post(
        "/api/screen",
        json={"query": "piotroski_f >= 7 AND country IN ('FR','DE')", "sort": "-piotroski_f", "page": 1, "page_size": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert [r["symbol"] for r in body["rows"]] == ["AIR.PA", "SAP.DE"]
    assert body["total"] == 2
    assert body["tookMs"] >= 0


def test_fr006_dsl_error_is_422_with_position_and_hint_never_5xx(client) -> None:
    response = client.post("/api/screen", json={"query": "piotroski > 7"})
    assert response.status_code == 422
    body = response.json()
    assert "piotroski_f" in body["detail"]["hint"]
    assert body["detail"]["position"] == 0


def test_fr006_unknown_symbol_is_404(client) -> None:
    assert client.get("/api/company/NOPE.PA").status_code == 404


def test_fr006_company_detail_has_history_scores_provenance(client) -> None:
    body = client.get("/api/company/AIR.PA").json()
    assert body["profile"]["name"] == "Airbus"
    assert body["profile"]["country"] == "FR"
    assert len(body["periods"]) == 1
    assert body["periods"][0]["piotroski_f"] == 8


def test_fr006_screen_csv_streams_full_result_set(client) -> None:
    response = client.get("/api/screen.csv", params={"query": "piotroski_f >= 5"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = [line for line in response.text.strip().splitlines() if line]
    assert len(lines) == 5  # header + all 4 rows, not a page


def test_fr006_presets_and_status_and_healthz(client) -> None:
    presets = client.get("/api/presets").json()
    assert any(p["id"] == "piotroski-strong" and p["dsl"] == "piotroski_f >= 7" for p in presets)
    status = client.get("/api/status").json()
    assert status["universe"] == 8
    assert client.get("/healthz").status_code == 200


def test_fr006_fields_endpoint_lists_snapshot_columns_with_types(client) -> None:
    fields = client.get("/api/fields").json()
    by_name = {f["name"]: f["type"] for f in fields}
    assert by_name["symbol"] == "string"
    assert by_name["country"] == "string"
    assert by_name["piotroski_f"] == "number"
    assert by_name["altman_z"] == "number"
    # the field list IS the live schema — same names the DSL whitelist accepts
    assert set(by_name) == {
        "symbol", "period", "piotroski_f", "altman_z", "beneish_m",
        "return_on_equity", "country", "name", "computed_at",
    }


def test_fr006_fresh_install_no_snapshot_is_200_with_hint(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path / "empty"))
    client = TestClient(create_app())
    response = client.post("/api/screen", json={"query": "piotroski_f >= 7"})
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == [] and body["total"] == 0
    assert "ingest" in body["hint"]
    assert client.get("/api/status").status_code == 200
    assert client.get("/api/fields").json() == []  # no snapshot → empty, never 5xx


def test_fr006_spa_is_served_at_root_with_api_reachable(tmp_path, monkeypatch) -> None:
    """FR-006 AC-3: the built SPA is served at / while /api stays reachable."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>crible</title>")
    (dist / "assets" / "index-abc123.js").write_text("// hashed asset")
    monkeypatch.setenv("CRIBLE_UI_DIST", str(dist))
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path / "empty"))
    client = TestClient(create_app())
    root = client.get("/")
    assert root.status_code == 200 and "crible" in root.text
    asset = client.get("/assets/index-abc123.js")
    assert asset.status_code == 200
    assert client.get("/api/status").status_code == 200  # same-origin API intact


def test_fr006_csv_export_restricts_to_visible_columns(client) -> None:
    """FR-007 AC-1 export clause: `columns` limits the CSV to what is shown."""
    response = client.get(
        "/api/screen.csv",
        params={"query": "piotroski_f >= 5", "columns": "symbol,piotroski_f,nonexistent"},
    )
    assert response.status_code == 200
    header = response.text.strip().splitlines()[0]
    assert header == "symbol,piotroski_f"  # unknown columns silently dropped
    assert client.get(
        "/api/screen.csv", params={"query": "piotroski_f >= 5", "columns": "nope"}
    ).status_code == 422
