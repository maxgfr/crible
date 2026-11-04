"""FR-004 — the screening entry point: DSL in, DataFrame out.

Queries run against the ``snapshot_latest`` relation (one row per symbol —
its latest fiscal period joined with universe metadata). ``screen`` is the
single implementation the CLI, the API and therefore the UI all share.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from crible.dsl.compiler import _check_field, compile_query, compile_sort, field_kind
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


# ─── stats: where one company sits among its peers ─────────────────────────

STATS_MAX_FIELDS = 40
STATS_QUANTILES = (0.1, 0.25, 0.5, 0.75, 0.9)


def _stats_fields(fields: list[str], whitelist: set[str], types: dict[str, str]) -> list[str]:
    if not fields:
        raise DslError("name at least one numeric field", hint="e.g. return_on_equity gross_margin")
    if len(fields) > STATS_MAX_FIELDS:
        raise DslError(f"at most {STATS_MAX_FIELDS} fields per call", hint=f"{len(fields)} were named")
    out: list[str] = []
    for i, field in enumerate(fields):
        _check_field(field, whitelist, i)  # unknown field → did-you-mean hint
        if types.get(field) != "number":
            raise DslError(f"{field!r} is not a numeric field", position=i, hint="statistics need numbers")
        if field not in out:
            out.append(field)
    return out


def _peer_group(
    con: duckdb.DuckDBPyConnection, symbol: str, types: dict[str, str], min_peers: int
) -> tuple[str, list, dict]:
    """region×sector of `symbol` when it holds ≥ min_peers latest rows, else the
    whole snapshot — the rule compute/ranks.py applies to the percentile ranks."""
    has = [c for c in ("region", "sector") if c in types]
    if len(has) < 2:
        return "TRUE", [], {"basis": "universe", "reason": "no region/sector columns"}
    row = con.execute("SELECT region, sector FROM snapshot_latest WHERE symbol = ?", [symbol]).fetchone()
    region, sector = row if row else (None, None)
    if region is None or sector is None:
        return "TRUE", [], {"basis": "universe", "reason": "the symbol has no region or sector"}
    where, params = "region = ? AND sector = ?", [region, sector]
    n = con.execute(f"SELECT count(*) FROM snapshot_latest WHERE {where}", params).fetchone()[0]
    if n < min_peers:
        return (
            "TRUE",
            [],
            {
                "basis": "universe",
                "reason": f"{region}×{sector} holds {n} < {min_peers} rows",
                "region": region,
                "sector": sector,
            },
        )
    return where, params, {"basis": "region×sector", "region": region, "sector": sector}


def _finite(v: object) -> float | None:
    if v is None:
        return None
    f = float(v)
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def stats(
    con: duckdb.DuckDBPyConnection,
    fields: list[str],
    *,
    query: str = "",
    symbol: str | None = None,
    whitelist: set[str],
    types: dict[str, str],
    min_peers: int,
) -> dict | None:
    """The distribution of numeric fields over a peer group, and — with a
    symbol — that symbol's value and percentile within it.

    The group is the DSL `query` when one is given, else the symbol's
    region×sector (≥ min_peers rows, else the universe), else the universe.
    Non-finite values and NULLs are left out of every statistic; `n` is per
    field. The percentile is the mid-rank share of the group below the value
    (ties count half), 0–100. None when `symbol` is not in the snapshot.
    """
    names = _stats_fields(list(fields), whitelist, types)
    if (
        symbol is not None
        and not con.execute("SELECT 1 FROM snapshot_latest WHERE symbol = ?", [symbol]).fetchone()
    ):
        return None
    if query and query.strip():
        where, params = _compile_where(query, whitelist, types)
        group: dict = {"basis": "query", "query": query}
    elif symbol is not None:
        where, params, group = _peer_group(con, symbol, types, min_peers)
    else:
        where, params, group = "TRUE", [], {"basis": "universe"}
    group["rows"] = int(
        _query(con, f"SELECT count(*) AS n FROM snapshot_latest WHERE {where}", params)["n"].iloc[0]
    )

    values: dict[str, float | None] = {}
    if symbol is not None:
        cols = ", ".join(f'CAST("{f}" AS DOUBLE) AS "{f}"' for f in names)
        own = _query(con, f"SELECT {cols} FROM snapshot_latest WHERE symbol = ?", [symbol])
        values = {
            f: _finite(own[f].iloc[0]) if len(own) and not pd.isna(own[f].iloc[0]) else None for f in names
        }

    out: dict[str, dict] = {}
    for f in names:
        x = f'CASE WHEN isfinite(CAST("{f}" AS DOUBLE)) THEN CAST("{f}" AS DOUBLE) END'
        parts = [
            f"count({x}) AS n",
            f"avg({x}) AS mean",
            f"min({x}) AS min",
            f"max({x}) AS max",
            *(f"quantile_cont({x}, {q}) AS q{i}" for i, q in enumerate(STATS_QUANTILES)),
        ]
        extra: list = []
        if values.get(f) is not None:
            parts.append(
                f"avg(CASE WHEN {x} < ? THEN 1.0 WHEN {x} = ? THEN 0.5 ELSE 0.0 END) FILTER (WHERE {x} IS NOT NULL) AS pct"
            )
            extra = [values[f], values[f]]
        row = _query(
            con, f"SELECT {', '.join(parts)} FROM snapshot_latest WHERE {where}", extra + params
        ).iloc[0]
        entry: dict = {"n": int(row["n"])}
        for k in ("mean", "min", "max"):
            entry[k] = _finite(row[k]) if not pd.isna(row[k]) else None
        for i, q in enumerate(STATS_QUANTILES):
            label = "median" if q == 0.5 else f"p{round(q * 100)}"
            entry[label] = _finite(row[f"q{i}"]) if not pd.isna(row[f"q{i}"]) else None
        if symbol is not None:
            entry["value"] = values.get(f)
            entry["percentile"] = (
                round(float(row["pct"]) * 100, 1) if "pct" in row.index and not pd.isna(row["pct"]) else None
            )
        out[f] = entry
    return {"symbol": symbol, "group": group, "fields": out}
