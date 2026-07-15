"""Mohanram G-Score (partial 6/8) — per-symbol inputs with hand-computed
values, then the cross-sectional peer-median signals with a fully
hand-checked 5-member peer group and the MIN_PEERS global fallback."""

from __future__ import annotations

import pandas as pd
import pytest

from crible.compute.mohanram import (
    MOHANRAM_SIGNALS,
    attach_mohanram,
    mohanram_inputs,
)
from crible.compute.ranks import MIN_PEERS


def test_mohanram_inputs_hand_computed() -> None:
    from crible.compute.canonical import CANONICAL_FIELDS

    periods = ["2022", "2023", "2024", "2025"]
    base = {f: [float("nan")] * 4 for f in CANONICAL_FIELDS}
    base.update(
        {
            "net_income": [80.0, 90.0, 100.0, 110.0],
            "operating_cashflow": [100.0, 110.0, 90.0, 130.0],
            "total_assets": [1000.0, 1000.0, 1000.0, 1000.0],
            "revenue": [1000.0, 1100.0, 1210.0, 1331.0],
            "capital_expenditure": [-50.0, -60.0, -70.0, -80.0],
        }
    )
    out = mohanram_inputs(pd.DataFrame(base, index=pd.Index(periods, name="period")))

    row = out.loc["2025"]
    assert row["mohanram_roa"] == pytest.approx(110.0 / 1000.0)
    assert row["mohanram_cfo_roa"] == pytest.approx(130.0 / 1000.0)
    assert row["mohanram_accruals_pass"] == 1.0  # CFO 130 > NI 110
    assert out.loc["2024", "mohanram_accruals_pass"] == 0.0  # CFO 90 < NI 100
    # capex is a negative outflow deflated by BEGINNING assets
    assert row["mohanram_capex_intensity"] == pytest.approx(80.0 / 1000.0)
    # variability needs 3 NON-NaN observations — roa itself is NaN in 2022
    # (averaged TA has no prior year), so the third valid point lands in 2025
    assert pd.isna(out.loc["2023", "mohanram_roa_var"])
    assert pd.isna(out.loc["2024", "mohanram_roa_var"])
    assert not pd.isna(out.loc["2025", "mohanram_roa_var"])
    # first period has no prior year — averaged-TA inputs are NaN
    assert pd.isna(out.loc["2022", "mohanram_roa"])


def _latest_frame() -> pd.DataFrame:
    """Five Tech peers with hand-pickable medians + two 'Micro' outliers that
    fall back to the global group."""
    n = 5
    frame = pd.DataFrame(
        {
            "symbol": [f"T{i}.PA" for i in range(n)] + ["M0.PA", "M1.PA"],
            "period": ["2025"] * (n + 2),
            "region": ["europe"] * (n + 2),
            "sector": ["Tech"] * n + ["Micro"] * 2,
            "mohanram_roa": [0.10, 0.08, 0.06, 0.04, 0.02, 0.30, 0.10],
            "mohanram_cfo_roa": [0.12, 0.10, 0.08, 0.06, 0.04, 0.35, 0.15],
            "mohanram_accruals_pass": [1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0],
            "mohanram_roa_var": [0.01, 0.02, 0.03, 0.04, 0.05, 0.01, 0.02],
            "mohanram_growth_var": [0.05, 0.04, 0.03, 0.02, 0.01, 0.01, 0.02],
            "mohanram_capex_intensity": [0.10, 0.08, 0.06, 0.04, 0.02, 0.09, 0.03],
        }
    )
    return frame


def test_mohanram_signals_hand_checked_medians() -> None:
    ranked = attach_mohanram(_latest_frame()).set_index("symbol")

    # Tech medians: roa 0.06 · cfo 0.08 · roa_var 0.03 · growth_var 0.03 · capex 0.06
    t0 = ranked.loc["T0.PA"]
    assert t0["mohanram_g1_roa"] == 1.0  # 0.10 > 0.06
    assert t0["mohanram_g2_cfo_roa"] == 1.0
    assert t0["mohanram_g3_accruals"] == 1.0
    assert t0["mohanram_g4_roa_stability"] == 1.0  # 0.01 < 0.03
    assert t0["mohanram_g5_growth_stability"] == 0.0  # 0.05 > 0.03
    assert t0["mohanram_g6_capex_intensity"] == 1.0
    assert t0["mohanram_g"] == 5.0

    t2 = ranked.loc["T2.PA"]  # sits exactly AT every median → strict compare = 0
    assert t2["mohanram_g"] == 0.0

    t4 = ranked.loc["T4.PA"]
    assert t4["mohanram_g"] == 1.0  # only growth stability (0.01 < 0.03) passes


def test_mohanram_small_peer_group_falls_back_to_global() -> None:
    assert MIN_PEERS > 2
    ranked = attach_mohanram(_latest_frame()).set_index("symbol")
    micro = ranked.loc[["M0.PA", "M1.PA"]]
    # the 2-member Micro sector ranks inside the global group — never dropped
    assert micro["mohanram_g"].notna().all()


def test_mohanram_missing_input_nulls_the_score_never_imputed() -> None:
    frame = _latest_frame()
    frame.loc[0, "mohanram_roa"] = float("nan")
    ranked = attach_mohanram(frame).set_index("symbol")
    assert pd.isna(ranked.loc["T0.PA", "mohanram_g1_roa"])
    assert pd.isna(ranked.loc["T0.PA", "mohanram_g"])  # skipna=False sum
    # peers still score (the median skips the NaN)
    assert ranked.loc["T1.PA", "mohanram_g"] == ranked.loc["T1.PA", MOHANRAM_SIGNALS].sum()


def test_mohanram_only_latest_rows_carry_signals() -> None:
    frame = _latest_frame()
    older = frame.assign(period="2024")
    both = pd.concat([older, frame], ignore_index=True)
    ranked = attach_mohanram(both)
    latest = ranked[ranked["period"] == "2025"]
    previous = ranked[ranked["period"] == "2024"]
    assert latest["mohanram_g"].notna().any()
    assert previous["mohanram_g"].isna().all()
