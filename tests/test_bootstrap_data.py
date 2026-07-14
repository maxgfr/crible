"""crible bootstrap — initialize data/ from the published open dataset:
release assets first, data branch fallback, safe tar extraction, and
never clobbering an existing layer without --force."""

from __future__ import annotations

import io
import tarfile

import pandas as pd
import pytest
from typer.testing import CliRunner

from crible.bootstrap import (
    BootstrapDataReport,
    BootstrapError,
    bootstrap_data,
    branch_tarball_url,
    release_asset_url,
)
from crible.cli import app

REPO = "maxgfr/crible"


def _parquet_bytes() -> bytes:
    buf = io.BytesIO()
    pd.DataFrame({"symbol": ["AAPL"], "name": ["Apple"]}).to_parquet(buf, index=False)
    return buf.getvalue()


def _tarball(names: list[str]) -> bytes:
    payload = _parquet_bytes()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as archive:
        for name in names:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


RELEASE_TAR = _tarball(
    [
        "data/universe.parquet",
        "data/snapshot/snapshot.parquet",
        "data/raw/provider=yfinance/symbol=AAPL/income-annual-000000000001000.parquet",
    ]
)
# the codeload branch tarball prefixes everything with <repo>-<branch>/ and
# also carries site-data/, which bootstrap must ignore
BRANCH_TAR = _tarball(
    [
        "crible-data/data/universe.parquet",
        "crible-data/data/snapshot/snapshot.parquet",
        "crible-data/site-data/universe.parquet",
    ]
)
HOSTILE_TAR = _tarball(
    [
        "data/../escaped.parquet",
        "data/universe.parquet",
    ]
)


class FakeResponse:
    """A streamed HTTP response. Accessing ``.content`` is a hard error — F13:
    bootstrap must stream the (multi-hundred-MB) archive to disk, never buffer
    the whole thing in memory (OOM on a small self-hosted host)."""

    def __init__(self, status_code: int, body: bytes = b"", chunk: int = 1 << 16) -> None:
        self.status_code = status_code
        self._body = body
        self._chunk = chunk

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    @property
    def content(self) -> bytes:
        raise AssertionError("bootstrap must stream, not buffer response.content")

    def iter_bytes(self, chunk_size: int = 0):
        size = chunk_size or self._chunk
        for i in range(0, len(self._body), size):
            yield self._body[i : i + size]

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc) -> bool:
        return False


class FakeHttp:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def stream(self, method: str, url: str, **_) -> FakeResponse:
        self.calls.append(url)
        return self.responses.get(url, FakeResponse(404))


def test_bootstrap_prefers_the_release_asset(tmp_path) -> None:
    http = FakeHttp({release_asset_url(REPO): FakeResponse(200, RELEASE_TAR)})
    report = bootstrap_data(tmp_path / "data", repo=REPO, http=http)
    assert report.source == "release" and report.files == 3
    assert (tmp_path / "data" / "universe.parquet").exists()
    assert (tmp_path / "data" / "snapshot" / "snapshot.parquet").exists()
    assert (tmp_path / "data" / "raw" / "provider=yfinance" / "symbol=AAPL").is_dir()
    assert http.calls == [release_asset_url(REPO)]  # the branch is never hit


def test_bootstrap_streams_the_archive_without_buffering(tmp_path) -> None:
    """F13 — the published archive is streamed to a temp file, never buffered
    whole in memory. FakeResponse.content raises, so any success proves the
    streaming path; tiny chunks exercise the iter_bytes loop."""
    http = FakeHttp({release_asset_url(REPO): FakeResponse(200, RELEASE_TAR, chunk=8)})
    report = bootstrap_data(tmp_path / "data", repo=REPO, http=http)
    assert report.source == "release" and report.files == 3
    assert (tmp_path / "data" / "universe.parquet").exists()


def test_bootstrap_falls_back_to_the_data_branch(tmp_path) -> None:
    http = FakeHttp({branch_tarball_url(REPO): FakeResponse(200, BRANCH_TAR)})
    report = bootstrap_data(tmp_path / "data", repo=REPO, http=http)
    assert report.source == "branch" and report.files == 2
    assert http.calls == [release_asset_url(REPO), branch_tarball_url(REPO)]
    assert (tmp_path / "data" / "universe.parquet").exists()
    # site-data/ from the branch tarball is not part of the data/ layer
    assert not (tmp_path / "data" / "site-data").exists()


def test_bootstrap_refuses_an_existing_dataset_without_force(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "universe.parquet").write_bytes(b"precious")
    http = FakeHttp({release_asset_url(REPO): FakeResponse(200, RELEASE_TAR)})
    with pytest.raises(BootstrapError, match="--force"):
        bootstrap_data(data_dir, repo=REPO, http=http)
    assert http.calls == []  # refused before any download
    assert (data_dir / "universe.parquet").read_bytes() == b"precious"

    report = bootstrap_data(data_dir, repo=REPO, http=http, force=True)
    assert report.source == "release"
    assert (data_dir / "universe.parquet").read_bytes() != b"precious"


def test_bootstrap_rejects_path_traversal_members(tmp_path) -> None:
    http = FakeHttp({release_asset_url(REPO): FakeResponse(200, HOSTILE_TAR)})
    report = bootstrap_data(tmp_path / "data", repo=REPO, http=http)
    assert report.files == 1  # only the honest member
    assert (tmp_path / "data" / "universe.parquet").exists()
    escaped = [p for p in tmp_path.rglob("escaped.parquet")]
    assert escaped == []  # nothing landed outside the data layer


def test_bootstrap_errors_when_nothing_is_published(tmp_path) -> None:
    http = FakeHttp({})
    with pytest.raises(BootstrapError, match="no published dataset"):
        bootstrap_data(tmp_path / "data", repo=REPO, http=http)
    assert not (tmp_path / "data").exists()  # no partial layer left behind


def test_bootstrap_cli_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path / "data"))

    def fake_bootstrap(data_dir, repo=None, http=None, force=False):
        return BootstrapDataReport(source="release", files=3)

    monkeypatch.setattr("crible.bootstrap.bootstrap_data", fake_bootstrap)
    result = CliRunner().invoke(app, ["bootstrap"])
    assert result.exit_code == 0, result.output
    assert "3 files from the release" in result.output


def test_bootstrap_cli_surfaces_errors(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path / "data"))

    def failing_bootstrap(data_dir, repo=None, http=None, force=False):
        raise BootstrapError("no published dataset found")

    monkeypatch.setattr("crible.bootstrap.bootstrap_data", failing_bootstrap)
    result = CliRunner().invoke(app, ["bootstrap"])
    assert result.exit_code == 1
