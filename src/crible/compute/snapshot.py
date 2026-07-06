"""FR-003 / ADR-0003 — the wide snapshot: build, publish (atomic swap), read.

One row per company × fiscal period: canonical fields, financetoolkit ratios,
year-over-year growth series, Piotroski/Altman/Beneish scores, provenance
metadata. Published by write-temp-then-rename so readers never observe a
half-written snapshot.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from crible.compute.canonical import CANONICAL_FIELDS, build_canonical
from crible.compute.ratios import compute_ratios
from crible.compute.scores import all_scores

SNAPSHOT_NAME = "snapshot.parquet"


def build_symbol_snapshot(
    symbol: str,
    frames: dict[tuple[str, str], pd.DataFrame],
    price: pd.Series | None = None,
    provider: str = "yfinance",
    computed_at: float | None = None,
) -> pd.DataFrame:
    canonical = build_canonical(frames)
    if canonical.empty:
        return pd.DataFrame()

    ratios = compute_ratios(canonical, price)
    scores = all_scores(canonical, price)
    growth = canonical[CANONICAL_FIELDS].pct_change(fill_method=None)
    growth.columns = [f"{col}_growth" for col in growth.columns]
    ratio_growth = ratios.pct_change(fill_method=None)
    ratio_growth.columns = [f"{col}_growth" for col in ratio_growth.columns]

    out = pd.concat([canonical, ratios, growth, ratio_growth, scores], axis=1)
    out.insert(0, "symbol", symbol)
    out.insert(1, "period", out.index.astype(str))
    out["provider"] = provider
    out["computed_at"] = computed_at if computed_at is not None else time.time()
    return out.reset_index(drop=True)


def latest_raw_frames(data_dir: Path | str, symbol: str) -> dict[tuple[str, str], pd.DataFrame]:
    """Pick the newest raw Parquet per (statement_type, freq) for a symbol."""
    safe_symbol = symbol.replace("/", "_")
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    root = Path(data_dir) / "raw"
    for directory in root.glob(f"provider=*/symbol={safe_symbol}"):
        for file in sorted(directory.glob("*.parquet")):
            statement_type, freq, _ = file.stem.split("-", 2)
            frames[(statement_type, freq)] = pd.read_parquet(file)
    return frames


def crawled_symbols(data_dir: Path | str) -> list[str]:
    root = Path(data_dir) / "raw"
    symbols = {
        d.name.split("=", 1)[1] for d in root.glob("provider=*/symbol=*") if d.is_dir()
    }
    return sorted(symbols)


UNIVERSE_COLUMNS = [
    "name", "country", "country_name", "region", "sector", "industry", "exchange", "currency", "isin",
]


def attach_universe(snapshot: pd.DataFrame, data_dir: Path | str) -> pd.DataFrame:
    """Embed universe metadata so the snapshot is self-contained: readers
    (API/CLI) never open the ingest-owned DuckDB file (ADR-0003)."""
    universe_path = Path(data_dir) / "universe.parquet"
    if snapshot.empty or not universe_path.exists():
        return snapshot
    universe = pd.read_parquet(universe_path)
    keep = ["symbol"] + [c for c in UNIVERSE_COLUMNS if c in universe.columns]
    return snapshot.merge(universe[keep], on="symbol", how="left")


def build_snapshot(data_dir: Path | str, symbols: list[str] | None = None) -> pd.DataFrame:
    todo = symbols if symbols is not None else crawled_symbols(data_dir)
    parts = []
    for symbol in todo:
        frames = latest_raw_frames(data_dir, symbol)
        if not frames:
            continue
        part = build_symbol_snapshot(symbol, frames)
        if not part.empty:
            parts.append(part)
    if not parts:
        return pd.DataFrame()
    return attach_universe(pd.concat(parts, ignore_index=True), data_dir)


def publish_snapshot(snapshot: pd.DataFrame, data_dir: Path | str) -> Path:
    """Atomic swap: write to a temp file, fsync via close, rename over the old."""
    directory = Path(data_dir) / "snapshot"
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / SNAPSHOT_NAME
    tmp = directory / f".tmp-{SNAPSHOT_NAME}"
    snapshot.to_parquet(tmp, index=False)
    tmp.rename(final)
    return final


def read_snapshot(data_dir: Path | str) -> pd.DataFrame | None:
    path = Path(data_dir) / "snapshot" / SNAPSHOT_NAME
    if not path.exists():
        return None
    return pd.read_parquet(path)
