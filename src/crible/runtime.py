"""The shared runtime: readers (CLI screen / API) touch ONLY published Parquet
(snapshot + universe) — never the ingest-owned DuckDB file (ADR-0003, single
writer per layer). One implementation of screening for CLI, API and UI.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

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

    def universe_path(self) -> Path:
        return self.data_dir / "universe.parquet"

    def mount_snapshot(self, con: duckdb.DuckDBPyConnection) -> None:
        """Expose ``snapshot_latest``: the latest fiscal period per symbol.

        The snapshot is self-contained (universe metadata embedded at compute
        time), so this only ever reads Parquet.
        """
        snapshot = self.snapshot_path()
        if not snapshot.exists():
            raise SnapshotMissingError(
                "no snapshot yet — run `crible ingest` then `crible compute` first"
            )
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW snapshot_latest AS
            SELECT * EXCLUDE (_rn) FROM (
                SELECT s.*,
                       row_number() OVER (PARTITION BY s.symbol ORDER BY s.period DESC) AS _rn
                FROM read_parquet('{snapshot.as_posix()}') s
            ) WHERE _rn = 1
            """
        )

    # -------------------------------------------------------------- surface

    def screen(
        self,
        query: str,
        *,
        sort: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[pd.DataFrame, int]:
        con = duckdb.connect()
        try:
            self.mount_snapshot(con)
            whitelist = whitelist_from_relation(con, "snapshot_latest")
            rows = store_screen(
                con, query, whitelist=whitelist, sort=sort, limit=limit, offset=offset
            )
            total = screen_count(con, query, whitelist=whitelist)
            return rows, total
        finally:
            con.close()

    def fields(self) -> list[dict]:
        """Snapshot columns with coarse types — the query builder's field list.

        Always derived from the live schema (DESCRIBE), never a hand-kept
        list, so the builder can only offer fields the DSL whitelist accepts.
        Empty (never an error) while no snapshot exists.
        """
        con = duckdb.connect()
        try:
            try:
                self.mount_snapshot(con)
            except SnapshotMissingError:
                return []
            described = con.execute("DESCRIBE snapshot_latest").fetchall()
        finally:
            con.close()
        return [
            {
                "name": name,
                "type": "string" if "VARCHAR" in str(col_type).upper() else "number",
            }
            for name, col_type, *_ in described
        ]

    def company(self, symbol: str) -> dict | None:
        """Profile (universe) + full period history (snapshot) for one symbol."""
        profile: dict | None = None
        if self.universe_path().exists():
            con = duckdb.connect()
            try:
                rows = con.execute(
                    f"SELECT * FROM read_parquet('{self.universe_path().as_posix()}') WHERE symbol = ?",
                    [symbol],
                ).fetchdf()
            finally:
                con.close()
            if len(rows):
                profile = rows.iloc[0].to_dict()

        periods: list[dict] = []
        if self.snapshot_path().exists():
            con = duckdb.connect()
            try:
                history = con.execute(
                    f"SELECT * FROM read_parquet('{self.snapshot_path().as_posix()}')"
                    " WHERE symbol = ? ORDER BY period DESC",
                    [symbol],
                ).fetchdf()
            finally:
                con.close()
            periods = json.loads(history.to_json(orient="records"))
            if profile is None and periods:
                profile = {k: periods[0].get(k) for k in ("symbol", "name", "country", "region", "sector")}

        if profile is None:
            return None
        clean_profile = {k: (None if pd.isna(v) else v) for k, v in profile.items()}
        return {"profile": clean_profile, "periods": periods}

    def search(self, q: str, limit: int = 20) -> list[dict]:
        """Symbol/name substring search over the universe — the way a 161k-row
        universe stays browsable before (and beyond) crawl coverage."""
        needle = q.strip()
        if not needle or not self.universe_path().exists():
            return []
        con = duckdb.connect()
        try:
            rows = con.execute(
                f"SELECT symbol, name, country, sector"
                f" FROM read_parquet('{self.universe_path().as_posix()}')"
                " WHERE symbol ILIKE ? OR name ILIKE ?"
                " ORDER BY symbol LIMIT ?",
                [f"%{needle}%", f"%{needle}%", limit],
            ).fetchall()
        finally:
            con.close()
        return [
            {"symbol": s, "name": n, "country": c, "sector": sec} for s, n, c, sec in rows
        ]

    def status(self) -> dict:
        out: dict = {"data_dir": str(self.data_dir)}
        if self.universe_path().exists():
            con = duckdb.connect()
            try:
                path = self.universe_path().as_posix()
                out["universe"] = con.execute(
                    f"SELECT count(*) FROM read_parquet('{path}')"
                ).fetchone()[0]
                out["by_region"] = dict(
                    con.execute(
                        f"SELECT region, count(*) FROM read_parquet('{path}') GROUP BY region"
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
