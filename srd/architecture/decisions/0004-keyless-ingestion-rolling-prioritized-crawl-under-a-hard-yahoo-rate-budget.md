# ADR 0004 — Keyless ingestion: rolling prioritized crawl under a hard Yahoo rate budget

**Status:** accepted

## Context

Yahoo has no bulk fundamentals endpoint — statements are per-ticker, per-statement-type calls — and rate-limits scrapers aggressively: bulk downloads trip YFRateLimitError ('Too Many Requests. Rate limited. Try after a while.') [E107][E108], long-running pulls crash or hang [E36][E82], and maintainers closed the core rate-limit issue as Yahoo policy rather than a fixable bug [E105][E106]. yfinance now rides curl_cffi with impersonated sessions and must own its session [E52]. No public figure exists for a 'safe' rate — so the budget is a deliberately conservative design parameter, not a claimed tolerance.

## Decision

A continuous priority-queue crawler with a global token bucket (default 330 upstream requests per rolling hour, configurable), counting every upstream call (a symbol sweep ≈ 7 requests: 3 statement types × 2 frequencies + profile). Jittered exponential backoff on 429 (1 min → 15 min cap), a per-request watchdog against hangs, persisted queue state for crash-resume, freshness-driven revisits (quarterly statements). Priority tiers: Europe → US large caps → rest of world. Bulk daily prices come from the keyless Stooq path outside this budget (FR-011); Europe's cross-sectional depth is compensated by the audited ESEF layer (FR-010).

## Consequences

The honest arithmetic: 330 req/h ≈ 7,900 req/day ≈ ~1,100 symbol-sweeps/day. The Europe tier (tens of thousands of listings) completes in roughly 3–6 weeks — inside the quarterly freshness contract; the full ~161k worldwide universe takes ≈ 20 weeks per sweep, so rest-of-world coverage is explicitly best-effort (~2 refreshes/year) in zero-key mode. Coverage and freshness are always visible in crible status; the single-switch EODHD upgrade (FR-014) is the documented cure when worldwide quarterly freshness is wanted. The crawler is a long-lived, stateful, polite process rather than a batch job; an extended Yahoo block degrades to serving the last snapshot with staleness badges, never to hammering.

## Alternatives considered

Parallel scraping with proxy rotation — rejected: hostile, fragile, and the documented blocking [E105] shows how it ends. Paid feed from day one — rejected: breaks the €0 v1 budget and the zero-key contract (ADR-0002). On-demand fetching only (no crawl) — rejected: screening needs the full cross-section precomputed. Pretending daily whole-universe price refresh fits the Yahoo budget — rejected by arithmetic; bulk prices belong to the keyless Stooq path (FR-011).

**Evidence:** [E105][E106][E107][E108][E52][E36][E82]
