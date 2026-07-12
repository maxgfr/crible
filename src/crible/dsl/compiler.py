"""FR-004 / NFR-011 — AST → parametrized DuckDB SQL over a strict whitelist.

Injection is impossible by construction: field names must be members of the
whitelist (rejected otherwise, with the closest valid name suggested), every
value is emitted as a ``?`` placeholder, and the SQL text is assembled only
from whitelisted identifiers, fixed operators and placeholders.
"""

from __future__ import annotations

import difflib

from crible.compute.ranks import RANK_COLUMNS
from crible.dsl.parser import BoolOp, Comparison, DslError, InList, Not

OPERATORS = {">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=", "==": "=", "!=": "<>", "<>": "<>"}

# FR-015 columns exist only in snapshots computed after the upgrade — the
# remedy is a recompute, not a spelling fix.
BUILD_TIME_COLUMNS = set(RANK_COLUMNS) | {"rank_peer_group", "rank_missing_pillars", "return_6m"}
BUILD_TIME_REMEDY = (
    "added at snapshot build time (FR-015) — recompute the snapshot"
    " (`crible compute`) after upgrading"
)


def _check_field(field: str, whitelist: set[str], position: int) -> str:
    if field in whitelist:
        return field
    if field in BUILD_TIME_COLUMNS:
        raise DslError(f"unknown field {field!r} at position {position}", position=position, hint=BUILD_TIME_REMEDY)
    closest = difflib.get_close_matches(field, sorted(whitelist), n=1)
    hint = f"did you mean {closest[0]!r}?" if closest else "no similar field exists"
    raise DslError(f"unknown field {field!r} at position {position}", position=position, hint=hint)


def compile_query(ast: object, whitelist: set[str]) -> tuple[str, list[float | str]]:
    params: list[float | str] = []

    def emit(node: object) -> str:
        if isinstance(node, Comparison):
            field = _check_field(node.field, whitelist, node.position)
            params.append(node.value)
            return f'"{field}" {OPERATORS[node.op]} ?'
        if isinstance(node, InList):
            field = _check_field(node.field, whitelist, node.position)
            params.extend(node.values)
            placeholders = ", ".join("?" for _ in node.values)
            return f'"{field}" IN ({placeholders})'
        if isinstance(node, Not):
            return f"NOT ({emit(node.operand)})"
        if isinstance(node, BoolOp):
            joined = f" {node.op} ".join(f"({emit(op)})" for op in node.operands)
            return joined
        raise DslError(f"unsupported query node: {type(node).__name__}")

    return emit(ast), params


def compile_sort(sort: str | None, whitelist: set[str]) -> str:
    if not sort:
        return ""
    clauses = []
    for raw in sort.split(","):
        raw = raw.strip()
        if not raw:
            continue
        direction = "DESC" if raw.startswith("-") else "ASC"
        field = raw.lstrip("+-")
        _check_field(field, whitelist, position=0)
        clauses.append(f'"{field}" {direction}')
    return f" ORDER BY {', '.join(clauses)}" if clauses else ""
