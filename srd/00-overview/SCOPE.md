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
- Team: solo developer (Maxime), TDD workflow (red-green-refactor).
- Timeline: v1 zero-key end-to-end first; phase 2 (free-key plugins) after.
- Budget: €0 for data in v1; the zero-key mode is a permanent, CI-enforced contract (empty-env E2E gate), not a marketing absolute.
- Compliance: MIT license; polite crawling under a hard request budget; English codebase and docs.
- Zero-key mode depends on four external keyless endpoints (FinanceDatabase, Yahoo via yfinance, filings.xbrl.org, GLEIF ISIN→LEI mapping files) plus the optional disabled-by-default Stooq fallback; their availability is monitored, an extended outage degrades to serving the last snapshot with staleness visible — fundamentals have no keyless fallback for Yahoo (that is exactly the EODHD switch, FR-014).
