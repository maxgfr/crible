"""Local-first bulk mirror with a last-good guarantee.

Every bulk source crible ingests (SEC companyfacts / FSDS, GLEIF ISIN-LEI,
Companies House, ECB FX…) is fetched ONCE to ``data/mirror/<source>/<name>``,
kept as the last-good copy, and re-fetched only when it goes stale — with an
``If-None-Match`` conditional request so an unchanged re-fetch is nearly free.

In steady state the ingestion reads the local mirror, never a live
per-record API; on a network failure it serves the last-good copy so coverage
NEVER regresses — and a whole refresh can run fully offline from the mirror.
This is the "self-hosted at the call level" contract.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

log = logging.getLogger("crible.ingest.mirror")

DEFAULT_MAX_AGE = 24 * 3600  # a day: bulk sources refresh at most daily


class MirrorError(RuntimeError):
    """The archive is neither fresh in the mirror nor reachable (no last-good)."""


@dataclass(frozen=True)
class MirrorResult:
    path: Path
    source: str  # "downloaded" | "cached" | "last-good"


def mirror_path(data_dir: Path | str, source: str, name: str) -> Path:
    return Path(data_dir) / "mirror" / source / name


def _read_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_meta(meta_path: Path, data: dict) -> None:
    """Atomic sidecar write — a crash mid-write must not leave a truncated meta
    that then reads as {} and forces a needless full re-download (F4)."""
    tmp = meta_path.with_name(meta_path.name + ".tmp")
    tmp.write_text(json.dumps(data))
    tmp.rename(meta_path)


def fetch_if_stale(
    data_dir: Path | str,
    source: str,
    name: str,
    url: str,
    *,
    http=None,
    headers: dict | None = None,
    max_age_seconds: float = DEFAULT_MAX_AGE,
    now: Callable[[], float] = time.time,
    chunk: int = 1 << 20,
) -> MirrorResult:
    """Ensure the mirror holds a usably-fresh copy of ``url`` and return it.

    Serves the cached copy without a network hit when it is younger than
    ``max_age_seconds``; otherwise streams a refresh (conditional on the stored
    ETag). On any network failure it returns the existing last-good copy, and
    only raises ``MirrorError`` when there is none.
    """
    path = mirror_path(data_dir, source, name)
    meta_path = path.with_name(path.name + ".meta.json")
    meta = _read_meta(meta_path)

    if path.exists() and (now() - float(meta.get("fetched_at", float("-inf"))) < max_age_seconds):
        return MirrorResult(path=path, source="cached")

    if http is None:
        import httpx

        http = httpx.Client(timeout=120, follow_redirects=True)

    request_headers = dict(headers or {})
    if meta.get("etag") and path.exists():
        request_headers["If-None-Match"] = meta["etag"]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with http.stream("GET", url, headers=request_headers) as response:
            if getattr(response, "status_code", 200) == 304 and path.exists():
                _write_meta(meta_path, {**meta, "fetched_at": now()})
                return MirrorResult(path=path, source="cached")
            response.raise_for_status()
            tmp = path.with_name(path.name + ".tmp")
            with open(tmp, "wb") as out:
                for block in response.iter_bytes(chunk):
                    out.write(block)
            tmp.rename(path)
        etag = getattr(response, "headers", {}) or {}
        _write_meta(meta_path, {"etag": etag.get("ETag"), "fetched_at": now()})
        log.info("mirror: refreshed %s/%s from %s", source, name, url)
        return MirrorResult(path=path, source="downloaded")
    except Exception as exc:  # noqa: BLE001 — never regress coverage on a hiccup
        if path.exists():
            log.warning(
                "mirror: %s/%s fetch failed (%s) — serving last-good copy", source, name, exc
            )
            return MirrorResult(path=path, source="last-good")
        raise MirrorError(f"{source}/{name}: no last-good copy and fetch failed: {exc}") from exc
