"""Captcha OCR — a thin wrapper over the ddddocr ONNX model (optional extra).

Dependency-light by design: ddddocr (onnxruntime + opencv + pillow) ships as
the OPTIONAL `captcha` extra, so importing crible core never pulls an ML stack.
The model is a small pretrained ONNX net; on CPU it reads a short alphanumeric
text captcha in a few milliseconds. Used by the automated Stooq bulk download
(`crible.ingest.stooq_fetch`), which clears Stooq's image-captcha gate.
"""

from __future__ import annotations

import functools
import re

_NON_ALNUM = re.compile(r"[^a-z0-9]")


class CaptchaError(RuntimeError):
    """The captcha OCR model is unavailable or failed."""


@functools.lru_cache(maxsize=1)
def _engine():
    """The ddddocr OCR engine, initialised once (model load is the slow part)."""
    try:
        import ddddocr
    except ImportError as exc:  # pragma: no cover - exercised via CaptchaError path
        raise CaptchaError(
            "captcha OCR needs the optional 'captcha' extra — install it with "
            "`uv sync --extra captcha` (or `pip install 'crible[captcha]'`)"
        ) from exc
    return ddddocr.DdddOcr(show_ad=False)


def solve_captcha(image: bytes, *, normalize: bool = True) -> str:
    """Read the code from a captcha image.

    `normalize` lowercases the result and strips it to ``[a-z0-9]`` (Stooq's
    codes are case-insensitive alphanumerics); pass ``False`` for the raw model
    output.
    """
    if not image:
        raise CaptchaError("empty captcha image")
    text = _engine().classification(image)
    return _NON_ALNUM.sub("", text.lower()) if normalize else text
