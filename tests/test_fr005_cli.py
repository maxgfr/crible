"""FR-005 — the crible CLI (offline, fixture-backed)."""

from __future__ import annotations

import time

import duckdb
import pandas as pd
import pytest
from typer.testing import CliRunner

from crible.cli import app
from crible.compute.snapshot import publish_snapshot
from crible.universe import bootstrap_universe, export_universe_parquet

from tests.test_fr001_universe import fixture_frame

runner = CliRunner()


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    # self-contained snapshot: universe metadata embedded (ADR-0003)
    snapshot = pd.DataFrame(
        {
            "symbol": ["AIR.PA", "SAP.DE", "AAPL", "7203.T"],
            "period": ["2025"] * 4,
            "piotroski_f": [8, 7, 9, 5],
            "altman_z": [3.2, 4.1, 6.0, 2.2],
            "beneish_m": [-2.5, -2.9, -2.7, -2.1],
            "return_on_equity": [0.18, 0.22, 0.45, 0.11],
            "name": ["Airbus", "SAP", "Apple", "Toyota"],
            "country": ["FR", "DE", "US", "JP"],
            "sector": ["Industrials", "Information Technology", "Information Technology", "Consumer Discretionary"],
            "computed_at": [time.time()] * 4,
        }
    )
    publish_snapshot(snapshot, tmp_path)
    return tmp_path


def test_fr005_screen_csv_streams_rows_with_header(data_dir) -> None:
    result = runner.invoke(
        app, ["screen", "piotroski_f >= 7 AND country IN ('FR','DE')", "--format", "csv", "--sort", "-piotroski_f"]
    )
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.strip().splitlines() if line]
    assert lines[0].startswith("symbol")
    assert "AIR.PA" in result.output and "SAP.DE" in result.output
    assert "AAPL" not in result.output


def test_fr005_fields_lists_the_dsl_whitelist_with_types(data_dir) -> None:
    result = runner.invoke(app, ["fields"])
    assert result.exit_code == 0, result.output
    assert "piotroski_f\tnumber" in result.output
    assert "country\tstring" in result.output


def test_fr005_data_dir_option_selects_the_dataset(data_dir, monkeypatch) -> None:
    monkeypatch.delenv("CRIBLE_DATA_DIR")
    result = runner.invoke(app, ["--data-dir", str(data_dir), "fields"])
    assert result.exit_code == 0, result.output
    assert "piotroski_f\tnumber" in result.output


def test_fr005_fields_without_snapshot_hints_bootstrap(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path / "empty"))
    result = runner.invoke(app, ["fields"])
    assert result.exit_code == 1
    assert "bootstrap" in result.output


def test_fr005_invalid_dsl_exits_nonzero_with_actionable_error(data_dir) -> None:
    result = runner.invoke(app, ["screen", "roe >"])
    assert result.exit_code != 0
    assert "invalid query" in result.output


def test_fr005_missing_snapshot_names_the_next_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    result = runner.invoke(app, ["screen", "piotroski_f >= 7"])
    assert result.exit_code != 0
    assert "crible ingest" in result.output or "ingest" in result.output


def test_fr005_status_reports_universe_coverage_fast(data_dir) -> None:
    start = time.monotonic()
    result = runner.invoke(app, ["status"])
    took = time.monotonic() - start
    assert result.exit_code == 0
    assert '"universe": 8' in result.output
    assert '"snapshot": true' in result.output
    assert took < 2.0


def test_fr005_export_writes_full_result_set(data_dir, tmp_path) -> None:
    out = tmp_path / "export.csv"
    result = runner.invoke(app, ["export", "piotroski_f >= 5", "--out", str(out)])
    assert result.exit_code == 0, result.output
    written = pd.read_csv(out)
    assert len(written) == 4  # full result set, not a page


def test_fr005_presets_are_visible_editable_dsl(data_dir) -> None:
    result = runner.invoke(app, ["presets"])
    assert result.exit_code == 0
    assert "piotroski-strong" in result.output
    assert "piotroski_f >= 7" in result.output  # the full DSL is printed
    result2 = runner.invoke(app, ["screen", "--preset", "piotroski-strong", "--format", "csv"])
    assert result2.exit_code == 0
    assert "AAPL" in result2.output


def test_fr005_status_exposes_coverage_freshness_and_provider_health(data_dir) -> None:
    """FR-005 AC-3: coverage %, freshness histogram, req/h and provider health
    all surface through crible status (via the ingest heartbeat)."""
    import json as _json

    heartbeat = {
        "requests_last_hour": 42,
        "budget_per_hour": 330,
        "coverage_pct": 3.2,
        "freshness": {"<7d": 6, "never": 2},
        "providers": {"yfinance": "healthy"},
        "esef_unmatched": 3,
    }
    (data_dir / "status.json").write_text(_json.dumps(heartbeat))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    body = _json.loads(result.output)
    ingest = body["ingest"]
    assert ingest["coverage_pct"] == 3.2
    assert ingest["freshness"]["<7d"] == 6
    assert ingest["requests_last_hour"] == 42
    assert ingest["providers"]["yfinance"] == "healthy"
    assert ingest["esef_unmatched"] == 3  # FR-010 AC-4 visibility
    assert body["by_region"]["europe"] == 6


def test_fr005_compute_is_incremental_and_skips_when_unchanged(tmp_path, monkeypatch) -> None:
    """The CLI `compute` must use the incremental path (F7): write the base
    cache and, on a second run with no raw change, skip the republish."""
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    from crible.ingest.raw import write_raw_statement

    write_raw_statement(
        tmp_path, symbol="AIR.PA", provider="yfinance", statement_type="income",
        freq="annual", frame=pd.DataFrame({"period": ["2024"], "TotalRevenue": [100.0]}),
        fetched_at=1000.0,
    )

    first = runner.invoke(app, ["compute"])
    assert first.exit_code == 0, first.output
    assert "published" in first.output
    assert (tmp_path / "snapshot" / "base.parquet").exists()  # incremental cache written

    second = runner.invoke(app, ["compute"])
    assert second.exit_code == 0, second.output
    assert "unchanged" in second.output.lower()  # no raw change → no republish
