# 0002. Self-hosting, zero-key contract and data ownership

- **Status:** accepted

## Context
Every credible fundamental screener with European coverage is subscription SaaS with closed formulas (Stockopedia [E67], Simply Wall St [E58], Uncle Stock [E59]); data feeds worth using are pay-gated — EODHD's free tier grants 20 API calls/day with paid plans required for more data [E111], the observed paid pricing being recorded to-revalidate in docs/prds/eodhd.md. The product's reason to exist is owning the screener: data, formulas, universe.

## Decision
Ship as a self-hosted Docker Compose deployment where the host owns all data. The zero-key mode (FinanceDatabase + yfinance + filings.xbrl.org + Stooq) is a permanent, CI-enforced contract — every core flow works with no account, no key, no external service. No auth layer: single operator, bound to the local network; no telemetry. [E58][E59][E61][E67][E98]

## Consequences
Data residency and polite-crawling compliance are the operator's responsibility (documented); the free path accepts Yahoo's shallow statement history (a handful of annual periods — observed behaviour, validated in integration tests, no contractual depth exists for a scraped source) and best-effort worldwide freshness as the price of €0; a hosted multi-tenant SaaS is explicitly out of scope. The zero-key guarantee is expressed as a testable contract: the release-gating CI job runs the E2E suite with no keys configured.

## Alternatives considered
Hosted SaaS — rejected: recreates the incumbents' model and their privacy/lock-in problems [E67][E58]. Mandatory free-tier keys (FMP/EODHD free) in v1 — rejected: their free tiers contribute nothing for Europe (US-only / no fundamentals [E61]) and would break the zero-key promise.
