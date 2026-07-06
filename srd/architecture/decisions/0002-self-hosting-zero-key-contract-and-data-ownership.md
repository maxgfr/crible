# ADR 0002 — Self-hosting, zero-key contract and data ownership

**Status:** accepted

## Context

Every credible fundamental screener with European coverage is subscription SaaS with closed formulas (Stockopedia [E67], Simply Wall St [E58], Uncle Stock [E59]); data feeds worth using are paid (EODHD fundamentals start at €59.99/mo [E61]). The product's reason to exist is owning the screener: data, formulas, universe.

## Decision

Ship as a self-hosted Docker Compose deployment where the host owns all data. The zero-key mode (FinanceDatabase + yfinance + filings.xbrl.org + Stooq) is a permanent, CI-enforced contract — every core flow works with no account, no key, no external service. No auth layer: single operator, bound to the local network; no telemetry.

## Consequences

Data residency and Yahoo-tolerance compliance are the operator's responsibility (documented); the free path accepts Yahoo's shallow history (~4 annual periods [E98]) and ~19-day full-universe sweep as the price of €0; a hosted multi-tenant SaaS is explicitly out of scope.

## Alternatives considered

Hosted SaaS — rejected: recreates the incumbents' model and their privacy/lock-in problems [E67][E58]. Mandatory free-tier keys (FMP/EODHD free) in v1 — rejected: their free tiers contribute nothing for Europe (US-only / no fundamentals [E61]) and would break the zero-key promise.

**Evidence:** [E58][E59][E61][E67][E98]
