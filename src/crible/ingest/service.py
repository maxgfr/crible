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
from crible.universe import BootstrapReport, refresh_universe

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


def _make_crawler(con: duckdb.DuckDBPyConnection) -> Crawler:
    return Crawler(
        queue=CrawlQueue(con),
        provider=YFinanceProvider(),
        budget=TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600),
        backoff=BackoffPolicy(),
        data_dir=config.data_dir(),
    )


def run_once(limit: int = 50) -> CrawlOutcome:
    con = _connect()
    try:
        crawler = _make_crawler(con)
        outcome = crawler.run_cycle(limit=limit)
        write_heartbeat(
            {
                "requests_last_hour": crawler.budget.used_in_window(),
                "budget_per_hour": crawler.budget.capacity,
                "last_cycle": {"fetched": len(outcome.fetched), "failed": len(outcome.failed)},
                "provider": crawler.provider.id,
                "ts": time.time(),
            }
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
            bars = yf.Ticker(symbol).history(period="5d", auto_adjust=False)
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

        if outcome.fetched or now - last_compute >= compute_every_seconds:
            run_compute()
            last_compute = now
        if not outcome.fetched and not outcome.failed:
            time.sleep(60)  # queue empty or nothing due — idle politely
