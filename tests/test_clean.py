"""`crible clean` — remove the local dataset directory (uninstall path)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from crible.cli import app

runner = CliRunner()


@pytest.fixture()
def marked_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / "universe.parquet").write_bytes(b"parquet")
    (tmp_path / "crible.duckdb").write_bytes(b"duckdb")
    (tmp_path / "raw").mkdir()
    return tmp_path


def test_clean_recognises_a_raw_layout_without_universe(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / "raw" / "provider=yfinance" / "symbol=AAPL").mkdir(parents=True)
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 0, result.output
    assert not tmp_path.exists()


def test_clean_refuses_an_empty_provider_folder(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / "raw" / "provider=x").mkdir(parents=True)
    (tmp_path / "thesis.tex").write_text("years of work")
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 1
    assert (tmp_path / "thesis.tex").exists()


@pytest.mark.parametrize("folder", ["raw", "snapshot"])
def test_clean_refuses_a_project_dir_that_merely_has_a_raw_folder(tmp_path, monkeypatch, folder) -> None:
    """`crible --data-dir ~/work clean -y` must not delete ~/work because it
    happens to contain a raw/ (or snapshot/) folder."""
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / folder).mkdir()
    (tmp_path / "thesis.tex").write_text("years of work")
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 1
    assert (tmp_path / "thesis.tex").exists()


def test_clean_removes_a_marked_dataset_dir(marked_dir) -> None:
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 0, result.output
    assert not marked_dir.exists()
    assert "removed" in result.output


def test_clean_refuses_a_dir_without_crible_markers(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / "précieux.txt").write_text("pas un dataset")
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 1
    assert tmp_path.exists()
    assert (tmp_path / "précieux.txt").exists()
    assert "does not look like a crible dataset" in result.output


def test_clean_is_a_noop_when_the_dir_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path / "absent"))
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 0, result.output
    assert "nothing to clean" in result.output


def test_clean_aborts_when_confirmation_is_declined(marked_dir) -> None:
    result = runner.invoke(app, ["clean"], input="n\n")
    assert result.exit_code != 0
    assert marked_dir.exists()
    assert (marked_dir / "universe.parquet").exists()


def test_clean_refuses_a_folder_holding_only_downloaded_assets(tmp_path, monkeypatch) -> None:
    """universe.parquet and snapshot.parquet are release assets anyone can
    download: ~/Downloads holding them is not a crible dataset."""
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / "universe.parquet").write_bytes(b"parquet")
    (tmp_path / "snapshot.parquet").write_bytes(b"parquet")
    (tmp_path / "taxes-2025.pdf").write_bytes(b"%PDF")
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 1
    assert (tmp_path / "taxes-2025.pdf").exists()


@pytest.mark.parametrize("marker", ["crible.duckdb", "snapshot/base-schema.json", ".restored-manifest.json"])
def test_clean_recognises_each_crible_written_marker(tmp_path, monkeypatch, marker) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / marker).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / marker).write_text("{}")
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 0, result.output
    assert not tmp_path.exists()


def test_clean_follows_a_symlinked_data_dir(tmp_path, monkeypatch) -> None:
    """data -> /mnt/disk/crible-data: rmtree refused the link with a
    traceback. The dataset it points to is removed, then the link."""
    real = tmp_path / "disk" / "crible-data"
    (real / "raw" / "provider=yfinance" / "symbol=AAPL").mkdir(parents=True)
    link = tmp_path / "data"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(link))
    result = runner.invoke(app, ["clean", "--yes"])
    assert result.exit_code == 0, result.output
    assert not real.exists() and not link.is_symlink()
    assert (tmp_path / "disk").exists()  # only the dataset went
