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
        json={
            "query": "piotroski_f >= 7 AND country IN ('FR','DE')",
            "sort": "-piotroski_f",
            "page": 1,
            "page_size": 10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert [r["symbol"] for r in body["rows"]] == ["AIR.PA", "SAP.DE"]
    assert body["total"] == 2
    assert body["tookMs"] >= 0


def test_fr006_blank_query_screens_the_full_snapshot(client) -> None:
    response = client.post("/api/screen", json={"query": ""})
    assert response.status_code == 200
    assert response.json()["total"] == 4


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
        "symbol",
        "period",
        "piotroski_f",
        "altman_z",
        "beneish_m",
        "return_on_equity",
        "country",
        "name",
        "computed_at",
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
    assert (
        client.get("/api/screen.csv", params={"query": "piotroski_f >= 5", "columns": "nope"}).status_code
        == 422
    )


def test_fr006_paths_with_a_quote_never_break_the_readers(tmp_path, monkeypatch) -> None:
    """Data directories are interpolated nowhere: a `'` in the path is data."""
    import pandas as pd

    from crible.runtime import Runtime

    data = tmp_path / "o'brien"
    (data / "snapshot").mkdir(parents=True)
    pd.DataFrame({"symbol": ["A", "B"], "period": ["2024", "2024"], "revenue": [1.0, 2.0]}).to_parquet(
        data / "snapshot" / "snapshot.parquet"
    )
    pd.DataFrame(
        {"symbol": ["A"], "name": ["Alpha"], "country": ["FR"], "sector": ["Tech"], "region": ["europe"]}
    ).to_parquet(data / "universe.parquet")
    runtime = Runtime(data_dir=data)
    rows, total = runtime.screen("revenue > 0")
    assert total == 2
    assert runtime.search("alp")[0]["symbol"] == "A"
    assert runtime.company("A")["profile"]["name"] == "Alpha"
    assert runtime.status()["universe"] == 1


@pytest.mark.parametrize(
    "body",
    [
        {"query": "country = 5"},
        {"query": 'piotroski_f = "abc"'},
        {"query": "NOT " * 3000 + "piotroski_f > 1"},
        {"query": "(" * 3000 + "piotroski_f > 1"},
        {"query": "piotroski_f > 1", "page": 10**17, "page_size": 1000},
        {"query": "piotroski_f > 1", "page": 2**40},
        {"query": "piotroski_f > 1", "sort": "-nope"},
        {"query": "name = '😀' AND ٣ > 1"},
    ],
)
def test_fr006_hostile_screen_input_is_a_4xx_never_a_5xx(client, body) -> None:
    response = client.post("/api/screen", json=body)
    assert 400 <= response.status_code < 500, response.text


def test_fr006_hostile_csv_and_price_paths_are_4xx_or_empty(client) -> None:
    assert client.get("/api/screen.csv", params={"query": "country = 5"}).status_code == 422
    assert client.get("/api/prices/*").json() == []
    assert client.get("/api/prices/[AB]*").json() == []


def test_fr006_duckdb_error_maps_to_422(tmp_path, monkeypatch) -> None:
    """Whatever the compiler lets through (a DATE column has no literal type
    check), a DuckDB error is the query's fault — 422 with the engine message
    as the hint, never a 500."""
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    snapshot = pd.DataFrame(
        {"symbol": ["A"], "period": ["2025"], "listed": pd.to_datetime(["2020-01-01"]).date}
    )
    publish_snapshot(snapshot, tmp_path)
    response = TestClient(create_app()).post("/api/screen", json={"query": "listed = 'not a date'"})
    assert response.status_code == 422, response.text
    assert "Conversion" in response.json()["detail"]["error"]


def test_fr006_pages_are_deterministic_and_never_overlap(client) -> None:
    """Ties on the sort key are broken by symbol: two pages of 2 over 4 rows
    cover each row exactly once, every time."""
    seen = []
    for page in (1, 2):
        body = client.post(
            "/api/screen", json={"query": "", "sort": "-beneish_m", "page": page, "page_size": 2}
        ).json()
        seen += [r["symbol"] for r in body["rows"]]
    assert sorted(seen) == sorted(["AIR.PA", "SAP.DE", "AAPL", "7203.T"])
    unsorted = [client.post("/api/screen", json={"query": ""}).json()["rows"] for _ in range(3)]
    assert all([r["symbol"] for r in rows] == ["7203.T", "AAPL", "AIR.PA", "SAP.DE"] for rows in unsorted)


def test_fr006_truncated_export_says_so(client, monkeypatch) -> None:
    from crible import store

    monkeypatch.setattr(store, "EXPORT_LIMIT", 2)
    response = client.get("/api/screen.csv", params={"query": ""})
    assert response.status_code == 200
    assert response.headers["X-Crible-Truncated"] == "4"
    assert len(response.text.strip().splitlines()) == 3  # header + 2 rows
    full = client.get("/api/screen.csv", params={"query": "piotroski_f >= 9"})
    assert "X-Crible-Truncated" not in full.headers
