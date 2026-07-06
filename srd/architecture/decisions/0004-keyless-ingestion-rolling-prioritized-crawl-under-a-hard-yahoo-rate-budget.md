# ADR 0004 — Keyless ingestion: rolling prioritized crawl under a hard Yahoo rate budget

**Status:** accepted

## Context

Yahoo has no bulk fundamentals endpoint — statements are per-ticker calls — and tolerates roughly 360 req/h before 429s; maintainers treat rate-limiting as Yahoo policy, wontfix [E3]. Users report failures from ~950 tickers per session and intermittent hangs [E36][E82]. yfinance now rides curl_cffi with impersonated sessions and must own its session (no requests-cache injection) [E52][E99]. At ~330 req/h a full 161k-symbol fundamentals sweep takes ≈ 19 days — but fundamentals move quarterly, so a rolling crawl is sufficient by design.

## Decision

A continuous priority-queue crawler with a global token bucket (≤ 330 req/h, 10% headroom), jittered exponential backoff on 429 (1 min → 15 min cap), a per-request watchdog against hangs, persisted queue state for crash-resume, and freshness-driven revisits (quarterly statements, daily prices). Priority tiers: Europe → US large caps → rest of world. Europe's cross-sectional gaps are compensated by the audited ESEF layer (FR-010); prices fail over to Stooq (FR-011).

## Consequences

Full worldwide coverage builds progressively over ~3 weeks from first boot (Europe first, visible in crible status); the crawler must be a long-lived, stateful, polite process rather than a batch job; the single-switch EODHD upgrade (FR-014) replaces exactly this fragile link if the operator ever pays.

## Alternatives considered

Parallel scraping with proxy rotation — rejected: hostile to Yahoo's tolerance, fragile, and against the polite-by-design constraint [E3]. Paid feed from day one — rejected: breaks the €0 v1 budget and the zero-key contract (ADR-0002). On-demand fetching only (no crawl) — rejected: screening needs the full cross-section precomputed; per-request fetching cannot fill a 161k universe interactively.

**Evidence:** [E3][E36][E52][E82][E98][E99]
