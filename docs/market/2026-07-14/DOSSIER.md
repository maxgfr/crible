# Search dossier

**Question:** self-hosted no-API-key fundamental stock screener data sources: bulk keyless fundamentals coverage freshness trust, competitors Stockopedia TIKR Simply Wall St, what self-hosted finance tool users complain about
**Mode:** startup · **depth:** standard · **lang:** en · **sources:** 30 · **built:** 2026-07-14T18:48:24.503Z
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
- Mojeek returned no results.
- Mojeek unreachable (status 403).
- Marginalia unreachable (status 0).
- Could not fetch https://www.marderfrei.ch/Blo/simply-wall-street-vs-stockopedia (status 404).
- agent: enrich thin areas with your own WebSearch, then ingest each good URL via `ultrasearch fetch --url <u> --out <dir>` before writing the report.

## Sources

### [S1] maxgfr/crible: Self-hosted fundamental stock screener - GitHub
url: https://github.com/maxgfr/crible · backend: duckduckgo · trust: 0.8 · extract: `sources/S1.md`

Why crible Serious fundamental screening is otherwise a paid SaaS — Stockopedia runs €550/year for Europe (€725 with the US), TIKR and Simply Wall St are monthly subscriptions. The open- source self-hosted tools track portfolios (Ghostfolio) or are research terminals (OpenBB); none of them is a turnkey fundamental screener you host yourself. crible is that m

### [S2] Best Free Stock Market APIs in 2026 (Tested): What Still Works — and ...
url: https://thenextgennexus.com/2026/05/15/10-best-free-stock-market-apis-2026/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S2.md`

An honest, tested 2026 comparison of free stock -market APIs — Yahoo, Alpha Vantage, Polygon, Finnhub, Twelve Data : what still works, real rate limits, and a no-API-key scraping alternative that scales past free quotas.

### [S3] Simply Wall St vs Stockopedia: Which Is Better? | Find My Moat
url: https://www.findmymoat.com/vs/simply-wall-st-vs-stockopedia · backend: duckduckgo · trust: 0.5 · extract: `sources/S3.md`

The bottom line Simply Wall St and Stockopedia cover a lot of the same ground (11 shared categories, including stock ideas, screeners , and data visualizations), so for the basics you won't go far wrong with either. Simply Wall St simply does more: 19 categories to Stockopedia's 16, including valuation models, dividends, and insider data. Stockopedia counter

### [S4] Simply Wall St vs Stockopedia: Which Is Better?
url: https://quantroutine.com/tools/simply-wall-st-vs-stockopedia/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S4.md`

Visual fundamentals vs systematic factor investing. Compare Simply Wall St and Stockopedia on pricing, screeners , and which suits European investors best.

### [S5] GitHub - m-turnergane/stock-screener: An advanced Stock Screener w ...
url: https://github.com/m-turnergane/stock-screener · backend: duckduckgo · trust: 0.8 · extract: `sources/S5.md`

📈 Advanced Stock Screener A comprehensive stock screening and analysis platform that delivers in-depth market insights through multi-sector analysis, technical indicators, and automated valuation metrics.

### [S6] Simply Wall St vs Stockopedia - InvestingBrokers.com
url: https://investingbrokers.com/simply-wall-st-vs-stockopedia/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S6.md`

Simply Wall St and Stockopedia are among the platforms that have risen to meet these demands. While both aim to empower users with deep insights into market fundamentals and company performance, they differ significantly in approach, design, and the spectrum of tools offered.

### [S7] GitHub - hjones20/fundamental-analysis: Screen stocks on fundamentals ...
url: https://github.com/hjones20/fundamental-analysis · backend: duckduckgo · trust: 0.8 · extract: `sources/S7.md`

Fundamental Analysis is a program that allows me to screen stocks using fundamental indicators and estimate the intrinsic value of qualified stocks using the Discounted Cash Flow method of valuation. The logic accomplishes 5 primary tasks: Downloads all stock tickers available via the FinancialModelingPrep API and generates profiles on each company Retrieves

### [S8] Stockopedia Review (2026): StockRanks, Pricing & Verdict
url: https://quantroutine.com/tools/stockopedia/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S8.md`

Stockopedia review for self-directed investors: StockRanks explained, pricing breakdown by region, who it's for, and how it compares to Simply Wall St .

### [S9] Simply Wall St vs Stockopedia - TradingBrokers.com
url: https://tradingbrokers.com/simply-wall-st-vs-stockopedia/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S9.md`

Overview of Simply Wall St Simply Wall St is a visual investment analysis platform that focuses on simplifying complex financial data. It provides a clear and user-friendly interface that helps investors understand the fundamentals of various stocks.

### [S10] Best Simply Wall St Alternative in 2026 — For Serious Fundamental ...
url: https://www.screenerhero.com/blog/simply-wall-st-alternative · backend: duckduckgo · trust: 0.5 · extract: `sources/S10.md`

The best Simply Wall St alternative for fundamental stock screening is ScreenerHero. It covers 17,000+ stocks across US, Canada, and all European exchanges with raw financial filters — P/E, EV/EBITDA, ROE, margins — rather than simplified visual scores. At $29/month, it costs less than Simply Wall St's paid plans while offering broader market coverage and a 

### [S11] Beyond yFinance: Comparing the Best Financial Data APIs for ... - Medium
url: https://medium.com/@trading.dude/beyond-yfinance-comparing-the-best-financial-data-apis-for-traders-and-developers-06a3b8bc07e2 · backend: duckduckgo · trust: 0.55 · extract: `sources/S11.md`

In this article, we compare the top financial data APIs that go beyond yfinance, analyzing their strengths in data coverage , pricing, rate limits, and integration ease.

### [S12] Stock Screener & Scanner | Stockopedia
url: https://www.stockopedia.com/features/stock-screener/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S12.md`

Build custom stock screens with over 350 advanced financial ratios in Stockopedia's global stock screener ; or try our pre-defined Guru Screens.

### [S13] Top 5 Free Financial Data APIs for Building a Powerful Stock Portfolio ...
url: https://dev.to/williamsmithh/top-5-free-financial-data-apis-for-building-a-powerful-stock-portfolio-tracker-4dhj · backend: duckduckgo · trust: 0.55 · extract: `sources/S13.md`

Conclusion Selecting the right financial data API with options ensures seamless stock portfolio tracking. Whether you're a software developer, API enthusiast, or SaaS provider, leveraging free APIs like Alpha Vantage, Yahoo Finance, Finnhub, IEX Cloud, and Twelve Data provides valuable market insights.

### [S14] Free Stock APIs in JSON & Excel | Alpha Vantage
url: https://www.alphavantage.co/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S14.md`

Alpha Vantage offers free stock APIs in JSON and CSV formats for realtime and historical stock market data , options, forex, commodity, cryptocurrency feeds and over 50 technical indicators. Global market news API and sentiment scores powered by AI and machine learning. Supports intraday, daily, weekly, and monthly quotes and technical analysis with chart-re

### [S15] Stock Screener & Alerts by Simply Wall St
url: https://simplywall.st/features/stock-screener · backend: duckduckgo · trust: 0.5 · extract: `sources/S15.md`

Fantastic coverage of global stocks. Their layout is super user friendly, simple yet effective enough to give you all the right info needed for value investing. Portfolio and watchlist features are excellent. Best feature is the snowflake analysis with screener .

### [S16] Python and yfinance: Free Fundamental Data for Algorithmic Trading
url: https://medium.com/@jeremywhittaker/python-and-yfinance-free-fundamental-data-for-algorithmic-trading-f9ad904a1a88 · backend: duckduckgo · trust: 0.55 · extract: `sources/S16.md`

I want to share a streamlined approach to accessing and storing fundamental data for a wide array of stocks using yfinance, a powerful tool that offers free access to financial data .

### [S17] simply wall street vs stockopedia - marderfrei.ch
url: https://www.marderfrei.ch/Blo/simply-wall-street-vs-stockopedia · backend: duckduckgo · trust: 0.5 · extract: `sources/S17.md` · ⚠ snippet only (page fetch failed)

It includes model portfolios, time series analysis, scoring models, sector and industry data, Excel plugin, stock screener , live news, analyst estimates and recommendations. Simply Wall ST is a stock tool that focuses on visualizing fundamental stock data. Importantly, you can also access the Simply Wall ST stock screener .

### [S18] Build a fast, real-time stock screener in Python | Databento Blog
url: https://databento.com/blog/how-to-build-a-blazing-fast-real-time-stock-screener-with-python · backend: duckduckgo · trust: 0.5 · extract: `sources/S18.md`

This tutorial shows you how to build a real-time stock screener (or scanner) that continuously analyzes a real-time market data feed across all U.S.

### [S19] Screener - Screen and Filter Stocks in all Markets - Simply Wall St
url: https://simplywall.st/screener/create · backend: duckduckgo · trust: 0.5 · extract: `sources/S19.md`

Use our stock screener to filter companies by market cap, PE ratio, Earnings growth or our unique Snowflake

### [S20] Finnhub Stock APIs - Real-time stock prices, Company fundamentals ...
url: https://finnhub.io/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S20.md` · ⚠ snippet only (page fetch failed)

Finnhub - Free APIs for realtime stock , forex, and cryptocurrency. Company fundamentals , Economic data , and Alternative data .

### [S21] Companies House data products - GOV.UK
url: https://www.gov.uk/guidance/companies-house-data-products · backend: claude · trust: 0.5 · extract: `sources/S21.md`

Companies House data products How to access public data from the Companies House register using our data products.

### [S22] Companies House
url: https://download.companieshouse.gov.uk/en_accountsdata.html · backend: claude · trust: 0.95 · extract: `sources/S22.md`

What is it? — The Accounts Data Product is a free downloadable ZIP file, which contains the individual data files (instance documents) of company accounts filed electronically. The most recent accounts data can be downloaded from the daily files provided here, whilst historic accounts data is available from the previous year's monthly files.

### [S23] SEC.gov | Financial Statement Data Sets
url: https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets · backend: claude · trust: 0.95 · extract: `sources/S23.md`

Financial Statement Data Sets The Financial Statement Data Sets below provide the numeric information from the face financials of all financial statements.

### [S24] SEC.gov | Webmaster Frequently Asked Questions
url: https://www.sec.gov/about/webmaster-frequently-asked-questions · backend: claude · trust: 0.95 · extract: `sources/S24.md`

List of Questions — Do you provide API data services? Directory browsing is allowed for the Central Index Key (CIK) child directories of /Archives/edgar/data/.

### [S25] Deutsche Börse Public Dataset - Registry of Open Data on AWS
url: https://registry.opendata.aws/deutsche-boerse-pds/ · backend: claude · trust: 0.5 · extract: `sources/S25.md`

Deprecated — The provider of this dataset will no longer maintain this dataset. Stock Price Movement Prediction Using The Deutsche Börse Public Dataset & Machine Learning by Originate

### [S26] Frankfurter | Free exchange rates API
url: https://frankfurter.dev/ · backend: claude · trust: 0.82 · extract: `sources/S26.md`

Frankfurter — Exchange rates and currency data API The API itself does not collect personal data.

### [S27] open-data-registry/datasets/deutsche-boerse-pds.yaml at main · awslabs/open-data-registry · GitHub
url: https://github.com/awslabs/open-data-registry/blob/main/datasets/deutsche-boerse-pds.yaml · backend: claude · trust: 0.8 · extract: `sources/S27.md`

File metadata and controls — DeprecatedNotice : The provider of this dataset will no longer maintain this dataset. - Title : " Stock Price Movement Prediction Using The Deutsche Börse Public Dataset & Machine Learning "

### [S28] Data Providers FAQ - FAQs | OpenBB Docs
url: https://docs.openbb.co/odp/python/faqs/data_providers · backend: claude · trust: 0.82 · extract: `sources/S28.md`

Data and Data Providers — Another reason could be the data entitlements of your API key. It may also be that the functions are served by provider extensions that require API keys.

### [S29] EDINET
url: https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WZEK0030.html · backend: claude · trust: 0.5 · extract: `sources/S29.md`

利用規約 — 本ウェブサイトで提供する検索、閲覧、ダウンロード、EDINET API（インターネットを通じて情報取得に関する要求を送信することで、EDINET上のコンテンツを取得することを可能とする機能。以下「API機能」といいます。）等の機能（以下「本機能」といいます。）の利用にあたっては、以下の項目に同意したものとみなします。 ウェブサイトから情報を抽出するコンピュータソフトウェア技術（スクレイピング等）を利用して本ウェブサイトからコンテンツを機械的に取得することは禁止します。ただし、API機能を利用する場合又はAPI機能で取得できないコンテンツを取得する場合はこの限りではありません。本ウェブサイトのコンテンツを機械的に取得するには、API機能を利用してください（ EDINET API関連資料 ）。

### [S30] GitHub - hemenkapadia/getbhavcopy: Free NSE and BSE data downloader · GitHub
url: https://github.com/hemenkapadia/getbhavcopy · backend: claude · trust: 0.8 · extract: `sources/S30.md`

Getbhavcopy is a FREE data downloader for Indian Stock Exchanges, NSE and BSE . Getbhavcopy exports the downloaded data in a format that is easily imported in leading technical analysis softwares like Metastock , Amibroker and Fcharts .
