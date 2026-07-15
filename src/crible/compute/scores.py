"""FR-003 — the three headline scores.

Piotroski F-Score and Altman Z-Score are computed through financetoolkit's
transparently-published pure functions; Beneish M-Score is crible's in-house
implementation (absent from financetoolkit). Missing inputs propagate as NaN —
never imputed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from financetoolkit.models import altman_model, piotroski_model

from crible.compute.beneish import beneish_components
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


def _avg(series: pd.Series) -> pd.Series:
    return (series + series.shift(1)) / 2


def _wide(series: pd.Series) -> pd.DataFrame:
    """financetoolkit's criteria diff along axis='columns' — periods as columns."""
    return series.to_frame("v").T


def piotroski(canonical: pd.DataFrame) -> pd.DataFrame:
    c = canonical
    avg_assets = _avg(c["total_assets"])
    issued = c["common_stock_issuance"].fillna(0)

    criteria = {
        "piotroski_roa_positive": piotroski_model.get_return_on_assets_criteria(
            _wide(c["net_income"]), _wide(avg_assets)
        ),
        "piotroski_ocf_positive": piotroski_model.get_operating_cashflow_criteria(
            _wide(c["operating_cashflow"])
        ),
        # In-house per the published definition (ΔROA > 0, i.e. ROA_t > ROA_{t-1}):
        # financetoolkit's criterion compares growth acceleration instead —
        # the exact deviation reported in FinanceToolkit issue #91 [E39].
        "piotroski_roa_improving": _wide(
            (c["net_income"] / avg_assets) > (c["net_income"] / avg_assets).shift(1)
        ),
        "piotroski_accruals": piotroski_model.get_accruals_criteria(
            _wide(c["net_income"]), _wide(avg_assets), _wide(c["operating_cashflow"]), _wide(c["total_assets"])
        ),
        "piotroski_leverage_decreasing": piotroski_model.get_change_in_leverage_criteria(
            _wide(c["total_debt"]), _wide(c["total_assets"])
        ),
        "piotroski_current_ratio_improving": piotroski_model.get_change_in_current_ratio_criteria(
            _wide(c["current_assets"]), _wide(c["current_liabilities"])
        ),
        "piotroski_no_dilution": piotroski_model.get_number_of_shares_criteria(_wide(issued)),
        "piotroski_gross_margin_improving": piotroski_model.get_gross_margin_criteria(
            _wide(c["revenue"]), _wide(c["cost_of_goods_sold"])
        ),
        "piotroski_asset_turnover_improving": piotroski_model.get_asset_turnover_ratio_criteria(
            _wide(c["revenue"]), _wide(avg_assets)
        ),
    }
    flat = {name: value.iloc[0] for name, value in criteria.items()}
    out = pd.DataFrame(flat, index=canonical.index)
    score = piotroski_model.get_piotroski_score(*(criteria[name] for name in PIOTROSKI_CRITERIA))
    out["piotroski_f"] = score.iloc[0]
    return out


def altman(canonical: pd.DataFrame, price: pd.Series | None = None) -> pd.DataFrame:
    c = canonical
    market_value_of_equity = (
        price * c["shares_outstanding"] if price is not None else pd.Series(float("nan"), index=c.index)
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
    return pd.DataFrame(
        {
            "altman_x1_wc_ta": x1,
            "altman_x2_re_ta": x2,
            "altman_x3_ebit_ta": x3,
            "altman_x4_mve_tl": x4,
            "altman_x5_s_ta": x5,
            "altman_z": altman_model.get_altman_z_score(x1, x2, x3, x4, x5),
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
    intwo = ((ni < 0) & (ni.shift(1) < 0)).astype(float)
    chin = (ni - ni.shift(1)) / (ni.abs() + ni.shift(1).abs())
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
    from crible.compute.mohanram import mohanram_inputs

    return pd.concat(
        [
            piotroski(canonical),
            altman(canonical, price),
            beneish_components(canonical),
            zmijewski(canonical),
            ohlson(canonical),
            montier_components(canonical),
            # per-symbol inputs only — the peer-relative signals + mohanram_g
            # attach at finalize (cross-sectional, like the FR-015 ranks)
            mohanram_inputs(canonical),
        ],
        axis=1,
    )
