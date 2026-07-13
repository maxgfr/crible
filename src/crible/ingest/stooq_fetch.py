"""Automated Stooq bulk download — clears Stooq's two anti-bot layers so the
otherwise CAPTCHA-gated archives at stooq.com/db/h/ can be fetched headlessly.

The gate has two layers (both reverse-engineered from the live site, 2026-07):

- **Layer 1 — SHA-256 proof-of-work.** `/db/h/` serves a "verify your browser"
  JS challenge: find ``n`` such that ``SHA256(c + n)`` starts with ``d`` hex
  zeros, then ``POST /__verify`` to earn the ``auth`` cookie. A plain hash loop
  solves it in tens of thousands of iterations — no browser, no model.
- **Layer 2 — a 4-char alphanumeric image captcha.** `/q/l/s/i/` returns the
  image; the code is OCR'd (`crible.ingest.captcha`, ddddocr ~85% first-try),
  then validated at `/q/l/s/?t=<code>` (Stooq replies ``1`` on success), which
  authorises the session. `/db/d/?b=<dataset>` then streams the real zip.

Politeness & licensing: one archive per invocation, low volume. Stooq data is
personal-use licensed — crible never stores or republishes the SERIES, only the
derived rows produced by `import_stooq` (see docs/DATA-SOURCES.md).
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Callable

log = logging.getLogger("crible.ingest.stooq_fetch")

BASE = "https://stooq.com"
DB_PAGE = f"{BASE}/db/h/"
VERIFY_URL = f"{BASE}/__verify"
CAPTCHA_IMAGE_URL = f"{BASE}/q/l/s/i/"
CAPTCHA_CHECK_URL = f"{BASE}/q/l/s/"
DOWNLOAD_URL = f"{BASE}/db/d/"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Common ASCII bulk codes (prefix d_/h_/5_ = daily/hourly/5-min): d_world_txt is
# the worldwide set crible's universe draws from; regions cover the rest.
KNOWN_DATASETS = (
    "d_world_txt", "d_us_txt", "d_uk_txt", "d_jp_txt",
    "d_hk_txt", "d_pl_txt", "d_hu_txt", "d_macro_txt",
)
_DATASET_RE = re.compile(r"^[dh5]_[a-z]+_(txt|ms)$")
_POW_C_RE = re.compile(r'c="([^"]+)"')
_POW_D_RE = re.compile(r"d=(\d+)")
_CAPTCHA_LEN = 4


class StooqError(RuntimeError):
    """The Stooq download could not be completed (challenge, captcha or refusal)."""


def solve_pow(challenge: str, difficulty: int) -> int:
    """Return the smallest ``n`` where ``SHA256(challenge + n)`` starts with
    ``difficulty`` hex zeros (Stooq's Layer-1 hashcash)."""
    target = "0" * difficulty
    n = 0
    while not hashlib.sha256(f"{challenge}{n}".encode()).hexdigest().startswith(target):
        n += 1
    return n


class StooqDownloader:
    """Drives the PoW + captcha flow over one cookie-persistent HTTP session."""

    def __init__(self, http=None, ocr: Callable[[bytes], str] | None = None) -> None:
        if http is None:
            import httpx

            http = httpx.Client(
                timeout=90,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Referer": DB_PAGE},
            )
        self._http = http
        self._ocr = ocr  # defaults to crible.ingest.captcha.solve_captcha (lazy)

    # -- Layer 1 -----------------------------------------------------------
    def verify_browser(self) -> None:
        """Solve the proof-of-work challenge and earn the session's auth cookie."""
        html = self._http.get(DB_PAGE).text
        m_c, m_d = _POW_C_RE.search(html), _POW_D_RE.search(html)
        if not (m_c and m_d):
            return  # no challenge served — already verified
        n = solve_pow(m_c.group(1), int(m_d.group(1)))
        self._http.post(
            VERIFY_URL,
            data={"c": m_c.group(1), "n": n},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self._http.get(DB_PAGE)  # reload to establish the PHP session
        log.info("stooq: proof-of-work cleared")

    # -- Layer 2 -----------------------------------------------------------
    def authorize(self, attempts: int = 6) -> bool:
        """OCR the image captcha and validate it until Stooq authorises the
        session (or ``attempts`` run out). A fresh image is fetched per try."""
        ocr = self._ocr
        if ocr is None:
            from crible.ingest.captcha import solve_captcha

            ocr = solve_captcha
        for attempt in range(1, attempts + 1):
            image = self._http.get(
                CAPTCHA_IMAGE_URL, params={"_": int(time.time() * 1000)}
            ).content
            code = ocr(image)
            if len(code) != _CAPTCHA_LEN:
                log.debug("stooq captcha attempt %d: bad length %r", attempt, code)
                continue
            result = self._http.get(CAPTCHA_CHECK_URL, params={"t": code}).text.strip()
            if result == "1":
                log.info("stooq: captcha solved on attempt %d", attempt)
                return True
            log.debug("stooq captcha attempt %d rejected (%r)", attempt, code)
        return False

    # -- Download ----------------------------------------------------------
    def download(self, dataset: str, out: Path | str, attempts: int = 6) -> Path:
        """Fetch a bulk archive to ``out``. Streams to disk; validates the ZIP
        magic so an auth failure surfaces as a StooqError, not a corrupt file."""
        if not _DATASET_RE.match(dataset):
            raise StooqError(
                f"unexpected dataset code {dataset!r} — e.g. {', '.join(KNOWN_DATASETS[:4])}"
            )
        out = Path(out)
        self.verify_browser()
        if not self.authorize(attempts):
            raise StooqError(
                f"could not solve the Stooq captcha in {attempts} attempts"
            )
        with self._http.stream("GET", DOWNLOAD_URL, params={"b": dataset}) as response:
            response.raise_for_status()
            chunks = response.iter_bytes(chunk_size=1 << 16)
            first = next(chunks, b"")
            if first[:2] != b"PK":
                body = (first + b"".join(chunks))[:200]
                raise StooqError(
                    f"stooq refused {dataset!r} (not a zip): {body!r}"
                )
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_suffix(out.suffix + ".tmp")
            with open(tmp, "wb") as handle:
                handle.write(first)
                for chunk in chunks:
                    handle.write(chunk)
            tmp.rename(out)
        log.info("stooq: downloaded %s -> %s (%d bytes)", dataset, out, out.stat().st_size)
        return out

    def close(self) -> None:
        close = getattr(self._http, "close", None)
        if callable(close):
            close()


def download_stooq(
    dataset: str, out: Path | str, attempts: int = 6, ocr: Callable[[bytes], str] | None = None
) -> Path:
    """Convenience: run the whole flow with a fresh session and close it."""
    downloader = StooqDownloader(ocr=ocr)
    try:
        return downloader.download(dataset, out, attempts=attempts)
    finally:
        downloader.close()
