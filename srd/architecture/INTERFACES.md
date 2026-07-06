# Interfaces

## CLI _(cli)_

The crible command (Typer): screen (DSL → table/CSV), ingest (bootstrap/once/loop), compute, status, export. Exit codes and stderr messages are part of the contract; same DSL semantics as the API.

_Related FRs: FR-001, FR-002, FR-003, FR-004, FR-005, FR-008, FR-009_

## HTTP API _(api)_

FastAPI: POST /screen, GET /screen.csv, GET /presets, GET /company/{symbol}, GET /status, GET /healthz; serves the built SPA at /. JSON errors carry message + hint; 422 for DSL errors, 404 for unknown symbols, never 5xx for user input.

_Related FRs: FR-004, FR-006, FR-007, FR-008, FR-009, FR-012_

## Web App _(ui)_

React/Vite SPA: query bar (DSL), TanStack results grid (sort, column picker, CSV export), presets menu, company-detail drawer, status view. Talks only to the HTTP API on the same origin.

_Related FRs: FR-007, FR-009, FR-012_

## Provider Plugin API _(api)_

Internal contract every data source implements: capabilities() (statements/prices/coverage), fetch_statements(symbol), fetch_prices(symbols), health(). Keyless providers are always on; keyed providers self-disable without their env key (one log line, no crash). External endpoints behind it: Yahoo via yfinance, filings.xbrl.org JSON-API, Stooq CSV; phase 2: FinancialReports.eu, SimFin, FMP free, EODHD free; future: EODHD paid.

_Related FRs: FR-002, FR-010, FR-011, FR-013, FR-014_
