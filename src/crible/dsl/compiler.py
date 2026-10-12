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
    "added at snapshot build time (FR-015) — recompute the snapshot (`crible compute`) after upgrading"
)


def _check_field(field: str, whitelist: set[str], position: int) -> str:
    if field in whitelist:
        return field
    if field in BUILD_TIME_COLUMNS:
        raise DslError(
            f"unknown field {field!r} at position {position}", position=position, hint=BUILD_TIME_REMEDY
        )
    closest = difflib.get_close_matches(field, sorted(whitelist), n=1)
    hint = f"did you mean {closest[0]!r}?" if closest else "no similar field exists"
    raise DslError(f"unknown field {field!r} at position {position}", position=position, hint=hint)


def field_kind(duckdb_type: str) -> str:
    """Coarse kind of a DuckDB column type: string | boolean | number | other."""
    upper = str(duckdb_type).upper()
    if "VARCHAR" in upper:
        return "string"
    if upper == "BOOLEAN":
        return "boolean"
    if any(t in upper for t in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "REAL")):
        return "number"
    return "other"


# kind → (message noun, example comparison) for a literal of the wrong type
_KIND_HINTS = {
    "number": ("a numeric field", "compare it to a number, e.g. {field} > 0"),
    "boolean": ("a true/false field", "compare it to true or false, e.g. {field} = true"),
    "string": ("a text field", "compare it to a quoted string, e.g. {field} = 'value'"),
}


def _check_value(field: str, value: float | str, kind: str | None, position: int) -> None:
    """A literal of the wrong type is a DslError (422) — DuckDB would raise a
    ConversionException (500) or silently cast."""
    if kind not in _KIND_HINTS:
        return
    expects_text = kind == "string"
    if isinstance(value, str) == expects_text:
        return
    noun, example = _KIND_HINTS[kind]
    raise DslError(
        f"{field!r} is {noun} at position {position}", position=position, hint=example.format(field=field)
    )


def compile_query(
    ast: object, whitelist: set[str], types: dict[str, str] | None = None
) -> tuple[str, list[float | str]]:
    """``types`` (field → field_kind) turns on literal type checking."""
    params: list[float | str] = []
    types = types or {}

    def emit(node: object) -> str:
        if isinstance(node, Comparison):
            field = _check_field(node.field, whitelist, node.position)
            _check_value(field, node.value, types.get(field), node.position)
            params.append(node.value)
            return f'"{field}" {OPERATORS[node.op]} ?'
        if isinstance(node, InList):
            field = _check_field(node.field, whitelist, node.position)
            for value in node.values:
                _check_value(field, value, types.get(field), node.position)
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
    """ORDER BY with ``"symbol" ASC`` as the final tie-break (and the whole
    order when no sort is asked): LIMIT/OFFSET pages over ties — integer
    piotroski_f, NULL ranks — would otherwise repeat or skip rows."""
    clauses = []
    fields = set()
    for raw in (sort or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        direction = "DESC" if raw.startswith("-") else "ASC"
        field = raw.lstrip("+-")
        _check_field(field, whitelist, position=0)
        clauses.append(f'"{field}" {direction}')
        fields.add(field)
    if "symbol" in whitelist and "symbol" not in fields:
        clauses.append('"symbol" ASC')
    return f" ORDER BY {', '.join(clauses)}" if clauses else ""
