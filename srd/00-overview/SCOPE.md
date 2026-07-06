# Scope

## In scope
- Worldwide universe built from FinanceDatabase
- Rolling prioritized keyless ingestion (yfinance)
- Ratio and score computation into a wide snapshot
- Filter DSL compiled to DuckDB SQL
- CLI (crible)
- HTTP API (FastAPI)
- React/Vite SPA
- Docker Compose deployment
- Preset screens
- ESEF XBRL Europe enrichment
- Stooq price fallback
- Company detail view

## Out of scope
- Technical analysis, chart patterns or momentum signals
- Portfolio management, backtesting or performance tracking
- Trade execution or brokerage integration
- Real-time or intraday data
- Multi-user SaaS: no accounts, no auth, single self-hosted operator
- Buying any paid data plan in v1 (paid providers are specced as PRDs only)
- Mobile apps

## Assumptions
- The team is: Solo developer (Maxime), TDD workflow (red-green-refactor).
- The timeline is: v1 zero-key end-to-end first; phase 2 (free-key plugins) after.
- The budget is: €0 for data in v1 (strict zero-key core; free-key plugins in phase 2; EODHD €59.99/mo is a documented future option, not a v1 dependency).
- Compliance applies: MIT license, Respect Yahoo rate tolerance (~360 req/h budget with jitter+backoff), English codebase and docs.
