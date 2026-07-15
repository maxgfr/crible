"""FR-003 — extra value / cash-quality metrics computed alongside the scores.

Kept out of ratios.py because financetoolkit does not publish these (Graham
number, Graham NCAV net-net, Greenblatt magic-formula components), and out of
scores.py because several are price-dependent: like Altman's market value of
equity, the price applies to the LATEST fiscal period only (older periods keep
NaN rather than pretending historical prices). Missing inputs propagate as NaN,
never imputed. The two Greenblatt columns feed ``magic_formula_rank`` in ranks.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_extras(canonical: pd.DataFrame, price: pd.Series | None = None) -> pd.DataFrame:
    c = canonical
    ebit = c["earnings_before_interest_and_taxes"]
    out = pd.DataFrame(index=canonical.index)

    # cash / earnings quality — no price needed
    out["ebitda_margin"] = c["ebitda"] / c["revenue"]
    out["fcf_margin"] = c["free_cash_flow"] / c["revenue"]
    out["fcf_conversion"] = c["free_cash_flow"] / c["net_income"]
    # abs() tolerates either sign convention for the reported outflow; 0 → NaN
    # (a non-payer has undefined coverage, not infinite)
    out["dividend_coverage"] = c["net_income"] / c["dividends_paid"].abs().replace(0, float("nan"))

    # Greenblatt magic-formula: return on capital = EBIT / (NWC + net fixed assets)
    out["greenblatt_roc"] = ebit / (c["working_capital"] + c["net_ppe"])

    # Graham deep-value: net current asset value (strict net-net)
    out["ncav"] = c["current_assets"] - c["total_liabilities"]

    # price-dependent block — latest fiscal period only, like Altman x4
    if price is not None:
        shares = c["shares_outstanding"]
        market_cap = price * shares
        enterprise_value = market_cap + c["total_debt"] - c["cash_and_equivalents"]
        eps = c["net_income"] / shares
        bvps = c["total_equity"] / shares
        # Graham number √(22.5·EPS·BVPS): only defined for positive EPS AND BVPS
        graham_base = 22.5 * eps * bvps
        out["graham_number"] = np.sqrt(graham_base.where((eps > 0) & (bvps > 0)))
        out["graham_margin_of_safety"] = out["graham_number"] / price - 1
        out["ncav_to_market_cap"] = out["ncav"] / market_cap
        out["greenblatt_earnings_yield"] = ebit / enterprise_value
    else:
        for col in (
            "graham_number",
            "graham_margin_of_safety",
            "ncav_to_market_cap",
            "greenblatt_earnings_yield",
        ):
            out[col] = float("nan")

    return out
