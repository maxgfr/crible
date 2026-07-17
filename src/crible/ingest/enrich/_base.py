"""Shared plumbing for the region-split audited enrichment cycles."""

from __future__ import annotations

import logging

from crible import config
from crible.ingest.state import connect as _connect
from crible.ingest.state import update_heartbeat

__all__ = ["config", "_connect", "update_heartbeat", "log", "seed_tasks_from_raw",
           "ESEF_REFRESH_SECONDS", "ESEF_SCHEMA", "ESEF_DEFAULT_HISTORY",
           "ensure_esef_schema", "EDGAR_REFRESH_SECONDS",
           "EDGAR_SCHEMA", "FSDS_MAX_AGE", "CH_MAX_AGE", "CVM_MAX_AGE", "TWSE_MAX_AGE"]

log = logging.getLogger("crible.ingest.enrichment")

ESEF_REFRESH_SECONDS = 90 * 24 * 3600

# merge the N most recent annual filings per filer (each older filing adds
# ~1 audited year); depth-gated, so the extra fetches are paid once per filer
ESEF_DEFAULT_HISTORY = 3

ESEF_SCHEMA = """
CREATE TABLE IF NOT EXISTS esef_tasks (
    symbol          VARCHAR PRIMARY KEY,
    lei             VARCHAR NOT NULL,
    last_fetched_at DOUBLE,
    history_depth   INTEGER
)
"""


def ensure_esef_schema(con) -> None:
    con.execute(ESEF_SCHEMA)
    # long-lived self-hosted DBs created before the history backfill
    con.execute("ALTER TABLE esef_tasks ADD COLUMN IF NOT EXISTS history_depth INTEGER")

EDGAR_REFRESH_SECONDS = 90 * 24 * 3600

EDGAR_SCHEMA = """
CREATE TABLE IF NOT EXISTS edgar_tasks (
    symbol          VARCHAR PRIMARY KEY,
    cik             BIGINT NOT NULL,
    last_fetched_at DOUBLE
)
"""

FSDS_MAX_AGE = 7 * 24 * 3600

CH_MAX_AGE = 30 * 24 * 3600

CVM_MAX_AGE = 7 * 24 * 3600  # the current-year DFP/FCA refresh weekly

TWSE_MAX_AGE = 24 * 3600  # daily snapshot endpoints — mirror for replayability


def seed_tasks_from_raw(
    con, data_dir, *, provider: str, table: str, key_column: str, keys: dict,
    history_column: str | None = None,
) -> int:
    """Rebuild an enrichment table's freshness from the raw layer's stamps.

    A CI run starts from a fresh operational DB — crible.duckdb never travels
    in the published dataset, only data/raw does. Without this re-seed the
    ESEF sweep forgot everything it had fetched and re-downloaded the same
    newest ~100 filings every night (the observed ~115-symbol coverage
    plateau). Mirrors restore_queue_from_raw for the crawl queue. ``keys``
    maps symbol → lei/cik; raw dirs whose symbol dropped out of the mapping
    are skipped, harmlessly. Returns the number of symbols seeded.

    ``history_column`` re-seeds the ESEF backfill depth from the newest raw
    file's ``_history_depth`` column (files written before the backfill have
    no such column and seed as legacy depth 1).
    """
    from pathlib import Path

    from crible.ingest.raw import iter_raw_files

    root = Path(data_dir) / "raw" / f"provider={provider}"
    by_safe = {str(symbol).replace("/", "_"): symbol for symbol in keys}
    seeded = 0
    for directory in root.glob("symbol=*"):
        symbol = by_safe.get(directory.name.split("=", 1)[1])
        if symbol is None:
            continue
        stamped_files = []
        for file in iter_raw_files(directory):
            try:
                stamped_files.append((int(file.stem.rsplit("-", 1)[1]) / 1000.0, file))
            except (IndexError, ValueError):
                continue
        if not stamped_files:
            continue
        newest_stamp, newest_file = max(stamped_files, key=lambda pair: pair[0])
        if history_column is None:
            con.execute(
                f"INSERT INTO {table} (symbol, {key_column}, last_fetched_at) VALUES (?, ?, ?)"
                f" ON CONFLICT (symbol) DO UPDATE SET last_fetched_at ="
                f" greatest(coalesce({table}.last_fetched_at, 0), excluded.last_fetched_at)",
                [symbol, keys[symbol], newest_stamp],
            )
        else:
            depth = _raw_history_depth(newest_file)
            con.execute(
                f"INSERT INTO {table} (symbol, {key_column}, last_fetched_at, {history_column})"
                f" VALUES (?, ?, ?, ?)"
                f" ON CONFLICT (symbol) DO UPDATE SET last_fetched_at ="
                f" greatest(coalesce({table}.last_fetched_at, 0), excluded.last_fetched_at),"
                f" {history_column} = greatest(coalesce({table}.{history_column}, 1),"
                f" coalesce(excluded.{history_column}, 1))",
                [symbol, keys[symbol], newest_stamp, depth],
            )
        seeded += 1
    return seeded


def _raw_history_depth(file) -> int | None:
    import pandas as pd

    try:
        column = pd.read_parquet(file, columns=["_history_depth"])
    except Exception:  # noqa: BLE001 — pre-backfill file without the column
        return None
    return int(column["_history_depth"].iloc[0]) if len(column) else None

