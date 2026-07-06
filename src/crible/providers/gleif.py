"""FR-010 — GLEIF ISIN→LEI mapping (keyless, public relationship files).

GLEIF publishes daily ISIN-to-LEI relationship files (CSV: LEI,ISIN). crible
caches one locally; coverage is partial (not all NNAs contribute) — unmatched
EU listings are counted, never errored.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from pathlib import Path

log = logging.getLogger("crible.providers.gleif")

# The stable landing page is https://www.gleif.org/en/lei-data/lei-mapping/
# download-isin-to-lei-relationship-files ; the actual file URL is dated and
# resolved at download time. Kept as a constant so the operator can override.
ISIN_LEI_LATEST_URL = "https://mapping.gleif.org/api/v2/isin-lei/latest/download"


def load_isin_lei_map(path: Path | str) -> dict[str, str]:
    """Parse a GLEIF relationship file (CSV or zipped CSV) into {ISIN: LEI}."""
    path = Path(path)
    raw: bytes = path.read_bytes()
    if path.suffix == ".zip" or raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            inner = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
            raw = archive.read(inner)
    mapping: dict[str, str] = {}
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")))
    for row in reader:
        lower = {k.lower(): v for k, v in row.items() if k}
        isin, lei = lower.get("isin"), lower.get("lei")
        if isin and lei:
            mapping[isin.strip()] = lei.strip()
    log.info("gleif: loaded %d ISIN→LEI relationships", len(mapping))
    return mapping


def resolve_leis(
    companies: list[dict], mapping: dict[str, str]
) -> tuple[dict[str, str], list[str]]:
    """symbol→LEI for companies whose ISIN resolves; plus unmatched symbols.

    Companies without an ISIN or without a GLEIF relationship land in the
    unmatched list — surfaced as the 'unmatched EU listings' status metric
    (FR-010 AC-4), never as an error.
    """
    resolved: dict[str, str] = {}
    unmatched: list[str] = []
    for company in companies:
        isin = company.get("isin")
        lei = mapping.get(isin) if isin else None
        if lei:
            resolved[company["symbol"]] = lei
        else:
            unmatched.append(company["symbol"])
    return resolved, unmatched
