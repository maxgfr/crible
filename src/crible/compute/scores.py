"""FR-003 — the three headline scores.

Altman Z-Score is computed through financetoolkit's transparently-published
pure functions; Piotroski F-Score and Beneish M-Score are crible's in-house
implementations (Piotroski's financetoolkit criteria turn NaN into a fail and
compare accruals across two asset bases). Missing inputs propagate as NaN —
never imputed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from financetoolkit.models import altman_model

from crible.compute.beneish import beneish_components
from crible.compute.canonical import average, price_shares, prior_period
from crible.compute.montier import montier_components

PIOTROSKI_CRITERIA = [
    "piotroski_roa_positive",
    "piotroski_ocf_positive",
    "piotroski_roa_improving",
    "piotroski_accruals",
    "piotroski_leverage_decreasing",
    "piotroski_current_ratio_improving",
    "piotroski_no_dilution",
    "piotroski_gross_margin_improving",
    "piotroski_asset_turnover_improving",
]


def _criterion(passed: pd.Series, *inputs: pd.Series) -> pd.Series:
    """A ✓/✗ criterion that is NULL (undecidable) unless every input exists —
    a missing input is never scored as a fail, nor as a pass."""
    decidable = pd.concat(inputs, axis=1).notna().all(axis=1)
    return passed.astype("boolean").where(decidable)


def piotroski(canonical: pd.DataFrame) -> pd.DataFrame:
    """The nine published criteria (Piotroski 2000), in-house on gap-aware
    prior periods: each is NULL when an input or the prior year is missing,
    and piotroski_f is NULL unless all nine are decidable (never imputed)."""
    c = canonical
    avg_assets = average(c["total_assets"])
    roa = c["net_income"] / avg_assets
    leverage = c["total_debt"] / c["total_assets"]
    current_ratio = c["current_assets"] / c["current_liabilities"]
    gross_margin = (c["revenue"] - c["cost_of_goods_sold"]) / c["revenue"]
    turnover = c["revenue"] / avg_assets
    # a parsed cash-flow statement without an issuance line is a genuine
    # non-issuer (the shareholder_yield reading); no statement at all stays NULL
    issued = c["common_stock_issuance"].mask(
        c["common_stock_issuance"].isna() & c["operating_cashflow"].notna(), 0.0
    )

    def improving(metric: pd.Series, *, lower: bool = False) -> pd.Series:
        prev = prior_period(metric)
        return _criterion(metric < prev if lower else metric > prev, metric, prev)

    criteria = {
        "piotroski_roa_positive": _criterion(roa > 0, roa),
        "piotroski_ocf_positive": _criterion(c["operating_cashflow"] > 0, c["operating_cashflow"]),
        # ΔROA > 0 per the published definition (financetoolkit compares growth
        # acceleration instead — FinanceToolkit issue #91 [E39])
        "piotroski_roa_improving": improving(roa),
        # cash earnings exceed accrual earnings: CFO > NI on the SAME base
        # (financetoolkit divided the two sides by different asset totals)
        "piotroski_accruals": _criterion(
            c["operating_cashflow"] > c["net_income"], c["operating_cashflow"], c["net_income"]
        ),
        "piotroski_leverage_decreasing": improving(leverage, lower=True),
        "piotroski_current_ratio_improving": improving(current_ratio),
        "piotroski_no_dilution": _criterion(issued == 0, issued),
        "piotroski_gross_margin_improving": improving(gross_margin),
        "piotroski_asset_turnover_improving": improving(turnover),
    }
    out = pd.DataFrame(criteria, index=canonical.index)
    out["piotroski_f"] = out[PIOTROSKI_CRITERIA].astype(float).sum(axis=1, skipna=False)
    return out


def altman(canonical: pd.DataFrame, price: pd.Series | None = None) -> pd.DataFrame:
    c = canonical
    market_value_of_equity = (
        price * price_shares(c) if price is not None else pd.Series(float("nan"), index=c.index)
    )
    x1 = altman_model.get_working_capital_to_total_assets_ratio(c["working_capital"], c["total_assets"])
    x2 = altman_model.get_retained_earnings_to_total_assets_ratio(c["retained_earnings"], c["total_assets"])
    x3 = altman_model.get_earnings_before_interest_and_taxes_to_total_assets_ratio(
        c["earnings_before_interest_and_taxes"], c["total_assets"]
    )
    x4 = altman_model.get_market_value_of_equity_to_book_value_of_total_liabilities_ratio(
        market_value_of_equity, c["total_liabilities"]
    )
    x5 = altman_model.get_sales_to_total_assets_ratio(c["revenue"], c["total_assets"])
    # Z'' (Altman 2002) for non-manufacturers and emerging markets: no sales
    # term (asset turnover is an industry artefact) and BOOK equity instead of
    # the market value — so it also scores a company with no price
    x4_book = c["total_equity"] / c["total_liabilities"].where(c["total_liabilities"] > 0)
    return pd.DataFrame(
        {
            "altman_x1_wc_ta": x1,
            "altman_x2_re_ta": x2,
            "altman_x3_ebit_ta": x3,
            "altman_x4_mve_tl": x4,
            "altman_x5_s_ta": x5,
            "altman_z": altman_model.get_altman_z_score(x1, x2, x3, x4, x5),
            "altman_z_double_prime": 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4_book,
        },
        index=canonical.index,
    )


def zmijewski(canonical: pd.DataFrame) -> pd.DataFrame:
    """Zmijewski (1984) probit distress score — X > 0 (prob > 0.5) flags distress.

        X = -4.336 - 4.513*(net_income/total_assets)
                    + 5.679*(total_liabilities/total_assets)
                    + 0.004*(current_assets/current_liabilities)

    Three inputs, no prior period needed. Missing inputs propagate as NaN.
    """
    c = canonical
    roa = c["net_income"] / c["total_assets"]
    leverage = c["total_liabilities"] / c["total_assets"]
    liquidity = c["current_assets"] / c["current_liabilities"]
    score = -4.336 - 4.513 * roa + 5.679 * leverage + 0.004 * liquidity
    return pd.DataFrame({"zmijewski_score": score}, index=canonical.index)


def ohlson(canonical: pd.DataFrame) -> pd.DataFrame:
    """Ohlson (1980) O-Score logit distress model — prob = 1/(1+e^-O), O > 0
    (prob > 0.5) flags distress. Uses the prior period like Beneish.

        O = -1.32 - 0.407*log(total_assets) + 6.03*(TL/TA) - 1.43*(WC/TA)
            + 0.0757*(CL/CA) - 1.72*OENEG - 2.37*(NI/TA) - 1.83*(FFO/TL)
            + 0.285*INTWO - 0.521*CHIN

    Two documented deviations from the 1980 paper (crible is multi-currency and
    provider-agnostic, unlike the US-firm sample Ohlson fitted):
    - the size term uses log(total_assets) directly instead of dividing total
      assets by a US GNP price-level index (base 1968);
    - funds-from-operations is proxied by operating cash flow (alternative:
      net_income + depreciation_and_amortization).
    OENEG/INTWO comparisons against NaN yield 0, but the arithmetic terms carry
    the NaN through, so any missing input still nulls the whole score.
    """
    c = canonical
    ta = c["total_assets"]
    tl = c["total_liabilities"]
    ni = c["net_income"]
    size = np.log(ta.where(ta > 0))
    oeneg = (tl > ta).astype(float)
    prev_ni = prior_period(ni)
    intwo = ((ni < 0) & (prev_ni < 0)).astype(float)
    chin = (ni - prev_ni) / (ni.abs() + prev_ni.abs())
    o = (
        -1.32
        - 0.407 * size
        + 6.03 * (tl / ta)
        - 1.43 * (c["working_capital"] / ta)
        + 0.0757 * (c["current_liabilities"] / c["current_assets"])
        - 1.72 * oeneg
        - 2.37 * (ni / ta)
        - 1.83 * (c["operating_cashflow"] / tl)
        + 0.285 * intwo
        - 0.521 * chin
    )
    return pd.DataFrame({"ohlson_o": o}, index=canonical.index)


def all_scores(canonical: pd.DataFrame, price: pd.Series | None = None) -> pd.DataFrame:
    from crible.compute.dechow import dechow_components
    from crible.compute.mohanram import mohanram_inputs

    return pd.concat(
        [
            piotroski(canonical),
            altman(canonical, price),
            beneish_components(canonical),
            zmijewski(canonical),
            ohlson(canonical),
            montier_components(canonical),
            dechow_components(canonical),
            # per-symbol inputs only — the peer-relative signals + mohanram_g
            # attach at finalize (cross-sectional, like the FR-015 ranks)
            mohanram_inputs(canonical),
        ],
        axis=1,
    )
