"""FR-004 — the screening entry point: DSL in, DataFrame out.

Queries run against the ``snapshot_latest`` relation (one row per symbol —
its latest fiscal period joined with universe metadata). ``screen`` is the
single implementation the CLI, the API and therefore the UI all share.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from crible.dsl.compiler import compile_query, compile_sort, field_kind
from crible.dsl.parser import DslError, parse

# the one cap on a single read — screen pages and the "full" CSV export alike
EXPORT_LIMIT = MAX_LIMIT = 10_000
# OFFSET beyond this is no real page (and LIMIT+OFFSET must fit in int64)
MAX_OFFSET = 10_000_000


def _compile_where(query: str, whitelist: set[str], types: dict[str, str] | None = None) -> tuple[str, list]:
    """A blank query means "no filter" — the full snapshot. The DSL grammar
    itself still rejects empty input (golden-locked with the TS port)."""
    if not query or not query.strip():
        return "TRUE", []
    return compile_query(parse(query), whitelist, types)


def _query(con: duckdb.DuckDBPyConnection, sql: str, params: list) -> pd.DataFrame:
    """Run compiled SQL; a DuckDB error is the query's fault (the compiler
    only emits whitelisted identifiers), so it surfaces as a DslError — a
    4xx, never a 500."""
    try:
        return con.execute(sql, params).fetchdf()
    except duckdb.Error as exc:
        raise DslError(f"the query cannot run on this snapshot: {type(exc).__name__}", hint=str(exc)) from exc


def _paging(limit: int, offset: int) -> tuple[int, int]:
    if not isinstance(limit, int) or not isinstance(offset, int) or limit < 0 or offset < 0:
        raise DslError("limit and offset must be non-negative integers")
    if offset > MAX_OFFSET:
        raise DslError(f"offset {offset} is past the last possible page", hint=f"at most {MAX_OFFSET}")
    return min(limit, MAX_LIMIT, EXPORT_LIMIT), offset


def screen(
    con: duckdb.DuckDBPyConnection,
    query: str,
    *,
    whitelist: set[str],
    sort: str | None = None,
    limit: int = 100,
    offset: int = 0,
    types: dict[str, str] | None = None,
) -> pd.DataFrame:
    rows, _ = screen_with_total(
        con, query, whitelist=whitelist, sort=sort, limit=limit, offset=offset, types=types
    )
    return rows


def screen_with_total(
    con: duckdb.DuckDBPyConnection,
    query: str,
    *,
    whitelist: set[str],
    sort: str | None = None,
    limit: int = 100,
    offset: int = 0,
    types: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, int]:
    """One page plus the total match count from ONE pass (count(*) OVER ())."""
    where, params = _compile_where(query, whitelist, types)
    order = compile_sort(sort, whitelist)
    limit, offset = _paging(limit, offset)
    sql = (
        f"SELECT *, count(*) OVER () AS __total FROM snapshot_latest WHERE {where}{order}"
        f" LIMIT {limit} OFFSET {offset}"
    )
    rows = _query(con, sql, params)
    if len(rows):
        total = int(rows["__total"].iloc[0])
    elif offset or not limit:  # a page past the end (or a count-only call) still reports the real total
        total = screen_count(con, query, whitelist=whitelist, types=types)
    else:
        total = 0
    return rows.drop(columns="__total"), total


def screen_count(
    con: duckdb.DuckDBPyConnection, query: str, *, whitelist: set[str], types: dict[str, str] | None = None
) -> int:
    where, params = _compile_where(query, whitelist, types)
    return int(_query(con, f"SELECT count(*) AS n FROM snapshot_latest WHERE {where}", params)["n"].iloc[0])


def whitelist_from_relation(con: duckdb.DuckDBPyConnection, relation: str = "snapshot_latest") -> set[str]:
    return set(field_types_from_relation(con, relation))


def field_types_from_relation(
    con: duckdb.DuckDBPyConnection, relation: str = "snapshot_latest"
) -> dict[str, str]:
    """Column → coarse kind (dsl.compiler.field_kind), for literal type checks."""
    return {
        name: field_kind(col_type) for name, col_type, *_ in con.execute(f"DESCRIBE {relation}").fetchall()
    }
