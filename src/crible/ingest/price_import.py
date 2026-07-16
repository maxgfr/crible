"""Offline price import — dump files, not APIs (the FR-011 gap-filler).

Two dump families:
- The HuggingFace daily-price dataset (paperswithbacktest/Stocks-Daily-Price):
  four parquet shards over plain HTTPS, refreshed ~monthly — US coverage.
- A Stooq bulk archive (stooq.com/db/h/), downloaded MANUALLY by the operator
  (Stooq gates automated downloads behind a CAPTCHA) — worldwide coverage;
  Stooq symbols are mapped onto the universe's Yahoo-style tickers.

Each import produces TWO artifacts (ADR-0007, 2026-07-13 — the published
dataset carries the price series; neither dump has an open license and the
redistribution risk is explicitly assumed, see docs/DATA-SOURCES.md):
- the windowed OHLCV series in data/prices/<source>.parquet (lean schema,
  whole-file replace) — exported to the site as prices-*.parquet shards;
- the one-row-per-symbol distillate (last close, as-of date, and the
  momentum features: return_6m, return_12_1, high_52w_proximity,
  volatility_1y) in data/prices-latest.parquet — what the snapshot consumes
  for valuation/momentum when the crawl has no bars. The feature math lives
  in ONE place: crible.compute.momentum.
"""

from __future__ import annotations

import csv
import io
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from crible.compute.momentum import FEATURE_COLUMNS, momentum_features
from crible.price_series import SERIES_WINDOW_DAYS, write_series

log = logging.getLogger("crible.ingest.price_import")

PRICES_LATEST = "prices-latest.parquet"

HF_DATASET = "paperswithbacktest/Stocks-Daily-Price"
HF_SHARDS = [
    f"https://huggingface.co/datasets/{HF_DATASET}/resolve/main/data/train-0000{i}-of-00004.parquet"
    for i in range(4)
]

# Stooq exchange suffix → the universe's Yahoo-style suffix. Each entry only
# helps if Stooq ships a bulk STOCK archive for that market AND its tickers
# align with the universe. Stooq's per-country stock archives are limited
# (d_us/uk/jp/hk/pl/hu_txt); d_world_txt is instruments only (no stocks).
STOOQ_SUFFIXES = {
    "us": "", "de": ".DE", "uk": ".L", "fr": ".PA", "jp": ".T",
    "pl": ".WA", "hu": ".BD", "it": ".MI", "hk": ".HK",
}

# Markets whose universe tickers are zero-padded numeric codes but whose Stooq
# filenames drop the leading zeros: Stooq '700.hk' → universe '0700.HK'.
STOOQ_TICKER_PAD = {"hk": 4}


@dataclass(frozen=True)
class ImportReport:
    source: str
    imported: int
    skipped_unknown: int


def prices_latest_path(data_dir: Path | str) -> Path:
    return Path(data_dir) / PRICES_LATEST


def load_prices_latest(data_dir: Path | str) -> pd.DataFrame:
    path = prices_latest_path(data_dir)
    if not path.exists():
        return pd.DataFrame(
            columns=["symbol", "close", "price_asof", *FEATURE_COLUMNS, "source", "imported_at"]
        )
    table = pd.read_parquet(path)
    # a pre-momentum file lacks the newer feature columns — backfill as NaN
    for col in FEATURE_COLUMNS:
        if col not in table.columns:
            table[col] = float("nan")
    return table


def latest_import_age_days(data_dir: Path | str, source: str | None = None) -> float | None:
    """Age of the newest import, from the table itself (file mtimes lie after
    a git checkout). With ``source``, only that dump's rows count — one dump's
    fresh import must not silence another's schedule."""
    table = load_prices_latest(data_dir)
    if table.empty or "imported_at" not in table.columns:
        return None
    if source is not None:
        table = table[table["source"] == source]
        if table.empty:
            return None
    return (time.time() - float(table["imported_at"].max())) / 86400.0


def universe_symbols(data_dir: Path | str) -> set[str]:
    path = Path(data_dir) / "universe.parquet"
    if not path.exists():
        return set()
    return set(pd.read_parquet(path, columns=["symbol"])["symbol"])


def _merge_and_publish(data_dir: Path | str, fresh: pd.DataFrame) -> None:
    """Newest price_asof wins per symbol; atomic temp-then-rename."""
    current = load_prices_latest(data_dir)
    merged = (
        pd.concat([current, fresh], ignore_index=True)
        .sort_values("price_asof")
        .drop_duplicates("symbol", keep="last")
        .reset_index(drop=True)
    )
    path = prices_latest_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    merged.to_parquet(tmp, index=False)
    tmp.rename(path)


def _distill(bars: pd.DataFrame) -> dict | None:
    """One symbol's distillate row fields from a date/close frame — a thin
    delegate to the shared momentum rule (never a re-implementation)."""
    return momentum_features(bars["date"], bars["close"])


def import_huggingface(
    data_dir: Path | str, shards: list[str] | None = None
) -> ImportReport:
    """Import the HF daily-price shards: windowed OHLCV series + distillate.

    One DuckDB pass over the shards (only the series window of bars is read);
    symbols outside the universe are counted and dropped.
    """
    shards = shards if shards is not None else HF_SHARDS
    known = universe_symbols(data_dir)
    con = duckdb.connect()
    try:
        if any(str(s).startswith("http") for s in shards):
            con.execute("INSTALL httpfs; LOAD httpfs;")
        placeholders = ", ".join("?" for _ in shards)
        series = con.execute(
            f"""
            SELECT symbol, CAST(date AS DATE) AS date,
                   open, high, low, close, adj_close, volume
            FROM read_parquet([{placeholders}])
            WHERE close IS NOT NULL AND close > 0
              AND date >= strftime(current_date - INTERVAL {SERIES_WINDOW_DAYS} DAY, '%Y-%m-%d')
            """,
            list(shards),
        ).fetchdf()
    finally:
        con.close()

    # the distillate runs the SHARED momentum rule over the same windowed
    # series frame — the old DuckDB re-implementation (drift risk, TODO) died
    now = time.time()
    adjusted = series.dropna(subset=["adj_close"])
    adjusted = adjusted[adjusted["adj_close"] > 0]
    total_symbols = adjusted["symbol"].nunique()
    records: list[dict] = []
    for symbol, group in adjusted.groupby("symbol", sort=False):
        if symbol not in known:
            continue
        features = momentum_features(group["date"], group["adj_close"])
        if features is None:
            continue
        records.append(
            {"symbol": symbol, **features, "source": "huggingface", "imported_at": now}
        )
    fresh = pd.DataFrame(records)
    skipped = total_symbols - len(fresh)
    if not fresh.empty:
        _merge_and_publish(data_dir, fresh)
    series = series[series["symbol"].isin(known)]
    if len(series):
        write_series(data_dir, "huggingface", series.assign(source="huggingface"))
    log.info("import-prices: %d symbols from huggingface (%d outside the universe)",
             len(fresh), skipped)
    return ImportReport(source="huggingface", imported=len(fresh), skipped_unknown=skipped)


def map_stooq_symbol(name: str) -> str | None:
    """'aapl.us' → 'AAPL', 'bmw.de' → 'BMW.DE', '700.hk' → '0700.HK' — None
    when the exchange suffix has no universe mapping. Numeric-code markets are
    zero-padded to the universe's width (STOOQ_TICKER_PAD)."""
    stem = name.rsplit("/", 1)[-1]
    if stem.endswith(".txt"):
        stem = stem[:-4]
    if "." not in stem:
        return None
    ticker, suffix = stem.rsplit(".", 1)
    suffix = suffix.lower()
    mapped = STOOQ_SUFFIXES.get(suffix)
    if mapped is None or not ticker:
        return None
    pad = STOOQ_TICKER_PAD.get(suffix)
    if pad and ticker.isdigit():
        ticker = ticker.zfill(pad)
    return ticker.upper() + mapped


def _stooq_number(value: str | None) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("nan")


def import_stooq(data_dir: Path | str, archive: Path | str) -> ImportReport:
    """Import a manually-downloaded Stooq bulk archive (CSV members named
    <ticker>.<exchange>.txt, dates YYYYMMDD): windowed series + distillate.

    Stooq publishes pre-adjusted bars without a separate adjusted close, so
    ``adj_close`` stays NULL — never fabricated."""
    known = universe_symbols(data_dir)
    now = time.time()
    records: list[dict] = []
    series_parts: list[pd.DataFrame] = []
    skipped = 0
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.namelist():
            if not member.lower().endswith(".txt"):
                continue
            symbol = map_stooq_symbol(member)
            if symbol is None or symbol not in known:
                skipped += 1
                continue
            with bundle.open(member) as handle:
                reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8", errors="replace"))
                rows = []
                for row in reader:
                    normalized = {k.strip("<>").lower(): v for k, v in row.items() if k}
                    date, close = normalized.get("date"), normalized.get("close")
                    if not date or not close:
                        continue
                    rows.append(
                        {"date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                         "open": _stooq_number(normalized.get("open")),
                         "high": _stooq_number(normalized.get("high")),
                         "low": _stooq_number(normalized.get("low")),
                         "close": float(close),
                         "volume": _stooq_number(normalized.get("vol"))}
                    )
            if not rows:
                continue
            distilled = _distill(pd.DataFrame(rows))
            if distilled is None:
                continue
            records.append(
                {"symbol": symbol, **distilled, "source": "stooq", "imported_at": now}
            )
            bars = pd.DataFrame(rows).assign(date=lambda f: pd.to_datetime(f["date"]))
            cutoff = bars["date"].max() - pd.Timedelta(days=SERIES_WINDOW_DAYS)
            series_parts.append(
                bars[bars["date"] > cutoff].assign(
                    symbol=symbol, adj_close=float("nan"), source="stooq"
                )
            )
    fresh = pd.DataFrame(records)
    if not fresh.empty:
        _merge_and_publish(data_dir, fresh)
    if series_parts:
        write_series(data_dir, "stooq", pd.concat(series_parts, ignore_index=True))
    log.info("import-prices: %d symbols from stooq (%d members unmapped)", len(fresh), skipped)
    return ImportReport(source="stooq", imported=len(fresh), skipped_unknown=skipped)
