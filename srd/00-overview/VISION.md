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
- Screen the full ~161k-equity worldwide universe on fundamentals in under 1 second locally (DuckDB over Parquet)
- Europe as depth priority: EU companies enriched with audited ESEF XBRL figures and always crawled first
- Zero-key guarantee: every core flow (ingest, compute, screen, UI) works with no API key configured, for life
- Sustain a complete worldwide fundamentals sweep within Yahoo's free rate tolerance (~360 req/h, full cycle ≈ 19 days, quarterly freshness)
- One-switch paid upgrade path: EODHD Fundamentals plugin specced and stubbed so paying €59.99/mo replaces the fragile yfinance link without touching the rest
