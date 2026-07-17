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
    (tmp_path / "raw").mkdir()
    return tmp_path


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
