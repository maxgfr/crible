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


def _avg(series: pd.Series) -> pd.Series:
    return (series + series.shift(1)) / 2


def _cagr_3y(series: pd.Series) -> pd.Series:
    """3-year compound annual growth rate, defined only when both endpoints
    are positive — fractional powers of negatives are undefined, and a
    sign-flipped growth rate would be worse than a missing one."""
    growth = (series / series.shift(3)) ** (1 / 3) - 1
    return growth.where((series > 0) & (series.shift(3) > 0))


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
    # Rule of 40 (Feld): YoY revenue growth + FCF margin. Computes its own
    # revenue growth from the same pct_change the snapshot's *_growth block
    # runs later — the two always agree.
    out["rule_of_40"] = c["revenue"].pct_change(fill_method=None) + out["fcf_margin"]
    # Sloan (1996) accruals: (NI − OCF) / AVERAGE total assets — deliberately
    # averaged per the paper, unlike beneish_tata which deflates by ending TA
    out["sloan_accruals"] = (c["net_income"] - c["operating_cashflow"]) / _avg(c["total_assets"])
    # 3-year trajectory as first-class, filterable columns (needs 4 periods —
    # EDGAR's 8-year depth qualifies); peg_ratio divides by EXACTLY this CAGR
    out["revenue_cagr_3y"] = _cagr_3y(c["revenue"])
    out["net_income_cagr_3y"] = _cagr_3y(c["net_income"])

    # Greenblatt magic-formula: return on capital = EBIT / (NWC + net fixed assets).
    # Non-positive invested capital would sign-flip the ratio (negative EBIT over a
    # negative denominator reads as a high return) and corrupt magic_formula_rank,
    # so it is undefined there — NaN, never imputed.
    invested_capital = c["working_capital"] + c["net_ppe"]
    out["greenblatt_roc"] = ebit / invested_capital.where(invested_capital > 0)

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
        # non-positive enterprise value sign-flips the yield → undefined (NaN)
        out["greenblatt_earnings_yield"] = ebit / enterprise_value.where(enterprise_value > 0)
        # PEG (Lynch): P/E over the 3-year earnings CAGR expressed in percent
        # (PEG 1 ⇔ P/E equals the growth rate) — the SAME published
        # net_income_cagr_3y column, one definition. A shrinking company has
        # no PEG.
        pe = market_cap / c["net_income"].where(c["net_income"] > 0)
        ni_cagr = out["net_income_cagr_3y"]
        out["peg_ratio"] = pe / (ni_cagr * 100).where(ni_cagr > 0)
        # total shareholder yield: dividends + net buybacks over market cap.
        # Buybacks are proxied by the share-count decline valued at the current
        # price (issuance reads negative — dilution shows up as a drag);
        # missing inputs propagate as NaN, never a fabricated zero. One reading
        # is not a fabrication: a PARSED cash-flow statement (operating_cashflow
        # present) with no dividends line is a genuine non-payer — dividends are
        # truly zero there, so the computable buyback signal survives.
        dividends = c["dividends_paid"].abs()
        dividends = dividends.mask(dividends.isna() & c["operating_cashflow"].notna(), 0.0)
        buyback_value = (shares.shift(1) - shares) * price
        out["shareholder_yield"] = (dividends + buyback_value) / market_cap
    else:
        for col in (
            "graham_number",
            "graham_margin_of_safety",
            "ncav_to_market_cap",
            "greenblatt_earnings_yield",
            "peg_ratio",
            "shareholder_yield",
        ):
            out[col] = float("nan")

    return out
