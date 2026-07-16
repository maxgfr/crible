"""FR-006 — the HTTP API. No auth by design (single self-hosted operator,
ADR-0002); user input can only produce 2xx/4xx, never a 5xx (DSL errors are
422 with position + hint; a fresh install screens to an empty set with a hint).
Serves the built SPA when ui/dist exists."""

from __future__ import annotations

import io
import time
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from crible.dsl.parser import DslError
from crible.presets import PRESETS
from crible.runtime import Runtime, SnapshotMissingError

MAX_PAGE_SIZE = 1000
EXPORT_LIMIT = 10_000


class ScreenRequest(BaseModel):
    query: str
    sort: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=MAX_PAGE_SIZE)


def create_app() -> FastAPI:
    app = FastAPI(title="crible", docs_url="/api/docs", openapi_url="/api/openapi.json")

    def runtime() -> Runtime:
        return Runtime.from_env()

    @app.exception_handler(DslError)
    async def dsl_error_handler(_, exc: DslError):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=422,
            content={"detail": {"error": str(exc), "position": exc.position, "hint": exc.hint}},
        )

    @app.post("/api/screen")
    def screen(request: ScreenRequest):
        started = time.perf_counter()
        try:
            rows, total = runtime().screen(
                request.query,
                sort=request.sort,
                limit=request.page_size,
                offset=(request.page - 1) * request.page_size,
            )
        except SnapshotMissingError as exc:
            return {"rows": [], "total": 0, "page": request.page, "tookMs": 0, "hint": str(exc)}
        took = round((time.perf_counter() - started) * 1000, 2)
        import json as _json

        return {
            "rows": _json.loads(rows.to_json(orient="records")),
            "total": total,
            "page": request.page,
            "tookMs": took,
        }

    @app.get("/api/screen.csv")
    def screen_csv(query: str, sort: str | None = None, columns: str | None = None):
        """Full result set of the query; `columns` (comma-separated) restricts
        the export to the currently visible columns (FR-007 AC-1)."""
        try:
            rows, _ = runtime().screen(query, sort=sort, limit=EXPORT_LIMIT, offset=0)
        except SnapshotMissingError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if columns:
            wanted = [c.strip() for c in columns.split(",") if c.strip()]
            keep = [c for c in wanted if c in rows.columns]
            if not keep:
                raise HTTPException(status_code=422, detail="no requested column exists")
            rows = rows[keep]
        buffer = io.StringIO()
        rows.to_csv(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="crible-screen.csv"'},
        )

    @app.get("/api/presets")
    def presets():
        return [asdict(p) for p in PRESETS.values()]

    @app.get("/api/company/{symbol}")
    def company(symbol: str):
        detail = runtime().company(symbol)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"unknown symbol {symbol!r}")
        if not detail["periods"]:
            # FR-012 AC-2: not crawled yet → queue position, never an error
            status = runtime().status()
            region = detail["profile"].get("region", "world")
            ingest = status.get("ingest", {}) if isinstance(status.get("ingest"), dict) else {}
            detail["queue"] = {
                "state": "queued",
                "region": region,
                "note": f"queued by region priority ({region} tier)",
                "coverage_pct": ingest.get("coverage_pct"),
            }
        return detail

    @app.post("/api/fetch/{symbol}", status_code=202)
    def fetch_symbol(symbol: str) -> dict:
        """FR-012 — user-triggered fetch for an uncrawled company. The API
        stays a READER (ADR-0003): it only drops a request file; the ingest
        loop crawls it budget-charged and recomputes within a cycle.
        Idempotent — re-posting refreshes the same request."""
        from crible import config
        from crible.ingest.requests import pending_requests, request_fetch

        detail = runtime().company(symbol)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"unknown symbol {symbol!r}")
        queued = request_fetch(config.data_dir(), symbol)
        if not queued:
            raise HTTPException(
                status_code=429, detail="fetch queue is full — try again in a few minutes"
            )
        return {
            "queued": True,
            "symbol": symbol,
            "pending": len(pending_requests(config.data_dir())),
            "note": "the ingest service picks it up within a cycle (~1-3 min)",
        }

    @app.get("/api/prices/{symbol}")
    def prices(symbol: str) -> list[dict]:
        """Published daily OHLCV bars for the company drawer chart — [] when
        the symbol has no series (the chart hides; never an error)."""
        return runtime().prices(symbol)

    @app.get("/api/search")
    def search(q: str, limit: int = 20) -> list[dict]:
        """Universe search by symbol/name substring — deep-links the company
        drawer for any of the 161k listings, crawled or not."""
        return runtime().search(q, limit=min(max(limit, 1), 100))

    @app.get("/api/status")
    def status():
        return runtime().status()

    @app.get("/api/fields")
    def fields() -> list[dict]:
        """Snapshot columns + coarse types for the UI query builder — always
        the live schema, so the builder and the DSL whitelist cannot drift."""
        return runtime().fields()

    @app.get("/api/providers")
    def providers() -> list[dict]:
        """FR-013/FR-014 — read-only provider inventory for the settings view.

        Derived from the shared catalog and each provider's own ``enabled(env)``
        (crible.providers.catalog) — never a re-enumerated list or a re-derived
        activation rule, so this view cannot drift from the real active set.
        """
        import os as env_os

        from crible.providers.catalog import default_catalog, inventory

        return inventory(default_catalog(), dict(env_os.environ))

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    import os

    # container: WORKDIR /app holds ui/dist (Dockerfile); dev: repo root cwd
    dist = Path(os.environ.get("CRIBLE_UI_DIST", "ui/dist"))
    if dist.exists():  # pragma: no cover — exercised in the docker E2E
        app.mount("/", StaticFiles(directory=dist, html=True), name="spa")

    return app


app = create_app()
