"""FR-008 — the ingest service loop: bootstrap → crawl → compute → publish.

Runs as the `ingest` Docker service. On first boot the bootstrap sample
(~100 liquid symbols: CAC 40 + DAX 40 + 20 US mega-caps, overridable via
CRIBLE_BOOTSTRAP_SAMPLE) is front-loaded so a first screen returns rows within
hours. Compute runs after every crawl cycle. A heartbeat (data/status.json)
exposes budget usage and cycle outcomes to `crible status` and GET /status.
"""

from __future__ import annotations

import json
import logging
import os
import time

import duckdb

from crible import config
from crible.compute.snapshot import build_snapshot, publish_snapshot
from crible.ingest.backoff import BackoffPolicy
from crible.ingest.budget import TokenBucket
from crible.ingest.crawler import Crawler, CrawlOutcome
from crible.ingest.queue import CrawlQueue
from crible.providers.yfinance_provider import YFinanceProvider
from crible.universe import BootstrapReport, UniverseSourceError, refresh_universe

log = logging.getLogger("crible.ingest.service")

CAC40 = [
    "AI.PA", "AIR.PA", "ALO.PA", "MT.AS", "CS.PA", "BNP.PA", "EN.PA", "BVI.PA", "CAP.PA",
    "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "EDEN.PA", "ENGI.PA", "EL.PA", "ERF.PA", "RMS.PA",
    "KER.PA", "OR.PA", "LR.PA", "MC.PA", "ML.PA", "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA",
    "SAF.PA", "SGO.PA", "SAN.PA", "SU.PA", "GLE.PA", "STLAP.PA", "STMPA.PA", "TEP.PA",
    "HO.PA", "TTE.PA", "URW.AS", "VIE.PA", "DG.PA",
]
DAX40 = [
    "ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BEI.DE", "BMW.DE", "BNR.DE", "CBK.DE", "CON.DE",
    "1COV.DE", "DTG.DE", "DBK.DE", "DB1.DE", "DHL.DE", "DTE.DE", "EOAN.DE", "FRE.DE", "FME.DE",
    "HNR1.DE", "HEI.DE", "HEN3.DE", "IFX.DE", "MBG.DE", "MRK.DE", "MTX.DE", "MUV2.DE",
    "P911.DE", "QIA.DE", "RHM.DE", "RWE.DE", "SAP.DE", "SRT3.DE", "SIE.DE", "ENR.DE", "SHL.DE",
    "SY1.DE", "VOW3.DE", "VNA.DE", "ZAL.DE", "PAH3.DE",
]
US_MEGA = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "LLY", "AVGO", "JPM",
    "V", "TSLA", "XOM", "UNH", "MA", "PG", "JNJ", "HD", "COST", "ORCL",
]


def bootstrap_sample() -> list[str]:
    override = os.environ.get("CRIBLE_BOOTSTRAP_SAMPLE")
    if override:
        return [s.strip() for s in override.split(",") if s.strip()]
    return CAC40 + DAX40 + US_MEGA


def _connect() -> duckdb.DuckDBPyConnection:
    path = config.database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def prioritize_sample(con: duckdb.DuckDBPyConnection, symbols: list[str]) -> None:
    """Front-load the bootstrap sample: highest priority, due immediately."""
    con.execute(
        "UPDATE crawl_tasks SET priority = -1, next_due = 0 WHERE symbol IN "
        f"({', '.join('?' for _ in symbols)})",
        symbols,
    )


def write_heartbeat(payload: dict) -> None:
    path = config.data_dir() / "status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, default=str))
    tmp.rename(path)


def update_heartbeat(**fields) -> None:
    """Merge fields into the heartbeat (read-modify-write, atomic rename)."""
    path = config.data_dir() / "status.json"
    current: dict = {}
    if path.exists():
        try:
            current = json.loads(path.read_text())
        except json.JSONDecodeError:
            current = {}
    current.update(fields)
    write_heartbeat(current)


def _queue_stats(con: duckdb.DuckDBPyConnection) -> dict:
    """FR-005 AC-3 — coverage %, freshness histogram, per-region backlog."""
    stats: dict = {}
    tables = {
        r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()
    }
    if "companies" in tables:
        stats["universe"] = con.execute("SELECT count(*) FROM companies").fetchone()[0]
        stats["by_region"] = dict(
            con.execute("SELECT region, count(*) FROM companies GROUP BY region").fetchall()
        )
    if "crawl_tasks" in tables:
        crawled = con.execute(
            "SELECT count(*) FROM crawl_tasks WHERE last_crawled_at IS NOT NULL"
        ).fetchone()[0]
        stats["crawled"] = crawled
        if stats.get("universe"):
            stats["coverage_pct"] = round(100.0 * crawled / stats["universe"], 2)
        stats["freshness"] = dict(
            con.execute(
                """
                SELECT CASE
                    WHEN last_crawled_at IS NULL THEN 'never'
                    WHEN last_crawled_at > epoch(now()) - 7*86400 THEN '<7d'
                    WHEN last_crawled_at > epoch(now()) - 30*86400 THEN '<30d'
                    WHEN last_crawled_at > epoch(now()) - 90*86400 THEN '<90d'
                    ELSE 'stale' END AS bucket, count(*)
                FROM crawl_tasks GROUP BY bucket
                """
            ).fetchall()
        )
    return stats


def run_bootstrap() -> BootstrapReport:
    con = _connect()
    try:
        report = refresh_universe(con)
        queue = CrawlQueue(con)
        queue.seed_from_universe()
        prioritize_sample(con, bootstrap_sample())
        return report
    finally:
        con.close()


def _make_crawler(con: duckdb.DuckDBPyConnection, provider=None) -> Crawler:
    return Crawler(
        queue=CrawlQueue(con),
        provider=provider if provider is not None else YFinanceProvider(),
        budget=TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600),
        backoff=BackoffPolicy(),
        data_dir=config.data_dir(),
    )


def run_once(limit: int = 50) -> CrawlOutcome:
    con = _connect()
    try:
        crawler = _make_crawler(con)
        outcome = crawler.run_cycle(limit=limit)
        update_heartbeat(
            requests_last_hour=crawler.budget.used_in_window(),
            budget_per_hour=crawler.budget.capacity,
            last_cycle={"fetched": len(outcome.fetched), "failed": len(outcome.failed)},
            providers={crawler.provider.id: "healthy"},
            **_queue_stats(con),
            ts=time.time(),
        )
        return outcome
    finally:
        con.close()


ESEF_REFRESH_SECONDS = 90 * 24 * 3600
ESEF_SCHEMA = """
CREATE TABLE IF NOT EXISTS esef_tasks (
    symbol          VARCHAR PRIMARY KEY,
    lei             VARCHAR NOT NULL,
    last_fetched_at DOUBLE
)
"""


def run_esef_cycle(limit: int = 5, client=None, mapping: dict[str, str] | None = None) -> dict:
    """FR-010 — the ESEF enrichment cycle: EU companies whose ISIN resolves to
    an LEI (GLEIF file at data/isin-lei.csv, operator-provided) get audited
    figures pulled from filings.xbrl.org into provider='esef' raw statements.
    Outages are recorded and the cycle resumes next time; unmatched listings
    are counted, never errored."""
    from crible.providers.gleif import load_isin_lei_map, resolve_leis

    data = config.data_dir()
    outcome: dict = {"enriched": [], "unmatched": 0, "outage": None, "skipped": None}

    if mapping is None:
        mapping_file = next(
            (p for p in (data / "isin-lei.csv", data / "isin-lei.zip") if p.exists()), None
        )
        if mapping_file is None:
            outcome["skipped"] = (
                "no GLEIF mapping file — download the ISIN-LEI relationship file to data/isin-lei.csv"
            )
            log.info("esef: %s", outcome["skipped"])
            return outcome
        try:
            mapping = load_isin_lei_map(mapping_file)
        except Exception as exc:  # noqa: BLE001 — treated as outage (FR-010 AC-2)
            outcome["outage"] = f"gleif mapping unreadable: {exc}"
            log.warning("esef: %s — resuming next cycle", outcome["outage"])
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
        from crible.providers.esef import facts_to_frames
        from crible.ingest.raw import write_raw_statement

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
                        freq=freq, frame=frame, fetched_at=fetched_at,
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


EDGAR_REFRESH_SECONDS = 90 * 24 * 3600
EDGAR_SCHEMA = """
CREATE TABLE IF NOT EXISTS edgar_tasks (
    symbol          VARCHAR PRIMARY KEY,
    cik             BIGINT NOT NULL,
    last_fetched_at DOUBLE
)
"""


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
    outcome: dict = {"enriched": 0, "unmatched": 0, "outage": None, "skipped": None}

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


def run_price_refresh(budget: TokenBucket, provider=None) -> dict:
    """FR-011 — daily price refresh for the priority set within the budget."""
    from crible.ingest.prices import PriceRefresher

    if provider is None:
        provider = _YfPriceAdapter()
    refresher = PriceRefresher(provider=provider, budget=budget, data_dir=config.data_dir())
    outcome = refresher.refresh(bootstrap_sample())
    return {"refreshed": len(outcome.refreshed), "skipped": len(outcome.skipped), "aborted": outcome.aborted}


class _YfPriceAdapter:
    id = "yfinance"

    def fetch_prices(self, symbol: str):
        import yfinance as yf

        from crible.providers.base import RateLimitedError
        from crible.providers.yfinance_provider import RATE_LIMIT_MARKERS

        try:
            # one year of daily bars is still ONE request — and FR-015's
            # return_6m needs ≥182 days of history to compute (momentum
            # pillar); a 5d window left it permanently NaN
            bars = yf.Ticker(symbol).history(period="1y", auto_adjust=False)
        except Exception as exc:  # noqa: BLE001
            if any(m in str(exc).lower() for m in RATE_LIMIT_MARKERS):
                raise RateLimitedError(str(exc)) from exc
            raise
        return bars.reset_index() if bars is not None and not bars.empty else None


def run_compute() -> int:
    data = config.data_dir()
    if not (data / "universe.parquet").exists() and config.database_path().exists():
        # self-heal installs bootstrapped before universe export existed
        con = _connect()
        try:
            from crible.universe import export_universe_parquet

            has = con.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
            ).fetchone()[0]
            if has:
                export_universe_parquet(con, data)
                log.info("compute: exported missing universe.parquet")
        finally:
            con.close()
    snapshot = build_snapshot(data)
    if snapshot.empty:
        log.info("compute: no raw data yet — skipping publish")
        return 0
    publish_snapshot(snapshot, data)
    log.info("compute: published %d rows × %d columns", len(snapshot), len(snapshot.columns))
    return len(snapshot)


def run_refresh(
    deadline_seconds: float = 9000.0,
    esef_limit: int = 25,
    edgar_limit: int = 25,
    *,
    edgar_bulk: bool = False,
    fetch_universe=None,
    provider=None,
    price_provider=None,
    edgar_client=None,
    cycle_limit: int = 10,
) -> dict:
    """One bounded, resumable refresh pass — the nightly demo-data run.

    Bootstrap (falling back to the last-good universe.parquet when
    FinanceDatabase is down) → prioritized crawl on ONE shared token bucket
    until the queue drains or the deadline passes (repeated ``ingest --once``
    calls would each get a fresh bucket and bust the hourly budget) → ESEF +
    EDGAR enrichment → price refresh → prune the raw layer → compute + publish.
    """
    from crible.ingest.raw import prune_raw
    from crible.universe import (
        export_universe_parquet,
        fetch_financedatabase,
        restore_universe_from_parquet,
    )

    started = time.monotonic()
    deadline = started + deadline_seconds
    data = config.data_dir()
    result: dict = {"universe_restored": False}

    con = _connect()
    try:
        try:
            report = refresh_universe(con, fetch=fetch_universe or fetch_financedatabase)
            result["universe_loaded"] = report.loaded
        except UniverseSourceError:
            if not (data / "universe.parquet").exists():
                raise
            log.warning("universe source down — restoring last-good universe.parquet")
            result["universe_loaded"] = restore_universe_from_parquet(
                con, data / "universe.parquet"
            )
            result["universe_restored"] = True
        crawler = _make_crawler(con, provider=provider)  # CrawlQueue() re-seeds
        prioritize_sample(con, bootstrap_sample())
        export_universe_parquet(con, data)

        fetched = failed = 0
        while time.monotonic() < deadline:
            outcome = crawler.run_cycle(limit=cycle_limit)
            fetched += len(outcome.fetched)
            failed += len(outcome.failed)
            if not outcome.fetched and not outcome.failed:
                break  # nothing due — the queue is drained for this run
        result["fetched"] = fetched
        result["failed"] = failed
        stats = _queue_stats(con)
    finally:
        con.close()

    try:
        result["esef"] = run_esef_cycle(limit=esef_limit)
    except Exception as exc:  # noqa: BLE001 — enrichment never kills the refresh
        log.warning("esef cycle failed: %s", exc)
        result["esef"] = {"outage": str(exc)}
    try:
        if edgar_bulk:
            # the bulk sweep marks every issuer fetched, so the per-CIK
            # cycle below finds nothing due — no double work
            result["edgar_bulk"] = run_edgar_bulk(client=edgar_client)
        result["edgar"] = run_edgar_cycle(limit=edgar_limit, client=edgar_client)
    except Exception as exc:  # noqa: BLE001 — enrichment never kills the refresh
        log.warning("edgar cycle failed: %s", exc)
        result["edgar"] = {"outage": str(exc)}
    try:
        result["prices"] = run_price_refresh(crawler.budget, provider=price_provider)
    except Exception as exc:  # noqa: BLE001
        log.warning("price refresh failed: %s", exc)
        result["prices"] = {"error": str(exc)}

    result["pruned"] = prune_raw(data)
    result["snapshot_rows"] = run_compute()
    result["took_seconds"] = round(time.monotonic() - started, 1)
    update_heartbeat(
        last_refresh={
            k: result[k]
            for k in ("fetched", "failed", "pruned", "snapshot_rows",
                      "universe_restored", "took_seconds")
        },
        requests_last_hour=crawler.budget.used_in_window(),
        budget_per_hour=crawler.budget.capacity,
        last_cycle={"fetched": fetched, "failed": failed},
        providers={crawler.provider.id: "healthy"},
        **stats,
        ts=time.time(),
    )
    return result


def run_loop(cycle_limit: int = 40, compute_every_seconds: float = 1800.0) -> None:  # pragma: no cover — long-lived loop
    # cycle_limit × ~7 requests must stay under the hourly budget so a cycle
    # never stalls mid-way on the token bucket before its compute runs
    con = _connect()
    has_universe = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
    ).fetchone()[0]
    con.close()
    if not has_universe:
        log.info("first boot — bootstrapping universe")
        run_bootstrap()

    first_cycle = not (config.data_dir() / "snapshot").exists()
    last_compute = 0.0
    last_price_refresh = 0.0
    price_budget = TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600)
    while True:
        # first boot: crawl exactly the bootstrap sample, then publish
        # immediately — a first screen must return rows within hours (FR-008)
        limit = max(10, len(bootstrap_sample())) if first_cycle else cycle_limit
        outcome = run_once(limit=limit)
        first_cycle = False
        now = time.time()

        # FR-011: daily priority-tier price refresh (shares the request budget)
        if now - last_price_refresh >= 20 * 3600:
            try:
                log.info("price refresh: %s", run_price_refresh(price_budget))
            except Exception as exc:  # noqa: BLE001 — never kills the loop
                log.warning("price refresh failed: %s", exc)
            last_price_refresh = now

        # FR-010: audited ESEF enrichment (keyless; idle without a GLEIF file)
        try:
            esef = run_esef_cycle()
            if esef["enriched"] or esef["outage"]:
                log.info("esef cycle: %s", esef)
        except Exception as exc:  # noqa: BLE001
            log.warning("esef cycle failed: %s", exc)

        # FR-016: audited EDGAR enrichment (keyless; own SEC fair-access pace)
        try:
            edgar = run_edgar_cycle()
            if edgar["enriched"] or edgar["outage"]:
                log.info("edgar cycle: %s", edgar)
        except Exception as exc:  # noqa: BLE001
            log.warning("edgar cycle failed: %s", exc)

        if outcome.fetched or now - last_compute >= compute_every_seconds:
            run_compute()
            last_compute = now
        if not outcome.fetched and not outcome.failed:
            time.sleep(60)  # queue empty or nothing due — idle politely
