"""Shared plumbing for the region-split audited enrichment cycles."""

from __future__ import annotations

import logging

from crible import config
from crible.ingest.state import connect as _connect
from crible.ingest.state import update_heartbeat

__all__ = ["config", "_connect", "update_heartbeat", "log",
           "ESEF_REFRESH_SECONDS", "ESEF_SCHEMA", "EDGAR_REFRESH_SECONDS",
           "EDGAR_SCHEMA", "FSDS_MAX_AGE", "CH_MAX_AGE"]

log = logging.getLogger("crible.ingest.enrichment")

ESEF_REFRESH_SECONDS = 90 * 24 * 3600

ESEF_SCHEMA = """
CREATE TABLE IF NOT EXISTS esef_tasks (
    symbol          VARCHAR PRIMARY KEY,
    lei             VARCHAR NOT NULL,
    last_fetched_at DOUBLE
)
"""

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

