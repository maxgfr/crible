"""FR-003 / ADR-0003 — the wide snapshot: build, publish (atomic swap), read.

One row per company × fiscal period: canonical fields, financetoolkit ratios,
year-over-year growth series, Piotroski/Altman/Beneish scores, provenance
metadata. Published by write-temp-then-rename so readers never observe a
half-written snapshot.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
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
from crible.ingest.raw import RawInventory, iter_raw_files
from crible.providers.audited import merge_audited
from crible.providers.fx import load_rates, price_factor, quote_currency

log = logging.getLogger("crible.compute.snapshot")

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
    splits: list[tuple[str, float]] | None = None,
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
    if price is not None and price_asof and _stale_period(canonical.index[-1], price_asof):
        # a 2015 fiscal year priced at today's close is no P/E at all
        price = pd.Series(float("nan"), index=price.index)
    reporting = currency[1] if currency else None
    if price is not None and currency:
        factor = price_factor(*currency)
        # an all-NaN price keeps the price-ratio columns, empty
        price = price * factor if factor is not None else pd.Series(float("nan"), index=price.index)
    if price is not None:
        # a split after the fiscal year end: the statements still count the
        # old shares, so the price goes back to their basis (BKNG's 25:1 put
        # its market cap at 4 % of the real one)
        price = price * _split_factor(canonical, frames, splits or [], price_asof, audited_fields)

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
    from crible.providers.edgar import MIN_PLAUSIBLE_SHARES

    audited = build_canonical(audited_frames)
    # raw parsed before the source floor existed still carries MCD's 713.4
    # "shares": a scale error never outranks the scraped count
    for column in ("shares_outstanding", "shares_outstanding_end"):
        audited[column] = audited[column].where(audited[column] >= MIN_PLAUSIBLE_SHARES)
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


def _split_factor(
    canonical: pd.DataFrame,
    frames: dict[tuple[str, str], pd.DataFrame],
    splits: list[tuple[str, float]],
    price_asof: str | None,
    audited_fields: dict[str, list[str]],
) -> float:
    """Cumulative split ratio between the latest period's share count and the
    price: splits dated after the period end (and, when the count is Yahoo's,
    after the statements' fetch — Yahoo restates counts for past splits), up
    to the price date. Sources: the crawled bars' "Stock Splits" column and
    the dump's split events."""
    from crible.compute.canonical import period_dates

    period = canonical.index[-1]
    end = period_dates(pd.Index([period])).iloc[0]
    if pd.isna(end):
        return 1.0
    after = end
    if "shares_outstanding" not in audited_fields.get(str(period), []):
        fetched = [
            pd.to_datetime(frame["_fetched_at"].max(), unit="s")
            for key, frame in frames.items()
            if key[0] in ("income", "balance")
            and "_fetched_at" in frame.columns
            and frame["_fetched_at"].notna().any()
        ]
        if fetched:
            after = max(after, max(fetched))
    until = pd.to_datetime(str(price_asof)[:10], errors="coerce") if price_asof else pd.NaT
    events = list(splits)
    bars = frames.get(("prices", "daily"))
    if bars is not None and "Stock Splits" in bars.columns:
        date_col = next((c for c in ("Date", "date", "Datetime") if c in bars.columns), None)
        if date_col:
            hits = bars[pd.to_numeric(bars["Stock Splits"], errors="coerce").fillna(0) > 0]
            events += [
                (str(d)[:10], float(r)) for d, r in zip(hits[date_col], hits["Stock Splits"], strict=True)
            ]
    factor, seen = 1.0, set()
    for day, ratio in events:
        when = pd.to_datetime(str(day)[:10], errors="coerce")
        if (
            pd.isna(when)
            or when <= after
            or (pd.notna(until) and when > until)
            or ratio <= 0
            or str(day)[:10] in seen
        ):
            continue
        seen.add(str(day)[:10])  # the same split from both sources counts once
        factor *= ratio
    return factor


def _load_splits(data_dir: Path | str) -> dict[str, list[tuple[str, float]]]:
    """symbol → [(date, ratio)] from the dump's split events ("25:1")."""
    path = Path(data_dir) / "events" / "defeatbeta-splits.parquet"
    if not path.exists():
        return {}
    out: dict[str, list[tuple[str, float]]] = {}
    for symbol, day, text in pd.read_parquet(path, columns=["symbol", "date", "split_factor"]).itertuples(
        index=False
    ):
        try:
            new, old = str(text).split(":", 1)
            ratio = float(new) / float(old)
        except (ValueError, ZeroDivisionError):
            continue
        out.setdefault(str(symbol), []).append((str(day)[:10], ratio))
    return out


# the latest fiscal period must end within this many days of the price date
# for a price-based multiple to mean anything (an annual report lands ~3
# months after year end, the next one 12 months later — 18 months is the
# outer edge of "the latest accounts")
MAX_PRICED_PERIOD_AGE_DAYS = 550


def _stale_period(period, price_asof: str) -> bool:
    from crible.compute.canonical import period_dates

    end = period_dates(pd.Index([period])).iloc[0]
    priced = pd.to_datetime(str(price_asof)[:10], errors="coerce")
    return pd.notna(end) and pd.notna(priced) and (priced - end).days > MAX_PRICED_PERIOD_AGE_DAYS


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
    data_dir: Path | str, symbol: str, provider: str = "*", inventory: RawInventory | None = None
) -> dict[tuple[str, str], pd.DataFrame]:
    """Pick the newest raw Parquet per (statement_type, freq) for a symbol —
    from ``inventory`` when given (one scan for the whole build), else by
    walking that symbol's directories."""
    if inventory is not None and provider != "*":
        return {key: pd.read_parquet(path) for key, path in inventory.files(provider, symbol).items()}
    safe_symbol = symbol.replace("/", "_")
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    root = Path(data_dir) / "raw"
    for directory in root.glob(f"provider={provider}/symbol={safe_symbol}"):
        for file in iter_raw_files(directory):
            statement_type, freq, _ = file.stem.split("-", 2)
            frames[(statement_type, freq)] = pd.read_parquet(file)
    return frames


def crawled_symbols(data_dir: Path | str, inventory: RawInventory | None = None) -> list[str]:
    inventory = inventory if inventory is not None else RawInventory.scan(data_dir)
    return sorted(inventory.symbols())


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
    """symbol → the currency the listing's PRICE is in (universe.parquet,
    minor units resolved — fx.quote_currency)."""
    path = Path(data_dir) / "universe.parquet"
    if not path.exists():
        return {}
    import pyarrow.parquet as pq

    if "currency" not in pq.ParquetFile(path).schema_arrow.names:
        return {}
    universe = pd.read_parquet(path, columns=["symbol", "currency"]).dropna()
    return {
        symbol: quote_currency(symbol, currency)
        for symbol, currency in zip(
            universe["symbol"].astype(str), universe["currency"].astype(str), strict=True
        )
    }


def _crawled_quote_currency(frames: dict[tuple[str, str], pd.DataFrame]) -> str | None:
    """The currency Yahoo quotes the crawled bars in (GBp, USD…), recorded
    at crawl time — it beats the universe's listed currency, which for
    CCEP.L is the EUR it reports in while it trades in pence."""
    bars = frames.get(("prices", "daily"))
    if bars is None or "_quote_currency" not in bars.columns:
        return None
    known = bars["_quote_currency"].dropna()
    return str(known.iloc[-1]) if len(known) else None


def _reporting_currency(audited: dict[tuple[str, str], pd.DataFrame]) -> str | None:
    """The statements' currency when a source records it (ESEF's and the
    crawl's ``_currency``) — None when no source says, and nothing is
    converted."""
    for key in (("income", "annual"), ("balance", "annual"), ("cashflow", "annual")):
        frame = audited.get(key)
        if frame is not None and "_currency" in frame.columns:
            known = frame["_currency"].dropna()
            if len(known):
                return str(known.iloc[-1])
    return None


# the SEC ticker directory republished with each filer's financial
# currency (defeatbeta) — mirrored daily as reference data: 1,445 US listings
# report in another currency than their USD quote (TM in JPY: P/E 0.06)
STATEMENT_CURRENCIES_URL = (
    "https://huggingface.co/datasets/defeatbeta/yahoo-finance-data/resolve/main/data/US/company_tickers.json"
)
STATEMENT_CURRENCIES_FILE = ("defeatbeta", "company_tickers.json")


def load_statement_currencies(data_dir: Path | str) -> dict[str, str]:
    """ticker → the currency its statements are in, {} without the mirror."""
    import json

    path = Path(data_dir) / "mirror" / STATEMENT_CURRENCIES_FILE[0] / STATEMENT_CURRENCIES_FILE[1]
    try:
        entries = json.loads(path.read_text()).values()
    except (OSError, ValueError, AttributeError):
        return {}
    return {
        str(e["ticker"]).strip().upper(): str(e["financial_currency"]).strip()
        for e in entries
        if isinstance(e, dict) and e.get("ticker") and e.get("financial_currency")
    }


# US derivative lines of a listed company (SPAC warrants, units, rights): Yahoo
# serves them the company's statements, and ratios on a $0.05 warrant price
# topped the net-net preset (TNONW: NCAV 23,654× its "market cap")
DERIVATIVE_SUFFIXES = ("WS", "WT", "UN", "RT", "W", "U", "R")
# a suffix without separator is Nasdaq's 5th letter after a 4-letter base
# (DAVEW, ACAHU): on a shorter base it is a coincidence between two
# companies (MU is not M + U, PHR not PH + R)
DERIVATIVE_BASE_LENGTH = 4


def derivative_listings(universe: set[str]) -> set[str]:
    """Symbols that are a listed base symbol plus a derivative suffix."""
    out = set()
    for symbol in universe:
        cut = max(symbol.rfind("."), symbol.rfind("-"))
        if cut >= 0:
            # NYSE spells them with a separator (RAC-WS, KCAC-UN); share
            # classes (BRK-B), preferreds (BAC-PL) and exchange suffixes
            # (SAP.DE, REI-UN.TO) end in no derivative suffix and stay
            if symbol[cut + 1 :] in DERIVATIVE_SUFFIXES and symbol[:cut] in universe:
                out.add(symbol)
            continue
        for suffix in DERIVATIVE_SUFFIXES:
            base = symbol[: -len(suffix)]
            if symbol.endswith(suffix) and len(base) >= DERIVATIVE_BASE_LENGTH and base in universe:
                out.add(symbol)
                break
    return out


def _universe_symbols(data_dir: Path | str) -> set[str]:
    path = Path(data_dir) / "universe.parquet"
    if not path.exists():
        return set()
    return set(pd.read_parquet(path, columns=["symbol"])["symbol"].astype(str))


# the currency each audited source files in, by construction of its parser
# (ESEF records its own per filing as _currency)
AUDITED_CURRENCIES = {
    "edgar": "USD",
    "edgar-fsds": "USD",
    "companies-house": "GBP",
    "cvm": "BRL",
    "twse": "TWD",
}


def _audited_currency(per_provider: dict[str, dict[tuple[str, str], pd.DataFrame]]) -> str | None:
    """The reporting currency of the audited layer: its first source (in
    precedence order) that holds frames."""
    for provider, frames in per_provider.items():
        if not frames:
            continue
        if provider in AUDITED_CURRENCIES:
            return AUDITED_CURRENCIES[provider]
        return _reporting_currency(frames)
    return None


# overlapping audited/scraped cells further apart than this, consistently,
# are two currencies (or units), not a restatement
CURRENCY_CONFLICT_FACTOR = 2.0


def _currency_conflict(
    scraped: dict[tuple[str, str], pd.DataFrame],
    audited: dict[tuple[str, str], pd.DataFrame],
    audited_currency: str | None,
) -> bool:
    """True when the scraped and audited statements are not in one currency:
    both declare theirs and they differ, or — raw written before currencies
    were recorded — the overlapping values sit wholesale apart (median
    ratio beyond 2× across at least three cells)."""
    scraped_currency = _reporting_currency(scraped)
    if scraped_currency and audited_currency:
        return scraped_currency != audited_currency
    a, s = build_canonical(audited), build_canonical(scraped)
    if a.empty or s.empty:
        return False
    from crible.compute.reconcile import align_periods

    a = align_periods(a, s.index)
    common = a.index.intersection(s.index)
    columns = [
        c for c in ("revenue", "total_assets", "total_equity", "net_income", "operating_cashflow") if c in a
    ]
    ratios = (a.loc[common, columns] / s.loc[common, columns]).abs().stack()
    ratios = ratios[np.isfinite(ratios) & (ratios > 0)]
    if len(ratios) < 3:
        return False
    median = float(ratios.median())
    return not (1 / CURRENCY_CONFLICT_FACTOR <= median <= CURRENCY_CONFLICT_FACTOR)


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


# the audited layer, merge order IS precedence: US companyfacts wins recent
# periods and FSDS backfills the deep history; ESEF (EU) and Companies House
# (UK) don't overlap it; regions don't overlap — relative order between BR/TW
# is inert
AUDITED_PRECEDENCE = ("edgar", "edgar-fsds", "esef", "companies-house", "cvm", "twse")


class ComputeStopped(Exception):
    """A stop was requested mid-build: nothing is published."""


def build_symbol_rows(
    data_dir: Path | str,
    symbols: list[str],
    inventory: RawInventory | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> pd.DataFrame:
    """The per-symbol stage: canonical fields + ratios + scores + price for each
    symbol, BEFORE the cross-sectional finalize (universe/FX/ranks). This is the
    expensive part — the seam incremental compute recomputes for changed symbols
    only."""
    quotes = _price_quotes(data_dir)
    quote_currencies = _listing_currencies(data_dir)
    rates = load_rates(data_dir)
    splits = _load_splits(data_dir)
    statement_currencies = load_statement_currencies(data_dir)
    # the raw layer's own symbols count as bases too: a warrant the SEC
    # directory maps to its parent's CIK (DAVEW) is not in the universe
    derivatives = derivative_listings(_universe_symbols(data_dir) | set(symbols))
    # ONE scan of the raw layer for the whole build (it used to be 8 globs
    # per symbol — the dominant cost at 20k symbols)
    inventory = inventory if inventory is not None else RawInventory.scan(data_dir)
    parts = []
    for symbol in symbols:
        if should_stop is not None and should_stop():
            raise ComputeStopped(symbol)
        if symbol in derivatives:
            continue  # a warrant/unit/right is not the company: no ratios on its price
        scraped = latest_raw_frames(data_dir, symbol, provider="yfinance", inventory=inventory)
        scraped_provider = "yfinance"
        if not any(key[0] in ("income", "balance", "cashflow") for key in scraped):
            # last-resort fallback: defeatbeta statements (Yahoo-derived dump,
            # only imported for symbols no other source serves). Crawled
            # yfinance frames — including prices-daily — keep their keys.
            fallback = latest_raw_frames(data_dir, symbol, provider="defeatbeta", inventory=inventory)
            if fallback:
                scraped = {**fallback, **scraped}
                scraped_provider = "defeatbeta"
        # the audited layer, per region (a listing realistically has one)
        per_provider = {
            audited_provider: latest_raw_frames(
                data_dir, symbol, provider=audited_provider, inventory=inventory
            )
            for audited_provider in AUDITED_PRECEDENCE
        }
        audited = merge_audited(*per_provider.values())
        if not scraped and not audited:
            continue
        audited_currency = _audited_currency(per_provider)
        if scraped and audited and _currency_conflict(scraped, audited, audited_currency):
            # VALE3.SA: CVM files in BRL, Yahoo reports in USD — a cell-by-cell
            # merge put BRL debt next to USD capex in one row. The audited
            # filing stands alone; the crawl keeps only its price bars
            log.warning(
                "snapshot %s: scraped and audited statements are in different currencies — audited only",
                symbol,
            )
            scraped = {key: frame for key, frame in scraped.items() if key[0] == "prices"}
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
            currency=(
                _crawled_quote_currency(scraped) or quote_currencies.get(symbol),
                audited_currency or _reporting_currency(scraped) or statement_currencies.get(symbol),
                rates,
            ),
            splits=splits.get(symbol),
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
# the price-distillate rows the base was built with (one fingerprint per symbol)
BASE_QUOTES_NAME = "base-quotes.parquet"
# Bump on EVERY commit that adds or removes per-symbol snapshot columns
# (tests/test_engine_schema.py enforces it) or changes their values.
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
#    reporting_currency (price converted into the statements' currency),
#    roic, gross_profitability, net_share_issuance, positive_fcf_years_5y,
#    altman_z_double_prime
# 10: values only, no new column — but every kept row must be redone: ROIC
#     capital floor, issuance unit guard, crawled quote currency (pence),
#     warrants outside the universe. Value-changing fixes bump too.
ENGINE_SCHEMA_VERSION = 10


def publish_incremental(
    data_dir: Path | str, should_stop: Callable[[], bool] | None = None
) -> pd.DataFrame | None:
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
    quotes = _quote_fingerprints(data_dir)
    built = _incremental_rows(data_dir, quotes, should_stop)
    if built is None:
        return None
    rows, refresh_base = built
    snapshot = finalize_snapshot(rows, data_dir)
    if snapshot.empty:
        return snapshot
    publish_snapshot(snapshot, data_dir)
    if refresh_base:
        _publish_base(rows, data_dir, watermark=started, quotes=quotes)
    return snapshot


def _quote_fingerprints(data_dir: Path) -> pd.DataFrame:
    """symbol → a hash of the price-distillate fields a base row bakes in
    (close, as-of, momentum features) — never the import stamp, which moves
    on every row at each import."""
    from crible.ingest.price_import import load_prices_latest

    table = load_prices_latest(data_dir)
    columns = [c for c in ("close", "price_asof", *MOMENTUM_COLUMNS) if c in table.columns]
    if table.empty:
        return pd.DataFrame({"symbol": pd.Series(dtype=str), "fingerprint": pd.Series(dtype="uint64")})
    hashed = pd.util.hash_pandas_object(table[columns].astype(str), index=False)
    return pd.DataFrame({"symbol": table["symbol"].astype(str).to_numpy(), "fingerprint": hashed.to_numpy()})


def _changed_quote_symbols(data_dir: Path, quotes: pd.DataFrame) -> set[str] | None:
    """Symbols whose distillate row differs from the one the base was built
    with (added, removed or changed); None when the base predates the record."""
    try:
        previous = pd.read_parquet(data_dir / "snapshot" / BASE_QUOTES_NAME)
    except (OSError, ValueError):
        return None
    merged = previous.merge(quotes, on="symbol", how="outer", suffixes=("_was", "_now"))
    return set(merged.loc[merged["fingerprint_was"] != merged["fingerprint_now"], "symbol"].astype(str))


def _incremental_rows(
    data_dir: Path, quotes: pd.DataFrame, should_stop: Callable[[], bool] | None = None
) -> tuple[pd.DataFrame, bool] | None:
    """(pre-finalize rows, whether the base cache must be rewritten), or None
    when the published snapshot is already current."""
    base_path = data_dir / "snapshot" / BASE_NAME
    inventory = RawInventory.scan(data_dir)
    symbols = crawled_symbols(data_dir, inventory=inventory)
    # no cache, or a cache built by a different engine schema (the nightly
    # restores base.parquet from the last release) → full rebuild
    if not base_path.exists() or _cached_schema_version(data_dir) != ENGINE_SCHEMA_VERSION:
        return build_symbol_rows(data_dir, symbols, inventory=inventory, should_stop=should_stop), True

    watermark = _base_watermark(data_dir)
    # a refreshed price distillate changes the price_quote / return_6m baked into
    # base rows (F8): the symbols whose distillate row moved are dirty — all of
    # them when the base predates that record (a 14-symbol Stooq import used to
    # cost a 36 min full rebuild)
    dirty = [s for s in symbols if inventory.newest_stamp(s) > watermark]
    price_file = data_dir / "prices-latest.parquet"
    if price_file.exists() and price_file.stat().st_mtime > watermark:
        moved = _changed_quote_symbols(data_dir, quotes)
        dirty = list(symbols) if moved is None else [s for s in symbols if s in moved or s in set(dirty)]
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
    fresh = (
        build_symbol_rows(data_dir, dirty, inventory=inventory, should_stop=should_stop)
        if dirty
        else pd.DataFrame()
    )
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


def _publish_base(
    rows: pd.DataFrame, data_dir: Path | str, watermark: float, quotes: pd.DataFrame | None = None
) -> None:
    import json

    directory = Path(data_dir) / "snapshot"
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / f".tmp-{BASE_NAME}"
    rows.to_parquet(tmp, index=False)
    tmp.rename(directory / BASE_NAME)
    if quotes is not None:
        tmp = directory / f".tmp-{BASE_QUOTES_NAME}"
        quotes.to_parquet(tmp, index=False)
        tmp.rename(directory / BASE_QUOTES_NAME)
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
