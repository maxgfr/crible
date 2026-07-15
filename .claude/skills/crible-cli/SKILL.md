---
name: crible-cli
description: Use when the user wants to screen stocks OR operate the crible screener from the terminal — find quality/value/undervalued companies, filter by fundamentals (P/E, ROE, debt, margins), scores (Piotroski, Altman Z, Beneish M), composite ranks, country/region/sector, export screening results to CSV, list filterable fields; AND to manage its data: pull/refresh the dataset, crawl or bootstrap the universe, import price dumps, download Stooq bulk, rebuild the snapshot, publish the static site, check coverage/freshness. Triggers include "screen for…", "find stocks/companies that…", "quelles sociétés…", "run a screen", "crible", "quality stocks in Europe", "P/E below…", "export the results", "refresh crible data", "update the dataset", "rebuild the snapshot", "publish the site", "ingest / crawl", "import prices".
---

# Run stock screens with the crible CLI

Inside the repo, run every command with `uv run crible …` (run `uv sync` once
if the environment is missing). Outside the repo, crible is an installable
tool — uv auto-provisions the required Python 3.12, and `bootstrap` pulls the
FULL published dataset (zero crawl), so three commands stand up a working
screener anywhere:

```bash
uv tool install git+https://github.com/maxgfr/crible
crible --data-dir ~/crible-data bootstrap
crible --data-dir ~/crible-data screen "piotroski_f >= 7" --sort -composite_rank
```

(One-shot alternative: `uvx --from git+https://github.com/maxgfr/crible crible …`.)

The global `--data-dir` option (before the subcommand) selects the dataset
location. Default: `$CRIBLE_DATA_DIR`, else `./data` **relative to the
current directory** — outside the repo, ALWAYS pass `--data-dir` (or export
`CRIBLE_DATA_DIR`) so bootstrap and screen see the same dataset.

## 0. Make sure data exists

```bash
uv run crible status        # universe count, coverage, snapshot present?
```

If there is no snapshot yet, pull the published open dataset (zero crawl,
~30 s) instead of crawling:

```bash
uv run crible bootstrap     # refuses to overwrite an existing data/; --force to re-pull
```


## 1. Discover what is filterable

```bash
uv run crible fields              # every column + its type (number|string)
uv run crible presets             # ready-made screens with their editable DSL
```

The field list IS the whitelist: any column it prints can be used in a query.
An unknown field fails with a "did you mean …?" hint when a close match
exists — but there are NO aliases: `roe`, `per`, `pe` do not resolve. Map
finance shorthand to exact names first (`crible fields | grep -i equity`):
P/E → `price_to_earnings_ratio`, ROE → `return_on_equity`,
market cap → `market_cap`, dividend yield → `weighted_dividend_yield`.

## 2. The filter DSL

`field op value`, combined with `AND` / `OR` / `NOT` and parentheses.
Operators: `> >= < <= = != <>` and `field IN (v1, v2, …)`.
Strings are single-quoted: `country = 'FR'`. Numbers are bare: `piotroski_f >= 7`.
**A blank query is valid and means NO filter** — `crible screen "" --sort
-composite_rank` screens the whole covered universe (the hosted UI's default).

```bash
uv run crible screen "piotroski_f >= 7 AND country IN ('FR','DE')" \
  --sort -composite_rank --limit 20
uv run crible screen "return_on_equity > 0.15" --format csv   # csv to stdout
uv run crible screen --preset quality                          # run a preset by id
uv run crible export "altman_z > 2.99 AND price_to_book_ratio < 1.5" --out results.csv
```

`--sort` takes `-field` for descending, `field` (or `+field`) for ascending,
comma-separated for multi-key (`--sort "country,-piotroski_f"`).

## 3. Field semantics you must get right

- **Ratios are decimals, not percent**: ROE 15 % is `return_on_equity > 0.15`.
- **Scores**: `piotroski_f` is 0–9 (≥7 strong); `altman_z` > 2.99 = safe zone,
  < 1.81 = distress; `beneish_m` > **-1.78** flags possible earnings
  manipulation (so `beneish_m < -1.78` selects the clean ones).
- **Distress & forensics (newer)**: `zmijewski_score` and `ohlson_o` < 0 =
  safe (> 0 = modelled distress); `montier_c` counts 0–6 red flags (≤1 clean);
  `dechow_f` < 1 = below-normal misstatement risk, ≥ 1.85 substantial;
  `mohanram_g` is a PARTIAL 0–6 growth-quality score (6 of the paper's 8
  signals — no published cutoff transfers).
- **GARP & cash**: `peg_ratio` (positive-only; ≤ 1 = growth at a reasonable
  price), `rule_of_40` (revenue growth + FCF margin, ≥ 0.4 passes),
  `shareholder_yield` (dividends + net buybacks / market cap),
  `sloan_accruals` (lower/negative is better), `cash_conversion_cycle` (days,
  lower is better — negative means suppliers finance operations).
- **TTM**: `ttm_revenue`/`ttm_net_income`/`ttm_operating_cashflow`/
  `ttm_free_cash_flow` + `price_to_earnings_ttm`/`price_to_sales_ttm`/
  `ttm_fcf_yield` — the last four discrete quarters (crawled symbols +
  audited US issuers reporting discrete 10-Q quarters).
- **Momentum (price-derived, latest period)**: `return_6m`, `return_12_1`
  (12-month skipping the last month), `high_52w_proximity` (1.0 = at the
  52-week high), `volatility_1y` (annualized).
- **Ranks** (`composite_rank`, `quality_rank`, `value_rank`, `momentum_rank`)
  are 0–100 percentiles within region×sector peer groups; `return_6m` is the
  momentum input (decimal).
- **3-year trajectory**: `revenue_cagr_3y` / `net_income_cagr_3y` (compound,
  decimals; `peg_ratio` divides by exactly the latter).
- The list above is a compass, not a catalog — `crible fields` prints every
  filterable column.
- **Identity fields**: `country` is ISO-2 uppercase (`'FR'`), `region` is one
  of `'europe' | 'us' | 'world'`, `sector` is GICS-like
  (`'Information Technology'`, `'Health Care'`, …).
- **Growth**: every fundamental/ratio has a `_growth` companion (YoY decimal),
  e.g. `revenue_growth > 0.10`.
- **NULLs never match**: a company missing an input simply drops out of any
  filter on it — nothing is imputed. `missing_inputs` / `rank_missing_pillars`
  explain why a value is NULL.

## 4. Recipes

```bash
# Quality + value in Europe, best composite first
uv run crible screen "region = 'europe' AND piotroski_f >= 7 AND earnings_yield > 0.08" \
  --sort -composite_rank --limit 25

# Cheap and safe: low P/B, Altman safe zone, no manipulation red flag
uv run crible screen "price_to_book_ratio < 1.5 AND altman_z > 2.99 AND beneish_m < -1.78"

# One company's full detail: filter on symbol
uv run crible screen "symbol = 'AIR.PA'" --format csv
```

When a screen returns 0 rows, loosen one clause at a time (coverage is bounded:
`crible status` shows how many companies are crawled) — do not conclude "no
company matches" from a thin dataset.

## 5. Operating crible (managing the data lifecycle)

Every command below is keyless. Pick the path that matches the setup.

**Consume-only (fastest — no crawl):** pull the published open dataset.
```bash
uv run crible bootstrap                 # ~30 s; refuses to overwrite an existing data/
uv run crible bootstrap --force         # re-pull the latest layer
uv run crible bootstrap --repo owner/name   # pull from a fork's published dataset
```

**Crawl your own universe:**
```bash
uv run crible ingest --bootstrap        # load the universe from FinanceDatabase (once)
uv run crible ingest --once --limit 50  # one bounded crawl cycle
uv run crible ingest --loop             # continuous crawl loop
uv run crible ingest --once --fetch-gleif   # also mirror GLEIF ISIN→LEI (unlocks audited EU)
```

**Nightly bounded refresh (the real dataset run — audited enrichment):**
```bash
uv run crible refresh --deadline 9000   # keyless pass: ESEF + EDGAR enrich, self-heal GLEIF, mirror ECB FX; prints a JSON report
```
Flags: `--edgar-bulk` (download companyfacts.zip ~1.4 GB and ingest ALL
resolved US issuers), `--fsds-quarters N` (backfill deep US history from the N
most recent SEC FSDS quarters), `--esef-limit` / `--edgar-limit` (per-run
caps, default 25), `--no-fetch-gleif` / `--no-fetch-fx` (skip those steps),
`--max-minutes N` (WHOLE-RUN wall-clock guard: enrichment stages stop early so
compute+publish always run; partial passes resume next run; 0 = unbounded).

**Prices (dump-based, no API):**
```bash
uv run crible import-prices huggingface           # US OHLCV dump, plain HTTPS
uv run crible import-prices path/to/stooq.zip     # worldwide (manual dl from stooq.com/db/h/)
uv run crible import-prices huggingface --max-age-days 1   # skip if imported < 1 day ago
uv run crible stooq-download d_world_txt --import # auto-fetch the captcha-gated Stooq bulk (clears PoW + OCR), then import
uv run crible solve-captcha shot.png              # standalone captcha OCR helper (optional 'captcha' extra)
```
Distillate = last close + as-of date + trailing 6-month return in
`data/prices-latest.parquet`; the windowed series lands in `data/prices/`.

**Rebuild & publish:**
```bash
uv run crible compute                   # build + atomically publish the wide snapshot (incremental: skips the republish when nothing changed)
uv run crible export-site --out site-data --min-symbols 50   # write the static artifacts the hosted screener serves (refuses below --min-symbols)
```

`docker compose up` runs the continuous crawl+compute loop as a service.
After any raw change, `crible compute` is what refreshes ratios/ranks. Check
`price_asof` in results — staleness is reported honestly, never imputed.

## 6. Use from agents (MCP)

`crible mcp` serves a READ-ONLY MCP tool surface over stdio — `screen`
(the same DSL; blank = whole universe), `fields`, `presets`, `company`,
`status`. No crawl/refresh tool is exposed. Register it in Claude Code after
bootstrap:

```bash
claude mcp add crible -e CRIBLE_DATA_DIR=$HOME/crible-data -- crible mcp
```
