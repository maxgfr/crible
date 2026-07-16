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
from crible.compute.extras import compute_extras
from crible.compute.momentum import FEATURE_COLUMNS as MOMENTUM_COLUMNS
from crible.compute.momentum import bars_features
from crible.compute.ranks import attach_ranks
from crible.compute.ttm import TTM_COLUMNS, ttm_from_quarterly, ttm_ratios
from crible.compute.ratios import RATIO_DENYLIST, compute_ratios, price_dependent_ratio_columns
from crible.compute.scores import all_scores
from crible.ingest.raw import iter_raw_files
from crible.providers.audited import merge_audited

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
    quote_features: dict | None = None,
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
    extras = compute_extras(canonical, price)
    growth = canonical[CANONICAL_FIELDS].pct_change(fill_method=None)
    growth.columns = [f"{col}_growth" for col in growth.columns]
    # price-based ratios exist for the latest period only, so their YoY
    # growth can never resolve — don't emit those always-NaN columns
    price_cols = price_dependent_ratio_columns()
    ratio_growth = ratios.drop(columns=[c for c in ratios.columns if c in price_cols]).pct_change(
        fill_method=None
    )
    ratio_growth.columns = [f"{col}_growth" for col in ratio_growth.columns]

    out = pd.concat([canonical, ratios, growth, ratio_growth, scores, extras], axis=1)
    # price-derived momentum features (return_6m feeds momentum_rank; plus
    # 12-1, 52-week-high proximity, 1y volatility), latest period only —
    # cross-sectional like the price itself; NaN when history is too short.
    # Crawled bars win; the imported-dump distillate fills per feature.
    for col in MOMENTUM_COLUMNS:
        out[col] = float("nan")
    if len(out):
        features = bars_features(frames.get(("prices", "daily")))
        for col in MOMENTUM_COLUMNS:
            value = features.get(col, float("nan"))
            if pd.isna(value) and quote_features is not None:
                value = quote_features.get(col, float("nan"))
            out.iloc[-1, out.columns.get_loc(col)] = value
    # TTM — the last four quarters summed onto the latest row (columns, not
    # rows). Audited discrete quarters (EDGAR 10-Q, v2) outrank scraped, and
    # a window is never source-mixed: all-audited or all-scraped, else NaN.
    for col in TTM_COLUMNS:
        out[col] = float("nan")
    if len(out):
        ttm = ttm_from_quarterly(audited_frames) if audited_frames else {}
        if not ttm:
            ttm = ttm_from_quarterly(frames)
        latest_price = price.iloc[-1] if price is not None else float("nan")
        latest_shares = canonical["shares_outstanding"].iloc[-1]
        market_cap_latest = (
            float(latest_price) * float(latest_shares)
            if pd.notna(latest_price) and pd.notna(latest_shares)
            else float("nan")
        )
        for col, value in {**ttm, **ttm_ratios(ttm, market_cap_latest)}.items():
            out.iloc[-1, out.columns.get_loc(col)] = value
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
        for file in iter_raw_files(directory):
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


def _price_quotes(data_dir: Path | str) -> dict[str, dict]:
    """symbol → {close, price_asof, <momentum features>} from the imported
    dump distillate (load_prices_latest backfills feature columns missing
    from a pre-momentum file as NaN)."""
    from crible.ingest.price_import import load_prices_latest

    table = load_prices_latest(data_dir)

    def _num(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("nan")

    quotes: dict[str, dict] = {}
    for row in table.itertuples():
        if pd.isna(row.close):
            continue
        quotes[str(row.symbol)] = {
            "close": float(row.close),
            "price_asof": str(row.price_asof),
            **{col: _num(getattr(row, col, None)) for col in MOMENTUM_COLUMNS},
        }
    return quotes


def build_symbol_rows(data_dir: Path | str, symbols: list[str]) -> pd.DataFrame:
    """The per-symbol stage: canonical fields + ratios + scores + price for each
    symbol, BEFORE the cross-sectional finalize (universe/FX/ranks). This is the
    expensive part — the seam incremental compute recomputes for changed symbols
    only."""
    quotes = _price_quotes(data_dir)
    parts = []
    for symbol in symbols:
        scraped = latest_raw_frames(data_dir, symbol, provider="yfinance")
        scraped_provider = "yfinance"
        if not any(key[0] in ("income", "balance", "cashflow") for key in scraped):
            # last-resort fallback: defeatbeta statements (Yahoo-derived dump,
            # only imported for symbols no other source serves). Crawled
            # yfinance frames — including prices-daily — keep their keys.
            fallback = latest_raw_frames(data_dir, symbol, provider="defeatbeta")
            if fallback:
                scraped = {**fallback, **scraped}
                scraped_provider = "defeatbeta"
        # the audited layer, per region (a listing realistically has one): US
        # companyfacts wins recent periods and FSDS backfills the deep history;
        # ESEF (EU), Companies House (UK) and EDINET (JP) don't overlap it.
        audited = merge_audited(
            latest_raw_frames(data_dir, symbol, provider="edgar"),
            latest_raw_frames(data_dir, symbol, provider="edgar-fsds"),
            latest_raw_frames(data_dir, symbol, provider="esef"),
            latest_raw_frames(data_dir, symbol, provider="companies-house"),
            latest_raw_frames(data_dir, symbol, provider="edinet"),
        )
        if not scraped and not audited:
            continue
        quote = quotes.get(symbol)
        # pass the audited frames ALWAYS (not only when scraped exists): an
        # audited-only listing has empty scraped canonical, so build_symbol_snapshot
        # takes the audited frames as the base AND marks their field-level
        # provenance — otherwise audited-only symbols ship blank audited_fields (F2/c3).
        part = build_symbol_snapshot(
            symbol,
            scraped,
            provider=scraped_provider if scraped else _frames_provider(audited, "esef"),
            audited_frames=audited or None,
            price_quote=(quote["close"], quote["price_asof"]) if quote else None,
            quote_features=quote,
        )
        if not part.empty:
            parts.append(part)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def finalize_snapshot(rows: pd.DataFrame, data_dir: Path | str) -> pd.DataFrame:
    """The cross-sectional stage over ALL symbols' rows: embed the universe,
    add the FX companions, then the peer-group ranks (FR-015 percentiles need
    the whole set). Cheap relative to the per-symbol stage, so incremental
    compute re-runs it over the merged rows every time."""
    if rows.empty:
        return rows
    # FX companions (*_eur) attach after the universe (needs currency); a no-op
    # when no ECB rates are mirrored, so offline builds are unchanged.
    from crible.compute.mohanram import attach_mohanram
    from crible.providers.fx import attach_fx

    return attach_mohanram(attach_ranks(attach_fx(attach_universe(rows, data_dir), data_dir)))


def build_snapshot(data_dir: Path | str, symbols: list[str] | None = None) -> pd.DataFrame:
    todo = symbols if symbols is not None else crawled_symbols(data_dir)
    return finalize_snapshot(build_symbol_rows(data_dir, todo), data_dir)


BASE_NAME = "base.parquet"
BASE_SCHEMA_NAME = "base-schema.json"
# Bump on EVERY commit that adds or removes per-symbol snapshot columns.
# Kept (non-dirty) base rows carry the schema they were built with: without
# this guard a deploy that adds columns would ship them as NULL for every
# unchanged symbol until its raw happens to change.
# 2: quick-win indicators (CCC/operating cycle, payout, ROIC, rule of 40,
#    Sloan accruals, PEG, shareholder yield)
# 3: momentum trio (return_12_1, high_52w_proximity, volatility_1y)
# 4: Mohanram G (partial 6/8) — inputs + peer-relative signals + score
# 5: Dechow F-Score (Model 1 accounting core) — 7 components + F
# 6: TTM v1 — quarterly flow sums + P/E·P/S·FCF-yield (TTM) on the latest row
# 7: 3-year CAGR columns (revenue_cagr_3y, net_income_cagr_3y)
ENGINE_SCHEMA_VERSION = 7


def _newest_raw_stamp(data_dir: Path | str, symbol: str) -> float:
    """The newest raw fetched-at stamp (ms → s) across all providers for a
    symbol — the change signal for incremental compute."""
    root = Path(data_dir) / "raw"
    safe = symbol.replace("/", "_")
    newest = 0.0
    for directory in root.glob(f"provider=*/symbol={safe}"):
        for file in iter_raw_files(directory):
            try:
                newest = max(newest, int(file.stem.rsplit("-", 1)[1]) / 1000.0)
            except (IndexError, ValueError):
                continue
    return newest


def build_snapshot_incremental(data_dir: Path | str) -> pd.DataFrame | None:
    """Recompute only the symbols whose raw changed since the last build, reuse
    the cached per-symbol rows for the rest, then re-finalize over everything.
    Returns the new snapshot, or None when nothing changed (no republish).

    The per-symbol stage is O(dirty); the cross-sectional finalize is O(all) but
    cheap. A ``base.parquet`` caches the pre-finalize rows so unchanged symbols
    are never rebuilt — the fix for full rebuilds at 20k+ issuers (F7)."""
    data_dir = Path(data_dir)
    base_path = data_dir / "snapshot" / BASE_NAME
    symbols = crawled_symbols(data_dir)
    # no cache, or a cache built by a different engine schema (the nightly
    # restores base.parquet from the last release) → full rebuild
    if not base_path.exists() or _cached_schema_version(data_dir) != ENGINE_SCHEMA_VERSION:
        rows = build_symbol_rows(data_dir, symbols)
        _publish_base(rows, data_dir)
        return finalize_snapshot(rows, data_dir)

    base_mtime = base_path.stat().st_mtime
    # a refreshed price distillate changes the price_quote / return_6m baked into
    # EVERY symbol's base row, so it makes them all dirty (F8) — otherwise the
    # base-persisted rows serve stale prices and value/momentum ranks.
    price_file = data_dir / "prices-latest.parquet"
    if price_file.exists() and price_file.stat().st_mtime > base_mtime:
        dirty = list(symbols)
    else:
        dirty = [s for s in symbols if _newest_raw_stamp(data_dir, s) > base_mtime]
    # the base cache may predate the schema (the nightly restores it from the
    # last release): scrub retired columns so kept rows can't resurrect them
    prev = _scrub_retired_columns(pd.read_parquet(base_path))
    known = set(prev["symbol"]) if "symbol" in prev.columns else set()
    # a symbol vanishing from the raw layer is also a change (drop its rows)
    dropped = known - set(symbols)
    if not dirty and not dropped:
        return None

    kept = prev[prev["symbol"].isin(set(symbols) - set(dirty))] if "symbol" in prev.columns else prev
    fresh = build_symbol_rows(data_dir, dirty) if dirty else pd.DataFrame()
    rows = pd.concat([kept, fresh], ignore_index=True) if not fresh.empty else kept.reset_index(drop=True)
    _publish_base(rows, data_dir)
    return finalize_snapshot(rows, data_dir)


def _scrub_retired_columns(rows: pd.DataFrame) -> pd.DataFrame:
    """Columns the engine no longer emits: the always-NaN price-ratio growth
    companions and the RATIO_DENYLIST duplicates (plus their growths)."""
    retired = {f"{c}_growth" for c in price_dependent_ratio_columns()}
    retired |= set(RATIO_DENYLIST) | {f"{c}_growth" for c in RATIO_DENYLIST}
    return rows.drop(columns=[c for c in rows.columns if c in retired])


def _cached_schema_version(data_dir: Path | str) -> int | None:
    import json

    path = Path(data_dir) / "snapshot" / BASE_SCHEMA_NAME
    try:
        return json.loads(path.read_text()).get("engine_schema_version")
    except (OSError, ValueError):
        return None


def _publish_base(rows: pd.DataFrame, data_dir: Path | str) -> None:
    import json

    directory = Path(data_dir) / "snapshot"
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / f".tmp-{BASE_NAME}"
    rows.to_parquet(tmp, index=False)
    tmp.rename(directory / BASE_NAME)
    (directory / BASE_SCHEMA_NAME).write_text(
        json.dumps({"engine_schema_version": ENGINE_SCHEMA_VERSION})
    )


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
