"""Price-derived momentum features — ONE implementation for every path.

The trailing-return rule used to live in three places (compute.ranks'
price_return, ingest.price_import._distill, and the DuckDB SQL inside
import_huggingface) — docs/TODO.md flagged the drift risk. This module is now
the single source: the crawl path (build_symbol_snapshot), the dump
distillates and ranks' momentum input all funnel through it.

Features (latest fiscal row only, like every price-derived value):
- ``return_6m``            trailing 182-day return — the momentum_rank input
- ``return_12_1``          Jegadeesh-Titman (1993) classic: the 12-month
                           return skipping the most recent 30 days
- ``high_52w_proximity``   close / 365-day high (1.0 = at the high)
- ``volatility_1y``        annualized std of daily log returns over 365 days

The published price window (price_series.SERIES_WINDOW_DAYS = 400) leaves 35
days of slack for the 12-month base. A base the history does not reach is
NaN — never extrapolated, the house rule.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

RETURN_6M_DAYS = 182
SKIP_DAYS = 30
YEAR_DAYS = 365
TRADING_DAYS_PER_YEAR = 252

FEATURE_COLUMNS = ["return_6m", "return_12_1", "high_52w_proximity", "volatility_1y"]

_EMPTY = {col: float("nan") for col in FEATURE_COLUMNS}


def _clean(dates: pd.Series, closes: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame(
        {"date": pd.to_datetime(dates.reset_index(drop=True)),
         "close": pd.to_numeric(closes.reset_index(drop=True), errors="coerce")}
    ).dropna()
    return frame[frame["close"] > 0].sort_values("date")


def _last_close_at_or_before(frame: pd.DataFrame, cutoff: pd.Timestamp) -> float:
    rows = frame[frame["date"] <= cutoff]
    return float(rows["close"].iloc[-1]) if len(rows) else float("nan")


def _ratio_return(numerator: float, base: float) -> float:
    if math.isnan(numerator) or math.isnan(base) or base == 0:
        return float("nan")
    return numerator / base - 1.0


def trailing_return(dates: pd.Series, closes: pd.Series, days: int) -> float:
    """Last close over the last close at or before asof − days, minus 1."""
    frame = _clean(dates, closes)
    if frame.empty:
        return float("nan")
    asof = frame["date"].iloc[-1]
    base = _last_close_at_or_before(frame, asof - pd.Timedelta(days=days))
    return _ratio_return(float(frame["close"].iloc[-1]), base)


def momentum_features(dates: pd.Series, closes: pd.Series) -> dict | None:
    """{close, price_asof, return_6m, return_12_1, high_52w_proximity,
    volatility_1y} from daily bars — None when no usable bar exists."""
    frame = _clean(dates, closes)
    if frame.empty:
        return None
    close = float(frame["close"].iloc[-1])
    asof = frame["date"].iloc[-1]

    base_6m = _last_close_at_or_before(frame, asof - pd.Timedelta(days=RETURN_6M_DAYS))
    recent = _last_close_at_or_before(frame, asof - pd.Timedelta(days=SKIP_DAYS))
    base_12m = _last_close_at_or_before(frame, asof - pd.Timedelta(days=YEAR_DAYS))

    year = frame[frame["date"] > asof - pd.Timedelta(days=YEAR_DAYS)]
    high = float(year["close"].max()) if len(year) else float("nan")

    # volatility needs the same full-year reach as the 12-month return —
    # a short window would understate risk, so it stays NaN instead
    if math.isnan(base_12m) or len(year) < 2:
        volatility = float("nan")
    else:
        log_returns = np.diff(np.log(year["close"].to_numpy()))
        volatility = float(log_returns.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))

    return {
        "close": close,
        "price_asof": str(asof.date()) if hasattr(asof, "date") else str(asof)[:10],
        "return_6m": _ratio_return(close, base_6m),
        "return_12_1": _ratio_return(recent, base_12m),
        "high_52w_proximity": close / high if not math.isnan(high) and high != 0 else float("nan"),
        "volatility_1y": volatility,
    }


def bars_features(bars: pd.DataFrame | None) -> dict[str, float]:
    """The FEATURE_COLUMNS from a raw daily-bars frame (tolerates the
    Close/close/Adj Close and Date/date/Datetime spellings); all-NaN when the
    frame is unusable."""
    if bars is None or not len(bars):
        return dict(_EMPTY)
    close_col = next((c for c in ("Close", "close", "Adj Close") if c in bars.columns), None)
    date_col = next((c for c in ("Date", "date", "Datetime") if c in bars.columns), None)
    if close_col is None or date_col is None:
        return dict(_EMPTY)
    features = momentum_features(bars[date_col], bars[close_col])
    if features is None:
        return dict(_EMPTY)
    return {col: features[col] for col in FEATURE_COLUMNS}
