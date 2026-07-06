# ADR 0003 — Persistence: DuckDB over layered Parquet with atomic snapshot swap

**Status:** accepted

## Context

Three data shapes coexist: append-heavy raw fetches (per provider, re-parseable), a wide computed snapshot the screener hammers, and small operational state (crawl queue, provider health). Readers (API/CLI) and the writer (ingest/compute) are separate processes [E4].

## Decision

A layered store on one shared volume: (1) raw layer — immutable, versioned Parquet per provider/fetch (write-temp-then-rename), the durable source of truth that survives any recompute; (2) snapshot layer — the wide company × period Parquet, published by atomic swap (write new, fsync, rename; readers re-open on change); (3) operational state — a small DuckDB database owned by the ingest process. The API opens Parquet read-only through DuckDB [E12][E10]; every external integration writes only through its provider adapter into the raw layer.

## Consequences

No write contention (single-writer per layer); any snapshot is reproducible from the raw layer; corruption recovery = delete snapshot, recompute. Cross-layer consistency is eventual (a screen can lag a fetch by one compute cycle) — acceptable for quarterly-moving fundamentals and surfaced via freshness metadata.

## Alternatives considered

One shared DuckDB database for everything — rejected: concurrent writer/reader processes across containers fight DuckDB's single-writer model. Postgres — rejected: an operational row store doing an analytical job, plus a server to operate (see ADR-0001 and the xang1234 timeout lesson [E88]). Event sourcing — deferred: the raw Parquet layer already gives replayability without the machinery.

**Evidence:** [E4][E10][E11][E12][E88]
