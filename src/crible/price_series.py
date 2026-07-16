"""The published OHLCV price series — load, resolve, shard, export.

One logical table (symbol, date, open, high, low, close, adj_close, volume,
source) assembled from two stores: the crawled yfinance daily bars in the raw
layer and the imported dump series in ``data/prices/`` (ADR-0007 — the series
ARE published, superseding the distillate-only policy). Per symbol, one whole
source wins — series from different sources are never mixed, their adjustment
bases differ — and the window is trimmed to the last ``SERIES_WINDOW_DAYS``.

Exported as symbol-sorted, size-bounded Parquet shards so the site stays
range-request friendly and every shard clears GitHub's 100 MB file wall.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SERIES_WINDOW_DAYS = 400  # covers the 1-year chart + the 6-month return base
SERIES_DIR = "prices"
SERIES_COLUMNS = [
    "symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "source",
]
# tie-break when two sources end on the same date: the crawled bars are the
# canonical layer (the snapshot itself prefers them over the distillate);
# among dumps, defeatbeta refreshes ~weekly and outranks the slower rotations
SOURCE_PRIORITY = {"yfinance": 0, "defeatbeta": 1, "stooq": 2, "huggingface": 3}

SHARD_PATTERN = "prices-*.parquet"
MAX_SHARD_BYTES = 95 * 1024 * 1024  # git refuses files >100 MB — fail early
SHARD_ROW_GROUP = 50_000  # small row groups keep WASM range requests small


class ShardSizeError(RuntimeError):
    """A written shard would break the 100 MB git wall — refuse to publish."""


def series_dir(data_dir: Path | str) -> Path:
    return Path(data_dir) / SERIES_DIR


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=SERIES_COLUMNS)


def normalize_yf_bars(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Raw yfinance daily bars → the lean series schema.

    The ``Date`` column is tz-aware in the exchange's zone; take the LOCAL
    calendar date (``.dt.date``) — a naive cast converts through UTC and can
    shift European bars a day back.
    """
    date_col = next((c for c in ("Date", "date", "Datetime") if c in frame.columns), None)
    close_col = next((c for c in ("Close", "close") if c in frame.columns), None)
    if date_col is None or close_col is None or not len(frame):
        return _empty()
    out = pd.DataFrame(
        {
            "symbol": symbol,
            "date": pd.to_datetime(pd.to_datetime(frame[date_col]).dt.date),
            "open": pd.to_numeric(frame.get("Open"), errors="coerce"),
            "high": pd.to_numeric(frame.get("High"), errors="coerce"),
            "low": pd.to_numeric(frame.get("Low"), errors="coerce"),
            "close": pd.to_numeric(frame[close_col], errors="coerce"),
            "adj_close": pd.to_numeric(frame.get("Adj Close"), errors="coerce"),
            "volume": pd.to_numeric(frame.get("Volume"), errors="coerce"),
            "source": "yfinance",
        }
    )
    return out.dropna(subset=["close"]).reset_index(drop=True)


def _load_yf_series(data_dir: Path | str, symbol: str | None = None) -> pd.DataFrame:
    """Newest prices-daily raw file per symbol, normalized."""
    pattern = (symbol or "*").replace("/", "_")
    parts = []
    for directory in (Path(data_dir) / "raw").glob(f"provider=yfinance/symbol={pattern}"):
        # zero-padded ms stamps make lexical order chronological
        files = sorted(directory.glob("prices-daily-*.parquet"))
        if not files:
            continue
        raw = pd.read_parquet(files[-1])
        name = raw["_symbol"].iloc[0] if "_symbol" in raw.columns and len(raw) else (
            directory.name.split("=", 1)[1]
        )
        parts.append(normalize_yf_bars(raw, str(name)))
    return _concat(parts)


def _load_store_series(data_dir: Path | str, symbol: str | None = None) -> pd.DataFrame:
    """The imported dump series (data/prices/<source>.parquet), lean schema."""
    parts = []
    for file in sorted(series_dir(data_dir).glob("*.parquet")):
        table = pd.read_parquet(file)
        if symbol is not None:
            table = table[table["symbol"] == symbol]
        if len(table):
            parts.append(table.assign(date=pd.to_datetime(table["date"])))
    return _concat(parts)


def write_series(data_dir: Path | str, source: str, frame: pd.DataFrame) -> Path:
    """Whole-file replace of one source's series store (temp-then-rename)."""
    directory = series_dir(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / f"{source}.parquet"
    tmp = directory / f".tmp-{source}.parquet"
    out = frame[SERIES_COLUMNS].sort_values(["symbol", "date"]).reset_index(drop=True)
    out["date"] = pd.to_datetime(out["date"]).dt.date
    out.to_parquet(tmp, index=False)
    tmp.rename(final)
    return final


def _concat(parts: list[pd.DataFrame]) -> pd.DataFrame:
    # concat with an empty object-dtype frame degrades the date column
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else _empty()


def _resolve(candidates: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """Per symbol: the source with the newest bar wins WHOLE (adjustment bases
    differ across sources — never mix rows), then trim to the window."""
    if not len(candidates):
        return _empty()
    candidates = candidates.assign(date=pd.to_datetime(candidates["date"]))
    latest = candidates.groupby(["symbol", "source"], as_index=False)["date"].max()
    latest["_priority"] = latest["source"].map(SOURCE_PRIORITY).fillna(len(SOURCE_PRIORITY))
    winners = (
        latest.sort_values(["symbol", "date", "_priority"], ascending=[True, False, True])
        .drop_duplicates("symbol")[["symbol", "source"]]
    )
    resolved = candidates.merge(winners, on=["symbol", "source"])
    cutoff = resolved.groupby("symbol")["date"].transform("max") - pd.Timedelta(days=window_days)
    resolved = resolved[resolved["date"] > cutoff]
    return (
        resolved[SERIES_COLUMNS]
        .sort_values(["symbol", "date"])
        .reset_index(drop=True)
    )


def load_all_series(
    data_dir: Path | str, window_days: int = SERIES_WINDOW_DAYS
) -> pd.DataFrame:
    """Every symbol's resolved, windowed series — the export's input."""
    candidates = _concat([_load_yf_series(data_dir), _load_store_series(data_dir)])
    return _resolve(candidates, window_days)


def load_symbol_series(
    data_dir: Path | str, symbol: str, window_days: int = SERIES_WINDOW_DAYS
) -> pd.DataFrame:
    """One symbol's resolved series — the API path (reads only its files)."""
    candidates = _concat(
        [_load_yf_series(data_dir, symbol), _load_store_series(data_dir, symbol)]
    )
    return _resolve(candidates, window_days)


def export_price_shards(
    data_dir: Path | str,
    out_dir: Path | str,
    max_rows_per_shard: int = 2_000_000,
    window_days: int = SERIES_WINDOW_DAYS,
) -> dict | None:
    """Write symbol-sorted shards to ``out_dir`` and return the manifest block.

    Greedy-packs WHOLE symbols per shard (disjoint symbol ranges → DuckDB's
    zone maps prune non-matching shards on a footer read). Stale shards from a
    previous export are removed first. None when no series exist — prices are
    an enrichment, never a gate.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob(SHARD_PATTERN):
        stale.unlink()

    series = load_all_series(data_dir, window_days=window_days)
    if not len(series):
        return None

    counts = series.groupby("symbol", sort=True).size()
    batches: list[list[str]] = [[]]
    rows_in_batch = 0
    for symbol, rows in counts.items():
        if batches[-1] and rows_in_batch + rows > max_rows_per_shard:
            batches.append([])
            rows_in_batch = 0
        batches[-1].append(str(symbol))
        rows_in_batch += rows

    series = series.set_index("symbol", drop=False)
    shards = []
    for index, symbols in enumerate(batches):
        file = out / f"prices-{index:02d}.parquet"
        part = series.loc[symbols].reset_index(drop=True)
        part["date"] = part["date"].dt.date
        part.to_parquet(file, index=False, row_group_size=SHARD_ROW_GROUP)
        size = file.stat().st_size
        if size > MAX_SHARD_BYTES:
            raise ShardSizeError(
                f"{file.name} is {size} bytes (> {MAX_SHARD_BYTES}) — lower"
                " max_rows_per_shard before this hits GitHub's 100 MB wall"
            )
        shards.append(
            {
                "file": file.name,
                "rows": int(len(part)),
                "bytes": int(size),
                "min_symbol": symbols[0],
                "max_symbol": symbols[-1],
            }
        )

    return {
        "symbols": int(series["symbol"].nunique()),
        "bars": int(len(series)),
        "window_days": window_days,
        "max_date": str(series["date"].max().date()),
        "shards": shards,
    }
