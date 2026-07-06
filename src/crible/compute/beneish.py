"""FR-003 — Beneish M-Score, implemented in-house (absent from financetoolkit).

Published 8-variable model (Beneish, "The Detection of Earnings Manipulation",
Financial Analysts Journal 1999):

    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
        + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

M > -1.78 flags a likely earnings manipulator.
"""

from __future__ import annotations

import pandas as pd

COEFFICIENTS = {
    "dsri": 0.920,
    "gmi": 0.528,
    "aqi": 0.404,
    "sgi": 0.892,
    "depi": 0.115,
    "sgai": -0.172,
    "tata": 4.679,
    "lvgi": -0.327,
}
INTERCEPT = -4.84
RED_FLAG_THRESHOLD = -1.78

COMPONENT_COLUMNS = [f"beneish_{c}" for c in COEFFICIENTS]


def beneish_components(canonical: pd.DataFrame) -> pd.DataFrame:
    """Compute the 8 components + M per period (needs the prior period)."""
    c = canonical

    def prev(series: pd.Series) -> pd.Series:
        return series.shift(1)

    receivable_to_sales = c["accounts_receivable"] / c["revenue"]
    dsri = receivable_to_sales / prev(receivable_to_sales)

    gross_margin = (c["revenue"] - c["cost_of_goods_sold"]) / c["revenue"]
    gmi = prev(gross_margin) / gross_margin

    hard_assets = (c["current_assets"] + c["net_ppe"]) / c["total_assets"]
    aqi = (1 - hard_assets) / (1 - prev(hard_assets))

    sgi = c["revenue"] / prev(c["revenue"])

    dep_rate = c["depreciation_and_amortization"] / (
        c["depreciation_and_amortization"] + c["net_ppe"]
    )
    depi = prev(dep_rate) / dep_rate

    sga_to_sales = c["sga_expenses"] / c["revenue"]
    sgai = sga_to_sales / prev(sga_to_sales)

    leverage = (c["long_term_debt"] + c["current_liabilities"]) / c["total_assets"]
    lvgi = leverage / prev(leverage)

    tata = (c["net_income"] - c["operating_cashflow"]) / c["total_assets"]

    out = pd.DataFrame(
        {
            "beneish_dsri": dsri,
            "beneish_gmi": gmi,
            "beneish_aqi": aqi,
            "beneish_sgi": sgi,
            "beneish_depi": depi,
            "beneish_sgai": sgai,
            "beneish_tata": tata,
            "beneish_lvgi": lvgi,
        },
        index=canonical.index,
    )
    out["beneish_m"] = INTERCEPT + sum(
        COEFFICIENTS[name] * out[f"beneish_{name}"] for name in COEFFICIENTS
    )
    return out
