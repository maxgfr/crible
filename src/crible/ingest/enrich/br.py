"""BR audited enrichment — CVM DFP bulk (fully-free, ODbL)."""

from __future__ import annotations

import time
from datetime import date

from crible.ingest.enrich._base import CVM_MAX_AGE, _connect, config, log, update_heartbeat

CLOSED_YEAR_MAX_AGE = 365 * 24 * 3600  # closed fiscal years never change


def run_cvm(
    years: int = 5, limit: int = 0, http=None, time_budget_seconds: float | None = None,
) -> dict:
    """Audited Brazil: mirror the CVM DFP yearly ZIPs, accumulate the last
    ``years`` fiscal years into ONE frame-set per company (the raw layer
    keeps a single newest frame per statement — per-year writes would
    shadow each other), and write provider='cvm' raw for every mapped
    ``.SA`` listing. ``limit <= 0`` is a pure no-op (the marathon convention)."""
    outcome: dict = {"enriched": 0, "unmatched": 0, "outage": None, "skipped": None}
    if limit <= 0:
        outcome["skipped"] = "limit 0"
        return outcome

    from crible.ingest.mirror import fetch_if_stale
    from crible.providers.audited import merge_audited, write_audited_frames
    from crible.providers.cvm import DFP_URL, FCA_URL, FIRST_DFP_YEAR, parse_dfp, resolve_cvm

    data = config.data_dir()
    started = time.monotonic()

    def out_of_time() -> bool:
        return (
            time_budget_seconds is not None
            and time.monotonic() - started >= time_budget_seconds
        )

    con = _connect()
    try:
        symbols = [
            row[0]
            for row in con.execute(
                "SELECT symbol FROM companies WHERE country = 'BR' AND NOT delisted"
                " ORDER BY crawl_priority, symbol"
            ).fetchall()
        ]
    finally:
        con.close()
    if not symbols:
        outcome["skipped"] = "no BR listings in the universe"
        return outcome

    this_year = date.today().year
    fca_path = None
    for fca_year in (this_year, this_year - 1):  # January: last year's register
        try:
            fca_path = fetch_if_stale(
                data, "cvm", f"fca_{fca_year}.zip", FCA_URL.format(year=fca_year),
                http=http, max_age_seconds=CVM_MAX_AGE,
            ).path
            break
        except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
            outcome["outage"] = f"fca {fca_year}: {exc}"
    if fca_path is None:
        log.warning("cvm: %s — resuming next run", outcome["outage"])
        return outcome

    mapping, unmatched = resolve_cvm(symbols, fca_path)
    outcome["unmatched"] = len(unmatched)
    update_heartbeat(cvm_resolved=len(mapping), cvm_unmatched=len(unmatched))
    if not mapping:
        outcome["skipped"] = "no CVM trading-code matches"
        return outcome

    wanted = set(mapping.values())
    accumulated: dict[str, dict] = {}
    fetched_years: list[int] = []
    # newest first: merge_audited lets the freshest filing win a period and
    # older years backfill the history
    for year in range(this_year, max(this_year - years, FIRST_DFP_YEAR) - 1, -1):
        if out_of_time():
            outcome["stopped"] = "budget"
            break
        try:
            result = fetch_if_stale(
                data, "cvm", f"dfp_{year}.zip", DFP_URL.format(year=year), http=http,
                max_age_seconds=CVM_MAX_AGE if year >= this_year - 1 else CLOSED_YEAR_MAX_AGE,
            )
        except Exception as exc:  # noqa: BLE001 — a missing year is not fatal
            outcome["outage"] = f"dfp {year}: {exc}"
            log.warning("cvm: %s — continuing", outcome["outage"])
            continue
        year_frames = parse_dfp(result.path, wanted)
        for cnpj, frames in year_frames.items():
            accumulated[cnpj] = merge_audited(accumulated.get(cnpj, {}), frames)
        fetched_years.append(year)
    outcome["years"] = fetched_years

    fetched_at = time.time()
    for symbol, cnpj in sorted(mapping.items()):
        if outcome["enriched"] >= limit:
            outcome["stopped"] = outcome.get("stopped") or "limit"
            break
        frames = accumulated.get(cnpj)
        if not frames:
            continue
        write_audited_frames(
            data, symbol=symbol, provider_id="cvm", frames=frames,
            fetched_at=fetched_at, skip_identical=True,
        )
        outcome["enriched"] += 1
    log.info("cvm: enriched %d BR listings over %s", outcome["enriched"], fetched_years)
    return outcome
