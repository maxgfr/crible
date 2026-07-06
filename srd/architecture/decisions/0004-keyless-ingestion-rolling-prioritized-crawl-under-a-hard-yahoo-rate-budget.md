# ADR 0004 — Keyless ingestion: rolling prioritized crawl under a hard Yahoo rate budget

**Status:** accepted

## Context

Yahoo has no bulk fundamentals endpoint — statements are per-ticker, per-statement-type calls — and rate-limits scrapers aggressively: bulk downloads trip YFRateLimitError ('Too Many Requests. Rate limited. Try after a while.') [E107][E108], long-running pulls crash or hang [E36][E82], and the core rate-limit issue is documented at length [E105]. yfinance rides curl_cffi with impersonated sessions and must own its session [E52]. No public figure exists for a 'safe' rate — the budget is a deliberately conservative design parameter, not a claimed tolerance. Design-time verification (2026-07-07) also found Stooq's CSV endpoints behind a JavaScript proof-of-work wall: there is NO keyless bulk price alternative, so prices must share the Yahoo budget.

## Decision

A continuous priority-queue crawler with a global token bucket (default 330 upstream requests per rolling hour, configurable), counting every upstream call (a fundamentals sweep ≈ 7 requests per symbol; every price request counts too). Jittered exponential backoff on 429 (1 min → 15 min cap), a per-request watchdog against hangs, persisted queue state for crash-resume, freshness-driven revisits (quarterly statements; daily prices for the priority tier only — FR-011). Priority tiers: Europe → US large caps → rest of world. Europe's cross-sectional depth is compensated by the audited ESEF layer (FR-010) joined via the keyless GLEIF ISIN→LEI mapping [E113][E114].

## Consequences

The honest arithmetic at the default budget (7,900 req/day): ~2,000/day reserved for daily priority-tier prices leaves ~5,900/day ≈ 840 fundamentals sweeps/day — the Europe tier (tens of thousands of listings) completes in roughly 5–7 weeks, inside the quarterly contract; the full ~161k worldwide universe takes ≈ 6+ months per sweep, so rest-of-world coverage is explicitly best-effort in zero-key mode. Non-priority valuation ratios may rest on week-old prices — visible via price_asof provenance, never silent. Coverage and freshness are always visible in crible status; the single-switch EODHD upgrade (FR-014) is the documented cure when worldwide freshness is wanted. The crawler is a long-lived, stateful, polite process; an extended Yahoo block degrades to serving the last snapshot with staleness badges, never to hammering.

## Alternatives considered

Parallel scraping with proxy rotation — rejected: hostile, fragile, and the documented blocking [E105] shows how it ends. Paid feed from day one — rejected: breaks the €0 v1 budget and the zero-key contract (ADR-0002). On-demand fetching only (no crawl) — rejected: screening needs the full cross-section precomputed. Stooq as a budget-free bulk price path — rejected after design-time verification (2026-07-07): its endpoints sit behind a JS proof-of-work wall; it survives only as an optional, disabled-by-default, non-load-bearing fallback plugin.

**Evidence:** [E105][E107][E108][E52][E36][E82][E113][E114]
