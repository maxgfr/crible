"""Runtime configuration — everything comes from the environment (.env in
Docker), nothing is hardcoded beyond safe defaults (NFR-009: zero-key first)."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

log = logging.getLogger("crible.config")

DEFAULT_BUDGET_PER_HOUR = 330
BOOTSTRAP_SAMPLE_SIZE = 100


def data_dir() -> Path:
    return Path(os.environ.get("CRIBLE_DATA_DIR", "data"))


def database_path() -> Path:
    return data_dir() / "crible.duckdb"


def budget_per_hour() -> int:
    return int(os.environ.get("CRIBLE_BUDGET_PER_HOUR", DEFAULT_BUDGET_PER_HOUR))


DEFAULT_FETCH_TIMEOUT = 60.0


def fetch_timeout() -> float:
    """Hard wall-clock ceiling for one provider fetch (ADR-0004 watchdog).

    yfinance pulls are known to hang; without a hard timeout a single stuck
    fetch freezes the whole rolling crawl. Set CRIBLE_FETCH_TIMEOUT to tune."""
    return float(os.environ.get("CRIBLE_FETCH_TIMEOUT", DEFAULT_FETCH_TIMEOUT))


# SEC fair-access wants a declared operator + contact. CRITICAL: the UA must
# NOT contain a URL — the SEC's Akamai WAF 403s any User-Agent with an http(s)
# link ("Undeclared Automated Tool" / "Request Rate Threshold Exceeded"),
# which silently killed the whole EDGAR layer. A bare name (+ email) is fine.
DEFAULT_SEC_USER_AGENT = "crible-screener"
_URL_IN_UA = re.compile(r"\s*\+?https?://\S+")


def sec_user_agent() -> str:
    """SEC fair-access requires a declared User-Agent naming the operator —
    set CRIBLE_SEC_USER_AGENT to include a contact email for your instance.
    Any URL is stripped defensively: the SEC WAF 403s UAs that contain one."""
    ua = os.environ.get("CRIBLE_SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT)
    stripped = _URL_IN_UA.sub("", ua).strip()
    if stripped != ua:
        log.warning(
            "CRIBLE_SEC_USER_AGENT contained a URL (SEC 403s those) — using %r", stripped
        )
    return stripped or DEFAULT_SEC_USER_AGENT
