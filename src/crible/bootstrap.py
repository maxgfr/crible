"""Bootstrap a self-hosted data/ from the published open dataset — zero crawl.

The nightly refresh publishes the dataset twice: as GitHub Release assets on
the rolling ``data-latest`` release (preferred — a stable download URL) and as
the orphan ``demo-data`` branch (fallback — exists as soon as the first
refresh ran). ``crible bootstrap`` pulls whichever answers first, extracts
only the ``data/`` layer (safe extraction: no links, no path escapes), and
leaves keeping it fresh to the normal ingest loop.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

log = logging.getLogger("crible.bootstrap")

DATA_RELEASE_TAG = "data-latest"
DATA_ASSET_NAME = "crible-data.tar.gz"


class BootstrapError(RuntimeError):
    pass


@dataclass(frozen=True)
class BootstrapDataReport:
    source: str  # "release" | "branch"
    files: int


def default_repo() -> str:
    return os.environ.get("CRIBLE_DATA_REPO", "maxgfr/crible")


def release_asset_url(repo: str) -> str:
    return f"https://github.com/{repo}/releases/download/{DATA_RELEASE_TAG}/{DATA_ASSET_NAME}"


def branch_tarball_url(repo: str) -> str:
    return f"https://codeload.github.com/{repo}/tar.gz/refs/heads/demo-data"


def _data_relpath(name: str) -> PurePosixPath | None:
    """The member's path inside the data/ layer, or None to skip it.

    The release tarball roots members at ``data/…``; the codeload branch
    tarball prefixes them with ``<repo>-demo-data/``. Anything outside data/
    (site-data, README…) and anything path-traversing is skipped.
    """
    parts = PurePosixPath(name).parts
    idx = None
    if parts and parts[0] == "data":
        idx = 0
    elif len(parts) > 1 and parts[1] == "data":
        idx = 1
    if idx is None:
        return None
    rel = PurePosixPath(*parts[idx:])
    if any(part in ("..", "", "/") for part in rel.parts):
        return None
    return rel


def _extract_data_layer(archive: tarfile.TarFile, dest: Path) -> int:
    """Extract the data/ layer under dest (which stands in for data/).

    Only regular files and directories, only under data/, never outside dest —
    symlinks/hardlinks/devices are dropped, not errors.
    """
    dest_resolved = dest.resolve()
    files = 0
    for member in archive:
        rel = _data_relpath(member.name)
        if rel is None or len(rel.parts) < 2:
            continue  # nothing directly useful at the data/ root itself
        target = dest.joinpath(*rel.parts[1:])
        if not target.resolve().is_relative_to(dest_resolved):
            continue  # path escape — hostile archive member
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if not member.isfile():
            continue  # links and specials are never extracted
        payload = archive.extractfile(member)
        if payload is None:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as handle:
            shutil.copyfileobj(payload, handle)
        files += 1
    return files


def _has_data(data_dir: Path) -> bool:
    return (data_dir / "universe.parquet").exists() or (data_dir / "snapshot").exists()


def _move_into(staging: Path, data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for entry in staging.iterdir():
        target = data_dir / entry.name
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        shutil.move(str(entry), str(target))


def bootstrap_data(
    data_dir: Path | str,
    repo: str | None = None,
    http=None,
    force: bool = False,
) -> BootstrapDataReport:
    """Initialize data_dir from the published dataset (release, then branch).

    Refuses to touch a data_dir that already holds a dataset unless ``force``
    — an operator's crawled data is never silently clobbered. Extraction goes
    through a staging directory so a failed download never leaves a partial
    layer behind.
    """
    data_dir = Path(data_dir)
    repo = repo or default_repo()
    if not force and _has_data(data_dir):
        raise BootstrapError(
            f"{data_dir} already contains a dataset (universe.parquet or snapshot/)"
            " — pass --force to overwrite it"
        )
    if http is None:
        import httpx

        http = httpx.Client(timeout=120, follow_redirects=True)

    attempts = [
        ("release", release_asset_url(repo)),
        ("branch", branch_tarball_url(repo)),
    ]
    last_error = "no attempt made"
    for source, url in attempts:
        try:
            response = http.get(url)
            if response.status_code == 404:
                last_error = f"{source} not published yet ({url})"
                continue
            response.raise_for_status()
            payload = io.BytesIO(response.content)
        except Exception as exc:  # noqa: BLE001 — try the next distribution channel
            last_error = f"{source}: {exc}"
            log.warning("bootstrap: %s — trying the next source", last_error)
            continue
        with tempfile.TemporaryDirectory(prefix=".crible-bootstrap-") as tmp:
            staging = Path(tmp) / "data"
            staging.mkdir()
            try:
                with tarfile.open(fileobj=payload, mode="r:gz") as archive:
                    files = _extract_data_layer(archive, staging)
            except tarfile.TarError as exc:
                last_error = f"{source}: unreadable archive: {exc}"
                continue
            if files == 0:
                last_error = f"{source}: archive contains no data/ layer"
                continue
            _move_into(staging, data_dir)
        log.info("bootstrap: restored %d files from the %s (%s)", files, source, url)
        return BootstrapDataReport(source=source, files=files)
    raise BootstrapError(f"no published dataset found for {repo} — last error: {last_error}")
