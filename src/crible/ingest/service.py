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


def run_compute() -> int:
    data = config.data_dir()
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
    while True:
        # first boot: crawl exactly the bootstrap sample, then publish
        # immediately — a first screen must return rows within hours (FR-008)
        limit = max(10, len(bootstrap_sample())) if first_cycle else cycle_limit
        outcome = run_once(limit=limit)
        first_cycle = False
        now = time.time()
        if outcome.fetched or now - last_compute >= compute_every_seconds:
            run_compute()
            last_compute = now
        if not outcome.fetched and not outcome.failed:
            time.sleep(60)  # queue empty or nothing due — idle politely
