"""Mohanram G-Score (2005) — growth-stock quality. PARTIAL: 6 of 8 signals.

Mohanram ("Separating Winners from Losers among Low Book-to-Market Stocks",
2005) scores growth stocks on fundamentals the way Piotroski scores value
stocks. Two of the paper's eight signals need R&D and advertising intensity —
neither field exists in the canonical vocabulary (no provider maps them), so
crible publishes an explicitly PARTIAL 0–6 variant. The paper's 6-of-8 cutoff
does not transfer; the score deliberately gets no color verdict in the UI.

Two stages, like the FR-015 ranks:
- per-symbol (here): the raw inputs on every period row —
  ``mohanram_inputs``;
- cross-sectional (``attach_mohanram``, called from finalize_snapshot):
  peer-group medians (region×sector, ranks.peer_group_key) turn the inputs
  into 0/1 signals on the LATEST row + ``mohanram_g`` = their sum with
  ``skipna=False`` — one undecidable signal nulls the score, never imputed.
"""

from __future__ import annotations

import pandas as pd

MOHANRAM_INPUTS = [
    "mohanram_roa", "mohanram_cfo_roa", "mohanram_accruals_pass",
    "mohanram_roa_var", "mohanram_growth_var", "mohanram_capex_intensity",
]

MOHANRAM_SIGNALS = [
    "mohanram_g1_roa", "mohanram_g2_cfo_roa", "mohanram_g3_accruals",
    "mohanram_g4_roa_stability", "mohanram_g5_growth_stability",
    "mohanram_g6_capex_intensity",
]


def _avg(series: pd.Series) -> pd.Series:
    return (series + series.shift(1)) / 2


def mohanram_inputs(canonical: pd.DataFrame) -> pd.DataFrame:
    """The per-symbol inputs the cross-sectional stage compares to peers."""
    c = canonical
    out = pd.DataFrame(index=canonical.index)
    avg_ta = _avg(c["total_assets"])
    out["mohanram_roa"] = c["net_income"] / avg_ta
    out["mohanram_cfo_roa"] = c["operating_cashflow"] / avg_ta
    # G3 is per-symbol, not peer-relative: earnings backed by cash (CFO > NI)
    diff = c["operating_cashflow"] - c["net_income"]
    out["mohanram_accruals_pass"] = (diff > 0).astype(float).where(diff.notna())
    # variability signals need at least 3 observations — expanding over the
    # available history (EDGAR's 8 fiscal years qualifies broadly)
    out["mohanram_roa_var"] = out["mohanram_roa"].expanding(min_periods=3).var()
    growth = c["revenue"].pct_change(fill_method=None)
    out["mohanram_growth_var"] = growth.expanding(min_periods=3).var()
    # capex intensity deflated by BEGINNING assets (the paper's deflator);
    # canonical capex is a negative outflow — flip the sign
    out["mohanram_capex_intensity"] = -c["capital_expenditure"] / c["total_assets"].shift(1)
    return out


def _signal_vs_median(group: pd.Series, *, above: bool) -> pd.Series:
    """0/1 vs the peer median; NaN inputs (or an undecidable median) stay NaN."""
    median = group.median()
    if pd.isna(median):
        return pd.Series(float("nan"), index=group.index)
    passed = (group > median) if above else (group < median)
    return passed.astype(float).where(group.notna())


def mohanram_signals(members: pd.DataFrame) -> pd.DataFrame:
    """One peer group's latest rows → the six 0/1 signals + mohanram_g."""
    out = pd.DataFrame(index=members.index)
    out["mohanram_g1_roa"] = _signal_vs_median(members["mohanram_roa"], above=True)
    out["mohanram_g2_cfo_roa"] = _signal_vs_median(members["mohanram_cfo_roa"], above=True)
    out["mohanram_g3_accruals"] = members["mohanram_accruals_pass"]
    out["mohanram_g4_roa_stability"] = _signal_vs_median(members["mohanram_roa_var"], above=False)
    out["mohanram_g5_growth_stability"] = _signal_vs_median(members["mohanram_growth_var"], above=False)
    out["mohanram_g6_capex_intensity"] = _signal_vs_median(
        members["mohanram_capex_intensity"], above=True
    )
    # one undecidable signal nulls the score — the house never-impute rule
    out["mohanram_g"] = out[MOHANRAM_SIGNALS].sum(axis=1, skipna=False)
    return out


def attach_mohanram(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Attach the peer-relative signals + score to each symbol's latest row."""
    from crible.compute.ranks import latest_period_index, peer_group_key

    if snapshot.empty or "symbol" not in snapshot.columns:
        return snapshot
    if any(col not in snapshot.columns for col in MOHANRAM_INPUTS):
        return snapshot
    snapshot = snapshot.reset_index(drop=True)
    new_cols = pd.DataFrame(
        {col: float("nan") for col in [*MOHANRAM_SIGNALS, "mohanram_g"]},
        index=snapshot.index,
    )
    snapshot = pd.concat([snapshot, new_cols], axis=1).copy()

    latest = snapshot.loc[latest_period_index(snapshot)]
    for _key, members in latest.groupby(peer_group_key(latest), sort=False):
        signals = mohanram_signals(members)
        for col in signals.columns:
            snapshot.loc[members.index, col] = signals[col]
    return snapshot
