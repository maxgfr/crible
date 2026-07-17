"""MCP server — screen crible from any agent (`crible mcp`, stdio).

Read-only by construction: the five tools wrap the shared Runtime — the same
DSL and the same schema-derived whitelist as the CLI/API/UI — and expose NO
crawl/refresh/compute: side effects stay out of the tool surface. Standard
registration, after `crible bootstrap` pulled the published dataset:

    claude mcp add crible -e CRIBLE_DATA_DIR=$HOME/.crible-data -- crible mcp
"""

from __future__ import annotations

import json
from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from crible.dsl.parser import DslError
from crible.runtime import Runtime, SnapshotMissingError

MAX_LIMIT = 200

mcp = FastMCP(
    "crible",
    instructions=(
        "Keyless fundamental stock screener over the published open dataset. "
        "screen() takes the crible DSL (e.g. \"piotroski_f >= 7 AND country "
        "IN ('FR','DE')\"; a blank query screens the whole covered universe); "
        "fields() lists every filterable column; presets() the published "
        "starting screens; company() one symbol's full period history; "
        "status() dataset coverage."
    ),
)


def _runtime() -> Runtime:
    return Runtime.from_env()


@mcp.tool()
def screen(query: str = "", sort: str | None = None, limit: int = 50) -> dict:
    """Screen the covered universe with the crible DSL.

    Blank query = every covered company. sort is a column name, '-' prefix
    for descending (e.g. '-composite_rank'). Returns at most `limit` rows
    (capped at 200) plus the total match count.
    """
    limit = max(1, min(int(limit), MAX_LIMIT))
    try:
        rows, total = _runtime().screen(query, sort=sort, limit=limit)
    except DslError as exc:
        # the message already carries position + did-you-mean hint
        raise ValueError(f"DSL error: {exc}") from exc
    except SnapshotMissingError as exc:
        raise ValueError(str(exc)) from exc
    records = json.loads(rows.to_json(orient="records"))  # NaN → null
    return {"total": total, "returned": len(records), "rows": records}


@mcp.tool()
def fields() -> list[dict]:
    """Every filterable snapshot column with its coarse type — the DSL
    whitelist, derived from the live schema."""
    return _runtime().fields()


@mcp.tool()
def presets() -> list[dict]:
    """The published preset screens: id, name, description, the FULL DSL
    (editable starting points, never hidden logic) and the columns each
    surfaces."""
    from crible.presets import PRESETS

    return [asdict(p) for p in PRESETS.values()]


@mcp.tool()
def company(symbol: str) -> dict | None:
    """One symbol's profile and full period history (every computed
    indicator, newest first). None when the symbol is not in the universe."""
    return _runtime().company(symbol)


@mcp.tool()
def status() -> dict:
    """Dataset coverage: universe size, by-region split, crawl heartbeat,
    snapshot presence."""
    out = _runtime().status()
    out.pop("data_dir", None)  # no local paths in the tool surface
    return out


def serve() -> None:
    """stdio transport — what `crible mcp` runs."""
    mcp.run()
