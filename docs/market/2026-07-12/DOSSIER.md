# Search dossier

**Question:** self-hosted no-API-key fundamental stock screener market: competitors (OpenBB, Stockopedia, Simply Wall St, TIKR, screener.in, Portfolio123, Ghostfolio), pricing, self-hoster demand signals (r/selfhosted, Hacker News, GitHub), gaps and adoption drivers
**Mode:** startup · **depth:** standard · **lang:** en · **sources:** 26 · **built:** 2026-07-12T12:01:57.472Z
**Backends used:** duckduckgo, claude

> Write two tiers from these sources: `SUMMARY.md` (TL;DR) and `REPORT.md` (the full template below, filled exhaustively — use every relevant source and end with an "Open questions / contradictions" section). Then run `render` and `check`. Do not answer from memory.

## Grounding rules

**Cite every factual claim** with the id of the source it rests on, e.g. `[S1]`
(multiple sources: `[S1][S4]`). The ids are listed below and in `sources.json`.

If you state something from your **own background knowledge** that no fetched
source backs, you must FLAG it as unverified — either end the sentence with
`[M]`, or put the passage in a `> [model-hint] …` blockquote. `ultrasearch check`
tolerates flagged hints but FAILS on any *unmarked* unsourced claim, and on any
`[S#]` that does not resolve to a real source.

## Report template (startup)

```markdown
## Executive summary
## Problem & customer
## Market sizing (TAM / SAM / SOM)
## Competitive landscape
### Competitor table (name · positioning · pricing)
## Pricing & business models observed
## Go-to-market channels
## Trends & timing
## Risks & moats
## Sources
```

## Retrieval notes

- Hacker News returned no results.
- SearXNG not configured — set --searxng <url> or ULTRASEARCH_SEARXNG (run `docker-compose up` for a local instance). Skipping.
- DuckDuckGo returned 10 result(s).
- Web cascade tried searxng → duckduckgo → ddglite → mojeek → marginalia; results from duckduckgo.
- DuckDuckGo Lite returned no results.
- Mojeek unreachable (status 403).
- Mojeek returned no results.
- Marginalia unreachable (status 0).
- agent: enrich thin areas with your own WebSearch, then ingest each good URL via `ultrasearch fetch --url <u> --out <dir>` before writing the report.

## Sources

### [S1] Alternatives to Stockopedia (2026) | Find My Moat
url: https://www.findmymoat.com/alternatives/stockopedia · backend: duckduckgo · trust: 0.5 · extract: `sources/S1.md`

See which Stockopedia alternative to try first across GuruFocus, Stock Rover, Investing.com, with pricing, workflow fit, and platform tradeoffs.

### [S2] Best Free Stock Market APIs in 2026 (Tested): What Still Works — and ...
url: https://thenextgennexus.com/2026/05/15/10-best-free-stock-market-apis-2026/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S2.md`

An honest, tested 2026 comparison of free stock - market APIs — Yahoo, Alpha Vantage, Polygon, Finnhub, Twelve Data: what still works, real rate limits, and a no-API-key scraping alternative that scales past free quotas.

### [S3] Best Free Screeners Tools for Investors | Find My Moat
url: https://www.findmymoat.com/free/screeners · backend: duckduckgo · trust: 0.5 · extract: `sources/S3.md`

Simply Wall St is a visual stock analysis and portfolio platform for long-term investors who prefer guided fundamental summaries over raw data tables. It is best known for its Snowflake-style company reports, global stock ideas, fair value views, dividend analysis, portfolio diagnostics, broker imports, and easy-to-scan visual research.

### [S4] GitHub - ghostfolio/ghostfolio: Open Source Wealth Management Software ...
url: https://github.com/ghostfolio/ghostfolio · backend: duckduckgo · trust: 0.8 · extract: `sources/S4.md`

Ghostfolio is an open source wealth management software built with web technology. The application empowers busy people to keep track of stocks, ETFs or cryptocurrencies and make solid, data-driven investment decisions. The software is designed for personal use in continuous operation.

### [S5] Ghostfolio vs OpenBB: Which Is Better? | Find My Moat
url: https://www.findmymoat.com/vs/ghostfolio-vs-openbb · backend: duckduckgo · trust: 0.5 · extract: `sources/S5.md`

For most investors, OpenBB is the better pick: it covers 12 workflows to Ghostfolio's 3. Key difference: OpenBB leads on Broader coverage (12 vs 3 categories).

### [S6] Stock Analysis Tools Compared (2026): Screeners, Charting & Research
url: https://wealthypot.com/stock-analysis-tools/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S6.md`

A side-by-side look at the stock research, screening, and charting tools worth using in 2026 — from charting platforms and screeners to research suites and open-source terminals.

### [S7] GitHub - jatoran/OpenMarketView: Free, self-hosted, open source Stock ...
url: https://github.com/jatoran/OpenMarketView · backend: duckduckgo · trust: 0.8 · extract: `sources/S7.md`

OpenMarketView is a Stock Market List Viewer. It is free, self-hosted , open source, web-app, etc. etc. It is designed to help users manage and analyze their stock portfolios and watchlists in separate tabs. It provides 5-minute and lifetime stock data, multiple viewing options, theme and UI customization, and various analysis metrics.

### [S8] ghostfolio/README.md at main · ghostfolio/ghostfolio · GitHub
url: https://github.com/ghostfolio/ghostfolio/blob/main/README.md · backend: duckduckgo · trust: 0.8 · extract: `sources/S8.md`

Ghostfolio is an open source wealth management software built with web technology. The application empowers busy people to keep track of stocks, ETFs or cryptocurrencies and make solid, data-driven investment decisions.

### [S9] GitHub - OpenBB-finance/OpenBB: Open Data Platform for analysts, quants ...
url: https://github.com/OpenBB-finance/OpenBB · backend: duckduckgo · trust: 0.8 · extract: `sources/S9.md`

Open Data Platform by OpenBB (ODP) is the open-source toolset that helps data engineers integrate proprietary, licensed, and public data sources into downstream applications like AI copilots and research dashboards. ODP operates as the "connect once, consume everywhere" infrastructure layer that consolidates and exposes data to multiple surfaces at once: Pyt

### [S10] Building a Wall Street-Grade Stock Screener with Openclaw AI ... - Medium
url: https://medium.com/coinmonks/building-a-wall-street-grade-stock-screener-with-openclaw-ai-agents-and-free-apis-48cbeeadd9d5 · backend: duckduckgo · trust: 0.55 · extract: `sources/S10.md`

How I built a professional stock screening system that analyzes 500 S&P 500 stocks using OpenClaw, Python, and free public APIs — all…

### [S11] Free Portfolio Tracker, Stock Insights and Community - Simply Wall St
url: https://simplywall.st/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S11.md`

All-in-one platform to improve your portfolios, speed up research and find winning stocks.

### [S12] Research and Manage - Manage your stock strategies - Portfolio123
url: https://www.portfolio123.com/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S12.md`

Be your own portfolio manager. Everything you need to manage your stock strategies.

### [S13] Workspace | OpenBB
url: https://openbb.co/products/workspace/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S13.md`

OpenBB Workspace is a collaborative and fully customizable investment research app for the 21st century.

### [S14] Ghostfolio
url: https://ghostfol.io/en/resources/personal-finance-tools/open-source-alternative-to-simply-wallstreet · backend: duckduckgo · trust: 0.5 · extract: `sources/S14.md` · ⚠ snippet only (page fetch failed)

Ghostfolio is an open source software (OSS), providing a cost-effective alternative to Stock Portfolio Tracker & Visualizer by Simply Wall St making it particularly suitable for individuals on a tight budget, such as those pursuing Financial Independence, Retire Early (FIRE).

### [S15] Simply Wall St vs Portfolio123 (2026) - YouTube
url: https://www.youtube.com/watch?v=FPhElMCmsIo · backend: duckduckgo · trust: 0.5 · extract: `sources/S15.md`

In this video, we compare Simply Wall St vs Portfolio123 to help investors choose the right stock analysis and investment research platform.

### [S16] Ghostfolio - Open Source Wealth Management Software
url: https://ghostfol.io/en/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S16.md` · ⚠ snippet only (page fetch failed)

Ghostfolio is a personal finance dashboard to keep track of your net worth including cash, stocks, ETFs and cryptocurrencies across multiple platforms.

### [S17] OpenBB - Build your own financial workspace
url: https://openbb.co/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S17.md`

The workspace where investment teams bring their data, workflows, and AI together. Under your control.

### [S18] Top 23 stock-analysis Open-Source Projects | LibHunt
url: https://www.libhunt.com/topic/stock-analysis · backend: duckduckgo · trust: 0.5 · extract: `sources/S18.md`

Which are the best open-source stock -analysis projects? This list will help you: ai-berkshire, stocksight, surpriver, Deep_Learning_Machine_Learning_Stock, stock -indicators-dotnet, indicator, and trendet.

### [S19] Stockopedia: Data-Driven Stock Research for Active Investors
url: https://www.stockopedia.com/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S19.md`

The award-winning stock market research platform for active investors - powerful rankings, comprehensive research tools, and expert analyst insights - everything you need to invest with confidence.

### [S20] Tutorials - Portfolio123
url: https://www.portfolio123.com/doc/tutorials.jsp · backend: duckduckgo · trust: 0.5 · extract: `sources/S20.md`

Be your own portfolio manager. Everything you need to manage your stock strategies.

### [S21] Pricing Plans
url: https://www.stockopedia.com/plans/ · backend: claude · trust: 0.5 · extract: `sources/S21.md`

Alerts — Set unlimited alerts on price, fundamentals, and more to stay up-to-date with the stocks on your radar. "Stockopedia is like a stock market encyclopedia and a great place to scan for new shares to buy; There is lots more really fantastic material and I believe access should help investors.

### [S22] Stockopedia Review (2026): Worth $200-$600/Year?
url: https://traderhq.com/stockopedia-review-smart-stock-research-tools-investors/ · backend: claude · trust: 0.5 · extract: `sources/S22.md`

The Stock Screener — The screener lets you filter 40,000+ stocks across major global markets (US, UK, Europe, Asia) using hundreds of criteria: But if you want to become a better stock picker yourself—especially in a market where sector rotation is creating 71-point dispersion between top and bottom performers—it’s one of the best investments you can make.

### [S23] OpenBBTerminal Server? · OpenBB-finance/OpenBB · Discussion #4601 · GitHub
url: https://github.com/OpenBB-finance/OpenBB/discussions/4601 · backend: claude · trust: 0.8 · extract: `sources/S23.md`

Uh oh! — Can OpenBBTerminal be "self-hosted" on a linux based server like Synology's? If only desktop only, are there any plans to introduce a server version that can be self-hosted?

### [S24] Money, Budgeting & Management - awesome-selfhosted
url: https://awesome-selfhosted.net/tags/money-budgeting--management.html · backend: claude · trust: 0.5 · extract: `sources/S24.md`

DePay — Peer-to-peer, free, self-hosted & open-source. A lightweight personal bookkeeping app hosted by yourself.

### [S25] https://simplywall.st/plans
url: https://simplywall.st/plans · backend: claude · trust: 0.5 · extract: `sources/S25.md`

Pick the plan that’s right for your investing needs — Need more portfolios or screeners? Stock screeners & Alerts Limited 3 10

### [S26] TIKR Review (2026): Features, Pricing and Who It's For
url: https://quantroutine.com/tools/tikr/ · backend: claude · trust: 0.5 · extract: `sources/S26.md`

TIKR Terminal Review (2026): — TIKR positions itself as Bloomberg for retail investors: S&P CapitalIQ data, 100,000+ global stocks, 20 years of financial history, at a fraction of the cost. But for a fundamental equity researcher who wants financial statements, valuation history, analyst estimates, and ownership data on global stocks, TIKR covers most of wha
