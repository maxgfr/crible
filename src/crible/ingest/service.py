"""FR-008 — the ingest service loop: bootstrap → crawl → compute → publish.

Runs as the `ingest` Docker service. On first boot the bootstrap sample
(~100 liquid symbols: CAC 40 + DAX 40 + 20 US mega-caps, overridable via
CRIBLE_BOOTSTRAP_SAMPLE) is front-loaded so a first screen returns rows within
hours. Compute runs after every crawl cycle. A heartbeat (data/status.json)
exposes budget usage and cycle outcomes to `crible status` and GET /status.
"""

from __future__ import annotations

import logging
import os
import time

import duckdb

from crible import config
from crible.compute.snapshot import build_snapshot_incremental, publish_snapshot
from crible.ingest.backoff import BackoffPolicy
from crible.ingest.budget import TokenBucket
from crible.ingest.crawler import Crawler, CrawlOutcome
from crible.ingest.enrichment import (  # re-exported for the CLI/tests/site_export
    run_edgar_bulk,
    run_edgar_cycle,
    run_esef_cycle,
    run_esef_sweep,
    run_fsds,
)
from crible.ingest.queue import CrawlQueue
from crible.ingest.state import connect as _connect
from crible.ingest.state import update_heartbeat
from crible.providers.yfinance_provider import YFinanceProvider
from crible.universe import BootstrapReport, UniverseSourceError, refresh_universe

__all__ = [
    "run_esef_cycle", "run_esef_sweep", "run_edgar_cycle", "run_edgar_bulk", "run_fsds",
    "run_once", "run_refresh", "run_loop", "run_bootstrap", "run_compute",
    "run_price_refresh", "bootstrap_sample",
]

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


def prioritize_sample(con: duckdb.DuckDBPyConnection, symbols: list[str]) -> None:
    """Front-load the bootstrap sample: highest priority, due immediately."""
    con.execute(
        "UPDATE crawl_tasks SET priority = -1, next_due = 0 WHERE symbol IN "
        f"({', '.join('?' for _ in symbols)})",
        symbols,
    )


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


def restore_queue_from_raw(con: duckdb.DuckDBPyConnection, data_dir) -> int:
    """Rebuild crawl freshness from the raw layer's filename stamps.

    A nightly Actions run starts from a fresh operational DB — only the raw
    parquet layer travels in the published dataset. Without this, every night
    re-crawls the same queue head instead of advancing (the coverage
    plateau observed at ~145 symbols). Raw filenames carry fetched_at as a
    zero-padded ms stamp, so the queue state is recoverable exactly.
    """
    from pathlib import Path

    from crible.ingest.queue import QUARTER_SECONDS

    root = Path(data_dir) / "raw" / "provider=yfinance"
    restored = 0
    for directory in root.glob("symbol=*"):
        stamps = []
        for file in directory.glob("*.parquet"):
            try:
                stamps.append(int(file.stem.rsplit("-", 1)[1]) / 1000.0)
            except (IndexError, ValueError):
                continue
        if not stamps:
            continue
        crawled_at = max(stamps)
        con.execute(
            "UPDATE crawl_tasks SET last_crawled_at = ?, next_due = ?"
            " WHERE symbol = ? AND (last_crawled_at IS NULL OR last_crawled_at < ?)",
            [crawled_at, crawled_at + QUARTER_SECONDS,
             directory.name.split("=", 1)[1], crawled_at],
        )
        restored += 1
    return restored


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


UNIVERSE_REFRESH_SECONDS = 7 * 24 * 3600


def maybe_refresh_universe(
    con: duckdb.DuckDBPyConnection, last_refresh: float, now: float, *, fetch=None,
    interval: float = UNIVERSE_REFRESH_SECONDS,
) -> float:
    """Re-fetch the universe (idempotent upsert) and re-seed the queue at most
    once per ``interval``; returns the timestamp to record. The self-hosted
    loop only bootstrapped once (F5), so new listings and delistings froze
    forever. A source outage is logged and retried next interval, never fatal."""
    if now - last_refresh < interval:
        return last_refresh
    try:
        refresh_universe(con, fetch=fetch) if fetch else refresh_universe(con)
        CrawlQueue(con).seed_from_universe()
        log.info("universe refreshed (periodic)")
    except UniverseSourceError as exc:
        log.warning("periodic universe refresh skipped: %s", exc)
    return now


def _make_crawler(con: duckdb.DuckDBPyConnection, provider=None, budget=None) -> Crawler:
    return Crawler(
        queue=CrawlQueue(con),
        provider=provider if provider is not None else YFinanceProvider(),
        # a caller-owned bucket is reused across cycles (the long-lived loop
        # keeps ONE rolling window, NFR-007); only a one-shot gets a fresh one
        budget=budget
        if budget is not None
        else TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600),
        backoff=BackoffPolicy(),
        data_dir=config.data_dir(),
        fetch_timeout=config.fetch_timeout(),
    )


def run_once(limit: int = 50, budget=None, provider=None, symbols: list[str] | None = None) -> CrawlOutcome:
    """One crawl cycle — or, with ``symbols``, a targeted crawl of exactly
    that set (in order), bypassing the queue's priority/due-ness. The budget
    is still charged per fetch: targeting never busts the hourly cap."""
    from crible.ingest.budget import load_bucket, save_bucket

    budget_state = config.data_dir() / "budget-state.json"
    if budget is None:
        # standalone invocations minutes apart must share ONE rolling hour
        budget = load_bucket(budget_state)
    con = _connect()
    try:
        crawler = _make_crawler(con, provider=provider, budget=budget)
        if symbols:
            outcome = CrawlOutcome()
            for symbol in symbols:
                (outcome.fetched if crawler.crawl_symbol(symbol) else outcome.failed).append(symbol)
        else:
            outcome = crawler.run_cycle(limit=limit)
        save_bucket(crawler.budget, budget_state)
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


def run_price_refresh(budget: TokenBucket, provider=None, topup_limit: int = 500) -> dict:
    """FR-011 — daily price refresh for the priority set within the budget.

    After the sample, audited-but-never-priced symbols (``price_gap_symbols``:
    ESEF/EDGAR fundamentals in raw, no price from any source) ride whatever
    budget is left, Europe-first — 1 request each, so a full nightly bucket
    prices ~330 of the ~1.8k French ESEF listings the crawl (7 req/symbol)
    and Stooq (no FR bulk dump) never reach. The sample always goes first:
    the gap top-up can only spend what the sample left over.
    """
    from crible.ingest.prices import PriceRefresher, price_gap_symbols

    if provider is None:
        provider = _YfPriceAdapter()
    refresher = PriceRefresher(
        provider=provider,
        budget=budget,
        data_dir=config.data_dir(),
        fetch_timeout=config.fetch_timeout(),
    )
    sample = bootstrap_sample()
    gaps = [s for s in price_gap_symbols(config.data_dir(), limit=topup_limit) if s not in set(sample)]
    outcome = refresher.refresh(sample + gaps)
    return {
        "refreshed": len(outcome.refreshed),
        "skipped": len(outcome.skipped),
        "aborted": outcome.aborted,
        "topup_candidates": len(gaps),
    }


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
    snapshot = build_snapshot_incremental(data)
    if snapshot is None:
        log.info("compute: no raw changes since last build — snapshot unchanged")
        return 0
    if snapshot.empty:
        log.info("compute: no raw data yet — skipping publish")
        return 0
    publish_snapshot(snapshot, data)
    log.info("compute: published %d rows × %d columns", len(snapshot), len(snapshot.columns))
    return len(snapshot)


# --max-minutes keeps this much wall-clock back for prune + compute + publish;
# the crawl and every enrichment stage yield before eating into it
ENRICH_RESERVE_SECONDS = 1800.0


def run_refresh(
    deadline_seconds: float = 9000.0,
    esef_limit: int = 25,
    edgar_limit: int = 25,
    *,
    edgar_bulk: bool = False,
    fsds_quarters: int = 0,
    fetch_gleif: bool = False,
    fetch_fx: bool = False,
    fetch_universe=None,
    provider=None,
    price_provider=None,
    edgar_client=None,
    cycle_limit: int = 10,
    max_seconds: float | None = None,
) -> dict:
    """One bounded, resumable refresh pass — the nightly dataset run.

    Bootstrap (falling back to the last-good universe.parquet when
    FinanceDatabase is down) → prioritized crawl on ONE shared token bucket
    until the queue drains or the deadline passes (repeated ``ingest --once``
    calls would each get a fresh bucket and bust the hourly budget) → ESEF +
    EDGAR enrichment → price refresh → prune the raw layer → compute + publish.

    ``deadline_seconds`` bounds the CRAWL loop only (historical semantics).
    ``max_seconds`` is the WHOLE-RUN wall-clock guard: the crawl and every
    enrichment stage (ESEF sweep, EDGAR bulk, FSDS) stop at
    ``max_seconds − ENRICH_RESERVE_SECONDS`` so prune + compute + publish
    always get their reserve — a slow night ships a partial-but-published
    dataset instead of being killed by the CI job timeout with nothing.
    """
    from crible.ingest.raw import prune_raw
    from crible.universe import (
        export_universe_parquet,
        fetch_financedatabase,
        restore_universe_from_parquet,
    )

    started = time.monotonic()
    hard_deadline = started + max_seconds if max_seconds else None
    deadline = started + deadline_seconds
    if hard_deadline is not None:
        deadline = min(deadline, hard_deadline - ENRICH_RESERVE_SECONDS)

    def stage_budget() -> float | None:
        """Seconds left for enrichment before the compute reserve — None = unbounded."""
        if hard_deadline is None:
            return None
        return max(0.0, (hard_deadline - ENRICH_RESERVE_SECONDS) - time.monotonic())

    data = config.data_dir()
    result: dict = {"universe_restored": False}

    if fetch_gleif:
        # self-heal the audited-EU layer: pull the GLEIF ISIN→LEI file into the
        # mirror. Skip only if the operator supplied their own file; otherwise
        # fetch every run — fetch_if_stale re-downloads only when the mirror copy
        # is stale (weekly), so GLEIF stays FRESH instead of freezing after the
        # first fetch (F9). Best-effort — a failure just leaves ESEF idle.
        from crible.providers.gleif import fetch_gleif as _fetch_gleif

        legacy = (data / "isin-lei.csv").exists() or (data / "isin-lei.zip").exists()
        if not legacy:
            try:
                _fetch_gleif(data)
            except Exception as exc:  # noqa: BLE001 — never kills the refresh
                log.warning("gleif fetch failed: %s — ESEF may stay idle this run", exc)

    if fetch_fx:
        # mirror the ECB daily rates so the snapshot gets *_eur companions
        from crible.providers.fx import fetch_rates

        try:
            fetch_rates(data)
        except Exception as exc:  # noqa: BLE001 — never kills the refresh
            log.warning("fx rates fetch failed: %s — *_eur columns stay NULL this run", exc)

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
        # resume the rolling budget window where the previous run left it —
        # chained CI runs must never double-spend the hour (NFR-007)
        from crible.ingest.budget import load_bucket, save_bucket

        budget_state = data / "budget-state.json"
        crawler = _make_crawler(con, provider=provider, budget=load_bucket(budget_state))
        prioritize_sample(con, bootstrap_sample())
        # AFTER prioritizing: fresh raw wins over the sample's due-now reset,
        # so the nightly advances into new symbols instead of re-crawling
        result["queue_restored"] = restore_queue_from_raw(con, data)
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
        save_bucket(crawler.budget, budget_state)  # crash-safe: enrichment may die
        stats = _queue_stats(con)
    finally:
        con.close()

    try:
        # index sweep, not per-LEI polling: every request lands on a real
        # filing, so the nightly covers actual EU filers at full speed
        result["esef"] = run_esef_sweep(limit=esef_limit, time_budget_seconds=stage_budget())
    except Exception as exc:  # noqa: BLE001 — enrichment never kills the refresh
        log.warning("esef sweep failed: %s", exc)
        result["esef"] = {"outage": str(exc)}
    try:
        if edgar_bulk:
            # the bulk sweep marks every issuer fetched, so the per-CIK
            # cycle below finds nothing due — no double work
            result["edgar_bulk"] = run_edgar_bulk(
                client=edgar_client, time_budget_seconds=stage_budget()
            )
        result["edgar"] = run_edgar_cycle(limit=edgar_limit, client=edgar_client)
    except Exception as exc:  # noqa: BLE001 — enrichment never kills the refresh
        log.warning("edgar cycle failed: %s", exc)
        result["edgar"] = {"outage": str(exc)}
    if fsds_quarters > 0:
        try:
            from crible.providers.edgar_fsds import recent_quarters

            result["fsds"] = run_fsds(
                recent_quarters(fsds_quarters), client=edgar_client,
                time_budget_seconds=stage_budget(),
            )
        except Exception as exc:  # noqa: BLE001 — enrichment never kills the refresh
            log.warning("fsds cycle failed: %s", exc)
            result["fsds"] = {"outage": str(exc)}
    budget_left = stage_budget()
    if budget_left is not None and budget_left <= 0:
        # inside the compute reserve — prices are an enrichment, never a gate
        result["prices"] = {"skipped": "time budget"}
    else:
        try:
            result["prices"] = run_price_refresh(crawler.budget, provider=price_provider)
        except Exception as exc:  # noqa: BLE001
            log.warning("price refresh failed: %s", exc)
            result["prices"] = {"error": str(exc)}
        save_bucket(crawler.budget, budget_state)  # prices spend the window too

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
    last_universe_refresh = time.time()  # just bootstrapped — next refresh in a week
    last_gleif = 0.0  # fetch on the first cycle so ESEF is not idle out-of-the-box
    last_fx = 0.0     # fetch on the first cycle so the snapshot gets *_eur columns
    last_edgar_bulk = 0.0
    # ONE long-lived bucket shared by the crawl and the price refresh — both
    # hit Yahoo, so NFR-007 (330 req/h) is a single rolling window, not one per
    # cycle. Rebuilding it each cycle (the F1 bug) reset the window every few
    # seconds and busted the budget. Mirrors run_refresh's shared bucket.
    budget = TokenBucket(capacity=config.budget_per_hour(), window_seconds=3600)
    provider = YFinanceProvider()
    while True:
        # first boot: crawl exactly the bootstrap sample, then publish
        # immediately — a first screen must return rows within hours (FR-008)
        limit = max(10, len(bootstrap_sample())) if first_cycle else cycle_limit
        outcome = run_once(limit=limit, budget=budget, provider=provider)
        first_cycle = False
        now = time.time()

        # FR-011: daily priority-tier price refresh (shares the request budget)
        if now - last_price_refresh >= 20 * 3600:
            try:
                log.info("price refresh: %s", run_price_refresh(budget))
            except Exception as exc:  # noqa: BLE001 — never kills the loop
                log.warning("price refresh failed: %s", exc)
            last_price_refresh = now

        # F5: keep the universe current — new listings / delistings otherwise
        # freeze at first boot (the self-hosted loop never re-fetched it)
        con = _connect()
        try:
            last_universe_refresh = maybe_refresh_universe(con, last_universe_refresh, now)
        except Exception as exc:  # noqa: BLE001 — never kills the loop
            log.warning("universe refresh failed: %s", exc)
        finally:
            con.close()

        # F6: self-heal the audited-EU layer for the self-hosted `ingest --loop`
        # deployment — download the GLEIF ISIN→LEI file (weekly) if we have none,
        # so ESEF is not idle out-of-the-box exactly as `crible refresh` does
        if now - last_gleif >= 7 * 24 * 3600:
            try:
                from crible.providers.gleif import fetch_gleif

                data = config.data_dir()
                legacy = (data / "isin-lei.csv").exists() or (data / "isin-lei.zip").exists()
                if not legacy:
                    fetch_gleif(data)  # mirror re-downloads only when stale (weekly)
            except Exception as exc:  # noqa: BLE001 — never kills the loop
                log.warning("gleif self-heal failed: %s", exc)
            last_gleif = now

        # F8: mirror the ECB rates (daily) so the snapshot gets *_eur columns
        if now - last_fx >= 20 * 3600:
            try:
                from crible.providers.fx import fetch_rates

                fetch_rates(config.data_dir())
            except Exception as exc:  # noqa: BLE001 — never kills the loop
                log.warning("fx rates fetch failed: %s", exc)
            last_fx = now

        # optional: whole-US audited coverage fast via the companyfacts bulk
        # (~1.4 GB) weekly, instead of the per-CIK trickle — opt-in for hosts
        # that can spare the bandwidth (CRIBLE_EDGAR_BULK=1)
        if os.environ.get("CRIBLE_EDGAR_BULK") and now - last_edgar_bulk >= 7 * 24 * 3600:
            try:
                log.info("edgar bulk: %s", run_edgar_bulk())
            except Exception as exc:  # noqa: BLE001 — never kills the loop
                log.warning("edgar bulk failed: %s", exc)
            last_edgar_bulk = now

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
