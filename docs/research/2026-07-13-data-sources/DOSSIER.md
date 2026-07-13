# Search dossier

**Question:** Most complete keyless/public data sources and open-source technologies for a self-hosted worldwide fundamental stock screener with licensing/ToS constraints
**Mode:** topic · **depth:** standard · **lang:** en · **sources:** 81 · **built:** 2026-07-13T10:08:02.933Z
**Backends used:** claude, wikipedia, standards, duckduckgo

> Write two tiers from these sources: `SUMMARY.md` (TL;DR) and `REPORT.md` (the full template below, filled exhaustively — use every relevant source and end with an "Open questions / contradictions" section). Then run `render` and `check`. Do not answer from memory.

## Grounding rules

**Cite every factual claim** with the id of the source it rests on, e.g. `[S1]`
(multiple sources: `[S1][S4]`). The ids are listed below and in `sources.json`.

If you state something from your **own background knowledge** that no fetched
source backs, you must FLAG it as unverified — either end the sentence with
`[M]`, or put the passage in a `> [model-hint] …` blockquote. `ultrasearch check`
tolerates flagged hints but FAILS on any *unmarked* unsourced claim, and on any
`[S#]` that does not resolve to a real source.

## Report template (topic)

```markdown
## TL;DR
## What it is
## How it works / key concepts
## History & evolution
## Current state (today)
## Notable variants / approaches
## Controversies & open debates
## Practical implications
## Sources
```

## Retrieval notes

- Merged 4 sub-dossier(s) → 81 source(s) (2 near-duplicate(s) collapsed).
- agent: write the report against THIS master dossier's [S#] ids; then verify + check --semantic.

## Sources

### [S1] GitHub - JerBouma/FinanceDatabase: This is a database of 300.000+ symbols containing Equities, ETFs, Funds, Indices, Currencies, Cryptocurrencies and Money Markets. · GitHub
url: https://github.com/JerBouma/FinanceDatabase · backend: claude · trust: 0.8 · extract: `sources/S1.md`

Usage — Comstock Resources, Inc. http://www.comstockresources.com

### [S2] SEC.gov | EDGAR Application Programming Interfaces (APIs)
url: https://www.sec.gov/search-filings/edgar-application-programming-interfaces · backend: claude · trust: 0.95 · extract: `sources/S2.md`

data.sec.gov/submissions/ — This JSON data structure contains metadata such as current name, former name, and stock exchanges and ticker symbols of publicly-traded companies. The object’s property path contains at least one year’s of filing or to 1,000 (whichever is more) of the most recent filings in a compact columnar data array.

### [S3] jeff3388/awesome-financial-data-apis - GitHub
url: https://github.com/jeff3388/awesome-financial-data-apis · backend: duckduckgo · trust: 0.8 · extract: `sources/S3.md`

A curated, actively maintained list of free and paid financial data APIs, Python client libraries, and data quality tools for individual investors, quants, and developers — with verified availability status as of 2026 . Why this list exists: After Yahoo Finance's unofficial API became unreliable in 2023 and Quandl transitioned to Nasdaq Data Link (with many 

### [S4] GitHub - JerBouma/FinanceToolkit: Transparent and Efficient Financial Analysis · GitHub
url: https://github.com/JerBouma/FinanceToolkit · backend: claude · trust: 0.8 · extract: `sources/S4.md`

Repository files navigation — This is why I designed the FinanceToolkit , this is an open-source toolkit in which all relevant financial ratios ( 200+ ), indicators and performance measurements are written down in the most simplistic way allowing for complete transparency of the method of calculation ( proof ). If data acquisition from Financial Modeling Pre

### [S5] SEC.gov | Accessing EDGAR Data
url: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data · backend: claude · trust: 0.95 · extract: `sources/S5.md`

Business hours and dissemination — Indexes incorporating the current business day's filings are updated nightly starting about 10:00 p.m., ET; the process is usually completed within a few hours. /Archives/edgar/Oldloads/ — daily concatenated archive files of all public filing submissions complete with the filing header.

### [S6] Stock Market Research Pack 6-in-1 Equities Scraper · Apify
url: https://apify.com/parseforge/stock-market-research-pack-scraper · backend: duckduckgo · trust: 0.5 · extract: `sources/S6.md`

📈 Stock Market Research Pack Scraper 🚀 Pull 6 public stock-market datasets in seconds. One actor, six sources: Alpha Vantage, Stooq snapshots, Twelve Data, Tiingo, Stooq historical OHLC, and MarketBeat analyst ratings. 🕒 Last updated: 2026 -05-27 · 📊 6 sources in one run · U.S. + global equities, FX, crypto · No login, no API key required The Stock Marke

### [S7] Finance Toolkit | Jeroen Bouma
url: https://www.jeroenbouma.com/projects/financetoolkit · backend: claude · trust: 0.5 · extract: `sources/S7.md`

This is why I designed the FinanceToolkit , this is an open-source toolkit in which all relevant financial ratios ( 200+ ), indicators and performance measurements are written down in the most simplistic way allowing for complete transparency of the calculation method ( proof ). If data acquisition from Financial Modeling Prep is unsuccessful (e.g., due to p

### [S8] Overview | OpenFIGI
url: https://www.openfigi.com/api/overview · backend: claude · trust: 0.5 · extract: `sources/S8.md`

Overview — The static output returns the FIGI and related Open Symbology metadata in the exact order requested for easier absorption. The same API key can be used to query Open Symbology data from any of the offered interfaces.

### [S9] filings.xbrl.org filing index
url: https://filings.xbrl.org/docs/about · backend: claude · trust: 0.5 · extract: `sources/S9.md`

Index structure — The index is structured by company identifier (typically LEI), then reporting Please note that for ESEF filings, beyond applying the XBRL Formula Rules defined in the ESEF taxonomy, we have not attempted to validate rules in the ESEF Reporting Manual , or any country-specific rules that may be applicable.

### [S10] GitHub - dgunning/edgartools: Read and analyze SEC EDGAR filings in Python. 10-K, 8-K, XBRL financials, Form 3/4/5, 13F, ADV — clean API, well-typed, MIT-licensed. · GitHub
url: https://github.com/dgunning/edgartools · backend: claude · trust: 0.8 · extract: `sources/S10.md`

EdgarTools — Python Library for SEC EDGAR Filings — EdgarTools is a Python library for accessing SEC EDGAR filings as structured data. EdgarTools is the open-source library — SEC-filing primitives you compose in your own code, free and self-run.

### [S11] Best Free Crypto APIs in 2026: Keyless Access & Free API Plans - CoinGecko
url: https://www.coingecko.com/learn/best-free-crypto-api · backend: duckduckgo · trust: 0.5 · extract: `sources/S11.md`

This guide walks through seven free crypto APIs worth considering in 2026 and where each fits best. We look at market coverage, keyless access, free-tier limits ( endpoints , credits, rate limits, historical data), and the types of use cases each one suits best.

### [S12] Download ISIN-to-LEI Relationship Files - LEI Mapping - LEI Data – GLEIF
url: https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files · backend: claude · trust: 0.5 · extract: `sources/S12.md`

Download ISIN-to-LEI Relationship Files — In April 2019, the Global Legal Entity Identifier Foundation (GLEIF) and the Association of National Numbering Agencies (ANNA) piloted the first daily open-source relationship files that link newly issued International Securities Identification Numbers (ISINs) and Legal Entity Identifiers (LEIs) .

### [S13] Companies House
url: https://download.companieshouse.gov.uk/en_accountsdata.html · backend: claude · trust: 0.95 · extract: `sources/S13.md`

What is it? — The Accounts Data Product is a free downloadable ZIP file, which contains the individual data files (instance documents) of company accounts filed electronically. The individual filenames will identify the company number (e.g.

### [S14] Docs - EdgarTools - Python Library for SEC Data Analysis
url: https://edgartools.readthedocs.io/ · backend: claude · trust: 0.82 · extract: `sources/S14.md`

EdgarTools: The Python Library for SEC EDGAR Data — Powerful Python library for SEC data analysis and financial research ✅ Simple, Pythonic API

### [S15] Market Data API & Stock API | Real-Time Financial Data | EODHD
url: https://eodhd.com/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S15.md`

Get real-time financial data , historical market data , and end-of-day pricing — plus fundamentals, options, news, Forex, and more. A complete stock API suite for any use case.

### [S16] Open Data - GLEIF – GLEIF
url: https://www.gleif.org/en/about/open-data · backend: claude · trust: 0.5 · extract: `sources/S16.md`

Open Data — The Global LEI Index is the only global online source that provides open, standardized, and high-quality legal entity reference data. Organizations that join GODIN will gain access to a collaborative network of like-minded organizations, fostering shared expertise, resources, and best practices.

### [S17] Developer Hub Home
url: https://developer.company-information.service.gov.uk/ · backend: claude · trust: 0.95 · extract: `sources/S17.md`

Companies House API overview — Our main functions are: to incorporate and dissolve limited companies; examine and store company get started guide, which has resources and information to help you.

### [S18] GitHub - OpenBB-finance/OpenBB: Open Data Platform for analysts, quants and AI agents. · GitHub
url: https://github.com/OpenBB-finance/OpenBB · backend: claude · trust: 0.8 · extract: `sources/S18.md`

Repository files navigation — ODP operates as the "connect once, consume everywhere" infrastructure layer that consolidates and exposes data to multiple surfaces at once: Python environments for quants, OpenBB Workspace and Excel for analysts, MCP servers for AI agents, and REST APIs for other applications. Connect this library to the OpenBB Workspace with a

### [S19] Financial Market Data APIs - FreeTier.dev
url: https://www.freetier.dev/services/finance-market-data/ · backend: duckduckgo · trust: 0.82 · extract: `sources/S19.md`

CoinGecko API Crypto market data API with a free getting-started option (no credit card): CoinGecko API Useful for crypto prices, market caps, exchange data, and related endpoints . Stooq Free historical OHLCV downloads via CSV: Stooq Useful for backtesting and research when EOD data is enough. No official API guarantees.

### [S20] Stooq Historical Stock Prices Scraper - Apify
url: https://apify.com/parseforge/stooq-historical-stocks-scraper · backend: duckduckgo · trust: 0.5 · extract: `sources/S20.md`

Download historical stock and index prices from Stooq . Export ticker, date, open , high, low, close, and volume as CSV , Excel, JSON, JSONL, XML, or HTML. Free public OHLC data for global equities and indices. Public- data export with no login required.

### [S21] GitHub - SimFin/simfin: Simple financial data for Python · GitHub
url: https://github.com/SimFin/simfin · backend: claude · trust: 0.8 · extract: `sources/S21.md`

SimFin - Simple financial data for Python — It automatically downloads share-prices and fundamental data from source activate simfin-env

### [S22] openbb · PyPI
url: https://pypi.org/project/openbb/ · backend: claude · trust: 0.5 · extract: `sources/S22.md`

OpenBB Platform — OpenBB is committed to build the future of investment research by focusing on an open source infrastructure accessible to everyone, everywhere. The package comes with a ready to use REST API - this allows developers from any language to easily create applications on top of OpenBB Platform.

### [S23] Symbol Directory Definitions
url: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs · backend: claude · trust: 0.5 · extract: `sources/S23.md`

Other Exchange-Listed Securities — The listing stock exchange or market of a security. Stock symbol of the primary security that underlies the option.

### [S24] IEX / Stooq Public Stock Data Scraper · Apify
url: https://apify.com/parseforge/iex-cloud-public-scraper · backend: duckduckgo · trust: 0.5 · extract: `sources/S24.md`

Export public stock price and metadata via Stooq (a free public source ): ticker, date, open , high, low, close, volume. Look up multiple tickers in bulk. Power finance dashboards and quant research. CSV , Excel, JSON, XML.

### [S25] DuckDB-Wasm: Efficient Analytical SQL in the Browser – DuckDB
url: https://duckdb.org/2021/10/29/duckdb-wasm · backend: claude · trust: 0.5 · extract: `sources/S25.md`

DuckDB-Wasm: Efficient Analytical SQL in the Browser — DuckDB-Wasm is fast! Today, we join the ranks with a first release of the npm library @duckdb/duckdb-wasm .

### [S26] Data License Agreement - SimFin
url: https://www.simfin.com/en/commercial-license/ · backend: claude · trust: 0.5 · extract: `sources/S26.md`

§2 PRO: “Commercial License, no re-distribution” — Licensee agrees that the DATA shall be for its own internal use only and shall not be sold, traded, copied, distributed, transferred, disposed of or otherwise made available to any other parties , except affiliates under common control or ownership with Licensee, and any company acquiring or merging with Lic

### [S27] All Tradable Instruments – Deutsche Börse Xetra
url: https://www.xetra.com/xetra-en/instruments/instruments · backend: claude · trust: 0.5 · extract: `sources/S27.md`

IPOs, index ascents, listing jubilees: Visit Frankfurt Stock Exchange

### [S28] EDINET for Developers: The Complete English Guide
url: https://axiora.dev/en/blog/edinet-for-developers · backend: claude · trust: 0.82 · extract: `sources/S28.md`

What EDINET Is (and Isn't) — Every listed company in Japan — plus investment funds, REITs, and any entity that publicly offers securities — must file through EDINET. The element name for "revenue" depends on which accounting standard the company uses, which industry it's in, and which section of the report you're reading.

### [S29] Redirecting…
url: https://duckdb.org/docs/stable/core_extensions/overview · backend: claude · trust: 0.5 · extract: `sources/S29.md`

Redirecting… — Click here if you are not redirected.

### [S30] Best Crude Oil Price Software | 2026 Expert Picks
url: https://gitnux.org/best/crude-oil-price-software/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S30.md`

The site emphasizes practical data retrieval over advanced charting or portfolio tooling, which fits crude oil price research workflows. For teams that need clean time series as input to analytics, Stooq provides a straightforward path from symbol to dataset .

### [S31] Stocks all markets - Euronext exchange Live quotes
url: https://live.euronext.com/en/products/equities/list · backend: claude · trust: 0.5 · extract: `sources/S31.md`

market — Euronext Growth Brussels Euronext Growth Dublin

### [S32] Historical Prices API for Stocks, ETFs, Forex, and Digital currencies ...
url: https://eodhd.com/lp/historical-eod-api · backend: duckduckgo · trust: 0.5 · extract: `sources/S32.md`

Get reliable historical data and volumes for stocks , ETFs, forex, and digital currencies from over 60 global exchanges with EODHD's API.

### [S33] Search and download documents - SEDAR+ Resources
url: https://systems.securities-administrators.ca/onlinehelp/general-help/search-sedar/search-and-download-documents/ · backend: claude · trust: 0.5 · extract: `sources/S33.md`

Securities Offerings filings Third party filings and securities acquisitions

### [S34] @duckdb/duckdb-wasm - npm
url: https://www.npmjs.com/package/@duckdb/duckdb-wasm · backend: claude · trust: 0.5 · extract: `sources/S34.md`

@duckdb/duckdb-wasm — Try it out at shell.duckdb.org and on Observable and read the API documentation . DuckDB-Wasm is fast!

### [S35] FAQ | OpenFIGI
url: https://www.openfigi.com/about/faq · backend: claude · trust: 0.5 · extract: `sources/S35.md`

How can I map to futures and options? — We offer multiple Derivative specific symbology options in the OpenFIGI API. For example: Full Exchange Symbol

### [S36] Attribution and copyright licensing
url: https://developer.mozilla.org/en-US/docs/MDN/Writing_guidelines/Attrib_copyright_license · backend: standards · trust: 0.9 · extract: `sources/S36.md`

MDN Web Docs content is available free of charge and is available under various open-source licenses.

### [S37] GitHub - LondonMarket/Global-Stock-Symbols: JSON, txt & CSV lists of securities listed on the London Stock Exchange (Main Market & AIM), New York Stock Exchange & NASDAQ, Toronto Stock Exchange, Frankfurt Stock Exchange, Australian Stock Exchange, Tokyo Stock Exchange & Hong Kong Stock Exchange · GitHub
url: https://github.com/LondonMarket/Global-Stock-Symbols · backend: claude · trust: 0.8 · extract: `sources/S37.md`

Uh oh! — Global-Stock-Symbols frankfurt_stock_listed_october_2024.xlsx

### [S38] xbrl-filings-api · PyPI
url: https://pypi.org/project/xbrl-filings-api/ · backend: claude · trust: 0.5 · extract: `sources/S38.md`

XBRL Filings API — In the case of ESEF, the reporters have issued securities on European these securities are shares.

### [S39] Arelle®
url: https://arelle.org/arelle/ · backend: claude · trust: 0.5 · extract: `sources/S39.md`

Overview — It seeks to provide the XBRL community with a free and easy to use open source platform for XBRL, supporting XBRL and its extension features in an extensible manner. It does this in a compact yet robust framework that can be used as a desktop application and can be integrated with other applications and languages utilizing its web service, command

### [S40] Free Stock Market Data API for Real-Time & Historical Data
url: https://marketstack.com/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S40.md`

Access free stock data API offering real-time and historical market data for global exchanges . Marketstack provides fast, reliable stock price API solutions.

### [S41] Where to Find a List of All Stock Market Ticker Symbols Without Web Scraping | by Wyatt Lang | Medium
url: https://medium.com/@wyattlang/where-to-find-a-list-of-all-stock-market-ticker-symbols-without-web-scraping-577896ccd718 · backend: claude · trust: 0.55 · extract: `sources/S41.md`

Where to Find a List of All Stock Market Ticker Symbols Without Web Scraping — In the beginning, I struggled to find a free, publicly available list of stock market tickers to download. I wanted to find a list of stock market ticker symbols that is well maintained with regular updates so that my application could consider new IPOs and drop the rare company w

### [S42] Well over 3,000 ESEF filings at filings.xbrl.org! Where are they coming from, and how can we improve access? | XBRL
url: https://www.xbrl.org/news/well-over-3000-esef-filings-at-filings-xbrl-org-where-are-they-coming-from-and-how-can-we-improve-access/ · backend: claude · trust: 0.5 · extract: `sources/S42.md`

Well over 3,000 ESEF filings at filings.xbrl.org! Where are they coming from, and how can we improve access? — Have you visited filings.xbrl.org  recently – and are you finding it a useful resource? Alongside a whole lot of other useful information, this includes a list of Sources for each country, which tells you exactly where we are getting all these filin

### [S43] 2026 FIFA World Cup - Wikipedia
url: https://en.wikipedia.org/wiki/2026_FIFA_World_Cup · backend: duckduckgo · trust: 0.85 · extract: `sources/S43.md`

The 2026 FIFA World Cup[A] is the 23rd FIFA World Cup and the current edition of the quadrennial international men's soccer championship contested by the national teams of the member associations of FIFA. The tournament began on June 11, 2026 , and will conclude on July 19. [3] It is jointly hosted by 16 cities—11 in the United States, 3 in Mexico, and 2 in 

### [S44] GitHub - Arelle/Arelle: Arelle open source XBRL platform · GitHub
url: https://github.com/Arelle/Arelle · backend: claude · trust: 0.8 · extract: `sources/S44.md`

Description — Arelle is an end-to-end open source XBRL platform, which provides the XBRL community languages utilizing its web service, command line interface, and Python API.

### [S45] GitHub - rreichel3/US-Stock-Symbols: Full lists of US Securities on the NASDAQ, NYSE, and AMEX powered by GitHub Actions · GitHub
url: https://github.com/rreichel3/US-Stock-Symbols · backend: claude · trust: 0.8 · extract: `sources/S45.md`

US-Stock-Symbols — An aggregation of current US Stock Symbols in json and txt formats. It is not a simple list of ticker symbols and contains full company name, etc.

### [S46] SEC.gov | Financial Statement Data Sets
url: https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets · backend: claude · trust: 0.95 · extract: `sources/S46.md`

More in this Section The data sets also contain additional fields including a company's Standard Industrial Classification to facilitate the data's use.

### [S47] Challenge: Building a house data UI
url: https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/House_data_UI · backend: standards · trust: 0.9 · extract: `sources/S47.md`

In this challenge we are going to get you to write some JavaScript for a house search/filter page on a property website. This will include fetching JSON data, filtering that data based on the values entered in provided form controls, and rendering that data to the UI. Along the way, we'll also test your knowledge of conditionals, loops, arrays and array meth

### [S48] Perspective
url: https://perspective.finos.org/ · backend: claude · trust: 0.5 · extract: `sources/S48.md`

What is Perspective? — browser, or in concert with Python and/or widget and Python client library, for

### [S49] The Complete List of Listed Stocks on the London Stock ExchangeTopForeignStocks.com
url: https://topforeignstocks.com/listed-companies-lists/the-complete-list-of-listed-stocks-on-the-london-stock-exchange/ · backend: claude · trust: 0.5 · extract: `sources/S49.md`

The Complete List of Listed Stocks on the London Stock Exchange as of Oct 6, 2024 are shown in the three tables below. 34 EN+ GROUP INTERNATIONAL PUBLIC JOINT-STOCK COMPANY 94PF Basic Resources United Kingdom USD

### [S50] Radware Captcha Page
url: https://www.sedarplus.ca/onlinehelp/terms-of-use/ · backend: claude · trust: 0.5 · extract: `sources/S50.md`

We apologize for the inconvenience... — ...but your activity and behavior on this site made us think that you are a bot. Note: A number of things could be going on here.

### [S51] GitHub - perspective-dev/perspective: A data visualization and analytics component, especially well-suited for large and/or streaming datasets. · GitHub
url: https://github.com/finos/perspective · backend: claude · trust: 0.8 · extract: `sources/S51.md`

Features — external data sources like DuckDB while translating A JupyterLab widget and Python client library for

### [S52] Free Stock APIs in JSON & Excel | Alpha Vantage
url: https://www.alphavantage.co/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S52.md`

Alpha Vantage offers free stock APIs in JSON and CSV formats for realtime and historical stock market data , options, forex, commodity, cryptocurrency feeds and over 50 technical indicators. Global market news API and sentiment scores powered by AI and machine learning. Supports intraday, daily, weekly, and monthly quotes and technical analysis with chart-re

### [S53] Download the GLEIF Golden Copy and Delta Files - GLEIF Golden Copy and Delta Files - LEI Data – GLEIF
url: https://www.gleif.org/en/lei-data/gleif-golden-copy/download-the-golden-copy · backend: claude · trust: 0.5 · extract: `sources/S53.md`

Download the GLEIF Golden Copy and Delta Files — The content of the Golden Copy files is also available in Resource Description Framework (RDF) format .

### [S54] SEDAR provides access to documents filed by public companies, investment funds and certain third-party filers | OSC
url: https://www.osc.ca/en/industry/sedarplus · backend: claude · trust: 0.5 · extract: `sources/S54.md`

About SEDAR+ — SEDAR+ will be the Canadian Securities Administrators’ national system that all market participants will use for filings, disclosure, payments and information searching in Canada’s capital markets. Effective cyber security and privacy management

### [S55] Community resources
url: https://developer.mozilla.org/en-US/docs/MDN/Community · backend: standards · trust: 0.9 · extract: `sources/S55.md`

👋 Welcome to MDN Web Docs, an open-source, collaborative project that documents web platform technologies, including HTML, CSS, JavaScript, and Web APIs.
We also provide extensive learning resources for early-stage developers and students.

### [S56] EDINET
url: https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/WEEK0060.html · backend: claude · trust: 0.5 · extract: `sources/S56.md`

For EDINET Taxonomy 2026 (Published on 11 November 2025) — For EDINET Taxonomy 2014(Revision for Deemed Registration Statement of Specified Securities)

### [S57] Global LEI Index - LEI Data – GLEIF
url: https://www.gleif.org/en/lei-data/global-lei-index · backend: claude · trust: 0.5 · extract: `sources/S57.md`

Global LEI Index — The Global LEI Index is the only global online source that provides open, standardized and high quality legal entity reference data. Subject to the selected mode of accessing the LEI data pool, users are able to source additional information relevant to an LEI record such as enriched reference data or other identifiers that have been mappe

### [S58] So you want to integrate with the SEC API - GreenFlux Blog
url: https://blog.greenflux.us/so-you-want-to-integrate-with-the-sec-api/ · backend: claude · trust: 0.5 · extract: `sources/S58.md`

Problem #2: Ticker Lookup Format is Not an Array — Most UI tools expect an array of objects for the input data. Most people only know companies by their name, and maybe their stock ticker, but not their CIK number.

### [S59] Data in WebGL
url: https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/Data · backend: standards · trust: 0.9 · extract: `sources/S59.md`

Shader programs have access to three kinds of data storage, each of which has a specific use case. Each kind of variable is accessible by one or both types of shader program (depending on the data store type) and possibly by the site's JavaScript code, depending on the specific type of variable.

### [S60] fx
url: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/fx · backend: standards · trust: 0.9 · extract: `sources/S60.md`

The fx attribute defines the x-axis coordinate of the focal point for a radial gradient.

### [S61] Download Stock Data and Historical Quotes for Global Indices [INDEX]
url: https://www.eoddata.com/download.aspx · backend: duckduckgo · trust: 0.5 · extract: `sources/S61.md`

EODData provides quality end‑of‑day quotes and intraday bar data across global exchanges with up to 30 years of historical market data .

### [S62] SummerSlam (2026)
url: https://en.wikipedia.org/wiki/SummerSlam_(2026) · backend: wikipedia · trust: 0.85 · extract: `sources/S62.md`

The 2026 SummerSlam, also promoted as SummerSlam: Minnesota, is an upcoming professional wrestling pay-per-view (PPV) and livestreaming event produced

### [S63] 2026 Venezuela earthquakes
url: https://en.wikipedia.org/wiki/2026_Venezuela_earthquakes · backend: wikipedia · trust: 0.85 · extract: `sources/S63.md`

On 24 June 2026, two large strike-slip earthquakes affected northwestern and central Venezuela. The epicenters of both earthquakes were in Veroes Municipality

### [S64] 2026 Formula One World Championship
url: https://en.wikipedia.org/wiki/2026_Formula_One_World_Championship · backend: wikipedia · trust: 0.85 · extract: `sources/S64.md`

2026 FIA Formula One World Championship Previous 2025 Next 2027 Races by country Races by venue Support series: Formula 2 Championship FIA Formula 3 Championship

### [S65] Find Open Datasets and Machine Learning Projects | Kaggle
url: https://www.kaggle.com/datasets · backend: duckduckgo · trust: 0.5 · extract: `sources/S65.md` · ⚠ snippet only (page fetch failed)

Browse and download hundreds of thousands of open datasets for AI research, model training, and analysis. Join a community of millions of researchers, developers, and builders to share and collaborate on Kaggle.

### [S66] Free Market Data - Stooq
url: https://stooq.com/db/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S66.md` · ⚠ snippet only (page fetch failed)

pon, 13 lip 2026 , 11:21 CEST, NY 5:21, Londyn 10:21, Tokio 18:21, WIG20 +0.12%

### [S67] FIFA World Cup 2026 Schedule: Dates, Times, Results and Venues
url: https://worldcupwiki.com/schedule/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S67.md`

FIFA World Cup 2026 full schedule: dates, kickoff times, matchups, results and Venues for all 104 matches. Updated from group stage to the Final.

### [S68] Free Historical Market Data - Stooq
url: https://stooq.com/db/h/ · backend: duckduckgo · trust: 0.5 · extract: `sources/S68.md` · ⚠ snippet only (page fetch failed)

pon, 13 lip 2026 , 11:22 CEST, NY 5:22, Londyn 10:22, Tokio 18:22, WIG20 +0.11%

### [S69] An Introduction to Stooq Pricing Data | QuantStart
url: https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data/ · backend: claude · trust: 0.5 · extract: `sources/S69.md`

For stocks listed on US exchanges it is also possible to obtain some fundamentals such as price earnings and market value, although there are no historic downloads available for these. One of the issues of relying on free data sources can often be determining whether adjustments have been made to the close price and how they have been carried out.

### [S70] Historical Data | Good source for .csv imports | Stooq - Quotes - Portfolio Performance Forum
url: https://forum.portfolio-performance.info/t/historical-data-good-source-for-csv-imports-stooq/37973 · backend: claude · trust: 0.5 · extract: `sources/S70.md`

Historical Data | Good source for .csv imports | Stooq A couple of my ETFs have issues with the historical data when using the app’s built-in data feed.

### [S71] Euro foreign exchange reference rates
url: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html · backend: claude · trust: 0.5 · extract: `sources/S71.md`

Euro foreign exchange reference rates — The reference rates are usually updated at around 16:00 CET every working day, except on TARGET closing days . The ECB has therefore decided to suspend its publication of a euro reference rate for the Russian rouble until further notice.

### [S72] Frankfurter | Free exchange rates API
url: https://frankfurter.dev/ · backend: claude · trust: 0.82 · extract: `sources/S72.md`

Providers — List the data sources behind the API. Open an issue to report a bug, request a feature, or suggest a new data source.

### [S73] New rate-limiting · Issue #2128 · ranaroussi/yfinance · GitHub
url: https://github.com/ranaroussi/yfinance/issues/2128 · backend: claude · trust: 0.8 · extract: `sources/S73.md`

Describe bug — I have used yfinance for the last year to pull 7 day, 1 minute granularity data on 7000 equity stocks at the end of each market day. On Wednesday 13/11/24, everything changed [when the fire nation attacked].

### [S74] Checking your browser - reCAPTCHA
url: https://www.kaggle.com/datasets/borismarjanovic/price-volume-data-for-all-us-stocks-etfs · backend: claude · trust: 0.5 · extract: `sources/S74.md`

Checking your browser before accessing www.kaggle.com ... Click here if you are not automatically redirected after 5 seconds.

### [S75] Deutsche Börse Public Dataset - Registry of Open Data on AWS
url: https://registry.opendata.aws/deutsche-boerse-pds/ · backend: claude · trust: 0.5 · extract: `sources/S75.md`

Description — It provides the initial price, lowest price, highest price, final price and volume for every minute of the trading day, and for every tradeable security. Stock Price Movement Prediction Using The Deutsche Börse Public Dataset & Machine Learning by Originate

### [S76] GitHub - hemenkapadia/getbhavcopy: Free NSE and BSE data downloader · GitHub
url: https://github.com/hemenkapadia/getbhavcopy · backend: claude · trust: 0.8 · extract: `sources/S76.md`

Getbhavcopy is a FREE data downloader for Indian Stock Exchanges, NSE and BSE . Getbhavcopy exports the downloaded data in a format that is easily imported in leading technical analysis softwares like Metastock , Amibroker and Fcharts .

### [S77] Huge Stock Market Dataset | Kaggle
url: https://web.archive.org/web/2026/https://www.kaggle.com/datasets/borismarjanovic/price-volume-data-for-all-us-stocks-etfs · backend: claude · trust: 0.5 · extract: `sources/S77.md`

Archive Team believes that by duplicated condemned data, the conversation and debate can continue, as well as the richness and insight gained by keeping the materials. Our projects have ranged in size from a single volunteer downloading the data to a small-but-critical site, to over 100 volunteers stepping forward to acquire terabytes of user-created data to

### [S78] https://api.github.com/repos/ranaroussi/yfinance/issues/2128
url: https://api.github.com/repos/ranaroussi/yfinance/issues/2128 · backend: claude · trust: 0.8 · extract: `sources/S78.md`

"issue_dependencies_summary": { "body": "### Describe bug\n\nI have used yfinance for the last year to pull 7 day, 1 minute granularity data on 7000 equity stocks at the end of each market day.

### [S79] Disclaimer & copyright
url: https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html · backend: claude · trust: 0.5 · extract: `sources/S79.md`

Disclaimer — is information of a general nature and is not intended to address the specific circumstances of any particular individual or entity While the euro short-term rate (€STR), the euro foreign exchange reference rates and other price information published on this website are based on sources which the ECB considers to be reliable, the ECB accepts no

### [S80] Download free market data from Stooq.com
url: https://www.chartoasis.com/free-data-download-stooq-help-cop3/ · backend: claude · trust: 0.5 · extract: `sources/S80.md`

Download free market data from Stooq.com — You can download market data for Polish, Japanese, Hungarian, German and USA stocks. Direct link is a link within Chartoasis.com that points directly at a free market data provider's subpage of a stock where you can start downloading market data.

### [S81] Stooq (website) — Grokipedia
url: https://grokipedia.com/page/stooq-website · backend: claude · trust: 0.5 · extract: `sources/S81.md`

Development and Expansion — By the 2010s , Stooq had further developed its offerings to encompass non-stock assets , including bonds , currencies , commodities , and cryptocurrencies, alongside extensive historical data archives that extend over 20 years for many assets. Examples of integration include using the API via libraries like pandas-datareader in Py
