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
  and NO preferred_stock in the canonical vocabulary.
- ``ch_cs`` = % change of cash sales (revenue − Δreceivables), undefined
  when the base is not positive.
- ``issue`` mirrors Piotroski's dilution criterion: common_stock_issuance
  ``fillna(0) > 0`` (34.6 % populated — flagged in docs; Dechow's variable
  also counts debt issuance, out of scope here).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

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


def _avg(series: pd.Series) -> pd.Series:
    return (series + series.shift(1)) / 2


def dechow_components(canonical: pd.DataFrame) -> pd.DataFrame:
    c = canonical
    out = pd.DataFrame(index=canonical.index)
    avg_ta = _avg(c["total_assets"])

    short_term_debt = c["total_debt"] - c["long_term_debt"]
    wc = (c["current_assets"] - c["cash_and_equivalents"]) - (
        c["current_liabilities"] - short_term_debt
    )
    nco = (c["total_assets"] - c["current_assets"] - c["marketable_securities"]) - (
        c["total_liabilities"] - c["current_liabilities"] - c["long_term_debt"]
    )
    fin = c["marketable_securities"] - c["total_debt"]
    out["dechow_rsst"] = (wc.diff() + nco.diff() + fin.diff()) / avg_ta

    out["dechow_ch_rec"] = c["accounts_receivable"].diff() / avg_ta
    out["dechow_ch_inv"] = c["inventory"].diff() / avg_ta
    out["dechow_soft_assets"] = (
        c["total_assets"] - c["net_ppe"] - c["cash_and_equivalents"]
    ) / c["total_assets"]

    cash_sales = c["revenue"] - c["accounts_receivable"].diff()
    out["dechow_ch_cs"] = (cash_sales / cash_sales.shift(1) - 1).where(cash_sales.shift(1) > 0)

    roa = c["net_income"] / avg_ta
    out["dechow_ch_roa"] = roa.diff()

    # actual-issuance dummy — same fillna(0) stance as piotroski_no_dilution
    out["dechow_issuance"] = (c["common_stock_issuance"].fillna(0) > 0).astype(float)

    logit = INTERCEPT + sum(
        coefficient * out[component] for component, coefficient in COEFFICIENTS.items()
    )
    out["dechow_f"] = (1.0 / (1.0 + np.exp(-logit))) / BASE_RATE
    return out
