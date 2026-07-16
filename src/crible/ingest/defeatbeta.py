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

from crible.compute.canonical import FIELD_CANDIDATES
from crible.compute.momentum import momentum_features
from crible.ingest.price_import import ImportReport, _merge_and_publish, universe_symbols
from crible.ingest.raw import iter_raw_files, write_raw_statement
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

EVENTS_DIR = "events"

# capital events keep their FULL history (tiny tables — MBs, not GBs);
# split_factor stays the raw "1398:1000" string, never a lossy float
_EVENT_SELECTS = {
    "dividends": "symbol, CAST(report_date AS DATE) AS date, CAST(amount AS DOUBLE) AS amount",
    "splits": "symbol, CAST(report_date AS DATE) AS date, split_factor",
    "shares": (
        "symbol, CAST(report_date AS DATE) AS date,"
        " CAST(shares_outstanding AS BIGINT) AS shares_outstanding"
    ),
}


# defeatbeta's stock_statement is LONG format (item_name/item_value) with
# snake_case yfinance-derived names; the raw layer speaks yfinance PascalCase
# (what build_canonical consumes). The auto rule inverts the casing; these
# item names deviate from it.
_ITEM_OVERRIDES = {
    "EBIT": "ebit",
    "EBITDA": "ebitda",
    "NormalizedEBITDA": "normalized_ebitda",
    "NetPPE": "net_ppe",
    "GrossPPE": "gross_ppe",
    "SellingGeneralAndAdministration": "selling_gen_admin",
}


def _auto_snake(name: str) -> str:
    return "".join(("_" + c.lower()) if c.isupper() else c for c in name).lstrip("_")


def _item_map() -> dict[str, str]:
    """defeatbeta item_name → yfinance column, for every canonical candidate."""
    mapping: dict[str, str] = {}
    for candidates in FIELD_CANDIDATES.values():
        for yf_name in candidates:
            if " " in yf_name:  # legacy display alias, not an item name
                continue
            mapping[_ITEM_OVERRIDES.get(yf_name) or _auto_snake(yf_name)] = yf_name
    return mapping


ITEM_TO_YF = _item_map()

_STATEMENT_TYPES = {"income_statement": "income", "balance_sheet": "balance", "cash_flow": "cashflow"}
_STATEMENT_KEYS = ("income", "balance", "cashflow")


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
    _import_events(data_dir, tables, known)
    log.info(
        "import-prices: %d symbols from defeatbeta (%d outside the universe)", len(fresh), skipped
    )
    return ImportReport(source="defeatbeta", imported=len(fresh), skipped_unknown=skipped)


def fundamentals_gap_symbols(data_dir: Path | str) -> list[str]:
    """Universe symbols whose fundamentals NO other source serves — the
    last-resort-only enforcement, done at import time so the ~10k
    EDGAR-covered issuers never get a defeatbeta raw file. A dir holding
    only crawled ``prices-daily`` files does not count as served."""
    known = universe_symbols(data_dir)
    root = Path(data_dir) / "raw"
    served: set[str] = set()
    for directory in root.glob("provider=*/symbol=*"):
        provider = directory.parent.name.split("=", 1)[1]
        if provider == "defeatbeta":
            continue  # re-imports refresh previously imported symbols
        if any(f.stem.split("-", 1)[0] in _STATEMENT_KEYS for f in iter_raw_files(directory)):
            served.add(directory.name.split("=", 1)[1])
    return sorted(known - served)


def import_defeatbeta_fundamentals(
    data_dir: Path | str,
    table: str | None = None,
    symbols: list[str] | None = None,
    limit: int | None = None,
) -> ImportReport:
    """Last-resort fundamentals: pivot the LONG stock_statement table into
    yfinance-vocabulary raw frames under ``provider=defeatbeta``.

    Only gap symbols (see ``fundamentals_gap_symbols``) are read; the
    snapshot falls back to these frames when no yfinance statements exist,
    and audited frames still reconcile ON TOP of them (audited always wins).
    ``skip_identical`` keeps incremental compute O(actually-changed)."""
    url = table if table is not None else DB_TABLES["statements"]
    gap = symbols if symbols is not None else fundamentals_gap_symbols(data_dir)
    if limit:
        gap = gap[:limit]
    if not gap:
        log.info("import-fundamentals: no gap symbols — every listing is already served")
        return ImportReport(source="defeatbeta", imported=0, skipped_unknown=0)

    items = list(ITEM_TO_YF)
    con = _connect(url)
    try:
        con.register("gap_symbols", pd.DataFrame({"symbol": list(gap)}))
        placeholders = ", ".join("?" for _ in items)
        long = con.execute(
            f"""
            SELECT s.symbol, s.report_date, s.item_name,
                   CAST(s.item_value AS DOUBLE) AS item_value,
                   s.finance_type, s.period_type
            FROM read_parquet(?) s
            JOIN gap_symbols USING (symbol)
            WHERE s.item_name IN ({placeholders})
              AND s.period_type IN ('annual', 'quarterly')
            """,
            [url, *items],
        ).fetchdf()
    finally:
        con.close()

    now = time.time()
    written: set[str] = set()
    for (symbol, finance_type, period_type), part in long.groupby(
        ["symbol", "finance_type", "period_type"], sort=False
    ):
        statement_type = _STATEMENT_TYPES.get(str(finance_type))
        if statement_type is None:
            continue
        wide = (
            part.pivot_table(index="report_date", columns="item_name",
                             values="item_value", aggfunc="last")
            .rename(columns=ITEM_TO_YF)
            .sort_index()
        )
        frame = wide.reset_index().rename(columns={"report_date": "period"})
        frame.columns.name = None
        write_raw_statement(
            data_dir, symbol=str(symbol), provider="defeatbeta",
            statement_type=statement_type, freq=str(period_type),
            frame=frame, fetched_at=now, skip_identical=True,
        )
        written.add(str(symbol))
    log.info(
        "import-fundamentals: statements for %d of %d gap symbols from defeatbeta",
        len(written), len(gap),
    )
    return ImportReport(
        source="defeatbeta", imported=len(written), skipped_unknown=len(gap) - len(written)
    )


def _import_events(data_dir: Path | str, tables: dict[str, str], known: set[str]) -> None:
    """Dividends, splits and shares outstanding → data/events/ (published;
    the release restore→publish cycle is the last-good guarantee)."""
    for name, select in _EVENT_SELECTS.items():
        url = tables.get(name)
        if url is None:
            continue
        con = _connect(url)
        try:
            frame = con.execute(f"SELECT {select} FROM read_parquet(?)", [url]).fetchdf()
        finally:
            con.close()
        frame = frame[frame["symbol"].isin(known)].reset_index(drop=True)
        if not len(frame):
            continue
        frame = frame.assign(date=pd.to_datetime(frame["date"]).dt.date, source="defeatbeta")
        directory = Path(data_dir) / EVENTS_DIR
        directory.mkdir(parents=True, exist_ok=True)
        final = directory / f"defeatbeta-{name}.parquet"
        tmp = directory / f".tmp-defeatbeta-{name}.parquet"
        frame.to_parquet(tmp, index=False)
        tmp.rename(final)
        log.info("import-prices: %d defeatbeta %s events for %d symbols",
                 len(frame), name, frame["symbol"].nunique())
