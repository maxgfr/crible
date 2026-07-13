---
name: crible-cli
description: Use when the user wants to screen stocks or run the crible screener from the terminal — find quality/value/undervalued companies, filter by fundamentals (P/E, ROE, debt, margins), scores (Piotroski, Altman Z, Beneish M), composite ranks, country/region/sector, export screening results to CSV, list filterable fields, check data coverage/freshness, or set up local data. Triggers include "screen for…", "find stocks/companies that…", "quelles sociétés…", "run a screen", "crible", "quality stocks in Europe", "P/E below…", "export the results".
---

# Run stock screens with the crible CLI

Run every command from the repo root with `uv run crible …` (run `uv sync`
once if the environment is missing).

## 0. Make sure data exists

```bash
uv run crible status        # universe count, coverage, snapshot present?
```

If there is no snapshot yet, pull the published open dataset (zero crawl,
~30 s) instead of crawling:

```bash
uv run crible bootstrap     # refuses to overwrite an existing data/; --force to re-pull
```

`CRIBLE_DATA_DIR` selects the data directory (default `./data`).

## 1. Discover what is filterable

```bash
uv run crible fields              # every column + its type (number|string)
uv run crible presets             # ready-made screens with their editable DSL
```

The field list IS the whitelist: any column it prints can be used in a query.
An unknown field in a query fails with a "did you mean …?" hint — trust it.

## 2. The filter DSL

`field op value`, combined with `AND` / `OR` / `NOT` and parentheses.
Operators: `> >= < <= = != <>` and `field IN (v1, v2, …)`.
Strings are single-quoted: `country = 'FR'`. Numbers are bare: `piotroski_f >= 7`.

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
- **Ranks** (`composite_rank`, `quality_rank`, `value_rank`, `momentum_rank`)
  are 0–100 percentiles within region×sector peer groups; `return_6m` is the
  momentum input (decimal).
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

## 5. Keeping data fresh

`docker compose up` runs the continuous crawl loop; a nightly
`uv run crible demo-refresh --deadline 9000` is the bounded cron alternative;
consume-only setups re-pull the published dataset with
`uv run crible bootstrap --force`.
