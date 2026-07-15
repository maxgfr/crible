"""FR-015 — composite quality/value/momentum rank across the universe.

Percentile ranks (0-100) computed at snapshot BUILD time (the read path is
untouched — NFR-008), from columns the snapshot already publishes; no new data
source, no API key. The blend is deliberately small and published:

- quality  = mean pct(piotroski_f ↑, altman_z ↑)
- value    = mean pct(earnings_yield ↑, price_to_book_ratio ↓)
- momentum = pct(return_6m ↑)
- composite = mean of the AVAILABLE pillar ranks

Peer group is region×sector when it holds at least ``MIN_PEERS`` latest rows,
otherwise the whole snapshot (recorded per row in ``rank_peer_group``). A
pillar with ANY missing input stays NULL — never imputed (FR-015 AC-2) — and
the omission is recorded in ``rank_missing_pillars``. Only the latest fiscal
period per symbol is ranked: percentiles are cross-sectional, older periods
keep NULL.
"""

from __future__ import annotations

import pandas as pd

MIN_PEERS = 5

# input column → +1 (higher is better) or -1 (lower is better)
PILLARS: dict[str, dict[str, int]] = {
    "quality": {"piotroski_f": 1, "altman_z": 1},
    "value": {"earnings_yield": 1, "price_to_book_ratio": -1},
    "momentum": {"return_6m": 1},
}

# Greenblatt magic formula — a standalone rank blending earnings yield (EBIT/EV)
# and return on capital (EBIT/(NWC+net fixed assets)). Deliberately NOT folded
# into composite_rank so the quality/value/momentum blend stays stable.
MAGIC_INPUTS: dict[str, int] = {"greenblatt_earnings_yield": 1, "greenblatt_roc": 1}

RANK_COLUMNS = [f"{p}_rank" for p in PILLARS] + ["composite_rank", "magic_formula_rank"]


def price_return(bars: pd.DataFrame, days: int = 182) -> float:
    """Trailing price return over ``days`` calendar days from daily bars.

    NaN when the history does not reach back to the cutoff — never
    extrapolated (same never-impute rule as every other computed field).
    """
    if bars is None or not len(bars):
        return float("nan")
    close_col = next((c for c in ("Close", "close", "Adj Close") if c in bars.columns), None)
    date_col = next((c for c in ("Date", "date", "Datetime") if c in bars.columns), None)
    if close_col is None or date_col is None:
        return float("nan")
    frame = bars[[date_col, close_col]].dropna()
    if not len(frame):
        return float("nan")
    dates = pd.to_datetime(frame[date_col])
    last_date = dates.iloc[-1]
    cutoff = last_date - pd.Timedelta(days=days)
    base_rows = frame[dates <= cutoff]
    if not len(base_rows):
        return float("nan")
    base = float(base_rows[close_col].iloc[-1])
    last = float(frame[close_col].iloc[-1])
    if base == 0:
        return float("nan")
    return last / base - 1


def _pct(series: pd.Series, direction: int) -> pd.Series:
    """Percentile rank 0-100, deterministic (average ties), NaN-preserving."""
    return (direction * series).rank(pct=True, method="average") * 100


def _blend(group: pd.DataFrame, inputs: dict[str, int]) -> pd.Series:
    """Mean of the inputs' percentiles; NULL if ANY input is missing (AC-2: a
    blend missing an input is never imputed)."""
    pcts = [
        _pct(group[col], direction) if col in group.columns else pd.Series(float("nan"), index=group.index)
        for col, direction in inputs.items()
    ]
    blended = pd.concat(pcts, axis=1).mean(axis=1)
    has_all = pd.concat(
        [group[col].notna() if col in group.columns else pd.Series(False, index=group.index) for col in inputs],
        axis=1,
    ).all(axis=1)
    return blended.where(has_all)


def _rank_group(group: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=group.index)
    for pillar, inputs in PILLARS.items():
        out[f"{pillar}_rank"] = _blend(group, inputs)
    out["composite_rank"] = out[[f"{p}_rank" for p in PILLARS]].mean(axis=1)
    out["magic_formula_rank"] = _blend(group, MAGIC_INPUTS)
    missing = out[[f"{p}_rank" for p in PILLARS]].isna()
    out["rank_missing_pillars"] = [
        ",".join(p for p in PILLARS if missing.loc[i, f"{p}_rank"]) or None for i in out.index
    ]
    return out


def attach_ranks(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Attach FR-015 rank columns to the latest period row of each symbol."""
    if snapshot.empty or "symbol" not in snapshot.columns:
        return snapshot
    snapshot = snapshot.reset_index(drop=True)
    # add all rank columns in ONE concat, then defragment — inserting them
    # one-by-one fragments the ~150-column snapshot on every build (F3)
    new_cols = pd.DataFrame(
        {
            **{col: float("nan") for col in RANK_COLUMNS},
            "rank_peer_group": None,
            "rank_missing_pillars": None,
        },
        index=snapshot.index,
    )
    snapshot = pd.concat([snapshot, new_cols], axis=1).copy()

    period = snapshot["period"] if "period" in snapshot.columns else pd.Series("", index=snapshot.index)
    latest_idx = (
        snapshot.assign(_period=period.astype(str))
        .sort_values("_period")
        .groupby("symbol", sort=False)
        .tail(1)
        .index
    )
    latest = snapshot.loc[latest_idx]

    region = latest["region"] if "region" in latest.columns else pd.Series(None, index=latest.index)
    sector = latest["sector"] if "sector" in latest.columns else pd.Series(None, index=latest.index)
    pair = region.astype("string").str.cat(sector.astype("string"), sep="×")
    sizes = pair.groupby(pair).transform("size")
    group_key = pair.where(pair.notna() & (sizes >= MIN_PEERS), "global")

    for key, members in latest.groupby(group_key, sort=False):
        ranks = _rank_group(members)
        for col in ranks.columns:
            snapshot.loc[members.index, col] = ranks[col]
        snapshot.loc[members.index, "rank_peer_group"] = key
    return snapshot
