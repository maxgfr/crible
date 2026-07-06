# Competitive landscape

No existing product or OSS project covers crible's target — worldwide fundamental screening with Europe depth, self-hosted, zero-key, transparent formulas. The paid tools prove the demand; the OSS projects supply the parts.

## Products

- **Finviz** — The reference free screener — US-only. Rich presets and thematic filters, but no European exchange coverage at all; Europe is exactly the gap crible fills. [E63][E71]
- **TradingView Stock Screener** — Broad multi-market SaaS screener; fundamental depth and export sit behind subscription tiers, formulas are opaque, and nothing is self-hostable. [E76]
- **Simply Wall St** — Polished fundamental-analysis SaaS with genuinely global coverage (praised for value-investing breadth) — but closed data, closed methodology, subscription-gated. crible's company detail is the transparent answer to its snowflake pages. [E58][E64]
- **Stockopedia** — Quality/Value/Momentum ranks over European + global markets, subscription SaaS. Its StockRanks are precisely the kind of closed composite score crible replaces with visible, editable DSL presets. [E67][E68]
- **Uncle Stock** — 'Professional stock screening for DIY investors' — the closest functional cousin for European fundamental screening, with backtesting; subscription, closed, not self-hostable. [E59][E60]
- **screener.in** — India's fundamental screener — the UX benchmark: information-dense tables, transparent query language, fast. crible aims for this feel over a worldwide, Europe-deep universe. [E75]
- **EODHD Screener API** — The data vendor's own screener endpoint. Fundamentals require the €59.99/mo tier (free tier: 20 calls/day, 1-year EOD, no fundamentals) — this is the single paid upgrade crible keeps on standby (FR-014), not a v1 dependency. [E61][E62]
- **Find My Moat** — EU-filings-based research tool built on the FinancialReports.eu data — evidence that the European-filings angle carries a product, and a pointer to the free MCP server crible integrates in phase 2 (FR-013). [E104][E69][E70]
- **OpenBB Platform** — Open-source multi-provider financial data platform (70k★). Considered as a foundation and rejected (ADR-0001): its free equity-fundamentals path is still yfinance underneath, and its screener providers (finviz et al.) cannot screen Europe. [E90][E91]

## Open-source prior art

- **[JerBouma/FinanceToolkit](https://github.com/JerBouma/FinanceToolkit)** — Core dependency: 200+ transparently-implemented ratios + Piotroski & Altman (Beneish absent — crible implements it). Yahoo backend supported via enforce_source; built for portfolios, so crible owns batching/backoff. [E1][E6][E7][E8][E9][E39]
- **[JerBouma/FinanceDatabase](https://github.com/JerBouma/FinanceDatabase)** — The universe: 160,995 equities across 117 countries as plain CSVs, symbols Yahoo-suffixed. Its issue tracker documents the data-quality caveats crible tolerates (CUSIP collisions, exchange-code drift) and the steady quality PRs that fix them. [E2][E16][E17][E25][E27][E40][E47][E48]
- **[ranaroussi/yfinance](https://github.com/ranaroussi/yfinance)** — The fragile-but-free fundamentals link: curl_cffi sessions, ~360 req/h tolerance, per-ticker statements ~4y deep, hangs and 429s documented in issues — ADR-0004 designs around every one of these. [E3][E52][E36][E82][E98][E99]
- **[xang1234/stock-screener](https://github.com/xang1234/stock-screener)** — Closest architectural prior art (FastAPI + Postgres + Celery + React, multi-exchange refresh queues). Its preset-filtering timeout fix is the cautionary tale that justified DuckDB-over-Parquet instead of an operational DB. [E77][E85][E88][E89]
- **[astro30/valinvest](https://github.com/astro30/valinvest)** — Clean reference implementation of Piotroski-style fundamental scoring (dead since 2023, FMP-bound) — used as a cross-check for crible's score implementations, not as a dependency. [E79][E80][E81]
- **[SimFin/simfin](https://github.com/SimFin/simfin)** — Official Python client for SimFin's free bulk US fundamentals (~12-month delay). Library dormant since 2023 → crible's phase-2 simfin plugin calls the REST API directly. [E78][E83][E49]
