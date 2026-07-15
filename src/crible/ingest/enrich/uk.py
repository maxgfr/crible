"""UK audited enrichment — Companies House Accounts Data Product."""

from __future__ import annotations

import time

from crible.ingest.enrich._base import CH_MAX_AGE, config, log


def load_uk_company_numbers(data_dir) -> dict[str, str]:
    """{symbol: company_number} from an operator-provided
    data/uk-company-numbers.csv (columns symbol,number). No clean keyless
    ISIN→company-number map exists, so UK resolution is operator-supplied."""
    import csv
    from pathlib import Path

    path = Path(data_dir) / "uk-company-numbers.csv"
    if not path.exists():
        return {}
    mapping: dict[str, str] = {}
    with open(path, newline="") as handle:
        for row in csv.DictReader(handle):
            lower = {k.lower(): v for k, v in row.items() if k}
            symbol, number = lower.get("symbol"), lower.get("number")
            if symbol and number:
                mapping[symbol.strip()] = number.strip()
    return mapping


def run_companies_house(
    mapping: dict[str, str] | None = None, url: str = "", http=None, name: str = "accounts.zip",
) -> dict:
    """UK audited layer: mirror an Accounts Data Product ZIP and write
    provider='companies-house' raw for the mapped listings. ``mapping`` is
    {symbol: company_number}; when omitted it is read from
    data/uk-company-numbers.csv. Assumed-risk redistribution (no licence
    stated) — kept out of the fully-free dataset tier."""
    from crible.ingest.mirror import fetch_if_stale
    from crible.providers.audited import write_audited_frames
    from crible.providers.companies_house import iter_accounts

    data = config.data_dir()
    outcome: dict = {"enriched": 0, "outage": None, "skipped": None}
    if mapping is None:
        mapping = load_uk_company_numbers(data)
    if not mapping:
        outcome["skipped"] = "no UK company-number map (data/uk-company-numbers.csv)"
        return outcome
    if not url:
        outcome["skipped"] = "no Accounts Data Product URL provided"
        return outcome

    by_number = {str(n).zfill(8): sym for sym, n in mapping.items()}
    try:
        result = fetch_if_stale(data, "companies-house", name, url, http=http, max_age_seconds=CH_MAX_AGE)
    except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
        outcome["outage"] = str(exc)
        log.warning("companies-house: %s", exc)
        return outcome
    fetched_at = time.time()
    for number, frames in iter_accounts(result.path, set(by_number)):
        write_audited_frames(
            data, symbol=by_number[number], provider_id="companies-house",
            frames=frames, fetched_at=fetched_at,
        )
        outcome["enriched"] += 1
    log.info("companies-house: enriched %d UK listings", outcome["enriched"])
    return outcome

