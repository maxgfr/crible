"""The defeatbeta yahoo-finance-data dump — one HF dataset, no API, no key.

Yahoo-derived data re-scraped by a single maintainer and republished on
Hugging Face (one parquet per table, plain HTTPS, refreshed ~weekly). The
ODC-BY label cannot cleanse Yahoo's exchange-licensed terms, so the
redistribution risk is explicitly assumed — same tier as the Stooq and
paperswithbacktest dumps (docs/DATA-SOURCES.md). Role: ADDITIONAL +
FALLBACK only; audited providers keep absolute precedence and crawled
yfinance bars win price ties (crible.price_series.SOURCE_PRIORITY).

US-centric coverage (~12k listings incl. OTC/ETF): its real value is the
"audited fundamentals but no prices" US gap — every symbol it prices drops
out of the Yahoo top-up, freeing crawl budget for Europe and the world.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import duckdb
import pandas as pd

from crible.compute.momentum import momentum_features
from crible.ingest.price_import import ImportReport, _merge_and_publish, universe_symbols
from crible.price_series import SERIES_WINDOW_DAYS, write_series

log = logging.getLogger("crible.ingest.defeatbeta")

DB_DATASET = "defeatbeta/yahoo-finance-data"
DB_BASE = f"https://huggingface.co/datasets/{DB_DATASET}/resolve/main/data"
DB_TABLES = {
    "prices": f"{DB_BASE}/stock_prices.parquet",
    "dividends": f"{DB_BASE}/stock_dividend_events.parquet",
    "splits": f"{DB_BASE}/stock_split_events.parquet",
    "shares": f"{DB_BASE}/stock_shares_outstanding.parquet",
    "statements": f"{DB_BASE}/stock_statement.parquet",
}


def _connect(url: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    if str(url).startswith("http"):
        con.execute("INSTALL httpfs; LOAD httpfs;")
    return con


def import_defeatbeta(data_dir: Path | str, tables: dict[str, str] | None = None) -> ImportReport:
    """Import the defeatbeta price table: windowed OHLCV series + distillate.

    One DuckDB pass over stock_prices.parquet (only the series window is
    read; ``report_date`` is an ISO string, safe to compare lexically).
    defeatbeta ships split-adjusted bars without a separate adjusted close,
    so ``adj_close`` stays NULL — never fabricated (the Stooq rule).
    """
    tables = tables if tables is not None else DB_TABLES
    known = universe_symbols(data_dir)
    con = _connect(tables["prices"])
    try:
        series = con.execute(
            f"""
            SELECT symbol, CAST(report_date AS DATE) AS date,
                   CAST(open AS DOUBLE) AS open, CAST(high AS DOUBLE) AS high,
                   CAST(low AS DOUBLE) AS low, CAST(close AS DOUBLE) AS close,
                   CAST(NULL AS DOUBLE) AS adj_close, CAST(volume AS DOUBLE) AS volume
            FROM read_parquet(?)
            WHERE close IS NOT NULL AND close > 0
              AND report_date >= strftime(current_date - INTERVAL {SERIES_WINDOW_DAYS} DAY, '%Y-%m-%d')
            """,
            [tables["prices"]],
        ).fetchdf()
    finally:
        con.close()

    now = time.time()
    total_symbols = series["symbol"].nunique()
    records: list[dict] = []
    for symbol, group in series.groupby("symbol", sort=False):
        if symbol not in known:
            continue
        features = momentum_features(group["date"], group["close"])
        if features is None:
            continue
        records.append({"symbol": symbol, **features, "source": "defeatbeta", "imported_at": now})
    fresh = pd.DataFrame(records)
    skipped = total_symbols - len(fresh)
    if not fresh.empty:
        _merge_and_publish(data_dir, fresh)
    series = series[series["symbol"].isin(known)]
    if len(series):
        write_series(data_dir, "defeatbeta", series.assign(source="defeatbeta"))
    log.info(
        "import-prices: %d symbols from defeatbeta (%d outside the universe)", len(fresh), skipped
    )
    return ImportReport(source="defeatbeta", imported=len(fresh), skipped_unknown=skipped)
