"""The shared runtime: one place that opens DuckDB, mounts the snapshot and
exposes the exact same screening surface to the CLI and the API (FR-005/FR-006).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb

from crible import config
from crible.compute.snapshot import SNAPSHOT_NAME
from crible.dsl.parser import DslError
from crible.store import screen as store_screen
from crible.store import screen_count, whitelist_from_relation


class SnapshotMissingError(RuntimeError):
    """No snapshot has been computed yet — run `crible ingest` then `crible compute`."""


@dataclass
class Runtime:
    data_dir: Path

    @classmethod
    def from_env(cls) -> "Runtime":
        return cls(data_dir=config.data_dir())

    # ------------------------------------------------------------- plumbing

    def snapshot_path(self) -> Path:
        return self.data_dir / "snapshot" / SNAPSHOT_NAME

    def connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        path = self.data_dir / "crible.duckdb"
        path.parent.mkdir(parents=True, exist_ok=True)
        if read_only and not path.exists():
            raise SnapshotMissingError(
                "no database yet — run `crible ingest --bootstrap` first"
            )
        return duckdb.connect(str(path), read_only=read_only)

    def mount_snapshot(self, con: duckdb.DuckDBPyConnection) -> None:
        """Expose ``snapshot_latest``: latest period per symbol + universe metadata."""
        snapshot = self.snapshot_path()
        if not snapshot.exists():
            raise SnapshotMissingError(
                "no snapshot yet — run `crible ingest` then `crible compute` first"
            )
        has_companies = con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
        ).fetchone()[0]
        join = (
            """
            JOIN companies c USING (symbol)
            """
            if has_companies
            else ""
        )
        extra = (
            "c.name, c.country, c.country_name, c.region, c.sector, c.industry, c.exchange, c.currency,"
            if has_companies
            else ""
        )
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW snapshot_latest AS
            SELECT * EXCLUDE (_rn) FROM (
                SELECT s.*, {extra}
                       row_number() OVER (PARTITION BY s.symbol ORDER BY s.period DESC) AS _rn
                FROM read_parquet('{snapshot.as_posix()}') s {join}
            ) WHERE _rn = 1
            """
        )

    def whitelist(self, con: duckdb.DuckDBPyConnection) -> set[str]:
        return whitelist_from_relation(con, "snapshot_latest")

    # -------------------------------------------------------------- surface

    def screen(
        self,
        query: str,
        *,
        sort: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        con = self.connect()
        try:
            self.mount_snapshot(con)
            whitelist = self.whitelist(con)
            rows = store_screen(
                con, query, whitelist=whitelist, sort=sort, limit=limit, offset=offset
            )
            total = screen_count(con, query, whitelist=whitelist)
            return rows, total
        finally:
            con.close()

    def status(self) -> dict:
        out: dict = {"data_dir": str(self.data_dir)}
        db = self.data_dir / "crible.duckdb"
        if db.exists():
            con = duckdb.connect(str(db), read_only=True)
            try:
                tables = {
                    r[0]
                    for r in con.execute(
                        "SELECT table_name FROM information_schema.tables"
                    ).fetchall()
                }
                if "companies" in tables:
                    out["universe"] = con.execute("SELECT count(*) FROM companies").fetchone()[0]
                    out["by_region"] = dict(
                        con.execute("SELECT region, count(*) FROM companies GROUP BY region").fetchall()
                    )
                if "crawl_tasks" in tables:
                    crawled = con.execute(
                        "SELECT count(*) FROM crawl_tasks WHERE last_crawled_at IS NOT NULL"
                    ).fetchone()[0]
                    out["crawled"] = crawled
                    if out.get("universe"):
                        out["coverage_pct"] = round(100.0 * crawled / out["universe"], 2)
                    out["freshness"] = dict(
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
            finally:
                con.close()
        heartbeat = self.data_dir / "status.json"
        if heartbeat.exists():
            try:
                out["ingest"] = json.loads(heartbeat.read_text())
            except json.JSONDecodeError:
                out["ingest"] = {"error": "unreadable heartbeat"}
        out["snapshot"] = self.snapshot_path().exists()
        out["generated_at"] = time.time()
        return out


__all__ = ["Runtime", "SnapshotMissingError", "DslError"]
