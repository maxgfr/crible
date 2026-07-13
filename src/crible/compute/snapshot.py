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
from crible.compute.ranks import attach_ranks, price_return
from crible.compute.ratios import compute_ratios
from crible.compute.scores import all_scores

SNAPSHOT_NAME = "snapshot.parquet"


def latest_close(frames: dict[tuple[str, str], pd.DataFrame]) -> tuple[float, str] | None:
    """(close, as-of date) from the newest daily price bar, if any (FR-011)."""
    bars = frames.get(("prices", "daily"))
    if bars is None or not len(bars):
        return None
    close_col = next((c for c in ("Close", "close", "Adj Close") if c in bars.columns), None)
    date_col = next((c for c in ("Date", "date", "Datetime") if c in bars.columns), None)
    if close_col is None:
        return None
    last = bars.dropna(subset=[close_col]).iloc[-1] if bars[close_col].notna().any() else None
    if last is None:
        return None
    as_of = str(last[date_col])[:10] if date_col else ""
    return float(last[close_col]), as_of


def build_symbol_snapshot(
    symbol: str,
    frames: dict[tuple[str, str], pd.DataFrame],
    price: pd.Series | None = None,
    provider: str = "yfinance",
    computed_at: float | None = None,
    audited_frames: dict[tuple[str, str], pd.DataFrame] | None = None,
    price_quote: tuple[float, str] | None = None,
    momentum_6m: float | None = None,
) -> pd.DataFrame:
    canonical = build_canonical(frames)
    audited_fields: dict[str, list[str]] = {}
    if audited_frames:
        from crible.compute.reconcile import align_periods, reconcile

        audited = build_canonical(audited_frames)
        if canonical.empty:
            canonical = audited
            audited_fields = {str(p): [c for c in audited.columns if pd.notna(audited.loc[p, c])] for p in audited.index}
        elif not audited.empty:
            audited = align_periods(audited, canonical.index)
            result = reconcile(canonical, audited, symbol=symbol)
            canonical = result.merged
            audited_fields = result.audited_fields
    if canonical.empty:
        return pd.DataFrame()

    price_asof: str | None = None
    if price is None:
        # crawled daily bars win; the imported dump quote is the fallback
        # (price_quote from data/prices-latest.parquet — derived values only)
        close = latest_close(frames) or price_quote
        if close is not None:
            value, price_asof = close
            # the current price applies to the LATEST fiscal period only —
            # older periods keep NaN rather than pretending historical prices
            price = pd.Series(float("nan"), index=canonical.index)
            price.iloc[-1] = value

    ratios = compute_ratios(canonical, price)
    scores = all_scores(canonical, price)
    growth = canonical[CANONICAL_FIELDS].pct_change(fill_method=None)
    growth.columns = [f"{col}_growth" for col in growth.columns]
    ratio_growth = ratios.pct_change(fill_method=None)
    ratio_growth.columns = [f"{col}_growth" for col in ratio_growth.columns]

    out = pd.concat([canonical, ratios, growth, ratio_growth, scores], axis=1)
    # FR-015 momentum input: trailing 6-month price return, latest period only
    # (cross-sectional like the price itself); NaN when history is too short.
    out["return_6m"] = float("nan")
    if len(out):
        momentum = price_return(frames.get(("prices", "daily")))
        if pd.isna(momentum) and momentum_6m is not None:
            momentum = momentum_6m  # distilled from the imported dump
        out.iloc[-1, out.columns.get_loc("return_6m")] = momentum
    out.insert(0, "symbol", symbol)
    out.insert(1, "period", out.index.astype(str))
    out["provider"] = provider
    out["price_asof"] = price_asof
    out["audited_fields"] = [
        ",".join(audited_fields.get(str(p), [])) or None for p in out["period"]
    ]
    # FR-003 AC-2 — the provenance note naming the missing inputs: every NULL
    # ratio is explainable by the canonical fields the provider did not supply
    missing_per_period = canonical[CANONICAL_FIELDS].isna()
    out["missing_inputs"] = [
        ",".join(missing_per_period.columns[missing_per_period.loc[p]]) or None
        for p in canonical.index
    ]
    out["computed_at"] = computed_at if computed_at is not None else time.time()
    return out.reset_index(drop=True)


def latest_raw_frames(
    data_dir: Path | str, symbol: str, provider: str = "*"
) -> dict[tuple[str, str], pd.DataFrame]:
    """Pick the newest raw Parquet per (statement_type, freq) for a symbol."""
    safe_symbol = symbol.replace("/", "_")
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    root = Path(data_dir) / "raw"
    for directory in root.glob(f"provider={provider}/symbol={safe_symbol}"):
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


def _frames_provider(frames: dict[tuple[str, str], pd.DataFrame], default: str) -> str:
    """Provider id from the raw layer's ``_provider`` metadata column."""
    for frame in frames.values():
        if "_provider" in frame.columns and len(frame):
            return str(frame["_provider"].iloc[0])
    return default


def _price_quotes(data_dir: Path | str) -> dict[str, tuple[float, str, float]]:
    """symbol → (close, asof, return_6m) from the imported dump distillate."""
    from crible.ingest.price_import import load_prices_latest

    table = load_prices_latest(data_dir)
    return {
        str(row.symbol): (float(row.close), str(row.price_asof), float(row.return_6m))
        for row in table.itertuples()
        if pd.notna(row.close)
    }


def build_snapshot(data_dir: Path | str, symbols: list[str] | None = None) -> pd.DataFrame:
    todo = symbols if symbols is not None else crawled_symbols(data_dir)
    quotes = _price_quotes(data_dir)
    parts = []
    for symbol in todo:
        scraped = latest_raw_frames(data_dir, symbol, provider="yfinance")
        # the audited layer: ESEF for the EU, EDGAR for the US — a symbol
        # realistically has one of the two
        audited = {
            **latest_raw_frames(data_dir, symbol, provider="esef"),
            **latest_raw_frames(data_dir, symbol, provider="edgar"),
        }
        if not scraped and not audited:
            continue
        quote = quotes.get(symbol)
        part = build_symbol_snapshot(
            symbol,
            scraped or audited,
            provider="yfinance" if scraped else _frames_provider(audited, "esef"),
            audited_frames=audited if scraped else None,
            price_quote=(quote[0], quote[1]) if quote else None,
            momentum_6m=quote[2] if quote else None,
        )
        if not part.empty:
            parts.append(part)
    if not parts:
        return pd.DataFrame()
    # FR-015: ranks are cross-sectional — computed once the whole universe
    # snapshot is assembled (peer groups need region/sector from the universe).
    return attach_ranks(attach_universe(pd.concat(parts, ignore_index=True), data_dir))


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
