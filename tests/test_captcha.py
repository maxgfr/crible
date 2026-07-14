"""Captcha OCR + the automated Stooq download flow.

The OCR test runs only when the optional `captcha` extra (ddddocr) is
installed; the proof-of-work and download-orchestration tests are pure and
network-free (a fake HTTP session stands in for Stooq).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from crible.ingest import stooq_fetch
from crible.ingest.stooq_fetch import StooqDownloader, StooqError, solve_pow

FIXTURES = Path(__file__).parent / "fixtures" / "captcha"


# --- Layer 1: proof-of-work (pure) ---------------------------------------
@pytest.mark.parametrize("difficulty", [1, 2, 3])
def test_solve_pow_hits_the_target(difficulty: int) -> None:
    challenge = "AAAAsome-challenge-blob"
    n = solve_pow(challenge, difficulty)
    digest = hashlib.sha256(f"{challenge}{n}".encode()).hexdigest()
    assert digest.startswith("0" * difficulty)
    # minimality: no smaller nonce works
    assert all(
        not hashlib.sha256(f"{challenge}{k}".encode()).hexdigest().startswith("0" * difficulty)
        for k in range(n)
    )


def test_solve_pow_rejects_an_infeasible_server_difficulty() -> None:
    """F12 — the difficulty is served by Stooq; an absurd value must abort, not
    spin the CPU forever (a trivial DoS, made worse by the missing watchdog)."""
    with pytest.raises(StooqError):
        solve_pow("challenge", 16, max_iterations=10_000)


def test_solve_pow_aborts_when_the_iteration_bound_is_exhausted() -> None:
    with pytest.raises(StooqError):
        solve_pow("challenge", 4, max_iterations=1)


# --- Layer 2 + download: orchestration against a fake session ------------
class _Resp:
    def __init__(self, *, text: str = "", content: bytes = b"", chunks=None) -> None:
        self.text = text
        self.content = content
        self._chunks = chunks or []

    def raise_for_status(self) -> None:  # pragma: no cover - trivial
        pass

    def iter_bytes(self, chunk_size: int = 0):
        yield from self._chunks

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeStooq:
    """Minimal stand-in: serves a trivial PoW page, a captcha, a verdict, a zip."""

    def __init__(self, *, verdict: str = "1", zip_chunks=(b"PK\x03\x04", b"body")) -> None:
        self.verdict = verdict
        self.zip_chunks = list(zip_chunks)
        self.calls: list[tuple[str, str]] = []

    def get(self, url, params=None):
        self.calls.append(("GET", url))
        if url == stooq_fetch.DB_PAGE:
            return _Resp(text='<script>c="abc",d=1</script>')
        if url == stooq_fetch.CAPTCHA_IMAGE_URL:
            return _Resp(content=b"fake-image")
        if url == stooq_fetch.CAPTCHA_CHECK_URL:
            return _Resp(text=self.verdict)
        return _Resp()

    def post(self, url, data=None, headers=None):
        self.calls.append(("POST", url))
        return _Resp()

    def stream(self, method, url, params=None):
        self.calls.append((method, url))
        return _Resp(chunks=self.zip_chunks)

    def close(self):  # pragma: no cover - trivial
        pass


def test_download_writes_zip_after_pow_and_captcha(tmp_path) -> None:
    fake = _FakeStooq()
    dl = StooqDownloader(http=fake, ocr=lambda _img: "ab12")
    out = dl.download("d_hu_txt", tmp_path / "hu.zip")
    assert out.read_bytes() == b"PK\x03\x04body"
    # the PoW handshake and the captcha check both happened
    assert ("POST", stooq_fetch.VERIFY_URL) in fake.calls
    assert ("GET", stooq_fetch.CAPTCHA_CHECK_URL) in fake.calls


def test_download_retries_captcha_then_gives_up(tmp_path) -> None:
    fake = _FakeStooq(verdict="2")  # Stooq always rejects the code
    dl = StooqDownloader(http=fake, ocr=lambda _img: "ab12")
    with pytest.raises(StooqError, match="captcha"):
        dl.download("d_hu_txt", tmp_path / "hu.zip", attempts=3)
    assert sum(c == ("GET", stooq_fetch.CAPTCHA_CHECK_URL) for c in fake.calls) == 3


def test_download_rejects_unknown_dataset_code(tmp_path) -> None:
    dl = StooqDownloader(http=_FakeStooq(), ocr=lambda _img: "ab12")
    with pytest.raises(StooqError, match="dataset code"):
        dl.download("not-a-code", tmp_path / "x.zip")


def test_download_surfaces_a_non_zip_refusal(tmp_path) -> None:
    fake = _FakeStooq(zip_chunks=(b"Unauthorized\n",))
    dl = StooqDownloader(http=fake, ocr=lambda _img: "ab12")
    with pytest.raises(StooqError, match="not a zip"):
        dl.download("d_hu_txt", tmp_path / "hu.zip")


def test_authorize_skips_wrong_length_codes(tmp_path) -> None:
    fake = _FakeStooq()
    # OCR returns a 5-char code → never submitted, so no authorisation
    dl = StooqDownloader(http=fake, ocr=lambda _img: "abcde")
    assert dl.authorize(attempts=2) is False
    assert ("GET", stooq_fetch.CAPTCHA_CHECK_URL) not in fake.calls


# --- OCR model (needs the optional extra) --------------------------------
def test_ddddocr_decodes_stooq_fixtures() -> None:
    pytest.importorskip("ddddocr", reason="install the 'captcha' extra to run OCR tests")
    from crible.ingest.captcha import solve_captcha

    fixtures = sorted(FIXTURES.glob("*.png"))
    assert fixtures, "no captcha fixtures bundled"
    for image in fixtures:
        assert solve_captcha(image.read_bytes()) == image.stem
