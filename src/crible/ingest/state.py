"""Shared ingest operational-state helpers: the DuckDB connection and the
status.json heartbeat.

Extracted from service.py (F4) so both the service loop and the audited
enrichment cycles import them without a circular dependency — this module
imports neither.
"""

from __future__ import annotations

import json

import duckdb

from crible import config


def connect() -> duckdb.DuckDBPyConnection:
    path = config.database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def write_heartbeat(payload: dict) -> None:
    path = config.data_dir() / "status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, default=str))
    tmp.rename(path)


def read_heartbeat() -> dict:
    """The current heartbeat, {} when missing or unreadable."""
    path = config.data_dir() / "status.json"
    try:
        current = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return current if isinstance(current, dict) else {}


def update_heartbeat(**fields) -> None:
    """Merge fields into the heartbeat (read-modify-write, atomic rename)."""
    current = read_heartbeat()
    current.update(fields)
    write_heartbeat(current)
