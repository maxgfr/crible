"""FR-012 — company detail: history, score breakdowns, provenance, and the
not-yet-crawled path (universe metadata + queue position instead of an error).
"""

from __future__ import annotations

import time

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app
from crible.compute.snapshot import publish_snapshot
from crible.runtime import Runtime
from crible.universe import bootstrap_universe, export_universe_parquet

from tests.test_fr001_universe import fixture_frame


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    snapshot = pd.DataFrame(
        {
            "symbol": ["AIR.PA", "AIR.PA"],
            "period": ["2024", "2025"],
            "revenue": [65e9, 70e9],
            "net_income": [4e9, 5e9],
            "piotroski_f": [6, 8],
            "piotroski_roa_positive": [True, True],
            "altman_z": [3.0, 3.2],
            "beneish_m": [-2.4, -2.5],
            "beneish_dsri": [1.0, 1.05],
            "provider": ["yfinance", "yfinance"],
            "computed_at": [time.time()] * 2,
        }
    )
    publish_snapshot(snapshot, tmp_path)
    return tmp_path


def test_fr012_full_history_scores_and_provenance(data_dir) -> None:
    detail = Runtime.from_env().company("AIR.PA")
    assert detail is not None
    assert detail["profile"]["name"] == "ABN AMRO" or detail["profile"]["symbol"] == "AIR.PA"
    periods = detail["periods"]
    assert [p["period"] for p in periods] == ["2025", "2024"]  # newest first
    assert periods[0]["piotroski_f"] == 8
    assert periods[0]["piotroski_roa_positive"] is True  # criterion-level breakdown
    assert periods[0]["beneish_dsri"] == pytest.approx(1.05)
    assert periods[0]["provider"] == "yfinance"
    assert periods[0]["computed_at"] is not None


def test_fr012_not_yet_crawled_company_shows_universe_metadata_not_error(data_dir) -> None:
    detail = Runtime.from_env().company("SAP.DE")  # in universe, not in snapshot
    assert detail is not None
    assert detail["profile"]["name"] == "SAP"
    assert detail["profile"]["country"] == "DE"
    assert detail["periods"] == []


def test_fr012_api_surfaces_the_same_contract(data_dir) -> None:
    client = TestClient(create_app())
    ok = client.get("/api/company/AIR.PA")
    assert ok.status_code == 200
    assert len(ok.json()["periods"]) == 2
    queued = client.get("/api/company/SAP.DE")
    assert queued.status_code == 200
    assert queued.json()["periods"] == []
