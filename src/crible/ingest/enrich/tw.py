"""TW audited enrichment — TWSE OpenAPI, forward accumulation in the raw layer."""

from __future__ import annotations

import json
import time

from crible.ingest.enrich._base import TWSE_MAX_AGE, _connect, config, log, update_heartbeat


def run_twse(limit: int = 0, http=None, time_budget_seconds: float | None = None) -> dict:
    """Audited Taiwan: mirror the two whole-market snapshot JSONs, union each
    company's newest period into its EXISTING raw frames (the accumulation
    store — snapshot endpoints forget history, the raw layer must not), and
    write provider='twse' raw with skip_identical so a no-new-period run
    re-stamps nothing. ``limit <= 0`` is a pure no-op."""
    outcome: dict = {"enriched": 0, "unmatched": 0, "outage": None, "skipped": None}
    if limit <= 0:
        outcome["skipped"] = "limit 0"
        return outcome

    from crible.compute.snapshot import latest_raw_frames
    from crible.ingest.mirror import fetch_if_stale
    from crible.providers.audited import merge_audited, write_audited_frames
    from crible.providers.twse import BALANCE_URL, INCOME_URL, frames_from_reports

    data = config.data_dir()
    started = time.monotonic()

    def out_of_time() -> bool:
        return (
            time_budget_seconds is not None
            and time.monotonic() - started >= time_budget_seconds
        )

    con = _connect()
    try:
        rows = con.execute(
            "SELECT symbol FROM companies WHERE country = 'TW' AND NOT delisted"
            " AND symbol LIKE '%.TW' ORDER BY crawl_priority, symbol"
        ).fetchall()
    finally:
        con.close()
    by_code = {symbol[:-3]: symbol for (symbol,) in rows}
    if not by_code:
        outcome["skipped"] = "no .TW listings in the universe"
        return outcome

    payloads: dict[str, list[dict]] = {}
    for name, url in (("income", INCOME_URL), ("balance", BALANCE_URL)):
        try:
            result = fetch_if_stale(
                data, "twse", f"{name}.json", url, http=http, max_age_seconds=TWSE_MAX_AGE
            )
            payloads[name] = json.loads(result.path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
            outcome["outage"] = f"{name}: {exc}"
            log.warning("twse: %s — resuming next run", outcome["outage"])
            return outcome

    reported = {
        str(row.get("公司代號", "")).strip()
        for payload in payloads.values()
        for row in payload
    }
    codes = sorted(set(by_code) & reported)
    outcome["unmatched"] = len(reported - set(by_code))
    update_heartbeat(twse_resolved=len(codes), twse_unmatched=outcome["unmatched"])

    fetched_at = time.time()
    for code in codes:
        if outcome["enriched"] >= limit:
            outcome["stopped"] = "limit"
            break
        if out_of_time():
            outcome["stopped"] = "budget"
            break
        symbol = by_code[code]
        fresh = frames_from_reports(payloads["income"], payloads["balance"], code)
        if not fresh:
            continue
        existing = latest_raw_frames(data, symbol, provider="twse")
        existing = {
            key: frame[[c for c in frame.columns if not str(c).startswith("_")]]
            for key, frame in existing.items()
        }
        merged = merge_audited(fresh, existing)  # new period wins, history backfills
        write_audited_frames(
            data, symbol=symbol, provider_id="twse", frames=merged,
            fetched_at=fetched_at, skip_identical=True,
        )
        outcome["enriched"] += 1
    log.info("twse: enriched %d TW listings (%d codes matched)", outcome["enriched"], len(codes))
    return outcome
