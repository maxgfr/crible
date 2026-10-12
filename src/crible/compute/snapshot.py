"""FR-003 / ADR-0003 — the wide snapshot: build, publish (atomic swap), read.

One row per company × fiscal period: canonical fields, financetoolkit ratios,
year-over-year growth series, Piotroski/Altman/Beneish scores, provenance
metadata. Published by write-temp-then-rename so readers never observe a
half-written snapshot.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from crible.compute.canonical import (
    CANONICAL_FIELDS,
    OUTFLOW_FIELDS,
    build_canonical,
    price_shares,
    yoy_growth,
)
from crible.compute.extras import compute_extras
from crible.compute.momentum import FEATURE_COLUMNS as MOMENTUM_COLUMNS
from crible.compute.momentum import bars_features
from crible.compute.ranks import attach_ranks
from crible.compute.ttm import TTM_COLUMNS, select_ttm, ttm_ratios
from crible.compute.ratios import RATIO_DENYLIST, compute_ratios, price_dependent_ratio_columns
from crible.compute.scores import all_scores
from crible.ingest.raw import iter_raw_files
from crible.providers.audited import merge_audited
from crible.providers.fx import load_rates, price_factor

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


# a feature missing from the price's own source may be filled from the other
# source only when that one is this close in time (a months-old crawl must not
# supply return_6m next to a fresh dump close)
FEATURE_FILL_DAYS = 7


def build_symbol_snapshot(
    symbol: str,
    frames: dict[tuple[str, str], pd.DataFrame],
    price: pd.Series | None = None,
    provider: str = "yfinance",
    computed_at: float | None = None,
    audited_frames: dict[tuple[str, str], pd.DataFrame] | None = None,
    price_quote: tuple[float, str] | None = None,
    quote_features: dict | None = None,
    currency: tuple[str | None, str | None, dict | None] | None = None,
) -> pd.DataFrame:
    """One symbol's rows: merged canonical fields → price → per-period blocks
    → latest-row overlays (momentum, TTM) → provenance. ±inf never leaves:
    a filter would match it while every reader shows null.

    ``currency`` = (quote currency, reporting currency, ECB rates): the price
    is expressed in the currency the statements are in before any multiple
    (pence → pounds, a EUR quote of a USD filer → USD); no rate → no price."""
    canonical, audited_fields = _merge_audited(build_canonical(frames), audited_frames, symbol)
    if canonical.empty:
        return pd.DataFrame()
    price_asof: str | None = None
    features = bars_features(frames.get(("prices", "daily")))
    if price is None:
        price, price_asof, features = _resolve_price(frames, price_quote, quote_features, canonical.index)
    elif quote_features is not None:
        features = _fill_features(features, quote_features)
    reporting = currency[1] if currency else None
    if price is not None and currency:
        factor = price_factor(*currency)
        # an all-NaN price keeps the price-ratio columns, empty
        price = price * factor if factor is not None else pd.Series(float("nan"), index=price.index)

    out = _period_blocks(canonical, price)
    _overlay_latest(out, canonical, price, price_asof, features, frames, audited_frames)
    out = _provenance(out, symbol, canonical, audited_fields, provider, price_asof, computed_at)
    out["reporting_currency"] = reporting
    return out.replace([np.inf, -np.inf], np.nan)


def _merge_audited(
    canonical: pd.DataFrame, audited_frames: dict[tuple[str, str], pd.DataFrame] | None, symbol: str
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Audited values over scraped ones (reconcile); an audited-only listing
    takes the audited frames as its base. Returns the per-period list of
    fields that came from the audited layer."""
    if not audited_frames:
        return canonical, {}
    from crible.compute.reconcile import align_periods, reconcile

    audited = build_canonical(audited_frames)
    if canonical.empty:
        fields = {str(p): [c for c in audited.columns if pd.notna(audited.loc[p, c])] for p in audited.index}
        return audited, fields
    if audited.empty:
        return canonical, {}
    result = reconcile(canonical, align_periods(audited, canonical.index), symbol=symbol)
    return result.merged, result.audited_fields


def _fill_features(primary: dict, fallback: dict | None) -> dict:
    """Per-feature fill of NaN momentum features from a second source."""
    if not fallback:
        return dict(primary)
    return {
        col: fallback.get(col, float("nan")) if pd.isna(primary.get(col, float("nan"))) else primary[col]
        for col in MOMENTUM_COLUMNS
    }


def _resolve_price(
    frames: dict[tuple[str, str], pd.DataFrame],
    price_quote: tuple[float, str] | None,
    quote_features: dict | None,
    index: pd.Index,
) -> tuple[pd.Series | None, str | None, dict]:
    """(price series, as-of, momentum features) from the freshest source.

    The crawled daily bars and the imported dump quote (prices-latest.parquet)
    compete on as-of — a same-day TradingView close must not lose to
    yesterday's crawled bar — and the momentum features come from the SAME
    source as the price, so return_6m and the close share a date. The current
    price applies to the LATEST fiscal period only: older periods keep NaN
    rather than pretending historical prices."""
    crawled = latest_close(frames)
    bar_features = bars_features(frames.get(("prices", "daily")))
    quote_features = quote_features or {}
    use_quote = price_quote is not None and (crawled is None or str(price_quote[1]) > str(crawled[1]))
    close = price_quote if use_quote else crawled
    if close is None:
        return None, None, _fill_features(bar_features, quote_features)
    primary, secondary = (quote_features, bar_features) if use_quote else (bar_features, quote_features)
    other = crawled if use_quote else price_quote
    other_asof = other[1] if other is not None else None
    if other_asof is not None and _days_between(str(close[1]), str(other_asof)) <= FEATURE_FILL_DAYS:
        features = _fill_features(
            {col: primary.get(col, float("nan")) for col in MOMENTUM_COLUMNS}, secondary
        )
    else:
        features = {col: primary.get(col, float("nan")) for col in MOMENTUM_COLUMNS}
    value, price_asof = close
    price = pd.Series(float("nan"), index=index)
    price.iloc[-1] = value
    return price, price_asof, features


def _days_between(a: str, b: str) -> float:
    days = abs((pd.to_datetime(a[:10], errors="coerce") - pd.to_datetime(b[:10], errors="coerce")).days)
    return float("inf") if pd.isna(days) else days


def _period_blocks(canonical: pd.DataFrame, price: pd.Series | None) -> pd.DataFrame:
    """Every per-period block in ONE concat: canonical fields, ratios,
    year-over-year growths, scores, extras, plus the NaN filler the
    latest-row overlays write into (inserting them one by one onto the
    many-block frame was pure PerformanceWarning spam at 57k rows)."""
    ratios = compute_ratios(canonical, price)
    scores = all_scores(canonical, price)
    extras = compute_extras(canonical, price)
    # outflows (negative by convention) grow by their magnitude
    magnitudes = canonical[CANONICAL_FIELDS].copy()
    magnitudes[list(OUTFLOW_FIELDS)] = magnitudes[list(OUTFLOW_FIELDS)].abs()
    growth = yoy_growth(magnitudes)
    growth.columns = [f"{col}_growth" for col in growth.columns]
    # price-based ratios exist for the latest period only, so their YoY
    # growth can never resolve — don't emit those always-NaN columns
    price_cols = price_dependent_ratio_columns()
    ratio_growth = yoy_growth(ratios.drop(columns=[c for c in ratios.columns if c in price_cols]))
    ratio_growth.columns = [f"{col}_growth" for col in ratio_growth.columns]
    filler = pd.DataFrame(float("nan"), index=canonical.index, columns=[*MOMENTUM_COLUMNS, *TTM_COLUMNS])
    return pd.concat([canonical, ratios, growth, ratio_growth, scores, extras, filler], axis=1).copy()


def _overlay_latest(
    out: pd.DataFrame,
    canonical: pd.DataFrame,
    price: pd.Series | None,
    price_asof: str | None,
    features: dict,
    frames: dict[tuple[str, str], pd.DataFrame],
    audited_frames: dict[tuple[str, str], pd.DataFrame] | None,
) -> None:
    """Latest-row-only columns, written in place: the price-derived momentum
    features (return_6m feeds momentum_rank; plus 12-1, 52-week-high
    proximity, 1y volatility — cross-sectional like the price itself) and the
    TTM sums + ratios (columns, not rows). The TTM source is the freshest
    clean four-quarter window (ttm.select_ttm)."""
    if not len(out):
        return
    last = len(out) - 1
    for col in MOMENTUM_COLUMNS:
        out.iloc[last, out.columns.get_loc(col)] = features.get(col, float("nan"))
    ttm = select_ttm(audited_frames, frames, price_asof)
    latest_price = price.iloc[-1] if price is not None else float("nan")
    latest_shares = price_shares(canonical).iloc[-1]
    market_cap_latest = (
        float(latest_price) * float(latest_shares)
        if pd.notna(latest_price) and pd.notna(latest_shares)
        else float("nan")
    )
    for col, value in {**ttm, **ttm_ratios(ttm, market_cap_latest)}.items():
        out.iloc[last, out.columns.get_loc(col)] = value


def _provenance(
    out: pd.DataFrame,
    symbol: str,
    canonical: pd.DataFrame,
    audited_fields: dict[str, list[str]],
    provider: str,
    price_asof: str | None,
    computed_at: float | None,
) -> pd.DataFrame:
    out.insert(0, "symbol", symbol)
    out.insert(1, "period", out.index.astype(str))
    out["provider"] = provider
    out["price_asof"] = price_asof
    out["audited_fields"] = [",".join(audited_fields.get(str(p), [])) or None for p in out["period"]]
    # FR-003 AC-2 — the provenance note naming the missing inputs: every NULL
    # ratio is explainable by the canonical fields the provider did not supply
    missing_per_period = canonical[CANONICAL_FIELDS].isna()
    out["missing_inputs"] = [
        ",".join(missing_per_period.columns[missing_per_period.loc[p]]) or None for p in canonical.index
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
    symbols = {d.name.split("=", 1)[1] for d in root.glob("provider=*/symbol=*") if d.is_dir()}
    return sorted(symbols)


UNIVERSE_COLUMNS = [
    "name",
    "country",
    "country_name",
    "region",
    "sector",
    "industry",
    "exchange",
    "currency",
    "isin",
    # the cap-census layer (universe_caps.py): screenable via the DSL
    # (top10k = true) and self-contained for every reader (ADR-0003)
    "top10k",
    "primary_listing",
    "cap_eur",
    "cap_rank_global",
    "company_group",
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


def _listing_currencies(data_dir: Path | str) -> dict[str, str]:
    """symbol → the currency the listing is quoted in (universe.parquet)."""
    path = Path(data_dir) / "universe.parquet"
    if not path.exists():
        return {}
    import pyarrow.parquet as pq

    if "currency" not in pq.ParquetFile(path).schema_arrow.names:
        return {}
    universe = pd.read_parquet(path, columns=["symbol", "currency"]).dropna()
    return dict(zip(universe["symbol"].astype(str), universe["currency"].astype(str), strict=True))


def _reporting_currency(audited: dict[tuple[str, str], pd.DataFrame]) -> str | None:
    """The statements' currency when an audited source records it (ESEF's
    ``_currency``) — None when no source says, and nothing is converted."""
    for key in (("income", "annual"), ("balance", "annual"), ("cashflow", "annual")):
        frame = audited.get(key)
        if frame is not None and "_currency" in frame.columns:
            known = frame["_currency"].dropna()
            if len(known):
                return str(known.iloc[-1])
    return None


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
    quote_currencies = _listing_currencies(data_dir)
    rates = load_rates(data_dir)
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
        # ESEF (EU) and Companies House (UK) don't overlap it.
        audited = merge_audited(
            latest_raw_frames(data_dir, symbol, provider="edgar"),
            latest_raw_frames(data_dir, symbol, provider="edgar-fsds"),
            latest_raw_frames(data_dir, symbol, provider="esef"),
            latest_raw_frames(data_dir, symbol, provider="companies-house"),
            # regions don't overlap — relative order between BR/TW is inert
            latest_raw_frames(data_dir, symbol, provider="cvm"),
            latest_raw_frames(data_dir, symbol, provider="twse"),
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
            currency=(quote_currencies.get(symbol), _reporting_currency(audited), rates),
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
# 8: short_term_debt canonical field + audited total_debt derivation
# 9: audit fixes — shares_outstanding_end, guarded multiples, gap-aware YoY,
#    in-house Piotroski, telescoped Dechow, fake ratios denied (ROIC & co),
#    reporting_currency (price converted into the statements' currency)
ENGINE_SCHEMA_VERSION = 9


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


def publish_incremental(data_dir: Path | str) -> pd.DataFrame | None:
    """Recompute only the symbols whose raw changed since the last build, reuse
    the cached per-symbol rows for the rest, re-finalize over everything and
    publish. Returns the published snapshot, or None when nothing changed (no
    republish); an empty frame when there is no raw data yet.

    The per-symbol stage is O(dirty); the cross-sectional finalize is O(all) but
    cheap. A ``base.parquet`` caches the pre-finalize rows so unchanged symbols
    are never rebuilt — the fix for full rebuilds at 20k+ issuers (F7).

    Ordering is the safety: the base (and its watermark, the compute START
    time) is written strictly AFTER the snapshot swap, so a finalize or publish
    that dies leaves the previous base and the next run redoes the work —
    never a base claiming a snapshot that was not published."""
    data_dir = Path(data_dir)
    started = time.time()
    built = _incremental_rows(data_dir)
    if built is None:
        return None
    rows, refresh_base = built
    snapshot = finalize_snapshot(rows, data_dir)
    if snapshot.empty:
        return snapshot
    publish_snapshot(snapshot, data_dir)
    if refresh_base:
        _publish_base(rows, data_dir, watermark=started)
    return snapshot


def _incremental_rows(data_dir: Path) -> tuple[pd.DataFrame, bool] | None:
    """(pre-finalize rows, whether the base cache must be rewritten), or None
    when the published snapshot is already current."""
    base_path = data_dir / "snapshot" / BASE_NAME
    symbols = crawled_symbols(data_dir)
    # no cache, or a cache built by a different engine schema (the nightly
    # restores base.parquet from the last release) → full rebuild
    if not base_path.exists() or _cached_schema_version(data_dir) != ENGINE_SCHEMA_VERSION:
        return build_symbol_rows(data_dir, symbols), True

    watermark = _base_watermark(data_dir)
    # a refreshed price distillate changes the price_quote / return_6m baked into
    # EVERY symbol's base row, so it makes them all dirty (F8) — otherwise the
    # base-persisted rows serve stale prices and value/momentum ranks.
    price_file = data_dir / "prices-latest.parquet"
    if price_file.exists() and price_file.stat().st_mtime > watermark:
        dirty = list(symbols)
    else:
        dirty = [s for s in symbols if _newest_raw_stamp(data_dir, s) > watermark]
    # the base cache may predate the schema (the nightly restores it from the
    # last release): scrub retired columns so kept rows can't resurrect them
    prev = _scrub_retired_columns(pd.read_parquet(base_path))
    known = set(prev["symbol"]) if "symbol" in prev.columns else set()
    # a symbol vanishing from the raw layer is also a change (drop its rows)
    dropped = known - set(symbols)
    if not dirty and not dropped:
        # per-symbol rows are current; the cross-sectional inputs (universe,
        # FX) may not be — or the snapshot itself is gone
        return (prev, False) if _snapshot_stale(data_dir) else None

    kept = prev[prev["symbol"].isin(set(symbols) - set(dirty))] if "symbol" in prev.columns else prev
    fresh = build_symbol_rows(data_dir, dirty) if dirty else pd.DataFrame()
    rows = pd.concat([kept, fresh], ignore_index=True) if not fresh.empty else kept.reset_index(drop=True)
    return rows, True


def _snapshot_stale(data_dir: Path) -> bool:
    """The published snapshot is missing, or older than an input only the
    finalize stage reads (universe.parquet, the ECB FX mirror)."""
    snapshot = data_dir / "snapshot" / SNAPSHOT_NAME
    if not snapshot.exists():
        return True
    published = snapshot.stat().st_mtime
    from crible.providers.fx import _mirror_file

    return any(
        path.exists() and path.stat().st_mtime > published
        for path in (data_dir / "universe.parquet", _mirror_file(data_dir))
    )


def _scrub_retired_columns(rows: pd.DataFrame) -> pd.DataFrame:
    """Columns the engine no longer emits: the always-NaN price-ratio growth
    companions and the RATIO_DENYLIST duplicates (plus their growths)."""
    retired = {f"{c}_growth" for c in price_dependent_ratio_columns()}
    retired |= set(RATIO_DENYLIST) | {f"{c}_growth" for c in RATIO_DENYLIST}
    return rows.drop(columns=[c for c in rows.columns if c in retired])


def _base_meta(data_dir: Path | str) -> dict:
    import json

    path = Path(data_dir) / "snapshot" / BASE_SCHEMA_NAME
    try:
        meta = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def _cached_schema_version(data_dir: Path | str) -> int | None:
    return _base_meta(data_dir).get("engine_schema_version")


def _base_watermark(data_dir: Path | str) -> float:
    """The start time of the compute that built the base; a base written
    before watermarks existed falls back to its file mtime."""
    watermark = _base_meta(data_dir).get("watermark")
    if isinstance(watermark, (int, float)):
        return float(watermark)
    return (Path(data_dir) / "snapshot" / BASE_NAME).stat().st_mtime


def _publish_base(rows: pd.DataFrame, data_dir: Path | str, watermark: float) -> None:
    import json

    directory = Path(data_dir) / "snapshot"
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / f".tmp-{BASE_NAME}"
    rows.to_parquet(tmp, index=False)
    tmp.rename(directory / BASE_NAME)
    (directory / BASE_SCHEMA_NAME).write_text(
        json.dumps({"engine_schema_version": ENGINE_SCHEMA_VERSION, "watermark": watermark})
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
