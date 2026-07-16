"""On-demand fetch requests — the API→ingest handoff (ADR-0003 safe).

The API is a READER: it never opens the ingest DuckDB nor writes the raw
layer. When a user hits a company with no data yet, the API drops a request
FILE here; the ingest loop picks pending requests up at the top of each
cycle, crawls them immediately (budget-charged — targeting never busts the
hourly cap), computes, and clears the files. Requests are idempotent (one
file per symbol) and capped so the queue cannot be flooded.
"""

from __future__ import annotations

import time
from pathlib import Path

REQUESTS_DIR = "fetch-requests"
MAX_PENDING = 100


def _directory(data_dir: Path | str) -> Path:
    return Path(data_dir) / REQUESTS_DIR


def request_fetch(data_dir: Path | str, symbol: str) -> bool:
    """Drop (or refresh) one symbol's request file. False when the pending
    queue is full — the caller reports 'try later', nothing breaks."""
    directory = _directory(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    safe = symbol.replace("/", "_")
    path = directory / f"{safe}.req"
    if not path.exists() and len(list(directory.glob("*.req"))) >= MAX_PENDING:
        return False
    tmp = directory / f".tmp-{safe}.req"
    tmp.write_text(f"{symbol}\n{time.time()}")
    tmp.rename(path)  # atomic on POSIX
    return True


def pending_requests(data_dir: Path | str) -> list[str]:
    """Pending symbols, oldest request first (the original symbol travels in
    the file body — the filename is only its safe form)."""
    directory = _directory(data_dir)
    if not directory.exists():
        return []
    entries: list[tuple[float, str]] = []
    for path in directory.glob("*.req"):
        try:
            lines = path.read_text().splitlines()
            symbol = lines[0].strip()
            stamp = float(lines[1]) if len(lines) > 1 else path.stat().st_mtime
        except (OSError, ValueError, IndexError):
            continue
        if symbol:
            entries.append((stamp, symbol))
    return [symbol for _, symbol in sorted(entries)]


def clear_request(data_dir: Path | str, symbol: str) -> None:
    path = _directory(data_dir) / f"{symbol.replace('/', '_')}.req"
    path.unlink(missing_ok=True)
