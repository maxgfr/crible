"""KR audited enrichment — OpenDART (free-key opt-in, EDINET-style)."""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

from crible.ingest.enrich._base import _connect, config, log, update_heartbeat

DART_REFRESH_SECONDS = 30 * 24 * 3600  # re-poll a covered symbol monthly


def _fresh_symbols(data_dir, max_age_seconds: float) -> set[str]:
    """Symbols whose newest provider='dart' raw stamp is younger than the
    refresh window — skipped so the steady-state nightly stays cheap."""
    from crible.ingest.raw import iter_raw_files

    fresh: set[str] = set()
    cutoff = (time.time() - max_age_seconds) * 1000
    for directory in (Path(data_dir) / "raw" / "provider=dart").glob("symbol=*"):
        stamps = []
        for file in iter_raw_files(directory):
            try:
                stamps.append(int(file.stem.rsplit("-", 1)[1]))
            except (IndexError, ValueError):
                continue
        if stamps and max(stamps) >= cutoff:
            fresh.add(directory.name.split("=", 1)[1])
    return fresh


def run_dart(
    years: int = 3, limit: int = 0, key: str | None = None, client=None,
    time_budget_seconds: float | None = None,
) -> dict:
    """Audited Korea: OpenDART annual reports (11011) for every ``.KS``/``.KQ``
    listing, consolidated (CFS) first with separate (OFS) fallback, the last
    ``years`` fiscal years accumulated into ONE frame-set per company.
    Free-key opt-in: OFF without ``CRIBLE_DART_KEY`` (the EDINET gate);
    ``limit <= 0`` is a pure no-op."""
    from crible.providers.audited import merge_audited, write_audited_frames
    from crible.providers.dart import KEY_ENV_VAR, DartApiClient, frames_from_accounts

    outcome: dict = {"enriched": 0, "unmatched": 0, "outage": None, "skipped": None}
    if limit <= 0:
        outcome["skipped"] = "limit 0"
        return outcome
    key = key or os.environ.get(KEY_ENV_VAR)
    if client is None and not key:
        outcome["skipped"] = f"DART disabled (set {KEY_ENV_VAR} to enable, free-key opt-in)"
        return outcome

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
            "SELECT symbol FROM companies WHERE country = 'KR' AND NOT delisted"
            " AND (symbol LIKE '%.KS' OR symbol LIKE '%.KQ')"
            " ORDER BY crawl_priority, symbol"
        ).fetchall()
    finally:
        con.close()
    by_code = {symbol.rsplit(".", 1)[0].zfill(6): symbol for (symbol,) in rows}
    if not by_code:
        outcome["skipped"] = "no KR listings in the universe"
        return outcome

    if client is None:
        client = DartApiClient(key)
    try:
        corp_codes = client.corp_codes()
    except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
        outcome["outage"] = f"corpCode: {exc}"
        log.warning("dart: %s — resuming next run", outcome["outage"])
        return outcome

    mapping = {
        symbol: corp_codes[code] for code, symbol in by_code.items() if code in corp_codes
    }
    outcome["unmatched"] = len(by_code) - len(mapping)
    update_heartbeat(dart_resolved=len(mapping), dart_unmatched=outcome["unmatched"])

    skip = _fresh_symbols(data, DART_REFRESH_SECONDS)
    fetched_at = time.time()
    last_full_year = date.today().year - 1
    for symbol, corp_code in sorted(mapping.items()):
        if outcome["enriched"] >= limit:
            outcome["stopped"] = "limit"
            break
        if out_of_time():
            outcome["stopped"] = "budget"
            break
        if symbol in skip:
            continue
        frames: dict = {}
        try:
            for year in range(last_full_year, last_full_year - years, -1):
                rows_ = client.fnltt_all(corp_code, str(year), "CFS")
                if not rows_:  # consolidated absent → separate statements
                    rows_ = client.fnltt_all(corp_code, str(year), "OFS")
                if rows_:
                    frames = merge_audited(frames, frames_from_accounts(rows_, str(year)))
        except Exception as exc:  # noqa: BLE001 — one company never kills the cycle
            outcome["outage"] = f"{symbol}: {exc}"
            log.warning("dart: %s — continuing", outcome["outage"])
            continue
        if not frames:
            continue
        write_audited_frames(
            data, symbol=symbol, provider_id="dart", frames=frames,
            fetched_at=fetched_at, skip_identical=True,
        )
        outcome["enriched"] += 1
    log.info("dart: enriched %d KR listings (%d resolved)", outcome["enriched"], len(mapping))
    return outcome
