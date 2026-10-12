"""Dechow F-Score — misstatement probability. Model 1 (accounting core).

Dechow, Ge, Larson & Sloan (2011), *Predicting Material Accounting
Misstatements* (Contemporary Accounting Research 28(1)), Model 1 — the
variant built ONLY from financial-statement variables. Models 2–3 add
off-balance-sheet and market variables crible does not have (documented
deviation, like Mohanram's missing R&D/advertising).

```
logit = −7.893 + 0.790·rsst + 2.518·ch_rec + 1.191·ch_inv
        + 1.979·soft_assets + 0.171·ch_cs − 0.932·ch_roa + 1.029·issue
prob  = 1 / (1 + e^(−logit))
F     = prob / 0.0037        (the sample's unconditional misstatement rate)
```

Published reading: F ≥ 1 above-normal misstatement risk, ≥ 1.85 substantial,
≥ 2.45 high. Canonical-field proxies (each deviation deliberate, sign-safe):

- ``rsst`` accruals = (ΔWC + ΔNCO + ΔFIN) / avg TA with
  WC  = (current_assets − cash) − (current_liabilities − short-term debt),
  NCO = (TA − current_assets − marketable_securities)
        − (TL − current_liabilities − long_term_debt),
  FIN = marketable_securities − total_debt — no long-term-investments split
  and NO preferred_stock in the canonical vocabulary. The three telescope to
  Δ(TA − TL − cash), which is what is computed: the debt split and the
  marketable securities cancel out, so their absence no longer nulls F.
- ``ch_cs`` = % change of cash sales (revenue − Δreceivables), undefined
  when the base is not positive.
- ``issue`` mirrors Piotroski's dilution criterion: common_stock_issuance
  > 0, a parsed cash-flow statement without the line reading as no issuance
  (34.6 % populated — flagged in docs; Dechow's variable also counts debt
  issuance, out of scope here). Every Δ is against the prior FISCAL year
  (``prior_period``), NaN across a calendar gap.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from crible.compute.canonical import average, prior_period, yoy_growth

INTERCEPT = -7.893
COEFFICIENTS = {
    "dechow_rsst": 0.790,
    "dechow_ch_rec": 2.518,
    "dechow_ch_inv": 1.191,
    "dechow_soft_assets": 1.979,
    "dechow_ch_cs": 0.171,
    "dechow_ch_roa": -0.932,
    "dechow_issuance": 1.029,
}
BASE_RATE = 0.0037

DECHOW_COMPONENTS = list(COEFFICIENTS)


def _delta(series: pd.Series) -> pd.Series:
    return series - prior_period(series)


def dechow_components(canonical: pd.DataFrame) -> pd.DataFrame:
    c = canonical
    out = pd.DataFrame(index=canonical.index)
    avg_ta = average(c["total_assets"])

    # ΔWC + ΔNCO + ΔFIN telescoped (module docstring)
    out["dechow_rsst"] = (
        _delta(c["total_assets"] - c["total_liabilities"] - c["cash_and_equivalents"]) / avg_ta
    )

    out["dechow_ch_rec"] = _delta(c["accounts_receivable"]) / avg_ta
    out["dechow_ch_inv"] = _delta(c["inventory"]) / avg_ta
    out["dechow_soft_assets"] = (c["total_assets"] - c["net_ppe"] - c["cash_and_equivalents"]) / c[
        "total_assets"
    ]

    cash_sales = c["revenue"] - _delta(c["accounts_receivable"])
    out["dechow_ch_cs"] = yoy_growth(cash_sales)

    roa = c["net_income"] / avg_ta
    out["dechow_ch_roa"] = _delta(roa)

    # actual-issuance dummy — same reading as piotroski_no_dilution
    issued = c["common_stock_issuance"].mask(
        c["common_stock_issuance"].isna() & c["operating_cashflow"].notna(), 0.0
    )
    out["dechow_issuance"] = (issued > 0).astype(float).where(issued.notna())

    logit = INTERCEPT + sum(coefficient * out[component] for component, coefficient in COEFFICIENTS.items())
    out["dechow_f"] = (1.0 / (1.0 + np.exp(-logit))) / BASE_RATE
    return out
