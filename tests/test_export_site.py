"""Site export — the static artifacts the hosted screener runs on.

`export_site` publishes the universe + snapshot Parquet, the price-series
shards and the JSON surfaces (presets/providers/status/manifest) into an
output directory, and is the "never publish an empty dataset" gate: it fails
below a minimum symbol count so the nightly workflow keeps the last-good
data instead.
"""

from __future__ import annotations

import json

import duckdb
import pandas as pd
import pytest
from typer.testing import CliRunner

from crible.cli import app
from crible.compute.snapshot import publish_snapshot
from crible.site_export import SiteExportError, export_site
from crible.universe import bootstrap_universe, export_universe_parquet

from tests.test_fr001_universe import fixture_frame


def make_snapshot(symbols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": symbols,
            "period": ["2025"] * len(symbols),
            "revenue": [100.0] * len(symbols),
            "piotroski_f": [7] * len(symbols),
            # attach_universe embeds region in every real snapshot
            "region": ["europe" if s.endswith((".PA", ".DE")) else "us" for s in symbols],
        }
    )


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect()
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    publish_snapshot(make_snapshot(["AIR.PA", "SAP.DE", "AAPL"]), tmp_path)
    (tmp_path / "status.json").write_text(json.dumps({"requests_last_hour": 12}))
    return tmp_path


def test_export_site_emits_all_artifacts_and_manifest(data_dir, tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("site")
    manifest = export_site(data_dir, out, min_symbols=2)

    for name in (
        "universe.parquet", "snapshot.parquet", "presets.json",
        "providers.json", "status.json", "manifest.json",
    ):
        assert (out / name).exists(), name

    assert manifest["schema"] == 2
    assert manifest["universe_rows"] == 8
    assert manifest["snapshot_rows"] == 3
    assert manifest["snapshot_symbols"] == 3
    # coverage honesty: covered companies split by region, symbols sum up
    assert manifest["snapshot_by_region"] == {"europe": 2, "us": 1}
    assert manifest["prices"] is None  # no series in this fixture — enrichment, not a gate
    assert not list(out.glob("prices-*.parquet"))
    assert isinstance(manifest["sample"], list) and manifest["sample"]
    assert manifest["generated_at"] > 0
    assert json.loads((out / "manifest.json").read_text()) == json.loads(
        json.dumps(manifest)
    )
    # the exported parquets are readable and complete
    con = duckdb.connect()
    assert con.execute(
        f"SELECT count(*) FROM read_parquet('{(out / 'universe.parquet').as_posix()}')"
    ).fetchone()[0] == 8
    assert con.execute(
        f"SELECT count(DISTINCT symbol) FROM read_parquet('{(out / 'snapshot.parquet').as_posix()}')"
    ).fetchone()[0] == 3


def test_export_site_ships_the_price_series_shards(data_dir, tmp_path_factory) -> None:
    from tests.test_price_series import write_yf_bars, yf_frame

    write_yf_bars(data_dir, "AIR.PA", yf_frame(days=5, start="2026-03-02"))
    out = tmp_path_factory.mktemp("site")
    manifest = export_site(data_dir, out, min_symbols=2)

    assert manifest["prices"]["symbols"] == 1
    assert manifest["prices"]["bars"] == 5
    assert manifest["prices"]["max_date"] == "2026-03-06"
    (shard,) = manifest["prices"]["shards"]
    assert (out / shard["file"]).exists()
    table = pd.read_parquet(out / shard["file"])
    assert list(table["symbol"].unique()) == ["AIR.PA"]
    assert str(table["date"].iloc[0]) == "2026-03-02"


def test_export_site_presets_are_the_shipped_presets(data_dir, tmp_path_factory) -> None:
    from crible.presets import PRESETS

    out = tmp_path_factory.mktemp("site")
    export_site(data_dir, out, min_symbols=2)
    presets = json.loads((out / "presets.json").read_text())
    assert [p["id"] for p in presets] == list(PRESETS)
    assert all(set(p) == {"id", "name", "description", "dsl", "columns"} for p in presets)
    # every shipped preset publishes the columns it surfaces on pick
    assert all(isinstance(p["columns"], list) and p["columns"] for p in presets)


def test_export_site_providers_reflect_keyless_zero_env(data_dir, tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("site")
    export_site(data_dir, out, min_symbols=2)
    providers = {p["id"]: p for p in json.loads((out / "providers.json").read_text())}
    assert providers["yfinance"]["enabled"] is True  # keyless
    assert all(not p["enabled"] for p in providers.values() if p["kind"] != "keyless")


def test_export_site_status_has_no_local_paths(data_dir, tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("site")
    export_site(data_dir, out, min_symbols=2)
    status = json.loads((out / "status.json").read_text())
    assert "data_dir" not in status
    assert status["universe"] == 8
    assert status["snapshot"] is True
    assert status["ingest"]["requests_last_hour"] == 12


def test_export_site_guard_refuses_missing_snapshot(tmp_path, monkeypatch, tmp_path_factory) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect()
    bootstrap_universe(con, fixture_frame())
    export_universe_parquet(con, tmp_path)
    con.close()
    with pytest.raises(SiteExportError):
        export_site(tmp_path, tmp_path_factory.mktemp("site"), min_symbols=2)


def test_export_site_guard_refuses_undersized_snapshot(data_dir, tmp_path_factory) -> None:
    with pytest.raises(SiteExportError, match="4"):
        export_site(data_dir, tmp_path_factory.mktemp("site"), min_symbols=4)


def test_export_site_guard_leaves_no_partial_output(data_dir, tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("site")
    with pytest.raises(SiteExportError):
        export_site(data_dir, out, min_symbols=4)
    assert not (out / "snapshot.parquet").exists()
    assert not (out / "manifest.json").exists()


def test_export_site_cli_command(data_dir, tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("site")
    result = CliRunner().invoke(app, ["export-site", "--out", str(out), "--min-symbols", "2"])
    assert result.exit_code == 0, result.output
    assert (out / "manifest.json").exists()


def test_export_site_cli_guard_exits_nonzero(data_dir, tmp_path_factory) -> None:
    out = tmp_path_factory.mktemp("site")
    result = CliRunner().invoke(app, ["export-site", "--out", str(out), "--min-symbols", "4"])
    assert result.exit_code == 1
