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


def fetch_gleif(data_dir: Path | str, http=None, max_age_seconds: float = 7 * 24 * 3600) -> Path:
    """Download the latest GLEIF ISIN→LEI relationship file into the local
    mirror (``data/mirror/gleif/isin-lei.zip``, ~200 MB, refreshed at most
    weekly) and return its path. ``load_mapping`` then finds it there, so a
    fresh install gets audited-EU coverage with no manual step. Keyless open
    data (CC0); on a network hiccup the mirror serves the last-good copy."""
    from crible.ingest.mirror import fetch_if_stale

    result = fetch_if_stale(
        data_dir, "gleif", "isin-lei.zip", ISIN_LEI_LATEST_URL,
        http=http, max_age_seconds=max_age_seconds,
    )
    log.info("gleif: mirror %s (%s)", result.path, result.source)
    return result.path


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


def load_mapping(
    data_dir: Path | str,
) -> tuple[dict[str, str] | None, str | None, str | None]:
    """Locate and parse the local GLEIF ISIN→LEI file under ``data_dir``.

    Returns ``(mapping, skipped_reason, outage)`` with exactly one set: a
    mapping on success, a skip reason when no file exists yet (the cycle idles
    politely), or an outage when a present file is unreadable (resume next run).
    Single source of truth for the two enrichment cycles that used to inline
    this block (F4 de-dup)."""
    data_dir = Path(data_dir)
    # legacy operator-provided locations first, then the auto-fetched mirror
    candidates = (
        data_dir / "isin-lei.csv",
        data_dir / "isin-lei.zip",
        data_dir / "mirror" / "gleif" / "isin-lei.zip",
        data_dir / "mirror" / "gleif" / "isin-lei.csv",
    )
    mapping_file = next((p for p in candidates if p.exists()), None)
    if mapping_file is None:
        return (
            None,
            "no GLEIF mapping file — download the ISIN-LEI relationship file to data/isin-lei.csv",
            None,
        )
    try:
        return load_isin_lei_map(mapping_file), None, None
    except Exception as exc:  # noqa: BLE001 — a present-but-unreadable file is an outage
        return None, None, f"gleif mapping unreadable: {exc}"


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
