"""FR-004 — the screening entry point: DSL in, DataFrame out.

Queries run against the ``snapshot_latest`` relation (one row per symbol —
its latest fiscal period joined with universe metadata). ``screen`` is the
single implementation the CLI, the API and therefore the UI all share.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from crible.dsl.compiler import compile_query, compile_sort
from crible.dsl.parser import DslError, parse

MAX_LIMIT = 10_000


def _compile_where(query: str, whitelist: set[str]) -> tuple[str, list]:
    """A blank query means "no filter" — the full snapshot. The DSL grammar
    itself still rejects empty input (golden-locked with the TS port)."""
    if not query or not query.strip():
        return "TRUE", []
    return compile_query(parse(query), whitelist)


def screen(
    con: duckdb.DuckDBPyConnection,
    query: str,
    *,
    whitelist: set[str],
    sort: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> pd.DataFrame:
    where, params = _compile_where(query, whitelist)
    order = compile_sort(sort, whitelist)
    if not isinstance(limit, int) or not isinstance(offset, int) or limit < 0 or offset < 0:
        raise DslError("limit and offset must be non-negative integers")
    limit = min(limit, MAX_LIMIT)
    sql = f"SELECT * FROM snapshot_latest WHERE {where}{order} LIMIT {limit} OFFSET {offset}"
    return con.execute(sql, params).fetchdf()


def screen_count(con: duckdb.DuckDBPyConnection, query: str, *, whitelist: set[str]) -> int:
    where, params = _compile_where(query, whitelist)
    return con.execute(f"SELECT count(*) FROM snapshot_latest WHERE {where}", params).fetchone()[0]


def whitelist_from_relation(con: duckdb.DuckDBPyConnection, relation: str = "snapshot_latest") -> set[str]:
    rows = con.execute(f"DESCRIBE {relation}").fetchall()
    return {r[0] for r in rows}
