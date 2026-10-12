# syntax=docker/dockerfile:1
# FR-008 — one image, two services (ingest / api) selected by command.
# Stage ui builds the SPA; stage builder resolves the locked Python env with
# uv (the deps layer survives src/ edits); stage runtime is slim + non-root.
# Bases are patch-pinned; dependabot's docker ecosystem keeps them fresh.
# BuildKit cache mounts keep the npm and uv download caches across builds
# (outside the image layers), so a lockfile bump re-downloads only the delta.

FROM ghcr.io/astral-sh/uv:0.12.21 AS uv

FROM node:26.10.0-alpine AS ui
WORKDIR /build
COPY ui/package.json ui/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund
COPY ui/ ./
RUN npm run build

FROM python:3.12.13-slim AS builder
COPY --from=uv /uv /bin/uv
# UV_LINK_MODE=copy: the cache mount is a separate filesystem, hardlinks
# into .venv would fail
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/root/.cache/uv \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# deps first: this layer only invalidates when the lockfile changes
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
# then the project itself (hatchling needs the README at build time)
COPY README.md ./
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12.13-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    CRIBLE_DATA_DIR=/data \
    PATH="/app/.venv/bin:$PATH"
# non-root: uid 1000 owns /data (named volumes inherit this on first use;
# volumes created by images <= v0.1.0 ran as root and need a one-time
# `chown -R 1000:1000 /data` — see README). --create-home so DuckDB can
# cache its extensions (httpfs) under ~/.duckdb.
RUN useradd --system --uid 1000 --create-home crible \
    && mkdir -p /data && chown crible:crible /data
WORKDIR /app
COPY --from=builder /app/.venv .venv
# api/main.py serves the SPA from ui/dist relative to WORKDIR
COPY --from=ui /build/dist ui/dist
USER crible
VOLUME /data
EXPOSE 8000
# default: the api service; compose overrides the command for ingest
CMD ["uvicorn", "crible.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
