# Evidence dossier

**Idea:** crible — self-hosted fundamental stock screener: worldwide universe (~161k equities) with Europe-depth priority, keyless open-data ingestion (FinanceDatabase, yfinance, ESEF XBRL filings, Stooq) into DuckDB/Parquet, 200+ ratios plus Piotroski/Altman/Beneish scores, filter DSL exposed via CLI, FastAPI and a React/Vite SPA, Docker-composed rolling prioritized crawler
**Angles:** market, oss, tech · **semantic:** off · **built:** 2026-07-06T21:25:24.742Z

> Ground the SRD's requirements and decisions in this evidence. Cite items by id, e.g. `[E1]`. Grounding is advisory — `construct check` reports coverage but never fails on it. Still: prefer a cited claim to a guessed one.

## Open-source prior art

### [E1] JerBouma/FinanceToolkit — prior art
ref: `JerBouma/FinanceToolkit` · loc: `https://github.com/JerBouma/FinanceToolkit` · score: 862
url: https://github.com/JerBouma/FinanceToolkit

```
Languages: csv:614, py:148, json:58, ipynb:12, pickle:7, md:6 · files: 862.


For example, Microsoft's Price-to-Earnings (PE) ratio on the 6th of May, 2023 is reported to be 28.93 (Stockopedia), 32.05 (Morningstar), 32.66 (Macrotrends), 33.09 (Finance Charts), 33.66 (Y Charts), 33.67 (Wall Street Journal), 33.80 (Yahoo Finance) and 34.4 (Companies Market Cap). All of these calculations are correct, however the method of calculation varies leading to different results. Therefore, collecting data from multiple sources can lead to wrong interpretation of the results given that one source could apply a different definition than another. And that is, if that definition is even available as often the underlying methods are hidden behind a paid subscription.

**This is why I designed the FinanceToolkit**, this is an open-source toolkit in which all relevant financial ratios ([200+](#core-functionality-and-metrics)), indicators and performance measurements are written down in the most simplistic way allowing for complete transparency of the method of calculation ([proof](https://github.com/JerBouma/FinanceToolkit/blob/main/financetoolkit/ratios/valuation_model.py)). This enables you to avoid dependence on metrics from other providers that do not provide their methods. With a large selection of financial statements in hand, it facilitates streamlined calculations, promoting the adoption of a consistent and universally understood methods and formulas.

Beyond Equities, it supports Options, Currencies, Cryptocurrencies, ETFs, Mutual Funds, Indices, Money Markets
```

### [E2] JerBouma/FinanceDatabase — prior art
ref: `JerBouma/FinanceDatabase` · loc: `https://github.com/JerBouma/FinanceDatabase` · score: 323
url: https://github.com/JerBouma/FinanceDatabase

```
Languages: csv:225, json:55, py:19, gzip:7, md:6, yml:4 · files: 323.

| **Call for Contributors to the FinanceDatabase**    |
|:------------------------------------------------------:|
| The **FinanceDatabase** serves the role of providing anyone with any type of financial product categorization entirely for free. To achieve this, the FinanceDatabase relies on community involvement to add, edit, and remove tickers over time. This is made easy enough that anyone, even those with a lack of coding experience, can contribute because of the use of CSV files that can be manually edited with ease.
**I'd like to invite you to go to the [Contributing Guidelines](https://github.com/JerBouma/FinanceDatabase/blob/main/CONTRIBUTING.md) to understand how you can help. Thank you!** |

As a private investor, the sheer amount of information that can be found on the internet is rather daunting. Trying to understand what types of companies or ETFs are available is incredibly challenging, with millions of companies and derivatives available on the market. Sure, the most traded companies and ETFs can quickly be found simply because they are known to the public (for example, Microsoft, Tesla, S&P 500 ETF, or an All-World ETF). However, what else is out there is often unknown.

**This database tries to solve that**. It features 300,000+ symbols containing Equities, ETFs, Funds, Indices, Currencies, Cryptocurrencies, and Money Markets. It therefore allows you to obtain a broad overview of sectors, industries, types of investments, and much more.

The aim of this datab
```

### [E3] ranaroussi/yfinance — prior art
ref: `ranaroussi/yfinance` · loc: `https://github.com/ranaroussi/yfinance` · score: 207
url: https://github.com/ranaroussi/yfinance

```
Languages: csv:79, py:71, rst:30, yml:9, md:4, txt:3 · files: 207.


<a href="https://trendshift.io/repositories/4578" target="_blank"><img src="https://trendshift.io/api/badge/repositories/4578" alt="ranaroussi%2Fyfinance | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**yfinance** offers a Pythonic way to fetch financial & market data from [Yahoo!Ⓡ finance](https://finance.yahoo.com).

---

> [!IMPORTANT]  
> **Yahoo!, Y!Finance, and Yahoo! finance are registered trademarks of Yahoo, Inc.**
>
> yfinance is **not** affiliated, endorsed, or vetted by Yahoo, Inc. It's an open-source tool that uses Yahoo's publicly available APIs, and is intended for research and educational purposes.
> 
> **You should refer to Yahoo!'s terms of use** ([here](https://policies.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.htm), [here](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html), and [here](https://policies.yahoo.com/us/en/yahoo/terms/index.htm)) **for details on your rights to use the actual data downloaded.
>
> Remember - the Yahoo! finance API is intended for personal use only.**
```

## Technology documentation

### [E4] Docs — https://duckdb.org/
ref: `https://duckdb.org/` · loc: `https://duckdb.org/#~45` · score: 5
url: https://duckdb.org/

```
Live demo
Query files and
cloud data directly
Use DuckDB's friendly but powerful SQL dialect to query any data source (Parquet, JSON, S3, data lakes, etc.)
Live demo
How we designed DuckDB
Simple
We made sure that you can install DuckDB in just a few seconds,
and built it on familiar technologies so you can start using it immediately.
Read more
Feature-rich
We support a wide range of industry standard technologies (e.g., Parquet, SQL, S3 API)
and combine them into a seamless user experience.
Read more
Fast
```

### [E5] Docs — https://filings.xbrl.org/docs/about
ref: `https://filings.xbrl.org/docs/about` · loc: `https://filings.xbrl.org/docs/about#~30` · score: 5
url: https://filings.xbrl.org/docs/about

```
Although we aim to include as many filings as possible, the repository is not complete.
In some cases, technical errors in a filing prevent us from providing the viewer and xBRL-JSON outputs. In other cases, the format of the filing is such that we cannot automatically determine the LEI and filing date to which it relates, and the filing will be excluded from the index altogether.
API
The filings database is also available via an API at https://filings.xbrl.org/api/filings . The API uses the JSON-API standard.
There is some limited API documentation available.
Performance
Some filings in this repository can be slow to open in a browser. This is typically because the Inline XBRL report has been created using automated PDF-to-HTML conversion software. Such software produces a document which faithfully reproduces the appearance of a PDF document, but the resulting HTML is often extremely inefficient, leading to large file sizes and slow rendering times.
We expect this to improve over time, as software improves, and preparers start to target the Inline XBRL format directly, rather than converting from PDF.
Index structure
The index is structured by company identifier (typically LEI), then reporting
date, filing system and country. In some cases there are multiple reports
within that structure. This is typically due to reports being provided in
multiple languages, but it may also be due to the submission of amended
reports. Where there are multiple reports, these are put into sepa
```

### [E6] Docs — https://github.com/JerBouma/FinanceToolkit
ref: `https://github.com/JerBouma/FinanceToolkit` · loc: `https://github.com/JerBouma/FinanceToolkit#~90` · score: 5
url: https://github.com/JerBouma/FinanceToolkit

```
Repository files navigation
While browsing a variety of websites, I repeatedly observed significant fluctuations in the same financial metric among different sources. Similarly, the reported financial statements often didn't line up, and there was limited information on the methodology used to calculate each metric.
For example, Microsoft's Price-to-Earnings (PE) ratio on the 6th of May, 2023 is reported to be 28.93 (Stockopedia), 32.05 (Morningstar), 32.66 (Macrotrends), 33.09 (Finance Charts), 33.66 (Y Charts), 33.67 (Wall Street Journal), 33.80 (Yahoo Finance) and 34.4 (Companies Market Cap). All of these calculations are correct, however the method of calculation varies leading to different results. Therefore, collecting data from multiple sources can lead to wrong interpretation of the results given that one source could apply a different definition than another. And that is, if that definition is even available as often the underlying methods are hidden behind a paid subscription.
This is why I designed the FinanceToolkit , this is an open-source toolkit in which all relevant financial ratios ( 200+ ), indicators and performance measurements are written down in the most simplistic way allowing for complete transparency of the method of calculation ( proof ). This enables you to avoid dependence on metrics from other providers that do not provide their methods. With a large selection of financial statements in hand, it facilitates streamlined calculations, promoting the 
```

### [E7] Docs — https://github.com/JerBouma/FinanceToolkit (lines 4412–4426)
ref: `https://github.com/JerBouma/FinanceToolkit` · loc: `https://github.com/JerBouma/FinanceToolkit#~4412` · score: 5
url: https://github.com/JerBouma/FinanceToolkit

```
46718.5
43178.3
MCP Server
The Finance Toolkit MCP Server exposes 200+ financial metrics, models, and economic indicators directly to any AI assistant that supports the Model Context Protocol (MCP). Ask questions in plain English — the AI fetches live financial data on your behalf, backed by the transparent, open-source calculation methods of the Finance Toolkit.
See an example of the Finance Toolkit MCP server in action in Claude Desktop below:
Finance.Toolkit.-.MCP.Demo.mp4
Remote server
Connect directly to the hosted server at https://financetoolkit.jeroenbouma.com/mcp . Nothing needs to be installed locally. On first connection your client opens an OAuth consent page asking for your FMP API key; enter it once and the server handles authentication from there.
Client
Steps
Claude Desktop
Customize → Connectors → Add custom connector → paste the URL
Claude.ai
Customize → Connectors → Add custom connector → paste the URL
Claude Code
```

### [E8] Docs — https://pypi.org/project/financetoolkit/
ref: `https://pypi.org/project/financetoolkit/` · loc: `https://pypi.org/project/financetoolkit/#~82` · score: 5
url: https://pypi.org/project/financetoolkit/

```
Project description
While browsing a variety of websites, I repeatedly observed significant fluctuations in the same financial metric among different sources. Similarly, the reported financial statements often didn't line up, and there was limited information on the methodology used to calculate each metric.
For example, Microsoft's Price-to-Earnings (PE) ratio on the 6th of May, 2023 is reported to be 28.93 (Stockopedia), 32.05 (Morningstar), 32.66 (Macrotrends), 33.09 (Finance Charts), 33.66 (Y Charts), 33.67 (Wall Street Journal), 33.80 (Yahoo Finance) and 34.4 (Companies Market Cap). All of these calculations are correct, however the method of calculation varies leading to different results. Therefore, collecting data from multiple sources can lead to wrong interpretation of the results given that one source could apply a different definition than another. And that is, if that definition is even available as often the underlying methods are hidden behind a paid subscription.
This is why I designed the FinanceToolkit , this is an open-source toolkit in which all relevant financial ratios ( 200+ ), indicators and performance measurements are written down in the most simplistic way allowing for complete transparency of the method of calculation ( proof ). This enables you to avoid dependence on metrics from other providers that do not provide their methods. With a large selection of financial statements in hand, it facilitates streamlined calculations, promoting the adoption
```

### [E9] Docs — https://pypi.org/project/financetoolkit/ (lines 4404–4418)
ref: `https://pypi.org/project/financetoolkit/` · loc: `https://pypi.org/project/financetoolkit/#~4404` · score: 5
url: https://pypi.org/project/financetoolkit/

```
46718.5
43178.3
MCP Server
The Finance Toolkit MCP Server exposes 200+ financial metrics, models, and economic indicators directly to any AI assistant that supports the Model Context Protocol (MCP). Ask questions in plain English — the AI fetches live financial data on your behalf, backed by the transparent, open-source calculation methods of the Finance Toolkit.
See an example of the Finance Toolkit MCP server in action in Claude Desktop below:
https://github.com/user-attachments/assets/96ad5288-d83d-4497-a345-1841c48c29d5
Remote server
Connect directly to the hosted server at https://financetoolkit.jeroenbouma.com/mcp . Nothing needs to be installed locally. On first connection your client opens an OAuth consent page asking for your FMP API key; enter it once and the server handles authentication from there.
Client
Steps
Claude Desktop
Customize → Connectors → Add custom connector → paste the URL
Claude.ai
Customize → Connectors → Add custom connector → paste the URL
Claude Code
```

### [E10] Docs — https://arrow.apache.org/docs/18.0/python/parquet.html
ref: `https://arrow.apache.org/docs/18.0/python/parquet.html` · loc: `https://arrow.apache.org/docs/18.0/python/parquet.html#~136` · score: 4
url: https://arrow.apache.org/docs/18.0/python/parquet.html

```
In [19]: parquet_file = pq . ParquetFile ( 'example.parquet' )
In [20]: parquet_file . metadata
Out[20]:
<pyarrow._parquet.FileMetaData object at 0x7f15a07eec50>
created_by: parquet-cpp-arrow version 18.0.0-SNAPSHOT
num_columns: 4
num_rows: 3
num_row_groups: 1
format_version: 2.6
serialized_size: 2581
In [21]: parquet_file . schema
Out[21]:
<pyarrow._parquet.ParquetSchema object at 0x7f15ee75edc0>
required group field_id=-1 schema {
optional double field_id=-1 one;
```

### [E11] Docs — https://arrow.apache.org/docs/18.0/python/parquet.html (lines 188–202)
ref: `https://arrow.apache.org/docs/18.0/python/parquet.html` · loc: `https://arrow.apache.org/docs/18.0/python/parquet.html#~188` · score: 4
url: https://arrow.apache.org/docs/18.0/python/parquet.html

```
In [29]: metadata = pq . read_metadata ( 'example.parquet' )
In [30]: metadata
Out[30]:
<pyarrow._parquet.FileMetaData object at 0x7f15a060a480>
created_by: parquet-cpp-arrow version 18.0.0-SNAPSHOT
num_columns: 4
num_rows: 3
num_row_groups: 1
format_version: 2.6
serialized_size: 2581
The returned FileMetaData object allows to inspect the
Parquet file metadata ,
such as the row groups and column chunk metadata and statistics:
In [31]: metadata . row_group ( 0 )
Out[31]:
```

### [E12] Docs — https://duckdb.org/ (lines 72–86)
ref: `https://duckdb.org/` · loc: `https://duckdb.org/#~72` · score: 4
url: https://duckdb.org/

```
In fact, we implemented many core DuckDB features as extensions.
Read more
Built for your stack
DuckDB has native clients and integrations with the data ecosystem
Protocols & storage
Cloudflare
Amazon Web Services
Microsoft Azure
Google Cloud
Hugging Face
HTTP
Databases
DuckDB
SQLite
MySQL
```

### [E13] Docs — https://fastapi.tiangolo.com/
ref: `https://fastapi.tiangolo.com/` · loc: `https://fastapi.tiangolo.com/#~109` · score: 4
url: https://fastapi.tiangolo.com/

```
— Kabir Khan, Microsoft (ref)
"We adopted the FastAPI library to spawn a REST server that can be queried to obtain predictions ." [for Ludwig]
— Piero Molino, Yaroslav Dudin, Sai Sumanth Miryala, Uber (ref)
" Netflix is pleased to announce the open-source release of our crisis management orchestration framework: Dispatch !" [built with FastAPI]
— Kevin Glisson, Marc Vilanova, Forest Monsen, Netflix (ref)
"If anyone is looking to build a production Python API, I would highly recommend FastAPI . It is beautifully designed , simple to use and highly scalable — it has become a key component in our API-first development strategy."
— Deon Pillsbury, Cisco (ref)
" [...] I'm using FastAPI a ton these days. [...] I'm actually planning to use it for all of my team's ML services at Microsoft . Some of them are getting integrated into the core Windows product and some Office products. "
Kabir Khan - Microsoft (ref)
" We adopted the FastAPI library to spawn a REST server that can be queried to obtain predictions . [for Ludwig] "
Piero Molino, Yaroslav Dudin, and Sai Sumanth Miryala - Uber (ref)
" Netflix is pleased to announce the open-source release of our crisis management orchestration framework: Dispatch ! [built with FastAPI ] "
Kevin Glisson, Marc Vilanova, Forest Monsen - Netflix (ref)
" If anyone is looking to build a production Python API, I would highly recommend FastAPI . It is beautifully designed , simple to use and highly scalable , it has become a key component in our API f
```

### [E14] Docs — https://fastapi.tiangolo.com/ (lines 305–319)
ref: `https://fastapi.tiangolo.com/` · loc: `https://fastapi.tiangolo.com/#~305` · score: 4
url: https://fastapi.tiangolo.com/

```
Deploying to FastAPI Cloud...
✅ Deployment successful!
🐔 Ready the chicken! Your app is ready at https://myapp.fastapicloud.dev
The CLI will automatically detect your FastAPI application and deploy it to the cloud. If you are not logged in, your browser will open to complete the authentication process.
That's it! Now you can access your app at that URL. ✨
About FastAPI Cloud &para;
FastAPI Cloud is built by the same author and team behind FastAPI .
It streamlines the process of building , deploying , and accessing an API with minimal effort.
It brings the same developer experience of building apps with FastAPI to deploying them to the cloud. 🎉
FastAPI Cloud is the primary sponsor and funding provider for the FastAPI and friends open source projects. ✨
Deploy to other cloud providers &para;
FastAPI is open source and based on standards. You can deploy FastAPI apps to any cloud provider you choose.
Follow your cloud provider's guides to deploy FastAPI apps with them. 🤓
Performance &para;
Independent TechEmpower benchmarks show FastAPI applications running under Uvicorn as one of the fastest Python frameworks available , only below Starlette and Uvicorn themselves (used internally by FastAPI). (*)
```

### [E15] Docs — https://filings.xbrl.org/docs/about (lines 67–81)
ref: `https://filings.xbrl.org/docs/about` · loc: `https://filings.xbrl.org/docs/about#~67` · score: 4
url: https://filings.xbrl.org/docs/about

```
Validation errors and warnings
Many of the filings in the index have validation errors and warnings.
XBRL Formula Rules defined in the ESEF taxonomy.
Please note that for ESEF filings, beyond applying the XBRL Formula Rules defined in the ESEF taxonomy, we have not attempted to validate rules in the ESEF Reporting Manual , or any country-specific rules that may be applicable.
Sources
Filings are sourced from the relevant data collection authority. In the case
of ESEF reports, this is the Officially Appointed Mechanism (OAM) for the
country in which it was filed. See the Filing Sources
for a list of the sources that we use.
Missing data
Unfortunately, there are a number of countries where ESEF filings are not made
available in a way that allows us to reliably discover and download them, or
where we have not been able to locate a source at all. These countries include:
Germany
Ireland
```

### [E16] Docs — https://github.com/JerBouma/FinanceDatabase
ref: `https://github.com/JerBouma/FinanceDatabase` · loc: `https://github.com/JerBouma/FinanceDatabase#~89` · score: 4
url: https://github.com/JerBouma/FinanceDatabase

```
I'd like to invite you to go to the Contributing Guidelines to understand how you can help. Thank you!
As a private investor, the sheer amount of information that can be found on the internet is rather daunting. Trying to understand what types of companies or ETFs are available is incredibly challenging, with millions of companies and derivatives available on the market. Sure, the most traded companies and ETFs can quickly be found simply because they are known to the public (for example, Microsoft, Tesla, S&P 500 ETF, or an All-World ETF). However, what else is out there is often unknown.
This database tries to solve that . It features 300,000+ symbols containing Equities, ETFs, Funds, Indices, Currencies, Cryptocurrencies, and Money Markets. It therefore allows you to obtain a broad overview of sectors, industries, types of investments, and much more.
The aim of this database is explicitly not to provide up-to-date fundamentals or stock data, as those can be obtained with ease (with the help of this database) by using the Finance Toolkit 🛠️ . Instead, it gives insights into the products that exist in each country, industry, and sector and provides the most essential information about each product. With this information, you can analyze specific areas of the financial world and/or find a product that is hard to find. For examples of how you can combine this database with the earlier mentioned packages, see the Usage section.
Some key statistics of the database:
Product
Quan
```

### [E17] Docs — https://github.com/JerBouma/FinanceDatabase (lines 379–393)
ref: `https://github.com/JerBouma/FinanceDatabase` · loc: `https://github.com/JerBouma/FinanceDatabase#~379` · score: 4
url: https://github.com/JerBouma/FinanceDatabase

```
'Software & Services', 'Technology Hardware & Equipment',
'Telecommunication Services', 'Transportation', 'Utilities'],
dtype=object)}
Since the equities database has already been loaded, it is also possible to use similar functionality from within the class as follows. The main difference is that this functionality allows you to see the options based on specific filtering. For example:
equities . show_options ( country = 'Netherlands' )
This shows a more concise list of parameters given the focus on the Netherlands.
{'currency': array(['ARS', 'AUD', 'BRL', 'CHF', 'CZK', 'EUR', 'GBP', 'ILA', 'MXN',
'NOK', 'RUB', 'USD', 'ZAC'], dtype=object),
'sector': array(['Communication Services', 'Consumer Discretionary',
'Consumer Staples', 'Energy', 'Financials', 'Health Care',
'Industrials', 'Information Technology', 'Materials',
'Real Estate', 'Utilities'], dtype=object),
'industry_group': array(['Automobiles & Components', 'Banks', 'Capital Goods',
'Commercial & Professional Services',
'Consumer Durables & Apparel', 'Consumer Services',
```

### [E18] Docs — https://react.dev/
ref: `https://react.dev/` · loc: `https://react.dev/#~168` · score: 4
url: https://react.dev/

```
People love web and native apps for different reasons. React lets you build both web apps and native apps using the same skills. It leans upon each platform’s unique strengths to let your interfaces feel just right on every platform.
example.com
Stay true to the web
People expect web app pages to load fast. On the server, React lets you start streaming HTML while you’re still fetching data, progressively filling in the remaining content before any JavaScript code loads. On the client, React can use standard web APIs to keep your UI responsive even in the middle of rendering.
12:30 AM
Go truly native
People expect native apps to look and feel like their platform. React Native and Expo let you build apps in React for Android, iOS, and more. They look and feel native because their UIs are truly native. It’s not a web view—your React components render real Android and iOS views provided by the platform.
With React, you can be a web and a native developer. Your team can ship to many platforms without sacrificing the user experience. Your organization can bridge the platform silos, and form teams that own entire features end-to-end.
Build for native platforms
Upgrade when the future is ready
React approaches changes with care. Every React commit is tested on business-critical surfaces with over a billion users. Over 100,000 React components at Meta help validate every migration strategy.
The React team is always researching how to improve React. Some research takes years to pay off
```

### [E19] Docs — https://tanstack.com/table/latest
ref: `https://tanstack.com/table/latest` · loc: `https://tanstack.com/table/latest#~164` · score: 4
url: https://tanstack.com/table/latest

```
}
Field notes
The best Table examples do not look alike.
That is the point. TanStack Table powers shadcn-style data tables, accessible React Aria tables, dense admin grids, custom filters, and spreadsheet-like product surfaces because it stays below the visual layer.
Loved by Developers
See what teams are saying
" Introducing Table and Data Table components. Powered by TanStack Table. With Pagination, Row Selection, Sorting, Filters, Row Actions and Keyboard Navigation. "
shadcn
@shadcn · Vercel
" I made a version using React Aria Components with arrow key navigation, multi selection, screen reader announcements, and more. Works great with TanStack Table too! "
Devon Govett
@devongovett · Adobe
" TanStack Table is the perfect choice if you need a lightweight, unopinionated, and fully customizable solution. It gives you the power and leaves the presentation up to you. "
Developer Review
Community ·
```

### [E20] Docs — https://tanstack.com/table/latest (lines 188–202)
ref: `https://tanstack.com/table/latest` · loc: `https://tanstack.com/table/latest#~188` · score: 4
url: https://tanstack.com/table/latest

```
" TanStack Table is the perfect choice if you need a lightweight, unopinionated, and fully customizable solution. It gives you the power and leaves the presentation up to you. "
Developer Review
Community ·
" Linear-style table filters using shadcn and TanStack Table. Open source. You'll be able to use this as an add-on to the Data Table component. "
Kian Bazza
@kianbazza · Developer
Open source ecosystem
Table is shaped by the people building serious tables.
Maintainers, framework adapters, partner integrations, examples, and GitHub sponsors all keep the table engine close to real product work.
Maintainers
Tanner Linsley
Kevin Van Cott
Riccardo Perra
View All Maintainers
Partners
```

### [E21] Docs — https://vite.dev/guide/
ref: `https://vite.dev/guide/` · loc: `https://vite.dev/guide/#~146` · score: 4
url: https://vite.dev/guide/

```
"preview" : "vite preview" // locally preview production build
}
}
You can specify additional CLI options like --port or --open . For a full list of CLI options, run npx vite --help in your project.
Learn more about the Command Line Interface
Using Unreleased Commits ​
If you can't wait for a new release to test the latest features, you can install a specific commit of Vite with https://pkg.pr.new :
npm Yarn pnpm Bun
bash
$ npm install -D https://pkg.pr.new/vite@SHA
bash
$ yarn add -D https://pkg.pr.new/vite@SHA
bash
$ pnpm add -D https://pkg.pr.new/vite@SHA
bash
```

## Issues (prior art)

### [E22] #103 ValueError: Can't clean for JSON: Period('2018', 'Y-DEC') [BUG] [closed]
ref: `issue#103` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/103` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/103

```
state: closed · comments: 4 · updated: 2024-02-24T21:42:39Z

import pandas as pd

from financetoolkit import Toolkit

# Initialize the Toolkit with company tickers
companies = Toolkit(
    ["AAPL", "AMZN", "META"], api_key=API_KEY, start_date="2005-01-01"
)
companies.ratios.collect_all_ratios()

gives the error below:

---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
File /shared-libs/python3.10/py-core/lib/python3.10/site-packages/jupyter_client/session.py:99, in json_packer(obj)
     98 try:
---> 99     return json.dumps(
    100         obj,
    101         default=json_default,
    102         ensure_ascii=False,
    103         allow_nan=False,
    104     ).encode("utf8", errors="surrogateescape")
    105 except (TypeError, ValueError) as e:
    106     # Fallback to trying to clean the json before serializing

File /usr/local/lib/python3.10/json/__init__.py:238, in dumps(obj, skipkeys, ensure_ascii, check_circular, allow_nan, cls, indent, separators, default, sort_keys, **kw)
    233     cls = JSONEncoder
    234 return cls(
    235     skipkeys=skipkeys, ensure_ascii=ensure_ascii,
    236     check_circular=check_circular, allow_nan
```

### [E23] #108 [Bug] unexpected keyword argument 'historical_source' [closed]
ref: `issue#108` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/108` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/108

```
state: closed · comments: 3 · updated: 2025-07-05T11:14:08Z

---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
Cell In[7], line 1
----> 1 toolkit = dutch_insurance_companies.to_toolkit(
      2     api_key=API_KEY
      3 )

File c:\Users\xqgj9\miniconda3\envs\geminiEnv\Lib\site-packages\financedatabase\helpers.py:247, in FinanceFrame.to_toolkit(self, api_key, start_date, end_date, quarterly, use_cached_data, risk_free_rate, benchmark_ticker, historical_source, convert_currency, intraday_period, rounding, remove_invalid_tickers, sleep_timer, progress_bar)
    237     print(
    238         "The parameter api_key is not set. Therefore, only historical data and "
    239         "indicators are available. Consider obtaining a key with the following "
   (...)    243         "get access to 30+ years of (quarterly) data which also supports the project."
    244     )
    245 symbols = self[self.index.notna()].index.to_list()
--> 247 toolkit = Toolkit(
    248     tickers=symbols,
    249     api_key=api_key,
    250     start_date=start_date,
    251     end_date=end_date,
    252     quarterly=quarterly,
    253     use_cached_data=use_cached_d
```

### [E24] #112 [IMPROVE] Exchange errors [closed]
ref: `issue#112` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/112` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/112

```
state: closed · comments: 1 · updated: 2025-11-14T08:54:41Z

**What's the feature or data that should be improved?**
A description of what's the feature or data you want improved, and a bit of context (why is that).

I found the following errors with the "market" column.

Repro:
```
import financedatabase as fd
fd.show_options("equities")
equities = fd.Equities()
display(equities)
```
Then view the `market` column

Issues:
1. exchange `CSE` is Columbo Stock Exchange, but `market` column says "First North Copenhagen"
- you can see the currency of all the stocks with exchange `CSE` is `LKR` Sri Lanka Rupee

2. exchange `TWO` is Taipei Stock Exchange, but `market` column says "Taiwan Stock Exchange". They are two distinct exchanges.
3. exchange `ICE` -> market should be "NASDAQ Iceland"


**Describe how you would like the feature or data improved**
A description of what the current feature or data is vs what it would be after your suggestion.
See above

**Possibly describe the ideal way to improve this**
If you have thought about how you would do it, add it here.
See above

**Additional information**
Add any other information or screenshots about the feature improvement.
See above
```

### [E25] #118 [IMPROVE] Data quality: CUSIP identifier collisions across different companies [closed]
ref: `issue#118` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/118` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/118

```
state: closed · comments: 2 · updated: 2026-05-18T22:09:05Z

Hi - human here writing this, thanks for the excellent open source data work - it's much appreciated.  Came across a possible DQ issue and thought it may be helpful to flag.  Disclaimer - this below could be making some assumptions about your data model that are wrong.  It's also (obviouly) quite heavily AI assisted in writing the bug report.  Hope it helps.

-Adam

[END HUMAN]

[START AI SLOP]

## Thanks & Context

First, thank you for maintaining FinanceDatabase - it's an excellent resource! We're using the Equities dataset to look up GICS sector classifications for bond issuers in our fixed income analytics platform, and it's been tremendously helpful.

During our integration work, we noticed some data quality issues with CUSIP identifiers that we wanted to flag.

## Issue

The same CUSIP identifier is sometimes assigned to completely different companies. This makes CUSIP-based lookups unreliable.

## Statistics

```python
import financedatabase as fd

equities = fd.Equities()
df = equities.select()

cusip_df = df[df['cusip'].notna()]
print(f"Total records with CUSIP: {len(cusip_df):,}")        # 13,990
print(f"Unique CUSIPs: {cusip_df['cusip'].nunique():,}")     # 2,459

cusip_
```

### [E26] #119 Missing Symbols in FinanceDatabase available in FinancialToolkit [closed]
ref: `issue#119` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/119` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/119

```
state: closed · comments: 1 · updated: 2024-03-13T05:48:35Z

I'm attempting to retrieve market cap such as "large, small cap" info for tickers in FinancialToolkit. I discovered that this information can be found in FinanceDatabase, so I've been trying to source market cap through the FinancialDB. I've encountered an issue where some symbols that are listed in FinancialToolkit do not appear in FinanceDatabase.

Is it also possible to retrieve market cap in FinancialToolkit?


To illustrate, here's the code I'm using for the HKSE exchange:

import financedatabase as fd
from financetoolkit import Discovery
API_KEY = ''
discovery = Discovery(api_key=API_KEY)
tickers = discovery.get_stock_list()
equities = fd.Equities()

financialtoolkit = tickers[tickers['Exchange Code'] == 'HKSE'].reset_index()
financedb = equities.select(country='Hong Kong', exclude_exchanges=False)
financedb.reset_index(inplace=True)
tickers_not_in_financialdb = financialtoolkit[~financialtoolkit['Symbol'].isin(financedb['symbol'])].reset_index(drop=True)
tickers_not_in_financialdb

['0002.HK', '0003.HK', '0005.HK', '0006.HK', '0007.HK',  .... ]
```

### [E27] #133 Incorrect `exchange` code "ASE" assigned to NYSE / NYSE American securities (BRK.B, BF.B, ...) [closed]
ref: `issue#133` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/133` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/133

```
state: closed · comments: 2 · updated: 2026-05-18T22:04:14Z

## Summary

The `exchange` column in `equities.csv` reports `"ASE"` for ~430 securities that are actually listed on **NYSE main board** (`NYQ` per Yahoo Finance), not on NYSE American. The value is also ambiguous as a short code: `ASE` collides with the ISO 10383 ACRONYM for Athens Stock Exchange (MIC `ASEX`).

## Reproduction

```python
import financedatabase as fd
eq = fd.Equities()
df = eq.select()
sample = df.loc[["BRK.B", "BF.B", "ARX", "ALH"], ["name", "exchange", "country"]]
print(sample)
```

Output:

| symbol | name | exchange | country |
|---|---|---|---|
| BRK.B | Berkshire Hathaway Inc. Class B | ASE | United States |
| BF.B  | Brown-Forman Corp. Class B      | ASE | United States |
| ARX   | Aeolus Pharmaceuticals          | ASE | Cayman Islands |
| ALH   | …                               | ASE | United States |

Cross-check via `yfinance`:

```python
import yfinance as yf
for sym in ["BRK-B", "BF-B", "ARX", "ALH"]:
    info = yf.Ticker(sym).info
    print(sym, info.get("exchange"), info.get("fullExchangeName"))
```

Output:

```
BRK-B NYQ NYSE
BF-B  NYQ NYSE
ARX   NYQ NYSE
ALH   NYQ NYSE
```

All four are NYSE main board listings, not NYSE American.

## Why this matte
```

### [E28] #162 [BUG] Economics Module HTTP Error 403 [closed]
ref: `issue#162` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/162` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/162

```
state: closed · comments: 3 · updated: 2024-12-12T18:13:04Z

Hi,

There seems to be a problem with the Economics module connecting to a website to scrap for data.  I have included minimal code needed to reproduce the error, the version of modules on my system, the python version, and OS version.   Please let me know if there is anything else I should include.

Minimal code needed to reproduce:

"
from financetoolkit import Economics
cls_economics = Economics(start_date = "2017-01-01", \
end_date = "2018-01-01", quarterly = True)
cls_economics.get_gross_domestic_product_growth(quarterly = True)
"

Error:
"
Traceback (most recent call last):
  File "C:\Users\jamie\Desktop\Personal\Finance\Stock_Picker\testBrokenEco.py", line 5, in <module>
    cls_economics.get_gross_domestic_product_growth(quarterly = True)
  File "C:\Users\jamie\AppData\Local\Programs\Python\Python312\Lib\site-packages\financetoolkit\economics\economics_controller.py", line 192, in get_gross_domestic_product_growth
    growth_gdp = oecd_model.get_quarterly_gross_domestic_product(
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\jamie\AppData\Local\Programs\Python\Python312\Lib\site-packages\financetoolkit\economics\oecd_model.py", line 272, 
```

### [E29] #36 TypeError: unsupported operand type(s) for |: 'type' and 'types.GenericAlias' [closed]
ref: `issue#36` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/36` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/36

```
state: closed · comments: 4 · updated: 2023-06-11T10:02:48Z

**What's the feature that should be improved?**
example 1: TypeError: unsupported operand type(s) for |: 'type' and 'types.GenericAlias'

**Describe how you would like the feature improved**
![image](https://github.com/JerBouma/FinanceToolkit/assets/20447334/8719ce7e-58df-4462-92da-c853c270c62c)

**Possibly describe the ideal way to improve this**
If you have thought about how you would do it, add it here.

**Additional information**
pip list
asttokens          2.2.1
backcall           0.2.0
colorama           0.4.6
comm               0.1.3
debugpy            1.6.7
decorator          5.1.1
executing          1.2.0
financedatabase    2.1.0
financetoolkit     1.0.0
importlib-metadata 6.6.0
ipykernel          6.23.1
ipython            8.14.0
jedi               0.18.2
jupyter_client     8.2.0
jupyter_core       5.3.0
matplotlib-inline  0.1.6
nest-asyncio       1.5.6
numpy              1.24.3
packaging          23.1
pandas             2.0.2
parso              0.8.3
pickleshare        0.7.5
pip                23.1.2
platformdirs       3.5.1
prompt-toolkit     3.0.38
psutil             5.9.5
pure-eval          0.2.2
Pygments           2.15.1
python-dateutil    2.8.2
pytz               202
```

### [E30] #38 [IMPROVE] Make it more robust when there is no data available for a ticker [closed]
ref: `issue#38` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/38` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/38

```
state: closed · comments: 0 · updated: 2023-07-20T09:25:05Z

The default source, FinancialModelingPrep, doesn't really support international exchanges. E.g. WIPRO.BO won't work but the American ticker name WIT works fine, see https://github.com/JerBouma/FinanceDatabase/discussions/43#discussioncomment-6374547. The error received is `KeyError: "['symbol'] not found in axis"` which is not a very clear error (this just means there is no data). This needs to be catched and patched.
```

### [E31] #45 [FR] Multiple criteria while searching [closed]
ref: `issue#45` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/45` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/45

```
state: closed · comments: 2 · updated: 2023-08-24T16:07:15Z

Hi,

Thanks for the project! I was wondering whether or not it would be a good idea to add support for multiple parameters when performing a search function. Currently, this could certainly be performed by joining multiple data frames that are returned via the search function or just by querying the entire dump at once and filter it by ourselves. But I think it would be more convenient if this feature is built in to the function? 

For example, to filter for both Large Cap & Mid Cap tech listed in NASDAQ it could be something like: 

`equities.search(country='United States', sector='Tech', market='NASDAQ', market_cap=['Large Cap', 'Mid Cap'])`

Or perhaps there is already something available, if so I apologise.
```

### [E32] #6 industry field anomalies [closed]
ref: `issue#6` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/6` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/6

```
state: closed · comments: 2 · updated: 2021-02-21T10:42:32Z

https://github.com/JerBouma/FinanceDatabase/raw/master/Database/Equities/Countries/United%20States/United%20States.json

"industry" field contains the following anomaly:
```

"Banks\u2014Diversified",
"Banks\u2014Regional",
"Beverages\u2014Brewers",
"Beverages\u2014Non-Alcoholic",
"Beverages\u2014Wineries & Distilleries",

"Drug Manufacturers\u2014General",
"Drug Manufacturers\u2014Specialty & Generic",
"Insurance\u2014Diversified",
"Insurance\u2014Life",
"Insurance\u2014Property & Casualty",
"Insurance\u2014Reinsurance",
"Insurance\u2014Specialty",
"Real Estate\u2014Development",
"Real Estate\u2014Diversified",

```

these could use some normalization
"Aerospace & Defense",
"Aerospace/Defense - Major Diversified",
"Aerospace/Defense Products & Services",

It's a lot faster to work on offline database, cheers!
```

### [E33] #7 No module named 'requests' [closed]
ref: `issue#7` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/7` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/7

```
state: closed · comments: 2 · updated: 2021-03-29T17:33:08Z

After pip installing FinanceDatabase I attempt to import it in my python file, but I get this error: Traceback (most recent call last):
  File "/Users/usrname/PycharmProjects/stockScreener/main.py", line 1, in <module>
    import FinanceDatabase as fd
  File "/Users/usrname/.virtualenvs/stockScreener/lib/python3.8/site-packages/FinanceDatabase/__init__.py", line 2, in <module>
    from .json_picker import select_cryptocurrencies
  File "/Users/usrname/.virtualenvs/stockScreener/lib/python3.8/site-packages/FinanceDatabase/json_picker.py", line 1, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
```

### [E34] #78 [IMPROVE] Please remove the unused dependency 'financedatabase' [closed]
ref: `issue#78` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/78` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/78

```
state: closed · comments: 7 · updated: 2023-11-08T09:49:42Z

[here](https://github.com/JerBouma/FinanceToolkit/blob/main/pyproject.toml#L44)

It is never imported.
On the other hand, financedatabase uses FinanceToolkit, so that the dependency goes the other way.
```

### [E35] #78 [DATA] How can we contribute ISIN codes ? [open]
ref: `issue#78` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/78` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/78

```
state: open · comments: 2 · updated: 2024-04-23T11:54:12Z

Hi,

you mention you'd like us to contribute with ISIN codes but how to add them? We could theoretically add a column but problem is that a single ticker can have multiple ISINs so that would create multiple columns or duplicate rows of the same ticker with different ISINs.

Thanks for your work!

PS: don't know if that can be relevant but I have an Excel file that, through powerquery, given a ticker, downloads all the historical values from yahoo finance. Problem is that now if the number of rows (tickers) changes, the query requires updating. I'm working on making it work on an array (to have it work no matter how many tickers, as any ticker is an iteration of the same cycle querying yahoo finance). The mix of your DB and this could create a very nice DB !

PPS: if you want to explore yourself here's the syntax:
https://query1.finance.yahoo.com/v7/finance/download/"&Ticker&"?period1=1214956800&period2=20037888000 where : 
- "&Ticker&" is the ticker (who would have guessed?!)
- period1= start date in UNIX format
- period2= end date in UNIX format
this will return a nice csv file with the following columns:
- Date
- Open
- High
- Low
- Close
- Adj Close
- Volume
- Ticker
```

### [E36] #80 Significant time delays in get_historical_data() [closed]
ref: `issue#80` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/80` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/80

```
state: closed · comments: 9 · updated: 2023-12-18T23:43:30Z

Hi,

I am having significant speed issues when running the get_historical_data() function.
The Toolkit works fine but running the above even for three stocks, takes ~135 seconds. Running for 100 takes 200 seconds. If I run for a large amount of stocks (say the 9500 or so of the large, mid and small cap stocks in the financedatabase module) the code always crashes and I get a long list of exception errors in multiple threads.

I ran CProfile, and no specific line of code seems to cause the backlog (tottime all < 0.001).

Does anyone have any idea on how to what could be the cause of this and stop errors from occurring when running for large numbers of stocks? Code snippet below:

`companies = Toolkit(
    tickers=ticker_list,
    start_date = date,
    api_key="xxxxxx",
)

hist_data = companies.get_historical_data()`
```

### [E37] #88 [FR] Present value of growth opportunities [closed]
ref: `issue#88` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/88` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/88

```
state: closed · comments: 17 · updated: 2024-01-05T15:26:30Z

**What's the problem of not having this feature?**
No specific problem, just seems as a useful ratio to have.

**Describe the solution you would like**
A simple PVGO ratio available for everyone.

**Describe alternatives you've considered**
Custom Ratios

**Additional information**
Wikipedia page:
https://en.wikipedia.org/wiki/Present_value_of_growth_opportunities
```

### [E38] #9 Error by:  core_selection = fd.select_etfs("core_selection_degiro_filtered")  [closed]
ref: `issue#9` · loc: `https://github.com/JerBouma/FinanceDatabase/issues/9` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/issues/9

```
state: closed · comments: 6 · updated: 2021-06-14T15:22:09Z

Hi,

As I run the code:
...
core_selection = fd.select_etfs("core_selection_degiro_filtered")
...
I got error as follow:
`JSONDecodeError                           Traceback (most recent call last)
~\anaconda3\lib\site-packages\FinanceDatabase\json_picker.py in select_etfs(category)
    105             request = requests.get(json_file)
--> 106             json_data = json.loads(request.text)
    107         except json.decoder.JSONDecodeError:

~\anaconda3\lib\json\__init__.py in loads(s, encoding, cls, object_hook, parse_float, parse_int, parse_constant, object_pairs_hook, **kw)
    347             parse_constant is None and object_pairs_hook is None and not kw):
--> 348         return _default_decoder.decode(s)
    349     if cls is None:

~\anaconda3\lib\json\decoder.py in decode(self, s, _w)
    339         if end != len(s):
--> 340             raise JSONDecodeError("Extra data", s, end)
    341         return obj

JSONDecodeError: Extra data: line 1 column 4 (char 3)

During handling of the above exception, another exception occurred:

ValueError                                Traceback (most recent call last)
<ipython-input-17-bb6bc10717f4> in <module>
----> 1 core_selection 
```

### [E39] #91 [IMPROVE] piotroski stock criteria [closed]
ref: `issue#91` · loc: `https://github.com/JerBouma/FinanceToolkit/issues/91` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/issues/91

```
state: closed · comments: 2 · updated: 2024-01-01T22:39:43Z

this seems backward

(https://github.com/JerBouma/FinanceToolkit/blob/b39fa9e111d464a6bff645c0e84eda1bea541baf/financetoolkit/models/piotroski_model.py#L278)
```

## Pull / Merge Requests (prior art)

### [E40] #115 Backfill a few missing columns in equities.csv [closed]
ref: `pr#115` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/115` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/115

```
state: closed · comments: 1 · updated: 2026-05-29T20:57:47Z

Wrote a quick script to backfill any missing columns in equities.csv. The script will keep any existing values, with the exception of market_cap. market_cap tended to be stale in several entries I looked at. The market_cap recomputation matches the update logic: https://github.com/JerBouma/FinanceDatabase/blob/main/.github/workflows/database_update.yml#L61-L77

The end goal of the script is to add missing any ISIN as it is keyed off of those.

This PR contains only a small amount of changes to confirm the expected behavior and the desirability of running this further.
```

### [E41] #134 Rename outdated market label "NYSE MKT" to "NYSE American" for exchange=ASE securities [draft]
ref: `pr#134` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/134` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/134

```
state: draft · comments: 0 · updated: 2026-05-11T18:29:56Z

"NYSE MKT" was NYSE American's branding from 2012–2017; the exchange has since reverted to "NYSE American". All 1,617 `exchange=ASE` rows in `equities.csv` carried this stale label, creating ambiguity for consumers mapping against ISO 10383 (where "ASE" also collides with the Athens Stock Exchange acronym).

## Changes

- **`database/equities.csv`** — `market` column: `"NYSE MKT"` → `"NYSE American"` for all 1,617 `exchange=ASE` rows
- **`compression/equities.bz2`** — regenerated to match updated CSV
- **`README.md`** — updated inline example using `"NYSE MKT"` as a market filter
- **`examples/FInance Database - 1. Getting Started.ipynb`** — updated three output cells referencing `"NYSE MKT"`

> Note: `"NYSE MKT"` references in `database/etfs.csv` are within fund **description text** (verbatim from prospectuses), not classification columns — left unchanged intentionally.

## Usage

```python
import financedatabase as fd
eq = fd.Equities()

# Before: market="NYSE MKT"
# After:
eq.select(market="NYSE American")
```
```

### [E42] #136 Added some missing currencies and names from SEC Data [closed]
ref: `pr#136` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/136` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/136

```
state: closed · comments: 2 · updated: 2026-05-13T16:39:47Z

Added a new parser to conservatively add missing currency (USD only) and names for equities, efts, funds, and moneymarket. Source data: exclusively SEC. 

> The controller is intentionally conservative. It prefers a smaller number of high-confidence updates over broad coverage, because US tickers can be reused after a security is delisted. When a row already has stronger identifiers such as `isin`, `cusip`, `figi`, `composite_figi`, or `shareclass_figi`, the controller will not auto-apply a ticker-only SEC match unless SEC-side identifiers corroborate the row.

Applied high confidence matches only. 

```bash
SEC_USER_AGENT="FinanceDatabase your-email@example.com" \
python parsers/sec_enrichment_controller.py
```

Run the above and review the dry run report for other potential matches; for this PR I only merged high confidence. 

GPT5.5 wrote the python; I reviewed all of the diffs to ensure they were targeted and look correct. (I did not exhaustively review the python but did skim it.)

There are a few oddballs in moneymaket where there is no issuer. But the fund is delisted, the name was empty before, and I didn't want to include data from other than SEC (Bloomberg tells me these 
```

### [E43] #138 Backfill ~4.5k CUSIP values in equities.csv from SEC 13F filings [closed]
ref: `pr#138` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/138` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/138

```
state: closed · comments: 3 · updated: 2026-05-17T18:10:44Z

## Summary

Populated the `cusip` column for **4,479** equity rows in `database/equities.csv` that had a matching `symbol` but no CUSIP. This brings FD's CUSIP coverage from ~2.5k to ~7k populated rows (~+180%).

## Data source & attribution

CUSIPs were extracted from **SEC EDGAR 13F-HR quarterly filings** as part of the [hedge-fund-tracker](https://github.com/dokson/hedge-fund-tracker) project, which maintains a `CUSIP → Ticker → Company` mapping built from real institutional holdings disclosures. CUSIPs reported in 13F filings are the SEC-canonical identifier for each security, so the source data is authoritative for the US securities universe.

## Gating (to avoid misattribution)

A naïve `ticker` join produces ~600 wrong matches (e.g. ticker `AC` would attach Air Canada's CUSIP to "Associated Capital Group" because FD's row for `AC` is the latter). The following gates were applied:

1. CUSIP regex `^[0-9A-Z]{9}$`
2. CUSIP Modulus-10 Double-Add-Double check digit
3. Skip rows where FD already has a `cusip` value
4. Skip ambiguous tickers (multiple empty-cusip rows for the same symbol)
5. Company-name similarity ≥ 0.7 between source `Company` and FD `name`, after normalisation (
```

### [E44] #140 Baseline test improvements: snapshots, local data, docstrings, infra cleanup [closed]
ref: `pr#140` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/140` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/140

```
state: closed · comments: 1 · updated: 2026-05-19T06:45:05Z

## Summary

A baseline cleanup of the test suite so future data and code PRs are easier to develop, review, and triage. All changes live in `tests/` (plus a one-character typo fix in `database/etfs.csv` that surfaced while validating the new local-data setup). **All 32 tests pass; black + pyright clean.**

Three structural problems were addressed, each motivating one of the commit's logical pieces:

1. **CI was testing `main`, not the PR.** The library defaults to `use_local_location=False`, fetching `compression/*` over HTTP from the `main` branch. Tests on a PR therefore validated `main`'s data instead of the PR's. Result: data-breaking PRs passed silently, data-fixing PRs (like #143) showed red CI for changes already correct on disk.
2. **Snapshot diffs were unreadable.** JSON snapshots were single-line 1–2 KB strings; CSV mismatch failures truncated both sides at 500 chars and often appeared identical in the visible window (we hit this on #141 and #143). There was no usable signal in the failure message.
3. **The test runner had hidden lint debt.** `# pylint: skip-file` in `conftest.py` masked real type issues; markers (`record_stdout`) were not declared; module docstrings were
```

### [E45] #142 Replace 725 boilerplate summaries with yfinance longBusinessSummary [closed]
ref: `pr#142` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/142` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/142

```
state: closed · comments: 1 · updated: 2026-05-18T22:07:17Z

## Summary

Follow-up to #141 (placeholder names). On the 1,084 rows where #141 fixed the junk `name` field, the `summary` column still carried boilerplate text like:

> *"two is a blank check company. The company was incorporated in 2021 and is based in San Francisco, California."*

This PR replaces those summaries with the real `longBusinessSummary` from yfinance for the same ticker, addressing @JerBouma's feedback on #141.

| Outcome | Count |
|---|---:|
| Summaries replaced with yfinance `longBusinessSummary` | **725** |
| yfinance had no usable summary — kept as-is | 359 |

359 rows have no recoverable summary on yfinance (mostly delisted tickers or thinly-covered exotic exchanges). They keep their boilerplate text and are best handled in a future LLM-based rewrite as you suggested.

## Example (before → after)

**`8439.T`** (Tokyo Century Corp., Tokyo Stock Exchange)

Before:
> *two is a blank check company. The company was incorporated in 2021 and is based in San Francisco, California.*

After:
> *Tokyo Century Corporation, together with its subsidiaries, engages in domestic leasing, automobile, specialty financing, international business, and other businesses in Japan and i
```

### [E46] #146 Test infra follow-ups #2: library invariants, helpers.py coverage 45→86%, cov in CI [closed]
ref: `pr#146` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/146` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/146

```
state: closed · comments: 0 · updated: 2026-05-19T08:15:49Z

## Summary

Closes the test-infra follow-ups deferred in #140. Five logically-distinct improvements bundled because they all touch `tests/` together and share the same audit pass (`pytest --cov=financedatabase --cov-report=term-missing`).

**Coverage 78% → 92%. Tests 32 → 49.** No snapshot file modified — only test code, config, and the workflow step.

| Improvement | Files |
|---|---|
| 1. `test_exchange_market_one_to_one` uses the library | `tests/test_equities.py` |
| 2. Cover the `helpers.py` 45% → 86% gap (+ asset-class invalid-value tests) | `tests/test_*.py` |
| 3. Behavioural smoke asserts in every `test_select` | all 7 asset-class test files |
| 4. Coverage reporting in CI | `.github/workflows/testing.yml` |
| 5. Deferred items called out explicitly (xdist, parametrize) | — |

## 1. `test_exchange_market_one_to_one` now uses the library

After #140, the library reads local data (`use_local_location=True`) and the conftest regenerates compression artifacts from `database/*.csv` at import time, so `equities.select()` is in sync with the checked-out source of truth for the test session. The previous `pd.read_csv("database/equities.csv")` workaround is no longer needed:

```di
```

### [E47] #147 ETFs/Funds data quality + cross-asset invariants + equities country/ISIN backfill + SPAC cleanup + README stats [closed]
ref: `pr#147` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/147` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/147

```
state: closed · comments: 9 · updated: 2026-05-29T17:18:21Z

## Summary

Two-commit data-quality + invariants PR. Started narrow (`etfs.csv` cleanup + README automation) and grew as deeper auditing surfaced two further contamination layers in `equities.csv`.

**Commit 1** — ETFs/Funds data quality + cross-asset invariants + country backfill + README stats
**Commit 2** — equities.csv ISIN cleanup + SPAC template removal + name canonicalization

What's in:

1. **`etfs.csv` data quality** — 100 rows cleaned (14 non-ETFs already in `equities.csv`, 56 cross-asset symbol collisions, 29 corrupted `exchange` values, FSST completed from all-NaN). After cleanup `equities.csv` / `etfs.csv` / `funds.csv` / `indices.csv` share **zero** symbols.
2. **Cross-asset invariants in CI** — `tests/test_invariants.py` with two tests:
   - `test_no_symbol_collisions_across_asset_classes` — symbol belongs to at most one of the 7 asset class files
   - `test_no_isin_collisions_across_asset_classes` — ISIN belongs to at most one of `equities.csv`/`etfs.csv` (the only two files that track ISIN)
3. **Country backfill on `equities.csv`** — **50.3% → 71.6%** using HQ-country semantics (per your earlier review). 35,118 rows filled across 7 sources.
4. **ISIN backfill + cle
```

### [E48] #149 Add mic_code (ISO 10383 MIC) column [closed]
ref: `pr#149` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/149` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/149

```
state: closed · comments: 9 · updated: 2026-05-29T20:57:47Z

Closes #110.

Adds a standardised **ISO 10383 MIC code** for each ticker, as requested in the issue, by mapping the existing Yahoo `exchange` code to its MIC.

## Data
- New `mic_code` column (placed right after `exchange`) in `equities`, `etfs`, `funds` and `indices`.
- Every Yahoo exchange code that corresponds to a real trading venue is mapped to its **operating MIC** (e.g. `NMS/NGM/NCM → XNAS`, `NYQ → XNYS`, `LSE/IOB → XLON`, `GER → XETR`, `JPX → XJPX`).
- All mapped MICs were validated as **ACTIVE** against the official ISO 10383 registry, with the ISO country code cross-checked against the data.
- Pseudo-codes that are not trading venues (indices, FX, crypto, NAV mutual funds) and venue-ambiguous codes (e.g. `ENX`, generic Euronext) are intentionally left **blank** rather than guessed.
- Spot-checked end-to-end on well-known tickers (AAPL→XNAS, JPM→XNYS, VOD.L→XLON, SAP.DE→XETR, 7203.T→XJPX, NESN.SW→XSWX, 005930.KS→XKRX, …).

## Package
- `mic_code` added as a filter to `select()` and as an option in `show_options()` for every asset class.
- The duplicated validate-and-filter blocks were refactored into a single shared helper (`FinanceDatabase._filter_by_options`) with a cent
```

### [E49] #195 Add comprehensive Kubernetes and container deployment documentation [draft]
ref: `pr#195` · loc: `https://github.com/JerBouma/FinanceToolkit/pull/195` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/pull/195

```
state: draft · comments: 0 · updated: 2026-05-29T21:00:15Z

## Overview

This PR addresses the community question about recommendations for running FinanceToolkit in Kubernetes by adding comprehensive deployment documentation.

## Changes

### New Documentation: `DEPLOYMENT.md`

Created a complete deployment guide (526 lines) that provides production-ready guidance for containerizing and orchestrating applications that use the FinanceToolkit. The guide includes:

**Docker Containerization**
- Complete Dockerfile example optimized for Python 3.10+
- Dependencies management and best practices
- Environment variable configuration for API keys

**Kubernetes Deployment Patterns**
- Basic Deployment configuration with resource limits and requests
- CronJob pattern for scheduled financial analysis tasks
- Service configuration for exposing REST APIs
- Horizontal Pod Autoscaler (HPA) for automatic scaling

**Best Practices**
- Resource management guidelines (memory and CPU allocation)
- API rate limiting strategies and caching with persistent volumes
- Security best practices:
  - Kubernetes Secrets for API key management
  - RBAC considerations
  - Network policies for egress control
- Monitoring and logging configurations
- Health check implement
```

### [E50] #200 Use approximate float comparison for JSON test records [closed]
ref: `pr#200` · loc: `https://github.com/JerBouma/FinanceToolkit/pull/200` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/pull/200

```
state: closed · comments: 0 · updated: 2026-03-13T15:05:26Z

Fixes #196.

Python's shortest-repr float formatting varies across versions (and platforms), which causes the test recorder to detect spurious changes in JSON fixture files. For example, a value recorded as `0.011710000000000002` may serialize as `0.01171` in a newer environment -- both represent the same IEEE 754 double, just with different string representations.

**What changed:**

In `tests/conftest.py`, the `Record` class now falls back to `math.isclose` (relative tolerance 1e-9) when comparing JSON record files whose string representations differ. The exact-match fast path is tried first, so there is zero overhead when strings already match. Non-JSON records (CSV, txt) are unaffected.

**How it works:**

- `_values_approx_equal` recursively walks two JSON-parsed structures, using `math.isclose` for float-to-float pairs and strict equality for everything else (ints, strings, bools, nulls, structure/length).
- `_json_strings_approx_equal` wraps the above with `json.loads` and catches decode errors (falling back to exact comparison).
- `record_changed` checks the file extension and only uses the approximate path for `.json` records.

No recorded fixtures were changed. No new dep
```

### [E51] #210 Add optional Adanos sentiment to Toolkit [open]
ref: `pr#210` · loc: `https://github.com/JerBouma/FinanceToolkit/pull/210` · score: 1
url: https://github.com/JerBouma/FinanceToolkit/pull/210

```
state: open · comments: 5 · updated: 2026-04-30T08:41:45Z

## Summary
- add optional Adanos market sentiment as a native `Toolkit.get_sentiment(...)` method
- back the Toolkit method with a dedicated `financetoolkit/sentiment_model.py` model module
- use the Toolkit tickers plus configured `start_date` and `end_date` when collecting sentiment
- remove the previous external dataset helper/example approach

## Validation
- `uv run python -m pytest tests/test_sentiment_model.py tests/test_toolkit_sentiment.py -q`
- `uv run ruff check financetoolkit/sentiment_model.py financetoolkit/toolkit_controller.py tests/test_sentiment_model.py tests/test_toolkit_sentiment.py`
- `uv run ruff format --check financetoolkit/sentiment_model.py tests/test_sentiment_model.py tests/test_toolkit_sentiment.py`
- `python3 -m py_compile financetoolkit/sentiment_model.py financetoolkit/toolkit_controller.py tests/test_sentiment_model.py tests/test_toolkit_sentiment.py`
- `git diff --cached --check`
```

### [E52] #2430 Incorporate curl_cffi to avoid rate limiting and cookie errors [closed]
ref: `pr#2430` · loc: `https://github.com/ranaroussi/yfinance/pull/2430` · score: 1
url: https://github.com/ranaroussi/yfinance/pull/2430

```
state: closed · comments: 5 · updated: 2025-05-06T13:30:30Z

~**Don't merge this!**~

~This is just a temporary workaround to allow yfinance to work if using an impersonated session from curl_cffi. Probably is better to actually incorporate curl_cffi into yfinance itself rather than require the session to be passed in to all requests, but this works for now.~

Made the change myself to use curl_cffi by default. Tested by downloading some data and appears to work locally.
```

### [E53] #2845 Determine login and subscription tier via the subscriptions API [closed]
ref: `pr#2845` · loc: `https://github.com/ranaroussi/yfinance/pull/2845` · score: 1
url: https://github.com/ranaroussi/yfinance/pull/2845

```
state: closed · comments: 10 · updated: 2026-06-09T17:41:47Z

Auth.check_login() parsed the finance.yahoo.com homepage for a 'nimbus-benji-config' element, which Yahoo builds client-side and is absent from the fetched HTML, so it always returned False even when logged in. Query the OBI subscriptions endpoint instead (/ws/obi-integration/v1/subscriptions): a lightweight JSON request (Yahoo rate-limits scraping of its large consumer web pages far more aggressively than its JSON APIs) where HTTP 200 with a guid means logged in and 401 means not.

Also add Auth.subscription_tier() -> 'gold'|'silver'|'bronze'|'free'|None, with the tier inferred from granted feature flags (stable across Yahoo's non-contiguous tier numbering). Auth.user returns {'guid': ...}.

The check is made live on each call rather than cached: the endpoint is cheap and not rate-limited at realistic volumes, so a fresh call keeps the answer correct after a runtime login/upgrade/expiry and lets the caller swap login cookies mid-process.

Add an allow_strategy_switch flag to YfData.get/_make_request; the login probe passes False so an expected 401 does not trigger the cookie-strategy toggle (which clears the session cookies, wiping T/Y). set_login_cookies() now also clears the cac
```

### [E54] #2883 Guard _fetch_sec_filings and _fetch_calendar against null/empty Yahoo results [open]
ref: `pr#2883` · loc: `https://github.com/ranaroussi/yfinance/pull/2883` · score: 1
url: https://github.com/ranaroussi/yfinance/pull/2883

```
state: open · comments: 2 · updated: 2026-07-06T04:10:28Z

### Problem
`_fetch_sec_filings` runs `filings = result["quoteSummary"]["result"][0]["secFilings"]["filings"]` immediately after the `if result is None: return None` guard. When Yahoo returns a **non-None** payload whose `quoteSummary.result` is `null`/empty (or is missing the `secFilings` key), this crashes with `TypeError: 'NoneType' object is not subscriptable` (or `KeyError`/`IndexError`).

`_fetch_calendar` has the same class of gap: its parse block only catches `(KeyError, IndexError)`, so a `null` nested structure raises an uncaught `TypeError`.

### Fix
- `_fetch_sec_filings`: wrap the nested lookup in `try/except (KeyError, IndexError, TypeError)` and return `None` — graceful degradation, consistent with the existing `result is None` guard.
- `_fetch_calendar`: add `TypeError` to the existing `except` tuple.

### Tests
Adds network-free regression tests (mocking `Quote._fetch`) in `tests/test_ticker.py`:
- `test_sec_filings_null_result` — a `null` result degrades to `None` instead of crashing
- `test_sec_filings_happy_path` — a valid payload still parses correctly
- `test_calendar_null_result` — a `null` result raises a clean `YFDataException`

Verified red→green: `test_se
```

### [E55] #31 Refactored Equities [closed]
ref: `pr#31` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/31` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/31

```
state: closed · comments: 7 · updated: 2023-02-15T20:20:28Z

(no description)
```

### [E56] #91 fix: updated FISV ticker to FI which is the new name [closed]
ref: `pr#91` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/91` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/91

```
state: closed · comments: 6 · updated: 2025-02-28T15:33:46Z

Corrected the ticker name for Fiserv.  Also needed to update Frank's International to their new ticker XPRO.
```

### [E57] #94 fix: added 2 canadian companies [closed]
ref: `pr#94` · loc: `https://github.com/JerBouma/FinanceDatabase/pull/94` · score: 1
url: https://github.com/JerBouma/FinanceDatabase/pull/94

```
state: closed · comments: 3 · updated: 2025-03-01T22:37:04Z

Added 2 missing Canadian Companies
```

## Retrieval notes

- Market discovery via none.
- No keyless engine returned results. Use your built-in WebSearch to find URLs, then ground them with `construct web --url <url> --out <run>`.
- Only the first 3 of 13 candidate technologies were grounded; skipped: financetoolkit (150+ transparent ratios, Piotroski F-Score, Altman Z-Score; enforce_source YahooFinance), financedatabase (universe: 160,995 equities, Yahoo-suffixed symbols), yfinance 1.x (curl_cffi default; per-ticker fundamentals ~4y annual / 4-5 quarters), FastAPI + uvicorn (HTTP API serving screens, presets, company detail, CSV export, and the built SPA), Typer (CLI: crible screen/ingest/status/export), React 18 + Vite + TypeScript SPA with TanStack Table (filterable/sortable results grid), Docker Compose (ingest service + api service, healthchecks, shared volume), pytest (TDD, FR-tagged tests), xbrl-JSON from filings.xbrl.org JSON-API (ESEF audited EU annual figures, keyless), Stooq CSV endpoints (keyless worldwide EOD price fallback). Drill them with `construct tech --out <run> --q "<tech>"`.
- Grounded 16 docs URL(s) passed via --docs-url.
- Docs discovery for "Python 3.12 (ingestion, compute, API)" via duckduckgo.
- Docs discovery for "DuckDB (embedded columnar query engine over Parquet)" via duckduckgo.
- Docs discovery for "Apache Parquet + pyarrow (versioned raw and snapshot layers)" via duckduckgo.
- No StackOverflow questions matched.
- No StackOverflow questions matched.
- No StackOverflow questions matched.

## Market — competitive web evidence

### [E58] Web — https://simplywall.st/
ref: `https://simplywall.st/` · loc: `https://simplywall.st/#~126` · score: 4
url: https://simplywall.st/

```
Anonymous Customer
United Kingdom
Best informative site for Value based investing
Fantastic coverage of global stocks. Their layout is super user friendly, simple yet effective enough to give you all the right info needed for value investing. Portfolio and watchlist features are excellent. Best feature is the snowflake analysis with screener.
They also send the articles and timely updates that cut through any jargon and provide very insightful information that layman like me can understand. Very happy to have found Simply Wall St.
Ricci Johannessen
South Africa
Simply Wall St is packed with loads of tools and info. As a beginner I am extremely excited to get stuck in. I know Simply Wall St will help me manage and improve the quality of my portfolio and watchlist.
Rajan
Australia
Glad to be able to subscribe to your premium plan. It’s a useful product particularly for the novice trader to get a good heads up on building up an investment portfolio. Pleasure dealing with the staff as well. Excellent value
Gary
United Kingdom
Seems to have a multitude of info, but broken down and explained simply enough for the amateur investor, yet intuitive enough for the more seasoned investor.
Very easy to keep track of your portfolio, and keeps providing important updates when there's a significant alert on stocks... Only downside, no info on funds, that I can find.
```

### [E59] Web — https://www.unclestock.com/
ref: `https://www.unclestock.com/` · loc: `https://www.unclestock.com/#~1` · score: 4
url: https://www.unclestock.com/

```
Uncle Stock - Fundamental Stock Screener
Home
Tutorial
Documentation
Pricing
Articles
Professional stock screening for DIY investors.
100,000 companies. 2,000+ metrics. Your strategy, your decisions. For $20/month.
100,000+ stocks from nano-cap to large-cap
2,000+ metrics with 30 years of historical data
Expert models from Buffett, Graham, Lynch
Built-in backtesting and smart alerts
```

### [E60] Web — https://www.unclestock.com/ (lines 55–69)
ref: `https://www.unclestock.com/` · loc: `https://www.unclestock.com/#~55` · score: 4
url: https://www.unclestock.com/

```
With a vast range of ratios, backtesting abilities and active user support. I strongly recommend Uncle Stock to everyone!
Christophe H. - Belgium
&ldquo;Thank you for your site.
It is the best stock screener ever made, for combining fundamental and technical analysis at the same time.
Morten VH. - Denmark
&ldquo;Thank you for all you are doing with this website.
It is pretty incredible and I think one of the best stock screeners on the internet.
Charles H. - Taiwan
&ldquo;I do love the site and all of the information that it provides. There are a lot of features which are very useful.
The ability to research the vast array of metrics available for a comparison / scrutiny of a stock all in once place without needing to perform your own calculations is invaluable.
Derek H. - UK
&ldquo;I subscribe to maybe 8 different programs like this. I have spent
thousands. All a waste of time as I only use your program. They all cost
the same as yours abs all have 1-100th the capability. Your product really
is democratising investing. There is simply no other way for part time or
```

### [E61] Web — https://eodhd.com/pricing
ref: `https://eodhd.com/pricing` · loc: `https://eodhd.com/pricing#~102` · score: 3
url: https://eodhd.com/pricing

```
List of traded tickers
Exchange Trading Hours
Fundamental Data
Stock Fundamentals
ETF Fundamentals
Mutual Funds Fundamentals
Earnings Per Share
Insider Transactions
Economic Events Data API
Macroeconomic Data API
40.000 stock market logos
Additional Packages
Corporate Events Calendar API
Financial News Feed API
Extended Fundamentals
```

### [E62] Web — https://eodhd.com/pricing (lines 331–345)
ref: `https://eodhd.com/pricing` · loc: `https://eodhd.com/pricing#~331` · score: 3
url: https://eodhd.com/pricing

```
€
299
/year
The largest collection of 40 000 stock market company logos is available via one API endpoint. The collection covers 60+ exchanges worldwide, consists of 200x200px PNG files with transparency.
Sign up & Pay
Learn more
Stock Market Logos API (SVG extension)
€
399
/year
The largest collection of 40 000 stock market company logos is available via one API endpoint. The collection covers 60+ exchanges worldwide, consists of 200x200px PNG files with transparency. Plus, access to SVG format logos for US and TO exchanges.
Sign up & Pay
Learn more
Market Status API: Global Equities & Derivatives
€
```

### [E63] Web — https://finviz.com/screener.ashx
ref: `https://finviz.com/screener.ashx` · loc: `https://finviz.com/screener.ashx#~83` · score: 3
url: https://finviz.com/screener.ashx

```
Theme
Any Aging Population & Longevity Agriculture & FoodTech Artificial Intelligence Autonomous Systems Big Data Biometrics Cloud Computing Commodities - Agriculture Commodities - Energy Commodities - Metals Consumer Goods Crypto & Blockchain Cybersecurity Defense & Aerospace Digital Entertainment E-commerce Education Technology Electric Vehicles Energy - Renewable Energy - Traditional Environmental Sustainability FinTech Hardware Healthcare & Biotech Healthy Food & Nutrition Industrial Automation Internet of Things Nanotechnology Quantum Computing Real Estate & REITs Robotics Semiconductors Smart Home Social Media Software Space Tech Telecommunications Transportation & Logistics Virtual & Augmented Reality Wearables Custom (Elite only)
Sub-theme
Any Agriculture - Alternative Proteins Agriculture - Agricultural Inputs & Crop Science Agriculture - Controlled Environment Agriculture Agriculture - Agri-Food Processing & Distribution Agriculture - Precision Agriculture & Farm Automation AI - Ads, Search & Recommendations AI - AGI, general intelligence AI - Apps, Domain-Specific AI AI - Cloud & Infrastructure AI - Compute & Acceleration AI - Data Infrastructure & Enablement AI - Edge & Embedded Systems AI - Power & Energy Solutions AI - Enterprise Productivity & Software Integration AI - Foundation Models & Platforms AI - Networking & Systems Optimization AI - Robotics & Automation AI - Cybersecurity Automation - Factory & Process Automation Systems Automation - Additive Manufact
```

### [E64] Web — https://simplywall.st/ (lines 1–12)
ref: `https://simplywall.st/` · loc: `https://simplywall.st/#~1` · score: 3
url: https://simplywall.st/

```
Portfolio Tracker & Analysis Dividend Tracker Stock Screener Community Narratives Plans About
Create free account Log in
Plans Log in
Welcome to your
Portfolio Command Center.
Stop wasting hours in spreadsheets and start growing your wealth with portfolio analysis, discovery tools and market alerts — all in one place.
View Portfolio demo Try Simply Wall St free
No credit card required.
One platform. Better decision making.
Stop reacting and start growing with data and insights the pros use.
Master your portfolio.
A high-fidelity view and analysis of your portfolio, bringing together performance, risk, and opportunities into one centralized location.
```

### [E65] Web — https://www.simfin.com/en/prices/
ref: `https://www.simfin.com/en/prices/` · loc: `https://www.simfin.com/en/prices/#~10` · score: 3
url: https://www.simfin.com/en/prices/

```
No billing
Get Started for Free
5,000 US Stocks
Stock Screener
80+ Indicators
High-Speed Access for Backtesting (500 credits)
Line Graphs & Box-Whisker Plots
Backtesting
5 Years Charts History
Data API & Bulk Download
5 Years Fundamentals History
Unlimited Portfolios
Copying, Commenting & Sharing
Start Free
START
```

### [E66] Web — https://www.simfin.com/en/prices/ (lines 176–186)
ref: `https://www.simfin.com/en/prices/` · loc: `https://www.simfin.com/en/prices/#~176` · score: 3
url: https://www.simfin.com/en/prices/

```
Where I can find further information about SimFin?
You can find more answers to typical questions as well as additional tips and video tutorials on how to use the SimFin tools in the support section .
Where does the financial data come from?
The fundamental data about stock companies is provided and owned by SimFin. SimFin aggregates this data directly from the regularly financial reports issued quarterly and yearly. This proprietary advantage enables SimFin users to trace back each data point to the financial statement in the original company report.
How is the quality of the financial data guaranteed?
Each financial statement must go through a QA evaluation process before it is published in the SimFin database. This way, users can be sure that the fundamental data is of the highest accuracy.
What happens if I exceed the monthly limit of High Speed Credits?
You will receive a notification to upgrade to a higher subscription or, if you already have the highest subscription, to purchase additional high speed credits.
Can’t find the right answer above?
Do not worry! Just move on and register for your free account. Things usually become clearer when you try them out.
Get free account
```

### [E67] Web — https://www.stockopedia.com/
ref: `https://www.stockopedia.com/` · loc: `https://www.stockopedia.com/#~106` · score: 3
url: https://www.stockopedia.com/

```
The three reasons your portfolio struggles
Most investors rely on tips, gut feelings, and incomplete information. They lack a systematic approach, leading to emotional decisions and poor results.
Picking story stocks
Falling for compelling narratives and hot tips without rigorous analysis. Following the crowd into overvalued stocks based on hype rather than fundamentals.
75% of low rank stocks lose money *
Unreliable sources
Forums full of rampers, broker research with hidden agendas, news driven by PR, clickbait. Plus it's scattered across the web. Hours wasted, still can't trust the data.
Multiple sites checked per decision
No clear strategy
No framework for what to buy or sell. No proven system - just woolly, unstructured guesswork creating anxiety. Trial and error with hard won, but easily lost, capital.
£1000s lost learning what works
The solution
Finally, a platform built to transform your investing
Stockopedia gives you the data insights, platform and mentorship to level up your investing process. Make decisions based on evidence, not emotions.
1
```

### [E68] Web — https://www.stockopedia.com/ (lines 199–213)
ref: `https://www.stockopedia.com/` · loc: `https://www.stockopedia.com/#~199` · score: 3
url: https://www.stockopedia.com/

```
Every feature is designed to support systematic, emotion-free investing through Drivers, Diversity, and Discipline.
StockRanks™
Our proprietary ranking system that scores stocks 0-100 on Quality, Value & Momentum
Stock Screener
Filter 35,000 global stocks with 350+ metrics to find exactly what you are looking for
Portfolio Analytics
Track performance, risk metrics, and get insights to improve your returns
Stock Reports
Comprehensive one-page reports with all the data you need to make decisions
Education Hub
Learn proven strategies with courses, webinars, and research-backed content
Community
Connect with 10,000+ serious investors sharing ideas and strategies
Daily Comment
Expert editorial insights and market commentary from our team of analysts
```

### [E69] Web — https://financialfilings.com/api-solutions/
ref: `https://financialfilings.com/api-solutions/` · loc: `https://financialfilings.com/api-solutions/#~91` · score: 2
url: https://financialfilings.com/api-solutions/

```
From regulator publication to a record in your stack - the whole pipeline is measured in seconds, not batch windows.
t + 0 s &rarr;
Detected.
Continuous polling of every regulator and exchange in coverage. New filings detected within seconds of publication.
t + 15 s &rarr;
Collected.
Original document fetched, deduplicated against the index, canonical PDF stored with a full audit trail.
t + 60 s &rarr;
Normalised.
Tables, footnotes, headings, and identifiers extracted into one canonical record - JSON, Markdown, and PDF served from it.
t + 90 s
Delivered.
Webhook fires. REST + GraphQL pull, S3 mirror, Snowflake or Databricks shares for bulk consumers.
04 / Code
Try it in two lines.
```

### [E70] Web — https://financialfilings.com/api-solutions/ (lines 136–150)
ref: `https://financialfilings.com/api-solutions/` · loc: `https://financialfilings.com/api-solutions/#~136` · score: 2
url: https://financialfilings.com/api-solutions/

```
Four audience views with sector-specific examples, customer references, and starter templates.
For hedge funds
Alpha generation.
Fundamental signals from filings, normalised to feed quant models without scraper maintenance.
Read more &rarr;
For asset managers
Portfolio screens.
Filing-driven screens that update on the wire. Discretionary teams stop running 24-hours-late.
Read more &rarr;
For analytics platforms
Embedded data layer.
License the index for redistribution. White-label or co-brand the filings layer in your product.
Read more &rarr;
For academic research
Cross-market studies.
```

### [E71] Web — https://finviz.com/screener.ashx (lines 1–14)
ref: `https://finviz.com/screener.ashx` · loc: `https://finviz.com/screener.ashx#~1` · score: 2
url: https://finviz.com/screener.ashx

```
Home
News
Screener
Charts
Maps
Groups
Portfolio
Insider
Futures
Forex
Crypto
Calendar
Pricing
Theme
```

### [E72] Web — https://github.com/financial-reports/financial-reports-mcp-server
ref: `https://github.com/financial-reports/financial-reports-mcp-server` · loc: `https://github.com/financial-reports/financial-reports-mcp-server#~104` · score: 2
url: https://github.com/financial-reports/financial-reports-mcp-server

```
Repository files navigation
FinancialReports MCP Server
Official Model Context Protocol (MCP) server for the FinancialReports API.
Direct access from Claude (and any MCP-compatible client) to regulatory filings, financial data, and corporate information from listed companies worldwide. 15 curated tools by default (set MCP_FULL_SURFACE=1 for the full 42-tool surface). Free for any FinancialReports account. Sourced from official regulators.
Quick start
If you're an analyst, researcher, or anyone who wants to ask Claude about public-company filings:
Create a free account at financialreports.eu — the MCP connector is free for any FinancialReports user. No paid plan required.
Add the connector in your MCP client — pick yours under Connect your client below. The two most common:
Claude.ai / Claude Desktop : Settings → Connectors → Add custom connector → URL: https://mcp.financialfilings.com/mcp
Claude Code : claude mcp add --transport http financialreports https://mcp.financialfilings.com/mcp
Sign in with your FinancialReports account when prompted. That's it.
Full setup walkthrough with screenshots: financialreports.eu/integrations/claude/ .
Connect your client
This is a remote MCP server — Streamable HTTP with OAuth (PKCE + Dynamic Client Registration). There is no API key to copy and no secret to store : connecting opens a browser sign-in with your FinancialReports account.
Endpoint: https://mcp.financialfilings.com/mcp
```

### [E73] Web — https://github.com/financial-reports/financial-reports-mcp-server (lines 331–345)
ref: `https://github.com/financial-reports/financial-reports-mcp-server` · loc: `https://github.com/financial-reports/financial-reports-mcp-server#~331` · score: 2
url: https://github.com/financial-reports/financial-reports-mcp-server

```
Special thanks to @itisaevalex for the original community-built MCP server , which served as the proof-of-concept that motivated this official version.
Built on FastMCP , FastAPI , and the Model Context Protocol .
About
Official Model Context Protocol (MCP) server for the FinancialReports API. Provides LLM-native access to European company filings and financial data.
financialreports.eu/
Topics
finance
trading
mcp
stocks
filing
fundamental-analysis
stocks-api
filings
mcp-server
```

### [E74] Web — https://www.esma.europa.eu/esmas-activities/data/european-single-access-point-esap
ref: `https://www.esma.europa.eu/esmas-activities/data/european-single-access-point-esap` · loc: `https://www.esma.europa.eu/esmas-activities/data/european-single-access-point-esap#~1` · score: 2
url: https://www.esma.europa.eu/esmas-activities/data/european-single-access-point-esap

```
Skip to main content
Search
European Single Access Point (ESAP)
The objective of ESAP is to offer a single access point for public financial and sustainability-related information about EU companies and EU investment products, thereby giving firms more visibility towards EU and international investors and opening up more sources of financing.
Background
Today’s public information on companies and financial products is scattered across many different places (e.g., issuer websites, national or EU public registers). With ESAP, all this information will be centrally accessible in one single place, searchable based on common criteria.
The “ESAP Regulation” gave ESMA the mandate to establish and operate the EU’s public portal, providing easier access to all publicly available information. ESAP will give companies greater visibility towards investors, which is particularly important for small businesses in small capital markets to attract EU and international investment. ESAP will also contain sustainability-related information published by companies to support the objectives of the European Green Deal.
The ESAP is a two-tier system: information is first collected from reporting entities by a “Collection Body” (which may be the NCA, another national body or register, or an EU body such as one of the ESAs) and then submitted to ESAP, so that the information can then be provided to the public on the ESMA-operated portal.
primary_grey_background
ESAP timeline and phases
The ESAP Regula
```

### [E75] Web — https://www.screener.in/
ref: `https://www.screener.in/` · loc: `https://www.screener.in/#~1` · score: 2
url: https://www.screener.in/

```
Stock analysis and screening tool for investors in India.
Or analyse:
Avantel
Coastal Corp
Frontier Springs
Godawari Power
Grand Continent
HBL Engineering
Pix Transmission
RACL Geartech
Sandur Manganese
Shivalik Bimetal
```

### [E76] Web — https://www.tradingview.com/screener/
ref: `https://www.tradingview.com/screener/` · loc: `https://www.tradingview.com/screener/#~1` · score: 1
url: https://www.tradingview.com/screener/

```
Search
EN
Get started
```

## Folded drill evidence

### [E77] xang1234/stock-screener — prior art
ref: `xang1234/stock-screener` · loc: `https://github.com/xang1234/stock-screener` · score: 1397
url: https://github.com/xang1234/stock-screener

```
Languages: py:944, jsx:176, js:84, md:67, json:50, csv:13 · files: 1397.

![Market Health and Exposure](docs/screenshots/health-exposure.jpg)
*Market Health and Exposure*

![Scan results with composite scores, RS sparklines, multi-screener ratings, and classification columns](docs/screenshots/scan-results.png)
*Scan results table*

![Relative Rotation Graph — sector rotation with direction-arrowed weekly tails](docs/screenshots/rrg-rotation.png)
*RRG: sector rotation with direction-arrowed weekly tails; full 197-group scope available from the same view*

**Typical flow:** sign in → bootstrap markets → review the Daily dashboard → run a Scan → drill into a stock → monitor Operations → validate outcomes on Backtest. For the full page-by-page tour, see the **[Live App Guide](docs/LIVE_APP_GUIDE.md)**.

## Quickstart (Docker)

Deploys tagged GHCR images instead of building locally:
```

### [E78] SimFin/simfin — prior art
ref: `SimFin/simfin` · loc: `https://github.com/SimFin/simfin` · score: 53
url: https://github.com/SimFin/simfin

```
Languages: py:26, rst:14, md:6, bat:1, ipynb:1, txt:1 · files: 53.


# SimFin - Simple financial data for Python

SimFin makes it easy to obtain and use financial and stock-market data in
Python. It automatically downloads share-prices and fundamental data from
the [SimFin](https://www.simfin.com/) server, saves the data to disk for
future use, and loads the data into Pandas DataFrames.

## Installation

    pip install simfin
    
More detailed installation instructions can be found [below](https://github.com/SimFin/simfin#installation-detailed-instructions).

## API-Key
```

### [E79] astro30/valinvest — prior art
ref: `astro30/valinvest` · loc: `https://github.com/astro30/valinvest` · score: 19
url: https://github.com/astro30/valinvest

```
Languages: py:9, yml:2, bat:1, md:1, rst:1, txt:1 · files: 19.


## Introduction

The aim of the package is to evaluate a stock according to his fundamentals by setting a score and identify buy and sells opportunies through technical indicators.

## Methodology description

The scoring methodology is based on Joseph Piotroski's study ([Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers](http://www.chicagobooth.edu/~/media/FE874EE65F624AAEBD0166B1974FD74D.pdf)). The F-Score is used to help financial investment decisions by finding the best value stocks on the market.<br>

> The Piostroski score is calculated based on 9 criteria divided into 3 groups:
> 
> #### Profitability
>
> - Return on Assets (1 point if it is positive in the current year, 0 otherwise)
> - Operating Cash Flow (1 point if it is positive in the current year, 0 otherwise)
```

### [E80] #11 Feature idea: Scenario-based analysis with multi-master frameworks [open]
ref: `issue#11` · loc: `https://github.com/astro30/valinvest/issues/11` · score: 1
url: https://github.com/astro30/valinvest/issues/11

```
state: open · comments: 0 · updated: 2026-03-17T07:09:54Z

First off, great project — I love that you've codified Buffett, Piotroski, and Graham criteria into a Python tool. Been using it alongside my own research workflow.

**Feature idea**: It would be interesting to add a scenario analysis mode where users can input current market conditions (PE, GDP growth, inflation, etc.) and get a side-by-side comparison of how different investment frameworks would evaluate the situation.

For example:
- **Graham** might flag "PE > 15, avoid" 
- **Buffett** might say "moat is strong, fair price is acceptable"
- **Piotroski** would run through its 9-point F-Score

I built a rough version of this concept in a [gist](https://gist.github.com/henu-wang/ca27dca833054688671ed54a70185c31) that evaluates scenarios across Buffett, Dalio, Munger, and Lynch frameworks. There's also a site called [KeepRule](https://keeprule.com/scenarios) that does something similar with 26 masters' principles, which could be a good reference for the kinds of frameworks to support.

Would this kind of multi-framework comparison be in scope for valinvest? Happy to contribute if there's interest.
```

### [E81] #12 Idea: Add investment principles context to valuation results [open]
ref: `issue#12` · loc: `https://github.com/astro30/valinvest/issues/12` · score: 1
url: https://github.com/astro30/valinvest/issues/12

```
state: open · comments: 0 · updated: 2026-03-23T08:25:12Z

Hi, really appreciate this tool! Using Buffett/Piotroski/Graham criteria for stock valuation is brilliant.

I had an idea that might complement the existing analysis: alongside the numerical scores, it could be helpful to surface relevant investment principles or quotes that reinforce *why* each criterion matters.

For example:
- When the Graham number flags a stock as overvalued, show Graham's related principle about margin of safety
- When Piotroski F-score is high, reference the research context behind each factor

I maintain a free API at [KeepRule](https://keeprule.com) that serves curated investment principles from Buffett, Graham, Munger and others, organized by category (valuation, risk management, behavioral biases, etc.). API docs: https://github.com/henu-wang/keeprule-api

This could add an educational layer that helps users not just see the numbers but understand the investing philosophy behind them. Just a thought — happy to help if you find this useful!
```

### [E82] #236 Price Update hung [closed]
ref: `issue#236` · loc: `https://github.com/xang1234/stock-screener/issues/236` · score: 1
url: https://github.com/xang1234/stock-screener/issues/236

```
state: closed · comments: 2 · updated: 2026-06-12T04:52:57Z

Updated from main and price updating has stopped working

<img width="1191" height="576" alt="Image" src="https://github.com/user-attachments/assets/1f195285-0302-4e60-9330-c2504fa1586b" />

It has been stuck updating the same 200 for what the stats say is 5 hours.
```

### [E83] #26 Bug Report [closed]
ref: `issue#26` · loc: `https://github.com/SimFin/simfin/issues/26` · score: 1
url: https://github.com/SimFin/simfin/issues/26

```
state: closed · labels: bug · comments: 5 · updated: 2024-03-17T10:12:40Z

# Bug Report

If you experience errors or bugs, please make a serious effort to solve the
problem yourself before asking here. The problem is quite likely in your own
code and a simple Google search for the error-message may help you solve it.
If it is a problem directly related to simfin, then please search the closed
GitHub issues, because it may already have been answered there.

Please make sure you have the latest simfin package installed by running:

    pip install --upgrade simfin
 
And make sure you have downloaded fresh data-files from the SimFin server
by setting `refresh_days=0` (see example below).

If you still cannot solve the problem and need our help, then please provide
the following.


## Description

Please write a brief description of the bug / error you have experienced.


## System Details

- Python version 3.12
- Simfin version 1.0.0
- Other relevant package versions
- Operation System and version
- Computer's CPU, RAM-size, free HD space, etc.
- Other relevant system information


## Code Example

Please write a minimal source-code example that reproduces the problem.
You can indent the code-block to get proper code-formatting, for example:

    import simf
```

### [E84] #159 feat(scanner): add Canadian market (TSX + TSXV) to supported markets [closed]
ref: `pr#159` · loc: `https://github.com/xang1234/stock-screener/pull/159` · score: 1
url: https://github.com/xang1234/stock-screener/pull/159

```
state: closed · comments: 3 · updated: 2026-06-13T03:36:22Z

Adds CA as the 8th supported market, covering TSX and TSX Venture listings.
Symbols are canonicalized to Yahoo-compatible suffixes (.TO for TSX, .V for
TSXV) with TMX-style dot-notation class/unit/preferred segments (e.g.
BIP.UN, BCE.PR.K) normalized to dashes (BIP-UN.TO, BCE-PR-K.TO).

Key additions:
- New CAUniverseIngestionAdapter modeled on TW (which also has dual-board
  suffix handling). Includes 10 unit tests covering canonicalization,
  TMX dot-to-dash normalization, exchange inference, deduplication, and
  source approval.
- TMX official-source fetcher (fetch_ca_snapshot) hits both TSX and
  TSXV company-directory JSON endpoints, filters out ETFs/funds/debt/
  derivative instruments, and emits combined ingest rows.
- CA fundamentals routed to yfinance only (mirrors HK/JP/TW pattern;
  Finviz screener is US-only and Alpha Vantage's free tier excludes
  Canadian listings).
- XTSE calendar via exchange_calendars (Canada Day, Victoria Day, etc.
  resolve correctly).
- ^GSPTSE primary benchmark with XIU.TO ETF fallback.
- Per-market Celery queues auto-derived from registry (data_fetch_ca,
  user_scans_ca, market_jobs_ca).
- Cache warmup at 17:00 ET, 30+ minutes after the 16:00
```

### [E85] #198 feat(markets): implement live Bursa Malaysia universe fetch [closed]
ref: `pr#198` · loc: `https://github.com/xang1234/stock-screener/pull/198` · score: 1
url: https://github.com/xang1234/stock-screener/pull/198

```
state: closed · comments: 3 · updated: 2026-06-13T03:36:55Z

## Summary

The weekly MY reference run (e.g. [run 26410876659](https://github.com/xang1234/stock-screener/actions/runs/26410876659)) was publishing only **47 stocks** because the bundled seed CSV was the sole source — `fetch_my_snapshot` raised `NotImplementedError` whenever `MY_UNIVERSE_SOURCE_URL` was set, blocking any live opt-in.

This PR implements a live Bursa Malaysia fetch that mirrors the SG pattern: walks the paginated equities-listing JSON endpoint, normalizes 4-digit issuer codes to `<NNNN>.KL`, filters to Main + ACE Markets, and drops REITs / business trusts / ETFs / structured warrants. The workflow now wires `MY_UNIVERSE_SOURCE_URL` from a repository variable with a Bursa default. On any HTTP or parse failure the fetcher falls back to the bundled CSV, so a broken URL is **not a regression** vs. today's 47-row baseline.

- `backend/app/services/official_market_universe_source_service.py` — new live path (`_fetch_my_live`, `_parse_my_api_json`, `_parse_my_records`, `_extract_my_records`, `_extract_my_total_pages`, `_with_query_param`, `_my_board_is_equity`, `_my_is_excluded_instrument`); pagination with a `my_universe_max_pages` cap so a runaway `totalPages` cannot lo
```

### [E86] #200 fix: sanitize static JSON and expand MY universe [closed]
ref: `pr#200` · loc: `https://github.com/xang1234/stock-screener/pull/200` · score: 1
url: https://github.com/xang1234/stock-screener/pull/200

```
state: closed · comments: 3 · updated: 2026-06-13T03:36:53Z

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->
## Summary by CodeRabbit

* **Bug Fixes**
  * Static site exports now produce browser-safe JSON by sanitizing non-finite numeric values.

* **Improvements**
  * Raised Malaysia live-universe minimum to 300 and added guards to reject undersized CSV fallbacks.
  * Adjusted Malaysia default minVolume threshold for more consistent filtering.

* **Tests**
  * Added regression tests for static JSON serialization and Malaysia universe/volume validations.

<!-- review_stack_entry_start -->

[![Review Change Stack](https://storage.googleapis.com/coderabbit_public_assets/review-stack-in-coderabbit-ui.svg)](https://app.coderabbit.ai/change-stack/xang1234/stock-screener/pull/200?utm_source=github_walkthrough&utm_medium=github&utm_campaign=change_stack)

<!-- review_stack_entry_end -->
<!-- end of auto-generated comment: release notes by coderabbit.ai -->
```

### [E87] #203 feat: add Australia market universe support [closed]
ref: `pr#203` · loc: `https://github.com/xang1234/stock-screener/pull/203` · score: 1
url: https://github.com/xang1234/stock-screener/pull/203

```
state: closed · comments: 2 · updated: 2026-06-13T03:36:59Z

## Summary
- adds Australia/AU market catalog facts, ASX public CSV universe ingestion, and bundled fallback CSV support
- wires AU into provider plans, cache warm schedules, official universe dispatch, weekly reference/static workflows, and Docker workers
- tightens market harmonization drift guards and filters frontend pages by backend market capabilities

## Validation
- `./venv/bin/python -m pytest tests/unit/test_market_drift_guards.py tests/unit/test_static_workflow_markets.py tests/unit/test_market_worker_config.py tests/unit/test_universe_tasks.py tests/unit/test_official_market_universe_source_service.py tests/unit/test_stock_universe_service.py::test_get_active_symbols_market_filter_falls_back_to_catalog_exchange_for_au tests/unit/test_static_site_export_service.py::test_resolve_static_default_filters_returns_per_market_threshold tests/unit/test_static_site_export_service.py::test_static_key_markets_include_australia_benchmark_symbols -q`
- `npm run test:run -- BreadthPage.test.jsx GroupRankingsPage.test.jsx RuntimeContext.test.jsx universeSelection.test.js`
- `npm run lint`
- `bash -n backend/start_celery.sh`
- `SERVER_AUTH_PASSWORD=compose-check docker compose --profile
```

### [E88] #251 perf(scan): fix preset filtering timeout (lean count + feature-store indexes) [closed]
ref: `pr#251` · loc: `https://github.com/xang1234/stock-screener/pull/251` · score: 1
url: https://github.com/xang1234/stock-screener/pull/251

```
state: closed · comments: 3 · updated: 2026-06-16T23:09:15Z

## Problem

On the live (server) site, selecting a scan **preset filtered nothing** — results stayed at the full unfiltered count with a cosmetic "(filtered)" label. Root cause (confirmed live across US/HK/JP): the preset logic was fine and the request URL was built correctly, but the **filtered results query was so slow it exceeded the 30s axios timeout and aborted** (`net::ERR_ABORTED`), leaving stale rows on screen. The static GitHub-Pages site was immune because it filters a precomputed dataset client-side.

Two backend read paths, two distinct causes:

| Path | Symptom | Cause |
|---|---|---|
| `scan_results` table (HK/JP) | 83ms → 25–37s once any filter added | `Query.count()` wrapped the heavy double-join, blob-projecting SELECT in a subquery → filtered counts read every row's `details`/sparkline blobs |
| `stock_feature_daily` (US daily) | indexed-col filter 106ms vs JSON-field filter >35s | preset fields live in the unindexed `details_json` blob → full scan reading every blob to evaluate `CAST(details_json ->> 'field' AS FLOAT)` |

## Fix

- **Lean count** (`lean_count` in `portability.py`, used by both query builders): `SELECT count(*)` over the same FROM/joins/WHERE inst
```

### [E89] #255 feat: Market Health & Exposure dashboard [closed]
ref: `pr#255` · loc: `https://github.com/xang1234/stock-screener/pull/255` · score: 1
url: https://github.com/xang1234/stock-screener/pull/255

```
state: closed · comments: 2 · updated: 2026-06-21T13:08:04Z

## Market Health & Exposure — "when to be aggressive"

Adds a transparent, rules-based **0–100 recommended-exposure score** computed daily per market and surfaced under the initial charts of the Daily Snapshot view (live tab **and** static site). Reframes the app from "here are stocks" to "here's whether to be buying stocks at all."

The single most valuable missing primitive — the **distribution-day count** (index down ≥0.2% on higher volume over a rolling 25 sessions) — is now computed, alongside a capped follow-through-day heuristic, 50/200-DMA trend, VIX, and breadth. No new data source, no rate limits: inputs are arithmetic over data already in `stock_prices` and `market_breadth`.

### Backend
- **`market_exposure` table** (migration `20260618_0022`) + `MarketExposure` model, mirroring the `MarketBreadth` `(date, market)` per-market upsert idiom. The dead `MarketStatus` table is left untouched.
- **`market_exposure_service`** — distribution-day count, FTD heuristic (explicitly capped: only raises the score floor after a correction), MA/trend, and a **tunable rubric** (module-level constants) that blends everything into 0–100 with a plain-language stance. Each score contributio
```

### [E90] Web — https://github.com/OpenBB-finance/OpenBB
ref: `https://github.com/OpenBB-finance/OpenBB` · loc: `https://github.com/OpenBB-finance/OpenBB#~106` · score: 5
url: https://github.com/OpenBB-finance/OpenBB

```
ruff.toml
View all files
Repository files navigation
Open Data Platform by OpenBB (ODP) is the open-source toolset that helps data engineers integrate proprietary, licensed, and public data sources into downstream applications like AI copilots and research dashboards.
ODP operates as the "connect once, consume everywhere" infrastructure layer that consolidates and exposes data to multiple surfaces at once: Python environments for quants, OpenBB Workspace and Excel for analysts, MCP servers for AI agents, and REST APIs for other applications.
Get started with: pip install openbb
from openbb import obb
output = obb . equity . price . historical ( "AAPL" )
df = output . to_dataframe ()
Data integrations available can be found here: https://docs.openbb.co/python/reference
OpenBB Workspace
While the Open Data Platform provides the open-source data integration foundation, OpenBB Workspace offers the enterprise UI for analysts to visualize datasets and leverage AI agents. The platform's "connect once, consume everywhere" architecture enables seamless integration between the two.
You can find OpenBB Workspace at https://pro.openbb.co .
Data integration:
You can learn more about adding data to the OpenBB workspace from the docs or this open source repository .
```

### [E91] Web — https://github.com/OpenBB-finance/OpenBB (lines 72–86)
ref: `https://github.com/OpenBB-finance/OpenBB` · loc: `https://github.com/OpenBB-finance/OpenBB#~72` · score: 4
url: https://github.com/OpenBB-finance/OpenBB

```
examples
images
images
openbb_platform
openbb_platform
.codespell.ignore
.codespell.ignore
.codespell.skip
.codespell.skip
.coveragerc
.coveragerc
.gitattributes
.gitattributes
.gitignore
.gitignore
```

## Folded drill evidence

### [E92] Docs — https://typer.tiangolo.com/
ref: `https://typer.tiangolo.com/` · loc: `https://typer.tiangolo.com/#~30` · score: 4
url: https://typer.tiangolo.com/

```
Dependencies
License
&para;
Typer, build great CLIs. Easy to code. Based on Python type hints.
Documentation : https://typer.tiangolo.com
Source Code : https://github.com/fastapi/typer
Typer is a library for building CLI applications that users will love using and developers will love creating . Based on Python type hints.
It's also a command line tool to run scripts, automatically converting them to CLI applications.
The key features are:
Intuitive to write : Great editor support. Completion everywhere. Less time debugging. Designed to be easy to use and learn. Less time reading docs.
Easy to use : It's easy to use for the final users. Automatic help, and automatic completion for all shells.
Short : Minimize code duplication. Multiple features from each parameter declaration. Fewer bugs.
Start simple : The simplest example adds only 2 lines of code to your app: 1 import, 1 function call .
Grow large : Grow in complexity as much as you want, create arbitrarily complex trees of commands and groups of subcommands, with options and arguments.
Run scripts : Typer includes a typer command/program that you can use to run scripts, automatically converting them to CLIs, even if they don't use Typer internally.
```

### [E93] Docs — https://typer.tiangolo.com/ (lines 209–221)
ref: `https://typer.tiangolo.com/` · loc: `https://typer.tiangolo.com/#~209` · score: 4
url: https://typer.tiangolo.com/

```
annotated-doc : to generate documentation from Python type annotations.
colorama (only on Windows): for producing colored terminal text on Windows.
Click code &para;
Typer used to depend on Click as well, a popular tool for building CLIs in Python.
Since version 0.26.0, Typer has vendored Click (included Click's source code internally, instead of installing it as a third party package) and has unified the code interactions between Typer and the embedded Click source code for easier maintainability in the future.
Note that some Click functionality will not be available anymore in the future, as we continue to improve and extend Typer's codebase.
typer-slim &para;
There used to be a slimmed-down version of Typer called typer-slim , which didn't include the dependencies rich and shellingham , nor the typer command.
However, since version 0.22.0, we have stopped supporting this, and typer-slim now simply installs (all of) Typer.
If you want to disable Rich globally, you can set an environmental variable TYPER_USE_RICH to False or 0 .
License &para;
This project is licensed under the terms of the MIT license.
Back to top
```

### [E94] Docs — https://docs.docker.com/compose/
ref: `https://docs.docker.com/compose/` · loc: `https://docs.docker.com/compose/#~1` · score: 3
url: https://docs.docker.com/compose/

```
# Docker Compose


Docker Compose is a tool for defining and running multi-container applications. 
It is the key to unlocking a streamlined and efficient development and deployment experience. 

Compose simplifies the control of your entire application stack, making it easy to manage services, networks, and volumes in a single YAML configuration file. Then, with a single command, you create and start all the services
from your configuration file.

Compose works in all environments - production, staging, development, testing, as
well as CI workflows. It also has commands for managing the whole lifecycle of your application:
```

### [E95] Docs — https://docs.pytest.org/en/stable/getting-started.html
ref: `https://docs.pytest.org/en/stable/getting-started.html` · loc: `https://docs.pytest.org/en/stable/getting-started.html#~41` · score: 3
url: https://docs.pytest.org/en/stable/getting-started.html

```
Anatomy of a test
About fixtures
Good Integration Practices
pytest import mechanisms and sys.path / PYTHONPATH
Typing in pytest
CI Pipelines
Flaky tests
Examples and customization tricks
Demo of Python failure reports with pytest
Basic patterns and examples
Parametrizing tests
Working with custom markers
A session-fixture which can look at all collected tests
Changing standard (Python) test discovery
Working with non-python tests
```

### [E96] Docs — https://docs.pytest.org/en/stable/getting-started.html (lines 87–101)
ref: `https://docs.pytest.org/en/stable/getting-started.html` · loc: `https://docs.pytest.org/en/stable/getting-started.html#~87` · score: 3
url: https://docs.pytest.org/en/stable/getting-started.html

```
The test
$ pytest
=========================== test session starts ============================
platform linux -- Python 3.x.y, pytest-9.x.y, pluggy-1.x.y
rootdir: /home/sweet/project
collected 1 item
test_sample.py F [100%]
================================= FAILURES =================================
_______________________________ test_answer ________________________________
def test_answer():
> assert func(3) == 5
E assert 4 == 5
E + where 4 = func(3)
test_sample.py :6: AssertionError
========================= short test summary info ==========================
```

### [E97] Docs — https://docs.python.org/3.12/whatsnew/3.12.html
ref: `https://docs.python.org/3.12/whatsnew/3.12.html` · loc: `https://docs.python.org/3.12/whatsnew/3.12.html#~151` · score: 3
url: https://docs.python.org/3.12/whatsnew/3.12.html

```
including strings reusing the same quote as the containing f-string,
multi-line expressions, comments, backslashes, and unicode escape sequences.
Let’s cover these in detail:
Quote reuse: in Python 3.11, reusing the same quotes as the enclosing f-string
raises a SyntaxError , forcing the user to either use other available
quotes (like using double quotes or triple quotes if the f-string uses single
quotes). In Python 3.12, you can now do things like this:
>>> songs = [ 'Take me back to Eden' , 'Alkaline' , 'Ascensionism' ]
>>> f "This is the playlist: { ", " . join ( songs ) } "
'This is the playlist: Take me back to Eden, Alkaline, Ascensionism'
Note that before this change there was no explicit limit in how f-strings can
be nested, but the fact that string quotes cannot be reused inside the
expression component of f-strings made it impossible to nest f-strings
arbitrarily. In fact, this is the most nested f-string that could be written:
>>> f """ { f ''' { f ' { f " { 1 + 1 } " } ' } ''' } """
```

### [E98] Docs — https://pypi.org/project/yfinance/
ref: `https://pypi.org/project/yfinance/` · loc: `https://pypi.org/project/yfinance/#~58` · score: 3
url: https://pypi.org/project/yfinance/

```
Report project as malware
Project description
Download market data from Yahoo! Finance's API
yfinance offers a Pythonic way to fetch financial & market data from Yahoo!Ⓡ finance .
[!IMPORTANT]
Yahoo!, Y!Finance, and Yahoo! finance are registered trademarks of Yahoo, Inc.
yfinance is not affiliated, endorsed, or vetted by Yahoo, Inc. It's an open-source tool that uses Yahoo's publicly available APIs, and is intended for research and educational purposes.
You should refer to Yahoo!'s terms of use ( here , here , and here ) **for details on your rights to use the actual data downloaded.
Remember - the Yahoo! finance API is intended for personal use only.**
[!TIP]
THE NEW DOCUMENTATION WEBSITE IS NOW LIVE! 🤘
Visit ranaroussi.github.io/yfinance
Main components
Ticker : single ticker data
Tickers : multiple tickers' data
```

### [E99] Docs — https://pypi.org/project/yfinance/ (lines 482–496)
ref: `https://pypi.org/project/yfinance/` · loc: `https://pypi.org/project/yfinance/#~482` · score: 3
url: https://pypi.org/project/yfinance/

```
File details
Details for the file yfinance-1.5.1.tar.gz .
File metadata
Download URL: yfinance-1.5.1.tar.gz
Upload date:
Jun 28, 2026
Size: 167.9 kB
Tags: Source
Uploaded using Trusted Publishing? No
Uploaded via: twine/6.2.0 CPython/3.14.6
File hashes
Hashes for yfinance-1.5.1.tar.gz
Algorithm
Hash digest
SHA256
```

### [E100] Docs — https://react.dev/learn
ref: `https://react.dev/learn` · loc: `https://react.dev/learn#~190` · score: 3
url: https://react.dev/learn

```
</ button >
) ;
}
Notice how onClick={handleClick} has no parentheses at the end! Do not call the event handler function: you only need to pass it down . React will call your event handler when the user clicks the button.
Updating the screen
Often, you’ll want your component to “remember” some information and display it. For example, maybe you want to count the number of times a button is clicked. To do this, add state to your component.
First, import useState from React:
import { useState } from 'react' ;
Now you can declare a state variable inside your component:
function MyButton ( ) {
const [ count , setCount ] = useState ( 0 ) ;
// ...
You’ll get two things from useState : the current state ( count ), and the function that lets you update it ( setCount ). You can give them any names, but the convention is to write [something, setSomething] .
The first time the button is displayed, count will be 0 because you passed 0 to useState() . When you want to change state, call setCount() and pass the new value to it. Clicking this button will increment the counter:
function MyButton ( ) {
```

### [E101] Docs — https://vite.dev/guide/
ref: `https://vite.dev/guide/` · loc: `https://vite.dev/guide/#~87` · score: 3
url: https://vite.dev/guide/

```
$ bun create vite my-vue-app --template vue
bash
$ deno init --npm vite my-vue-app --template vue
See create-vite for more details on each supported template: vanilla , vanilla-ts , vue , vue-ts , react , react-ts , preact , preact-ts , lit , lit-ts , svelte , svelte-ts , solid , solid-ts , qwik , qwik-ts .
You can use . for the project name to scaffold in the current directory.
To create a project without interactive prompts, you can use the --no-interactive flag.
Community Templates ​
create-vite is a tool to quickly start a project from a basic template for popular frameworks. Check out Awesome Vite for community maintained templates that include other tools or target different frameworks.
For a template at https://github.com/user/project , you can try it out online using https://github.stackblitz.com/user/project (adding .stackblitz after github to the URL of the project).
You can also use a tool like tiged to scaffold your project with one of the templates. Assuming the project is on GitHub and uses main as the default branch, you can create a local copy using:
bash
npx tiged user/project my-project
cd my-project
npm install
npm run dev
```

### [E102] Docs — https://docs.python.org/3.12/whatsnew/3.12.html (lines 3–17)
ref: `https://docs.python.org/3.12/whatsnew/3.12.html` · loc: `https://docs.python.org/3.12/whatsnew/3.12.html#~3` · score: 2
url: https://docs.python.org/3.12/whatsnew/3.12.html

```
modules |
next |
previous |
Python »
3.12.13 Documentation »
What’s New in Python »
What’s New In Python 3.12
|
Theme
Auto
Light
Dark
|
What’s New In Python 3.12 ¶
Editor :
```

### [E103] Docs — https://react.dev/learn (lines 1–12)
ref: `https://react.dev/learn` · loc: `https://react.dev/learn#~1` · score: 2
url: https://react.dev/learn

```
Learn React
Copy page Copy
Quick Start
Welcome to the React documentation! This page will give you an introduction to 80% of the React concepts that you will use on a daily basis.
You will learn
How to create and nest components
How to add markup and styles
How to display data
How to render conditions and lists
How to respond to events and update the screen
How to share data between components
Creating and nesting components
```

### [E104] Web — https://www.findmymoat.com/
ref: `https://www.findmymoat.com/` · loc: `https://www.findmymoat.com/#~14` · score: 3
url: https://www.findmymoat.com/

```
Stats
More
Checking
Find My Moat
VOL. XCIV, NO. 247
★ A CURATED DIRECTORY OF INVESTMENT RESEARCH TOOLS ★
Checking
Monday, July 6, 2026
```

