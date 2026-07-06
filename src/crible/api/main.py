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
    def screen_csv(query: str, sort: str | None = None):
        try:
            rows, _ = runtime().screen(query, sort=sort, limit=EXPORT_LIMIT, offset=0)
        except SnapshotMissingError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
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
        return detail

    @app.get("/api/status")
    def status():
        return runtime().status()

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    dist = Path(__file__).resolve().parents[3] / "ui" / "dist"
    if dist.exists():  # pragma: no cover — exercised in the docker E2E
        app.mount("/", StaticFiles(directory=dist, html=True), name="spa")

    return app


app = create_app()
