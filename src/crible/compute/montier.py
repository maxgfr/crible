"""FR-003 — Montier C-Score, implemented in-house (a 6-flag earnings-manipulation
checklist that complements Beneish M).

James Montier, "Cooking the Books, or, More Sailing Under the Black Flag" (2008):
six binary red flags of aggressive accounting. Each raised flag adds 1, so the
score runs 0–6 and a company at 5–6 is an aggressive-accounting candidate. Every
flag compares the current period with the prior one, so the first period (and any
period whose inputs are missing) is NaN — never imputed, like Beneish.

Unlike Piotroski's criteria (where a raised flag ✓ is GOOD), a raised Montier flag
means BAD, so the flags are kept as 0/1 counters rather than ✓/✗.
"""

from __future__ import annotations

import pandas as pd

FLAG_COLUMNS = [
    "montier_ni_cfo_diverging",
    "montier_dso_rising",
    "montier_dsi_rising",
    "montier_oca_to_rev_rising",
    "montier_depr_declining",
    "montier_asset_growth_high",
]

ASSET_GROWTH_THRESHOLD = 0.10
RED_FLAG_THRESHOLD = 5  # 5–6 raised flags → aggressive-accounting candidate


def montier_components(canonical: pd.DataFrame) -> pd.DataFrame:
    """Compute the 6 flags + C per period (needs the prior period)."""
    c = canonical

    def prev(series: pd.Series) -> pd.Series:
        return series.shift(1)

    def rising(metric: pd.Series) -> pd.Series:
        """1 where the metric rose vs the prior period, NaN where undecidable."""
        p = prev(metric)
        return (metric > p).astype(float).where(metric.notna() & p.notna())

    def falling(metric: pd.Series) -> pd.Series:
        p = prev(metric)
        return (metric < p).astype(float).where(metric.notna() & p.notna())

    ni_cfo_gap = c["net_income"] - c["operating_cashflow"]
    dso = c["accounts_receivable"] / c["revenue"]
    dsi = c["inventory"] / c["cost_of_goods_sold"]
    other_current_assets = (
        c["current_assets"] - c["cash_and_equivalents"] - c["accounts_receivable"] - c["inventory"]
    )
    oca_to_rev = other_current_assets / c["revenue"]
    dep_rate = c["depreciation_and_amortization"] / c["gross_ppe"]
    asset_growth = c["total_assets"] / prev(c["total_assets"]) - 1

    out = pd.DataFrame(
        {
            "montier_ni_cfo_diverging": rising(ni_cfo_gap),
            "montier_dso_rising": rising(dso),
            "montier_dsi_rising": rising(dsi),
            "montier_oca_to_rev_rising": rising(oca_to_rev),
            "montier_depr_declining": falling(dep_rate),
            "montier_asset_growth_high": (asset_growth > ASSET_GROWTH_THRESHOLD)
            .astype(float)
            .where(asset_growth.notna()),
        },
        index=canonical.index,
    )
    # a flag we could not decide nulls the whole score (never imputed)
    out["montier_c"] = out[FLAG_COLUMNS].sum(axis=1, skipna=False)
    return out
