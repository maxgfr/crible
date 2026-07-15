"""US audited enrichment — SEC EDGAR companyfacts + FSDS."""

from __future__ import annotations

import time

from crible.ingest.enrich._base import (
    EDGAR_REFRESH_SECONDS, EDGAR_SCHEMA, FSDS_MAX_AGE, _connect, config, log, update_heartbeat,
)

def run_edgar_cycle(limit: int = 5, client=None, ticker_map: dict[str, int] | None = None) -> dict:
    """FR-016 — the EDGAR enrichment cycle: US companies whose ticker resolves
    in the SEC directory (company_tickers.json) get audited figures pulled
    from companyfacts into provider='edgar' raw statements. Outages are
    recorded and the cycle resumes next time; unmatched listings are counted,
    never errored — symmetric with the ESEF cycle."""
    from crible.providers.edgar import facts_to_frames, resolve_ciks

    data = config.data_dir()
    outcome: dict = {"enriched": [], "unmatched": 0, "outage": None, "skipped": None}

    con = _connect()
    try:
        con.execute(EDGAR_SCHEMA)
        companies = [
            {"symbol": s}
            for (s,) in con.execute(
                "SELECT symbol FROM companies WHERE region = 'us' AND NOT delisted"
            ).fetchall()
        ]
        if not companies:
            outcome["skipped"] = "no US companies in the universe yet"
            return outcome
        if ticker_map is None:
            if client is None:
                from crible.providers.edgar import EdgarClient

                client = EdgarClient()
            try:
                ticker_map = client.company_tickers()
            except Exception as exc:  # noqa: BLE001 — outage: record, resume next cycle
                outcome["outage"] = f"company_tickers.json: {exc}"
                log.warning("edgar: %s — resuming next cycle", outcome["outage"])
                return outcome
        resolved, unmatched = resolve_ciks(companies, ticker_map)
        outcome["unmatched"] = len(unmatched)
        # FR-016: the unmatched-US-listings metric is visible in status
        update_heartbeat(edgar_unmatched=len(unmatched), edgar_resolved=len(resolved))
        for symbol, cik in resolved.items():
            con.execute(
                "INSERT INTO edgar_tasks (symbol, cik) VALUES (?, ?) ON CONFLICT (symbol) DO NOTHING",
                [symbol, cik],
            )
        due = con.execute(
            "SELECT symbol, cik FROM edgar_tasks WHERE last_fetched_at IS NULL"
            " OR last_fetched_at < ? ORDER BY last_fetched_at NULLS FIRST LIMIT ?",
            [time.time() - EDGAR_REFRESH_SECONDS, limit],
        ).fetchall()
        if not due:
            return outcome

        if client is None:
            from crible.providers.edgar import EdgarClient

            client = EdgarClient()
        from crible.ingest.raw import write_raw_statement

        for symbol, cik in due:
            try:
                frames = facts_to_frames(client.companyfacts(int(cik)))
                fetched_at = time.time()
                for (statement_type, freq), frame in frames.items():
                    write_raw_statement(
                        data, symbol=symbol, provider="edgar", statement_type=statement_type,
                        freq=freq, frame=frame, fetched_at=fetched_at,
                    )
                con.execute(
                    "UPDATE edgar_tasks SET last_fetched_at = ? WHERE symbol = ?",
                    [fetched_at, symbol],
                )
                if frames:
                    outcome["enriched"].append(symbol)
                    log.info("edgar: enriched %s (%d statement frame(s)) from CIK %010d",
                             symbol, len(frames), int(cik))
            except Exception as exc:  # noqa: BLE001 — outage: record, resume next cycle
                outcome["outage"] = f"{symbol}: {exc}"
                log.warning("edgar: outage on %s: %s — resuming next cycle", symbol, exc)
                break
        return outcome
    finally:
        con.close()


def run_edgar_bulk(
    zip_path=None, client=None, ticker_map: dict[str, int] | None = None,
    download: bool = True, limit: int | None = None,
    time_budget_seconds: float | None = None,
) -> dict:
    """FR-016 / ADR-0005 scale-up — the bulk variant: ONE companyfacts.zip
    gives the audited layer for EVERY resolved US listing (~10k issuers),
    instead of the per-CIK trickle. The archive is processed member-by-member
    (memory-safe) and never committed; a broken filing is skipped, a missing
    archive is an outage — recorded, resumed next run."""
    from pathlib import Path

    from crible.ingest.raw import write_raw_statement
    from crible.providers.edgar import facts_to_frames, iter_bulk_companyfacts, resolve_ciks

    data = config.data_dir()
    outcome: dict = {"enriched": 0, "unmatched": 0, "outage": None, "skipped": None, "stopped": None}
    # wall-clock budget (run_refresh --max-minutes): per-symbol granularity is
    # safe — edgar_tasks stamps and raw writes are per-symbol, so a partial
    # pass resumes cleanly (idempotent writes skip the already-ingested)
    stage_deadline = (
        None if time_budget_seconds is None else time.monotonic() + time_budget_seconds
    )

    def out_of_time() -> bool:
        return stage_deadline is not None and time.monotonic() >= stage_deadline

    con = _connect()
    try:
        con.execute(EDGAR_SCHEMA)
        companies = [
            {"symbol": s}
            for (s,) in con.execute(
                "SELECT symbol FROM companies WHERE region = 'us' AND NOT delisted"
            ).fetchall()
        ]
        if not companies:
            outcome["skipped"] = "no US companies in the universe yet"
            return outcome
        if out_of_time():
            outcome["stopped"] = "budget"
            return outcome
        if ticker_map is None or (download and zip_path is None):
            if client is None:
                from crible.providers.edgar import EdgarClient

                client = EdgarClient()
        if ticker_map is None:
            try:
                ticker_map = client.company_tickers()
            except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
                outcome["outage"] = f"company_tickers.json: {exc}"
                log.warning("edgar bulk: %s", outcome["outage"])
                return outcome
        resolved, unmatched = resolve_ciks(companies, ticker_map)
        outcome["unmatched"] = len(unmatched)
        update_heartbeat(edgar_unmatched=len(unmatched), edgar_resolved=len(resolved))

        archive = Path(zip_path) if zip_path is not None else data / "companyfacts.zip"
        if not archive.exists():
            if not download:
                outcome["skipped"] = f"no bulk archive at {archive}"
                return outcome
            try:
                log.info("edgar bulk: downloading companyfacts.zip (~1.4 GB)")
                client.download_bulk(archive)
            except Exception as exc:  # noqa: BLE001
                outcome["outage"] = f"companyfacts.zip download: {exc}"
                log.warning("edgar bulk: %s", outcome["outage"])
                return outcome

        by_cik = {cik: symbol for symbol, cik in resolved.items()}
        fetched_at = time.time()
        for cik, facts in iter_bulk_companyfacts(archive, set(by_cik)):
            if out_of_time():
                outcome["stopped"] = "budget"
                break
            frames = facts_to_frames(facts)
            if not frames:
                continue
            symbol = by_cik[cik]
            for (statement_type, freq), frame in frames.items():
                write_raw_statement(
                    data, symbol=symbol, provider="edgar", statement_type=statement_type,
                    freq=freq, frame=frame, fetched_at=fetched_at,
                )
            con.execute(
                "INSERT INTO edgar_tasks (symbol, cik, last_fetched_at) VALUES (?, ?, ?)"
                " ON CONFLICT (symbol) DO UPDATE SET last_fetched_at = excluded.last_fetched_at",
                [symbol, int(cik), fetched_at],
            )
            outcome["enriched"] += 1
            if limit is not None and outcome["enriched"] >= limit:
                break
        log.info("edgar bulk: enriched %d US issuers from %s", outcome["enriched"], archive)
        return outcome
    finally:
        con.close()


def run_fsds(
    quarters, client=None, ticker_map: dict[str, int] | None = None, http=None,
    limit: int | None = None,
    time_budget_seconds: float | None = None,
) -> dict:
    """SEC FSDS depth cycle: for each (year, quarter), mirror the archive and
    write provider='edgar-fsds' raw for resolved US issuers. companyfacts
    (provider='edgar') wins recent periods at reconcile; FSDS backfills the
    pre-8-year history companyfacts drops. Public domain — redistributable."""
    from crible.ingest.mirror import fetch_if_stale
    from crible.providers.audited import write_audited_frames
    from crible.providers.edgar import resolve_ciks
    from crible.providers.edgar_fsds import iter_fsds, quarter_url

    data = config.data_dir()
    outcome: dict = {
        "enriched": 0, "quarters": [], "unmatched": 0, "outage": None, "skipped": None,
        "stopped": None,
    }
    # wall-clock budget, per-quarter granularity (one archive = one unit)
    stage_deadline = (
        None if time_budget_seconds is None else time.monotonic() + time_budget_seconds
    )

    con = _connect()
    try:
        companies = [
            {"symbol": s}
            for (s,) in con.execute(
                "SELECT symbol FROM companies WHERE region = 'us' AND NOT delisted"
            ).fetchall()
        ]
        if not companies:
            outcome["skipped"] = "no US companies in the universe yet"
            return outcome
        if ticker_map is None:
            if client is None:
                from crible.providers.edgar import EdgarClient

                client = EdgarClient()
            try:
                ticker_map = client.company_tickers()
            except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
                outcome["outage"] = f"company_tickers.json: {exc}"
                log.warning("fsds: %s", outcome["outage"])
                return outcome
        resolved, unmatched = resolve_ciks(companies, ticker_map)
        outcome["unmatched"] = len(unmatched)
        by_cik = {cik: symbol for symbol, cik in resolved.items()}
        headers = {"User-Agent": config.sec_user_agent()}
        fetched_at = time.time()
        for year, quarter in quarters:
            if stage_deadline is not None and time.monotonic() >= stage_deadline:
                outcome["stopped"] = "budget"
                break
            try:
                result = fetch_if_stale(
                    data, "edgar-fsds", f"{year}q{quarter}.zip", quarter_url(year, quarter),
                    http=http, headers=headers, max_age_seconds=FSDS_MAX_AGE,
                )
            except Exception as exc:  # noqa: BLE001 — one bad quarter never sinks the run
                outcome["outage"] = f"{year}q{quarter}: {exc}"
                log.warning("fsds: %s — skipping quarter", outcome["outage"])
                continue
            count = 0
            for cik, frames in iter_fsds(result.path, set(by_cik)):
                write_audited_frames(
                    data, symbol=by_cik[cik], provider_id="edgar-fsds",
                    frames=frames, fetched_at=fetched_at,
                )
                count += 1
                outcome["enriched"] += 1
                if limit is not None and outcome["enriched"] >= limit:
                    break
            outcome["quarters"].append(f"{year}q{quarter} ({count})")
            if limit is not None and outcome["enriched"] >= limit:
                break
        log.info("fsds: enriched %d issuer-quarters across %s", outcome["enriched"], outcome["quarters"])
        return outcome
    finally:
        con.close()

