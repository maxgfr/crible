# Vision

**Product:** crible

## Problem
Serious fundamental screening across ALL of Europe (and the world) is locked behind expensive feeds (EODHD €59.99/mo, FMP Ultimate $149/mo); free tools are US-centric (Finviz), shallow, or SaaS with no control over data, formulas or universe. Investors who want transparent, reproducible fundamental screens over European small/mid caps have no self-hosted option.

## Target users
- Individual fundamental investor (Maxime) screening European + worldwide equities with value/quality/forensic criteria
- Technical tinkerer who self-hosts the stack, tunes the crawl priorities and writes custom screens via the DSL or SQL

## Value proposition
A screener you own: worldwide universe with Europe-depth, 100% functional with zero API keys (guaranteed forever), transparent formulas (financetoolkit + published score definitions), audited ESEF figures for EU names, DuckDB-fast filtering, and a single optional paid switch (EODHD) ready when deeper history is wanted — never required.

## Success metrics
- Screen the full worldwide snapshot (~161k equities × ~200 columns) in under 1 second locally — enforced by a CI benchmark on a synthetic full-size snapshot
- Europe as depth priority: European listings are always crawled first and, where an ISIN→LEI mapping resolves, enriched with audited ESEF XBRL figures (coverage partial until ESAP opens)
- Zero-key contract: a dedicated CI job runs the full E2E suite with no API keys configured and must pass for every release
- Rolling keyless crawl under a hard request budget: the Europe tier refreshes within a quarter; worldwide completes ≈ 2 sweeps/year; coverage and freshness are always visible in crible status
- One-switch paid upgrade path: the EODHD Fundamentals plugin is specced and stubbed so a single key upgrade replaces the fragile yfinance link without touching the rest
