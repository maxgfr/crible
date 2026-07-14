"""FIX-002 / F6 — GLEIF ISIN→LEI auto-fetch unlocks the idle audited-EU layer.

The whole ESEF enrichment stays idle out-of-the-box because nothing downloads
the GLEIF relationship file. `crible ingest --fetch-gleif` streams it into the
local mirror, and load_mapping then finds it there — so a fresh self-hosted
install gets audited EU coverage without any manual step.
"""

from __future__ import annotations

import io
import zipfile

from crible.providers.gleif import fetch_gleif, load_mapping

GLEIF_CSV = b"LEI,ISIN\n969500A1G9QKR8Q79815,FR0000121014\n529900D6BF99LW9R2E68,DE0007164600\n"


def _zip(csv: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("isin-lei.csv", csv)
    return buf.getvalue()


class FakeResp:
    def __init__(self, body: bytes) -> None:
        self.status_code = 200
        self._body = body
        self.headers = {}

    def raise_for_status(self) -> None:
        pass

    def iter_bytes(self, chunk_size: int = 0):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeHttp:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls = 0

    def stream(self, method: str, url: str, headers=None):
        self.calls += 1
        return FakeResp(self.body)


def test_fetch_gleif_populates_the_mirror_and_load_mapping_reads_it(tmp_path) -> None:
    http = FakeHttp(_zip(GLEIF_CSV))
    path = fetch_gleif(tmp_path, http=http)

    assert path.exists()
    assert "mirror" in path.parts and "gleif" in path.parts  # landed in the local mirror

    mapping, skipped, outage = load_mapping(tmp_path)
    assert skipped is None and outage is None
    assert mapping["FR0000121014"] == "969500A1G9QKR8Q79815"
    assert mapping["DE0007164600"] == "529900D6BF99LW9R2E68"
