"""stats(): the distribution of numeric fields over a peer group and one
symbol's percentile in it — the same whitelist and DSL as screen()."""

from __future__ import annotations

import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from crible.api.main import create_app
from crible.compute.snapshot import publish_snapshot
from crible.dsl.parser import DslError
from crible.runtime import Runtime


@pytest.fixture()
def runtime(tmp_path, monkeypatch) -> Runtime:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    tech = [f"T{i}" for i in range(6)]  # europe×tech: 6 rows ≥ MIN_PEERS
    rows = {
        "symbol": [*tech, "B1", "B2", "U1"],
        "period": ["2025"] * 9,
        "region": ["europe"] * 8 + ["us"],
        "sector": ["tech"] * 6 + ["banks", "banks", "tech"],
        "name": ["x"] * 9,
        "roe": [0.10, 0.20, 0.30, 0.40, 0.50, math.inf, 0.05, 0.07, 0.9],
        "pe": [10.0, 12.0, None, 14.0, 16.0, 18.0, 8.0, 9.0, 30.0],
    }
    publish_snapshot(pd.DataFrame(rows), tmp_path)
    return Runtime(data_dir=tmp_path)


def test_symbol_defaults_to_its_region_by_sector(runtime) -> None:
    out = runtime.stats(["roe", "pe"], symbol="T2")
    assert out["group"] == {"basis": "region×sector", "region": "europe", "sector": "tech", "rows": 6}
    roe = out["fields"]["roe"]
    assert roe["n"] == 5  # the infinite value is left out
    assert roe["median"] == pytest.approx(0.30)
    assert roe["value"] == pytest.approx(0.30) and roe["percentile"] == 50.0
    pe = out["fields"]["pe"]
    assert pe["n"] == 5 and pe["value"] is None and pe["percentile"] is None


def test_small_group_falls_back_to_the_universe(runtime) -> None:
    out = runtime.stats(["roe"], symbol="B1")
    assert out["group"]["basis"] == "universe" and out["group"]["rows"] == 9
    assert "2 < 5" in out["group"]["reason"]
    assert out["fields"]["roe"]["percentile"] == pytest.approx(100 * 0.5 / 8, abs=0.1)


def test_query_sets_the_group_and_blank_is_the_universe(runtime) -> None:
    q = runtime.stats(["pe"], query="sector = 'banks'")
    assert q["symbol"] is None and q["group"]["rows"] == 2
    assert q["fields"]["pe"]["median"] == pytest.approx(8.5)
    assert "value" not in q["fields"]["pe"]
    assert runtime.stats(["pe"])["group"] == {"basis": "universe", "rows": 9}


def test_rejects_unknown_text_and_missing_fields(runtime) -> None:
    with pytest.raises(DslError, match="unknown field"):
        runtime.stats(["roee"])
    with pytest.raises(DslError, match="not a numeric field"):
        runtime.stats(["sector"])
    with pytest.raises(DslError, match="at least one"):
        runtime.stats([])
    assert runtime.stats(["roe"], symbol="NOPE") is None


def test_api_stats(runtime) -> None:
    client = TestClient(create_app())
    ok = client.get("/api/stats", params={"fields": "roe,pe", "symbol": "T0"})
    assert ok.status_code == 200 and ok.json()["fields"]["roe"]["percentile"] == 10.0
    assert client.get("/api/stats", params={"fields": "roee"}).status_code == 422
    assert client.get("/api/stats", params={"fields": "roe", "symbol": "NOPE"}).status_code == 404
