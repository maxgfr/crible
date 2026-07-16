"""EU audited enrichment — ESEF (filings.xbrl.org)."""

from __future__ import annotations

import time

import duckdb

from crible.ingest.enrich._base import (
    ESEF_REFRESH_SECONDS, ESEF_SCHEMA, _connect, config, log, seed_tasks_from_raw,
    update_heartbeat,
)

# entities-index paging cap for the name→LEI→ISIN backfill: ~10k ESEF filers
# at 200/page fits well inside it; filings.xbrl.org is not budget-bound
ENTITY_PAGE_SIZE = 200
MAX_ENTITY_PAGES = 100


def _backfill_nameless_isins(con: duckdb.DuckDBPyConnection, client, mapping: dict[str, str]) -> int:
    """Name→LEI→ISIN backfill (FR-010 reach) — best-effort, never kills the
    sweep. Runs only while ISIN-less EU rows exist; conservative matching
    lives in crible.ingest.enrich.backfill."""
    from crible.ingest.enrich.backfill import backfill_missing_isins

    nameless = con.execute(
        "SELECT count(*) FROM companies"
        " WHERE region = 'europe' AND NOT delisted AND isin IS NULL"
    ).fetchone()[0]
    if not nameless or not hasattr(client, "entities_index"):
        return 0
    try:
        entities: list[tuple[str, str]] = []
        page = 1
        while page <= MAX_ENTITY_PAGES:
            pairs, count = client.entities_index(page_size=ENTITY_PAGE_SIZE, page_number=page)
            entities.extend(pairs)
            if not pairs or page * ENTITY_PAGE_SIZE >= count:
                break
            page += 1
        report = backfill_missing_isins(con, entities=entities, mapping=mapping)
        if report["backfilled"]:
            log.info(
                "esef backfill: %d ISIN(s) recovered by name (%d ambiguous, %d without ISIN)",
                report["backfilled"], report["ambiguous"], report["no_isin_for_lei"],
            )
        return report["backfilled"]
    except Exception as exc:  # noqa: BLE001 — enrichment reach, never a gate
        log.warning("esef backfill failed: %s — resuming next run", exc)
        return 0


def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
    """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
    an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
    figures pulled from filings.xbrl.org into provider='esef' raw statements.
    Outages are recorded and the cycle resumes next time; unmatched listings
    are counted, never errored."""
    from crible.providers.gleif import load_mapping, resolve_leis

    data = config.data_dir()
    outcome: dict = {"enriched": [], "unmatched": 0, "outage": None, "skipped": None}

    if mapping is None:
        mapping, skipped, outage = load_mapping(data)
        if mapping is None:
            outcome["skipped"], outcome["outage"] = skipped, outage
            if skipped:
                log.info("esef: %s", skipped)
            else:
                log.warning("esef: %s — resuming next cycle", outage)
            return outcome

    con = _connect()
    try:
        con.execute(ESEF_SCHEMA)
        companies = [
            {"symbol": s, "isin": i}
            for s, i in con.execute(
                "SELECT symbol, isin FROM companies WHERE region = 'europe' AND NOT delisted"
            ).fetchall()
        ]
        resolved, unmatched = resolve_leis(companies, mapping)
        outcome["unmatched"] = len(unmatched)
        # FR-010 AC-4: the unmatched-EU-listings metric is visible in status
        update_heartbeat(esef_unmatched=len(unmatched), esef_resolved=len(resolved))
        for symbol, lei in resolved.items():
            con.execute(
                "INSERT INTO esef_tasks (symbol, lei) VALUES (?, ?) ON CONFLICT (symbol) DO NOTHING",
                [symbol, lei],
            )
        due = con.execute(
            "SELECT symbol, lei FROM esef_tasks WHERE last_fetched_at IS NULL"
            " OR last_fetched_at < ? ORDER BY last_fetched_at NULLS FIRST LIMIT ?",
            [time.time() - ESEF_REFRESH_SECONDS, limit],
        ).fetchall()
        if not due:
            return outcome

        if client is None:
            from crible.providers.esef import EsefClient

            client = EsefClient()
        from crible.ingest.raw import write_raw_statement
        from crible.providers.esef import facts_to_frames

        for symbol, lei in due:
            try:
                filings = client.filings_for_lei(lei)
                if not filings:
                    con.execute(
                        "UPDATE esef_tasks SET last_fetched_at = ? WHERE symbol = ?",
                        [time.time(), symbol],
                    )
                    continue
                xbrl = client.fetch_xbrl_json(filings[0])
                frames = facts_to_frames(xbrl) if xbrl else {}
                fetched_at = time.time()
                for (statement_type, freq), frame in frames.items():
                    write_raw_statement(
                        data, symbol=symbol, provider="esef", statement_type=statement_type,
                        freq=freq, frame=frame, fetched_at=fetched_at, skip_identical=True,
                    )
                con.execute(
                    "UPDATE esef_tasks SET last_fetched_at = ? WHERE symbol = ?",
                    [fetched_at, symbol],
                )
                if frames:
                    outcome["enriched"].append(symbol)
                    log.info("esef: enriched %s (%d statement frame(s)) from filing of LEI %s",
                             symbol, len(frames), lei)
            except Exception as exc:  # noqa: BLE001 — outage: record, resume next cycle
                outcome["outage"] = f"{symbol}: {exc}"
                log.warning("esef: outage on %s: %s — resuming next cycle", symbol, exc)
                break
        return outcome
    finally:
        con.close()


def _esef_due(con: duckdb.DuckDBPyConnection, symbol: str, cutoff: float) -> bool:
    row = con.execute(
        "SELECT last_fetched_at FROM esef_tasks WHERE symbol = ?", [symbol]
    ).fetchone()
    return row is None or row[0] is None or row[0] < cutoff


def run_esef_sweep(
    limit: int = 100, client=None, mapping: dict[str, str] | None = None,
    page_size: int = 100, max_pages: int = 300,
    time_budget_seconds: float | None = None,
) -> dict:
    """FR-010 at index scale: walk filings.xbrl.org's FULL index (newest
    first) instead of querying one LEI at a time — every request lands on a
    real filing, so the whole EU/EEA ESEF gisement (~25k filings) is
    coverable in a few nightly runs. Filers outside the universe are counted
    and skipped; dual listings sharing one LEI are all enriched; freshness
    (esef_tasks, 90 days) prevents refetching. Outages resume next run."""
    from crible.providers.esef import facts_to_frames, filing_lei
    from crible.providers.gleif import load_mapping

    data = config.data_dir()
    outcome: dict = {
        "enriched": [], "skipped_unknown": 0, "outage": None, "skipped": None, "stopped": None,
    }
    if limit <= 0:
        # the crawl-marathon runs `refresh --esef-limit 0`: a pure no-op —
        # no entities paging, no backfill, zero requests to filings.xbrl.org
        outcome["skipped"] = "limit 0"
        return outcome
    # wall-clock budget (run_refresh --max-minutes): a partial sweep is fine —
    # freshness state makes the next run resume where this one stopped
    stage_deadline = (
        None if time_budget_seconds is None else time.monotonic() + time_budget_seconds
    )

    def out_of_time() -> bool:
        return stage_deadline is not None and time.monotonic() >= stage_deadline

    if mapping is None:
        mapping, skipped, outage = load_mapping(data)
        if mapping is None:
            outcome["skipped"], outcome["outage"] = skipped, outage
            if skipped:
                log.info("esef sweep: %s", skipped)
            else:
                log.warning("esef sweep: %s — resuming next run", outage)
            return outcome

    if client is None:
        from crible.providers.esef import EsefClient

        client = EsefClient()

    con = _connect()
    try:
        con.execute(ESEF_SCHEMA)
        outcome["backfilled"] = _backfill_nameless_isins(con, client, mapping)
        rows = con.execute(
            "SELECT symbol, isin FROM companies"
            " WHERE region = 'europe' AND NOT delisted AND isin IS NOT NULL"
        ).fetchall()
        by_lei: dict[str, list[str]] = {}
        for symbol, isin in rows:
            lei = mapping.get(isin)
            if lei:
                by_lei.setdefault(lei, []).append(symbol)
        update_heartbeat(
            esef_resolved=sum(len(v) for v in by_lei.values()),
            esef_unmatched=len(rows) - sum(len(v) for v in by_lei.values()),
        )
        # a fresh operational DB (every CI run) must not forget what previous
        # runs fetched — re-derive freshness from the restored raw layer
        seed_tasks_from_raw(
            con, data, provider="esef", table="esef_tasks", key_column="lei",
            keys={s: lei for lei, symbols in by_lei.items() for s in symbols},
        )

        from crible.ingest.raw import write_raw_statement

        cutoff = time.time() - ESEF_REFRESH_SECONDS
        seen_leis: set[str] = set()
        page = 1
        while len(outcome["enriched"]) < limit and page <= max_pages:
            if out_of_time():
                outcome["stopped"] = "budget"
                break
            try:
                filings, _total = client.filings_index(page_size=page_size, page_number=page)
            except Exception as exc:  # noqa: BLE001 — outage: record, resume next run
                outcome["outage"] = f"index page {page}: {exc}"
                log.warning("esef sweep: %s — resuming next run", outcome["outage"])
                return outcome
            if not filings:
                break
            page += 1
            for filing in filings:
                if out_of_time():
                    outcome["stopped"] = "budget"
                    break
                lei = filing_lei(filing)
                if not lei or lei in seen_leis:
                    continue  # newest-first: only the latest filing per filer
                seen_leis.add(lei)
                symbols = by_lei.get(lei)
                if not symbols:
                    outcome["skipped_unknown"] += 1
                    continue
                due = [s for s in symbols if _esef_due(con, s, cutoff)]
                if not due:
                    continue
                try:
                    xbrl = client.fetch_xbrl_json(filing)
                    frames = facts_to_frames(xbrl) if xbrl else {}
                except Exception as exc:  # noqa: BLE001
                    outcome["outage"] = f"{lei}: {exc}"
                    log.warning("esef sweep: outage on %s: %s — resuming next run", lei, exc)
                    return outcome
                fetched_at = time.time()
                for symbol in due:
                    for (statement_type, freq), frame in frames.items():
                        write_raw_statement(
                            data, symbol=symbol, provider="esef",
                            statement_type=statement_type, freq=freq,
                            frame=frame, fetched_at=fetched_at, skip_identical=True,
                        )
                    con.execute(
                        "INSERT INTO esef_tasks (symbol, lei, last_fetched_at) VALUES (?, ?, ?)"
                        " ON CONFLICT (symbol) DO UPDATE SET"
                        " last_fetched_at = excluded.last_fetched_at",
                        [symbol, lei, fetched_at],
                    )
                    if frames:
                        outcome["enriched"].append(symbol)
                if len(outcome["enriched"]) >= limit:
                    break
            if outcome["stopped"]:
                break
        if outcome["enriched"]:
            log.info("esef sweep: enriched %d listings (%d filers outside the universe)%s",
                     len(outcome["enriched"]), outcome["skipped_unknown"],
                     " — stopped on time budget" if outcome["stopped"] else "")
        return outcome
    finally:
        con.close()

