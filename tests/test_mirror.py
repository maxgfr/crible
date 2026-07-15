"""FR-021 — Local-first bulk mirror with a last-good guarantee (F4 / local-first pillar).

Every bulk source's archive is fetched once to data/mirror/<source>/, kept as
last-good, and re-fetched only when stale. In steady state ingestion reads the
local mirror; on a network failure it falls back to the last-good copy so
coverage never regresses — and a run can be fully offline.
"""

from __future__ import annotations

import pytest

from crible.ingest.mirror import MirrorError, fetch_if_stale

URL = "https://example.test/archive.bin"


class FakeResp:
    def __init__(self, status: int, body: bytes, etag: str | None = None) -> None:
        self.status_code = status
        self._body = body
        self.headers = {"ETag": etag} if etag else {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_bytes(self, chunk_size: int = 0):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeHttp:
    def __init__(self, body: bytes = b"data", fail: bool = False, etag: str | None = None) -> None:
        self.body = body
        self.fail = fail
        self.etag = etag
        self.calls = 0

    def stream(self, method: str, url: str, headers=None):
        self.calls += 1
        if self.fail:
            raise ConnectionError("offline")
        return FakeResp(200, self.body, self.etag)


def test_mirror_downloads_then_serves_from_cache(tmp_path) -> None:
    http = FakeHttp(body=b"companyfacts")
    r1 = fetch_if_stale(
        tmp_path, "edgar", "companyfacts.zip", URL,
        http=http, max_age_seconds=1e9, now=lambda: 1000.0,
    )
    assert r1.source == "downloaded"
    assert r1.path.read_bytes() == b"companyfacts"
    assert http.calls == 1

    # within max_age → served from the local mirror, no second network hit
    r2 = fetch_if_stale(
        tmp_path, "edgar", "companyfacts.zip", URL,
        http=http, max_age_seconds=1e9, now=lambda: 1500.0,
    )
    assert r2.source == "cached"
    assert http.calls == 1


def test_mirror_falls_back_to_last_good_when_offline(tmp_path) -> None:
    ok = FakeHttp(body=b"v1")
    fetch_if_stale(
        tmp_path, "gleif", "isin-lei.csv", URL,
        http=ok, max_age_seconds=0, now=lambda: 1000.0,
    )
    # stale (max_age 0) forces a re-fetch, but the network is down → last-good
    down = FakeHttp(fail=True)
    r = fetch_if_stale(
        tmp_path, "gleif", "isin-lei.csv", URL,
        http=down, max_age_seconds=0, now=lambda: 2000.0,
    )
    assert r.source == "last-good"
    assert r.path.read_bytes() == b"v1"
    assert down.calls == 1  # it did try


def test_mirror_without_last_good_raises_when_offline(tmp_path) -> None:
    with pytest.raises(MirrorError):
        fetch_if_stale(
            tmp_path, "gleif", "isin-lei.csv", URL,
            http=FakeHttp(fail=True), max_age_seconds=0, now=lambda: 1000.0,
        )


def test_mirror_aborts_a_response_over_the_size_ceiling(tmp_path) -> None:
    """A pathological/huge response must not fill the disk — the stream aborts
    past max_bytes and leaves no partial file behind."""
    with pytest.raises(MirrorError):
        fetch_if_stale(
            tmp_path, "edgar", "companyfacts.zip", URL,
            http=FakeHttp(body=b"x" * 5000), max_age_seconds=0, now=lambda: 1000.0,
            max_bytes=1000,
        )
    # no partial download left behind
    assert not (tmp_path / "mirror" / "edgar" / "companyfacts.zip").exists()
    assert not list((tmp_path / "mirror" / "edgar").glob("*.tmp")) if (tmp_path / "mirror" / "edgar").exists() else True
