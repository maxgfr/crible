"""Runtime configuration — everything comes from the environment (.env in
Docker), nothing is hardcoded beyond safe defaults (NFR-009: zero-key first)."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_BUDGET_PER_HOUR = 330
BOOTSTRAP_SAMPLE_SIZE = 100


def data_dir() -> Path:
    return Path(os.environ.get("CRIBLE_DATA_DIR", "data"))


def database_path() -> Path:
    return data_dir() / "crible.duckdb"


def budget_per_hour() -> int:
    return int(os.environ.get("CRIBLE_BUDGET_PER_HOUR", DEFAULT_BUDGET_PER_HOUR))


DEFAULT_SEC_USER_AGENT = "crible (https://github.com/maxgfr/crible)"


def sec_user_agent() -> str:
    """SEC fair-access requires a declared User-Agent naming the operator —
    set CRIBLE_SEC_USER_AGENT to include a contact email for your instance."""
    return os.environ.get("CRIBLE_SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT)
