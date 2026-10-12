"""The shared runtime: readers (CLI screen / API) touch ONLY published Parquet
(snapshot + universe) — never the ingest-owned DuckDB file (ADR-0003, single
writer per layer). One implementation of screening for CLI, API and UI.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from crible import config
from crible.compute.snapshot import SNAPSHOT_NAME
from crible.dsl.parser import DslError
from crible.store import field_types_from_relation, screen_with_total


class SnapshotMissingError(RuntimeError):
    """No snapshot has been computed yet — run `crible ingest` then `crible compute`."""


# The latest-period table is materialised ONCE per published snapshot (keyed
# on its path + mtime + size) instead of re-running the row_number() window
# over the whole parquet on every request — twice (rows + count) before.
_LATEST_SQL = """
    CREATE TABLE snapshot_latest AS
    SELECT * EXCLUDE (_rn) FROM (
        SELECT s.*, row_number() OVER (PARTITION BY s.symbol ORDER BY s.period DESC) AS _rn
        FROM read_parquet(?) s
    ) WHERE _rn = 1
"""
_latest_lock = threading.Lock()
_latest_cache: dict[str, tuple[tuple[int, int], duckdb.DuckDBPyConnection, dict[str, str]]] = {}


def _latest(snapshot: Path) -> tuple[duckdb.DuckDBPyConnection, dict[str, str]]:
    """(a cursor on the materialised snapshot_latest, field → kind)."""
    try:
        stat = snapshot.stat()
    except FileNotFoundError:
        raise SnapshotMissingError(
            "no snapshot yet — run `crible ingest` then `crible compute` first"
        ) from None
    key, stamp = str(snapshot.resolve()), (stat.st_mtime_ns, stat.st_size)
    with _latest_lock:
        cached = _latest_cache.get(key)
        if cached is None or cached[0] != stamp:
            con = duckdb.connect()
            con.execute(_LATEST_SQL, [snapshot.as_posix()])
            # the previous connection is left to the GC: a request may still
            # hold a cursor on it
            cached = (stamp, con, field_types_from_relation(con))
            _latest_cache[key] = cached
        return cached[1].cursor(), cached[2]


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

    # -------------------------------------------------------------- surface

    def screen(
        self,
        query: str,
        *,
        sort: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[pd.DataFrame, int]:
        con, types = _latest(self.snapshot_path())
        try:
            return screen_with_total(
                con, query, whitelist=set(types), sort=sort, limit=limit, offset=offset, types=types
            )
        finally:
            con.close()

    def fields(self) -> list[dict]:
        """Snapshot columns with coarse types — the query builder's field list.

        Always derived from the live schema (DESCRIBE), never a hand-kept
        list, so the builder can only offer fields the DSL whitelist accepts.
        Empty (never an error) while no snapshot exists.
        """
        try:
            con, _ = _latest(self.snapshot_path())
        except SnapshotMissingError:
            return []
        try:
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
                    "SELECT * FROM read_parquet(?) WHERE symbol = ?",
                    [self.universe_path().as_posix(), symbol],
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
                    "SELECT * FROM read_parquet(?) WHERE symbol = ? ORDER BY period DESC",
                    [self.snapshot_path().as_posix(), symbol],
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

    def prices(self, symbol: str) -> list[dict]:
        """Published daily bars for one symbol, oldest first — [] when the
        symbol has no series (the drawer chart hides; never an error)."""
        from crible.price_series import load_symbol_series

        series = load_symbol_series(self.data_dir, symbol)
        if series.empty:
            return []
        series = series.assign(date=series["date"].dt.strftime("%Y-%m-%d"))
        return json.loads(series.drop(columns=["symbol"]).to_json(orient="records"))

    def search(self, q: str, limit: int = 20) -> list[dict]:
        """Symbol/name substring search over the universe — the way a 161k-row
        universe stays browsable before (and beyond) crawl coverage."""
        needle = q.strip()
        if not needle or not self.universe_path().exists():
            return []
        # the needle is a literal substring: LIKE's own % and _ are escaped
        pattern = "%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        con = duckdb.connect()
        try:
            rows = con.execute(
                "SELECT symbol, name, country, sector FROM read_parquet(?)"
                " WHERE symbol ILIKE ? ESCAPE '\\' OR name ILIKE ? ESCAPE '\\'"
                " ORDER BY symbol LIMIT ?",
                [self.universe_path().as_posix(), pattern, pattern, limit],
            ).fetchall()
        finally:
            con.close()
        return [{"symbol": s, "name": n, "country": c, "sector": sec} for s, n, c, sec in rows]

    def status(self) -> dict:
        out: dict = {"data_dir": str(self.data_dir)}
        if self.universe_path().exists():
            con = duckdb.connect()
            try:
                path = self.universe_path().as_posix()
                out["universe"] = con.execute("SELECT count(*) FROM read_parquet(?)", [path]).fetchone()[0]
                out["by_region"] = dict(
                    con.execute(
                        "SELECT region, count(*) FROM read_parquet(?) GROUP BY region", [path]
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
