# Competitive landscape

## Competitors

| Product | Note | Evidence |
|---|---|---|
| Finviz | The reference free screener, US-market presets and thematic filters [E63][E71]; planning research found no European exchange coverage — Europe is exactly the gap crible fills. | [E63][E71] |
| TradingView Stock Screener | Broad multi-market SaaS screener [E76]; subscription-gated depth, closed formulas, not self-hostable (product model, not a snippet claim). | [E76] |
| Simply Wall St | Fundamental-analysis SaaS with praised global coverage for value investors [E58][E64]; a closed subscription product — crible's company detail is the transparent, self-hosted answer. | [E58][E64] |
| Stockopedia | Quality/Value/Momentum ranks over European + global markets, subscription SaaS. Its StockRanks are precisely the kind of closed composite score crible replaces with visible, editable DSL presets. | [E67][E68] |
| Uncle Stock | 'Professional stock screening for DIY investors' — the closest functional cousin for European fundamental screening, with backtesting; subscription, closed, not self-hostable. | [E59][E60] |
| screener.in | India's fundamental screener — the UX benchmark: information-dense tables, transparent query language, fast. crible aims for this feel over a worldwide, Europe-deep universe. | [E75] |
| EODHD Screener API | The data vendor's own screener endpoint. Fundamentals are pay-gated: the free tier grants 20 API calls/day and more data requires a paid plan [E111][E112]; the Fundamentals-feed price observed during planning is recorded to-revalidate in docs/prds/eodhd.md (FR-014) — the single paid upgrade crible keeps on standby, not a v1 dependency. | [E111][E112][E61] |
| Find My Moat | A curated directory of investment research tools [E104] that surfaced FinancialReports.eu in planning research — the pointer to the free EU-filings MCP server crible integrates in phase 2 (FR-013) [E69][E70]. | [E104][E69][E70] |
| OpenBB Platform | Open-source multi-provider financial data platform [E90]. Considered as a foundation and rejected (ADR-0001): planning-time docs verification showed its free fundamentals path is yfinance underneath and its screener providers cannot screen Europe. | [E90] |

## Comparable open-source projects

| Project | Note | Evidence |
|---|---|---|
| [JerBouma/FinanceToolkit](https://github.com/JerBouma/FinanceToolkit) | Core dependency: 200+ transparently-implemented ratios + Piotroski & Altman (Beneish absent — crible implements it). Yahoo backend supported via enforce_source; built for portfolios, so crible owns batching/backoff. | [E1][E6][E7][E8][E9][E39] |
| [JerBouma/FinanceDatabase](https://github.com/JerBouma/FinanceDatabase) | The universe: 160,995 equities across 117 countries as plain CSVs, symbols Yahoo-suffixed. Its issue tracker documents the data-quality caveats crible tolerates (CUSIP collisions, exchange-code drift) and the steady quality PRs that fix them. | [E2][E16][E17][E25][E27][E40][E47][E48] |
| [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) | The fragile-but-free fundamentals link: curl_cffi impersonated sessions [E52], endemic rate limiting (429 / YFRateLimitError on bulk pulls [E105][E107][E108]) and hangs [E36][E82]. Statement depth is shallow (a handful of annual periods — observed behaviour, validated in integration; no contractual depth exists). ADR-0004 designs around every one of these. | [E3][E52][E105][E107][E108][E36][E82] |
| [xang1234/stock-screener](https://github.com/xang1234/stock-screener) | Closest architectural prior art (FastAPI + Postgres + Celery + React, multi-exchange refresh queues). Its preset-filtering timeout fix is the cautionary tale that justified DuckDB-over-Parquet instead of an operational DB. | [E77][E85][E88][E89] |
| [astro30/valinvest](https://github.com/astro30/valinvest) | Clean reference implementation of Piotroski-style fundamental scoring (dead since 2023, FMP-bound) — used as a cross-check for crible's score implementations, not as a dependency. | [E79][E80][E81] |
| [SimFin/simfin](https://github.com/SimFin/simfin) | Official Python client for SimFin's free bulk US fundamentals (5,000 US stocks, 20+ years of history via API/bulk download [E115][E116]; free-tier limitations vs paid re-verified when the phase-2 plugin is built). Library dormant since 2023 → crible's plugin would call the REST API directly. | [E78][E115][E116] |
