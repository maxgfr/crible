"""The MCP tool surface: read-only wrappers over the shared Runtime — same
DSL, same whitelist, no side-effecting tool exposed."""

from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from crible import mcp_server
from crible.compute.snapshot import publish_snapshot


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    publish_snapshot(
        pd.DataFrame(
            {
                "symbol": ["AIR.PA", "SAP.DE", "AAPL"],
                "period": ["2025"] * 3,
                "piotroski_f": [8, 6, 9],
                "composite_rank": [70.0, 40.0, 90.0],
                "region": ["europe", "europe", "us"],
            }
        ),
        tmp_path,
    )
    return tmp_path


def test_mcp_screen_runs_the_shared_dsl(data_dir) -> None:
    out = mcp_server.screen("piotroski_f >= 7", sort="-piotroski_f", limit=5)
    assert out["total"] == 2
    assert [r["symbol"] for r in out["rows"]] == ["AAPL", "AIR.PA"]


def test_mcp_blank_query_screens_the_whole_universe(data_dir) -> None:
    out = mcp_server.screen("", sort="-composite_rank")
    assert out["total"] == 3
    assert out["rows"][0]["symbol"] == "AAPL"


def test_mcp_limit_is_capped(data_dir) -> None:
    out = mcp_server.screen("", limit=10_000)
    assert out["returned"] <= mcp_server.MAX_LIMIT


def test_mcp_dsl_errors_surface_readably(data_dir) -> None:
    with pytest.raises(ValueError, match="unknown field"):
        mcp_server.screen("nonexistent_column > 1")


def test_mcp_fields_presets_company_status(data_dir) -> None:
    names = [f["name"] for f in mcp_server.fields()]
    assert "piotroski_f" in names

    presets = mcp_server.presets()
    assert len(presets) >= 26
    assert all(p["dsl"] and p["columns"] for p in presets)

    detail = mcp_server.company("AIR.PA")
    assert detail is not None and detail["periods"][0]["piotroski_f"] == 8
    assert mcp_server.company("NOPE.XX") is None

    status = mcp_server.status()
    assert status["snapshot"] is True
    assert "data_dir" not in status  # no local paths in the tool surface


def test_mcp_surface_is_read_only() -> None:
    """Guard: only the five read tools exist — no crawl/refresh/compute."""
    tools = asyncio.run(mcp_server.mcp.list_tools())
    assert sorted(t.name for t in tools) == ["company", "fields", "presets", "screen", "status"]
