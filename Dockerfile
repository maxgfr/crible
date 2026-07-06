# FR-008 — one image, two services (ingest / api) selected by command.
# Stage 1: build the SPA. Stage 2: python runtime with the built UI.

FROM node:24-alpine AS ui
WORKDIR /build
COPY ui/package.json ui/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY ui/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    CRIBLE_DATA_DIR=/data
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
RUN pip install --no-cache-dir .
COPY --from=ui /build/dist ui/dist
VOLUME /data
EXPOSE 8000
# default: the api service; compose overrides the command for ingest
CMD ["uvicorn", "crible.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
