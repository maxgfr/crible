"""FR-003 — ratio and score computation into a wide snapshot.

Beneish reference vectors are hand-derived from the published 1999 formula
(M = -4.84 + 0.920 DSRI + 0.528 GMI + 0.404 AQI + 0.892 SGI + 0.115 DEPI
 - 0.172 SGAI + 4.679 TATA - 0.327 LVGI): an all-flat company and a fully
worked example whose components are analytically exact.
"""

from __future__ import annotations

import pandas as pd
import pytest

from crible.compute.beneish import beneish_components
from crible.compute.canonical import build_canonical
from crible.compute.extras import compute_extras
from crible.compute.montier import montier_components
from crible.compute.scores import altman, ohlson, piotroski, zmijewski
from crible.compute.snapshot import build_symbol_snapshot, publish_snapshot, read_snapshot


def income_frame(rows: dict[str, list[float]], periods: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"period": periods, **rows})


def canonical_from(values: dict[str, dict[str, list[float]]], periods: list[str]) -> pd.DataFrame:
    frames = {
        (stmt, "annual"): income_frame(rows, periods) for stmt, rows in values.items()
    }
    return build_canonical(frames)


# ------------------------------------------------------------------ canonical


def test_fr003_canonical_maps_yfinance_vocabulary() -> None:
    canonical = canonical_from(
        {
            "income": {"TotalRevenue": [1000.0], "CostOfRevenue": [600.0], "NetIncome": [80.0]},
            "balance": {"TotalAssets": [1000.0], "CurrentAssets": [500.0], "CurrentLiabilities": [200.0]},
            "cashflow": {"OperatingCashFlow": [60.0], "CapitalExpenditure": [-20.0]},
        },
        ["2025"],
    )
    row = canonical.loc["2025"]
    assert row["revenue"] == 1000.0
    assert row["cost_of_goods_sold"] == 600.0
    # transparent derivations
    assert row["gross_profit"] == 400.0
    assert row["working_capital"] == 300.0
    assert row["free_cash_flow"] == 40.0


def test_fr003_missing_statement_yields_null_never_fabricated() -> None:
    canonical = canonical_from(
        {"income": {"TotalRevenue": [1000.0], "NetIncome": [80.0]}},
        ["2025"],
    )
    row = canonical.loc["2025"]
    assert pd.isna(row["operating_cashflow"])
    assert pd.isna(row["total_assets"])
    # the row still exists — company not dropped
    assert row["revenue"] == 1000.0


def test_fr003_ebitda_derived_from_ebit_plus_depreciation() -> None:
    canonical = canonical_from(
        {"income": {"TotalRevenue": [1000.0], "EBIT": [150.0], "ReconciledDepreciation": [50.0]}},
        ["2025"],
    )
    # transparent derivation when the provider does not publish EBITDA directly
    assert canonical.loc["2025", "ebitda"] == 200.0


# -------------------------------------------------------------------- beneish

FLAT = {
    "income": {
        "TotalRevenue": [1000.0, 1000.0],
        "CostOfRevenue": [600.0, 600.0],
        "SellingGeneralAndAdministration": [100.0, 100.0],
        "NetIncome": [60.0, 60.0],
        "ReconciledDepreciation": [50.0, 50.0],
    },
    "balance": {
        "TotalAssets": [1000.0, 1000.0],
        "CurrentAssets": [500.0, 500.0],
        "CurrentLiabilities": [200.0, 200.0],
        "AccountsReceivable": [100.0, 100.0],
        "NetPPE": [400.0, 400.0],
        "LongTermDebt": [100.0, 100.0],
    },
    "cashflow": {"OperatingCashFlow": [60.0, 60.0]},
}

WORKED = {
    "income": {
        "TotalRevenue": [1000.0, 1200.0],
        "CostOfRevenue": [600.0, 780.0],
        "SellingGeneralAndAdministration": [100.0, 130.0],
        "NetIncome": [80.0, 100.0],
        "ReconciledDepreciation": [50.0, 55.0],
    },
    "balance": {
        "TotalAssets": [1000.0, 1150.0],
        "CurrentAssets": [500.0, 550.0],
        "CurrentLiabilities": [200.0, 230.0],
        "AccountsReceivable": [100.0, 150.0],
        "NetPPE": [400.0, 420.0],
        "LongTermDebt": [100.0, 130.0],
    },
    "cashflow": {"OperatingCashFlow": [60.0, 60.0]},
}


def test_fr003_beneish_flat_company_matches_published_formula() -> None:
    out = beneish_components(canonical_from(FLAT, ["2024", "2025"]))
    row = out.loc["2025"]
    for comp in ("dsri", "gmi", "aqi", "sgi", "depi", "sgai", "lvgi"):
        assert row[f"beneish_{comp}"] == pytest.approx(1.0, abs=1e-9)
    assert row["beneish_tata"] == pytest.approx(0.0, abs=1e-9)
    # M = -4.84 + sum(coefs) with all indexes at 1, TATA at 0
    assert row["beneish_m"] == pytest.approx(-2.480, abs=0.01)


def test_fr003_beneish_worked_example_components_are_analytically_exact() -> None:
    out = beneish_components(canonical_from(WORKED, ["2024", "2025"]))
    row = out.loc["2025"]
    expected = {
        "beneish_dsri": 1.25,
        "beneish_gmi": 0.4 / 0.35,
        "beneish_aqi": (1 - 970 / 1150) / (1 - 900 / 1000),
        "beneish_sgi": 1.2,
        "beneish_depi": (50 / 450) / (55 / 475),
        "beneish_sgai": (130 / 1200) / (100 / 1000),
        "beneish_lvgi": (360 / 1150) / (300 / 1000),
        "beneish_tata": 40 / 1150,
    }
    for name, value in expected.items():
        assert row[name] == pytest.approx(value, abs=1e-6), name
    assert row["beneish_m"] == pytest.approx(-1.6383, abs=0.01)
    # above the published red-flag threshold of -1.78
    assert row["beneish_m"] > -1.78


# ------------------------------------------------------------------ piotroski

IMPROVING = {
    "income": {
        "TotalRevenue": [1000.0, 1200.0, 1500.0],
        "CostOfRevenue": [700.0, 800.0, 950.0],
        "NetIncome": [50.0, 80.0, 120.0],
    },
    "balance": {
        "TotalAssets": [1000.0, 1040.0, 1080.0],
        "CurrentAssets": [400.0, 450.0, 500.0],
        "CurrentLiabilities": [200.0, 210.0, 220.0],
        "TotalDebt": [300.0, 290.0, 270.0],
    },
    "cashflow": {"OperatingCashFlow": [100.0, 150.0, 200.0], "CommonStockIssuance": [0.0, 0.0, 0.0]},
}


def test_fr003_piotroski_perfect_year_scores_nine() -> None:
    out = piotroski(canonical_from(IMPROVING, ["2023", "2024", "2025"]))
    assert out.loc["2025", "piotroski_f"] == 9
    # the score is always the sum of its nine visible criteria
    criteria_sum = sum(int(out.loc["2025", c]) for c in out.columns if c != "piotroski_f")
    assert out.loc["2025", "piotroski_f"] == criteria_sum


# --------------------------------------------------------------------- altman


def test_fr003_altman_z_matches_hand_computed_value() -> None:
    canonical = canonical_from(
        {
            "income": {"TotalRevenue": [1000.0], "EBIT": [150.0], "BasicAverageShares": [100.0]},
            "balance": {
                "TotalAssets": [1000.0],
                "WorkingCapital": [200.0],
                "RetainedEarnings": [300.0],
                "TotalLiabilitiesNetMinorityInterest": [400.0],
            },
        },
        ["2025"],
    )
    price = pd.Series([6.0], index=canonical.index)
    out = altman(canonical, price)
    # Z = 1.2*0.2 + 1.4*0.3 + 3.3*0.15 + 0.6*1.5 + 1.0*1.0 = 3.055
    assert out.loc["2025", "altman_z"] == pytest.approx(3.055, abs=0.01)


# ------------------------------------------------------------------ zmijewski


def test_fr003_zmijewski_matches_hand_computed_value() -> None:
    canonical = canonical_from(
        {
            "income": {"NetIncome": [80.0]},
            "balance": {
                "TotalAssets": [1000.0],
                "TotalLiabilitiesNetMinorityInterest": [400.0],
                "CurrentAssets": [500.0],
                "CurrentLiabilities": [200.0],
            },
        },
        ["2025"],
    )
    out = zmijewski(canonical)
    # X = -4.336 - 4.513*0.08 + 5.679*0.4 + 0.004*2.5 = -2.41544 (X<0 → safe)
    assert out.loc["2025", "zmijewski_score"] == pytest.approx(-2.41544, abs=1e-5)


# --------------------------------------------------------------------- ohlson

OHLSON_FRAME = {
    "income": {"NetIncome": [50.0, 80.0]},
    "balance": {
        "TotalAssets": [1000.0, 1000.0],
        "TotalLiabilitiesNetMinorityInterest": [400.0, 400.0],
        "CurrentAssets": [500.0, 500.0],
        "CurrentLiabilities": [200.0, 200.0],
    },
    "cashflow": {"OperatingCashFlow": [100.0, 100.0]},
}


def test_fr003_ohlson_o_matches_hand_computed_value() -> None:
    out = ohlson(canonical_from(OHLSON_FRAME, ["2024", "2025"]))
    # Hand-worked from the 1980 coefficients (natural log; size = log(total_assets);
    # FFO ≈ operating cash flow; WC = CA-CL = 300; CHIN = 30/130): O ≈ -2.8855.
    assert out.loc["2025", "ohlson_o"] == pytest.approx(-2.8855, abs=1e-3)
    # needs the prior period → the first period is NaN, never fabricated
    assert pd.isna(out.loc["2024", "ohlson_o"])


# -------------------------------------------------------------------- montier

# A fully aggressive company: every one of the six Montier flags is raised.
MONTIER_MANIP = {
    "income": {
        "TotalRevenue": [1000.0, 1200.0],
        "CostOfRevenue": [600.0, 700.0],
        "NetIncome": [100.0, 150.0],
        "ReconciledDepreciation": [50.0, 40.0],
    },
    "balance": {
        "TotalAssets": [1000.0, 1200.0],
        "CurrentAssets": [500.0, 800.0],
        "AccountsReceivable": [100.0, 200.0],
        "Inventory": [200.0, 300.0],
        "CashAndCashEquivalents": [100.0, 100.0],
        "GrossPPE": [500.0, 500.0],
    },
    "cashflow": {"OperatingCashFlow": [120.0, 100.0]},
}


def test_fr003_montier_c_flags_aggressive_accounting() -> None:
    out = montier_components(canonical_from(MONTIER_MANIP, ["2024", "2025"]))
    row = out.loc["2025"]
    for flag in (
        "montier_ni_cfo_diverging", "montier_dso_rising", "montier_dsi_rising",
        "montier_oca_to_rev_rising", "montier_depr_declining", "montier_asset_growth_high",
    ):
        assert row[flag] == 1.0, flag
    assert row["montier_c"] == 6
    # the prior period cannot be decided (nothing before it) → NaN, never 0
    assert pd.isna(out.loc["2024", "montier_c"])


def test_fr003_montier_c_null_when_a_flag_input_is_missing() -> None:
    frame = {k: {**v} for k, v in MONTIER_MANIP.items()}
    del frame["balance"]["GrossPPE"]  # depreciation-rate flag undecidable
    out = montier_components(canonical_from(frame, ["2024", "2025"]))
    assert pd.isna(out.loc["2025", "montier_depr_declining"])
    assert pd.isna(out.loc["2025", "montier_c"])  # a missing flag nulls the score


# ----------------------------------------------------------------- extras (value)

EXTRAS_FRAME = {
    "income": {
        "TotalRevenue": [1000.0],
        "EBIT": [150.0],
        "ReconciledDepreciation": [50.0],
        "NetIncome": [100.0],
    },
    "balance": {
        "TotalAssets": [1000.0],
        "CurrentAssets": [500.0],
        "CurrentLiabilities": [200.0],
        "TotalLiabilitiesNetMinorityInterest": [400.0],
        "StockholdersEquity": [900.0],
        "NetPPE": [400.0],
        "TotalDebt": [200.0],
        "CashAndCashEquivalents": [100.0],
        "BasicAverageShares": [100.0],
    },
    "cashflow": {"FreeCashFlow": [80.0], "CashDividendsPaid": [-40.0]},
}


def test_fr003_extras_value_and_quality_metrics_are_exact() -> None:
    canonical = canonical_from(EXTRAS_FRAME, ["2025"])
    price = pd.Series([10.0], index=canonical.index)
    out = compute_extras(canonical, price).loc["2025"]
    assert out["ebitda_margin"] == pytest.approx(0.2)  # (150+50)/1000
    assert out["fcf_margin"] == pytest.approx(0.08)
    assert out["fcf_conversion"] == pytest.approx(0.8)
    assert out["dividend_coverage"] == pytest.approx(2.5)  # 100 / |−40|
    assert out["greenblatt_roc"] == pytest.approx(150 / 700)  # EBIT/(WC+netPPE)
    assert out["ncav"] == pytest.approx(100.0)  # CA − total liabilities
    # Graham number √(22.5·EPS·BVPS) = √(22.5·1·9) = √202.5
    assert out["graham_number"] == pytest.approx(202.5**0.5)
    assert out["graham_margin_of_safety"] == pytest.approx(202.5**0.5 / 10 - 1)
    assert out["ncav_to_market_cap"] == pytest.approx(0.1)  # 100 / (10·100)
    assert out["greenblatt_earnings_yield"] == pytest.approx(150 / 1100)  # EBIT/EV


def test_fr003_extras_without_price_null_the_price_dependent_block() -> None:
    out = compute_extras(canonical_from(EXTRAS_FRAME, ["2025"]), None).loc["2025"]
    # price-free metrics are still computed
    assert out["ebitda_margin"] == pytest.approx(0.2)
    assert out["ncav"] == pytest.approx(100.0)
    assert out["greenblatt_roc"] == pytest.approx(150 / 700)
    # price-dependent metrics are NaN, never fabricated
    for col in ("graham_number", "graham_margin_of_safety", "ncav_to_market_cap", "greenblatt_earnings_yield"):
        assert pd.isna(out[col]), col


def test_fr003_graham_number_null_when_earnings_not_positive() -> None:
    frame = {
        "income": {"TotalRevenue": [1000.0], "NetIncome": [-50.0]},
        "balance": {
            "StockholdersEquity": [900.0], "BasicAverageShares": [100.0],
            "CurrentAssets": [500.0], "TotalLiabilitiesNetMinorityInterest": [400.0],
        },
    }
    canonical = canonical_from(frame, ["2025"])
    price = pd.Series([10.0], index=canonical.index)
    out = compute_extras(canonical, price).loc["2025"]
    assert pd.isna(out["graham_number"])  # EPS < 0 → undefined, never imputed


def test_fr003_greenblatt_undefined_on_nonpositive_capital_or_ev() -> None:
    """Regression: non-positive invested capital / enterprise value would
    sign-flip the Greenblatt ratios (negative EBIT over a negative denominator
    reads as a high return) and corrupt magic_formula_rank — must be NaN."""
    canonical = canonical_from(
        {
            "income": {"TotalRevenue": [1000.0], "EBIT": [150.0], "NetIncome": [100.0]},
            "balance": {
                "CurrentAssets": [100.0], "CurrentLiabilities": [500.0],  # working capital = -400
                "NetPPE": [100.0],                                        # invested capital = -300
                "TotalDebt": [0.0], "CashAndCashEquivalents": [500.0],
                "BasicAverageShares": [100.0], "StockholdersEquity": [50.0],
                "TotalLiabilitiesNetMinorityInterest": [600.0],
            },
        },
        ["2025"],
    )
    price = pd.Series([1.0], index=canonical.index)  # market cap = 100 → EV = 100 + 0 - 500 = -400
    out = compute_extras(canonical, price).loc["2025"]
    assert pd.isna(out["greenblatt_roc"])              # invested capital ≤ 0 → undefined
    assert pd.isna(out["greenblatt_earnings_yield"])   # enterprise value ≤ 0 → undefined


# ------------------------------------------------------------- Dechow F-Score


def _dechow_canonical(periods: int = 3, issuance: float = 0.0) -> pd.DataFrame:
    """Identical periods → every Δ term is exactly 0 where defined, so the
    logit collapses to intercept + soft-assets (+ issuance) — hand-computable."""
    from crible.compute.canonical import CANONICAL_FIELDS

    index = pd.Index([f"202{i + 3}" for i in range(periods)], name="period")
    base = {f: [float("nan")] * periods for f in CANONICAL_FIELDS}
    base.update(
        {
            "total_assets": [1000.0] * periods,
            "current_assets": [400.0] * periods,
            "cash_and_equivalents": [100.0] * periods,
            "current_liabilities": [200.0] * periods,
            "total_debt": [150.0] * periods,
            "long_term_debt": [100.0] * periods,
            "marketable_securities": [50.0] * periods,
            "total_liabilities": [500.0] * periods,
            "accounts_receivable": [80.0] * periods,
            "inventory": [120.0] * periods,
            "net_ppe": [300.0] * periods,
            "revenue": [1000.0] * periods,
            "net_income": [100.0] * periods,
            "common_stock_issuance": [issuance] * periods,
        }
    )
    return pd.DataFrame(base, index=index)


def test_fr003_dechow_flat_company_matches_hand_computed_logit() -> None:
    """All-flat: every Δ = 0, soft assets = (1000−300−100)/1000 = 0.6, no
    issuance → logit = −7.893 + 1.979·0.6; F = sigmoid/0.0037."""
    import math

    from crible.compute.dechow import dechow_components

    out = dechow_components(_dechow_canonical())
    row = out.iloc[-1]  # the third period: every Δ term is defined and 0
    for component in (
        "dechow_rsst", "dechow_ch_rec", "dechow_ch_inv", "dechow_ch_cs", "dechow_ch_roa",
    ):
        assert row[component] == pytest.approx(0.0)
    assert row["dechow_soft_assets"] == pytest.approx(0.6)
    assert row["dechow_issuance"] == 0.0
    logit = -7.893 + 1.979 * 0.6
    assert row["dechow_f"] == pytest.approx((1.0 / (1.0 + math.exp(-logit))) / 0.0037)


def test_fr003_dechow_issuance_dummy_and_early_periods() -> None:
    import math

    from crible.compute.dechow import dechow_components

    out = dechow_components(_dechow_canonical(issuance=5.0))
    # actual issuance flips the dummy and adds its published coefficient
    logit = -7.893 + 1.979 * 0.6 + 1.029
    assert out.iloc[-1]["dechow_f"] == pytest.approx((1.0 / (1.0 + math.exp(-logit))) / 0.0037)
    # ch_cs needs two consecutive cash-sales figures → the first TWO periods
    # of a company can never carry an F (NaN, never imputed)
    assert out.iloc[0:2]["dechow_f"].isna().all()


def test_fr003_dechow_components_move_the_hand_computed_way() -> None:
    from crible.compute.dechow import dechow_components

    canonical = _dechow_canonical()
    canonical.loc["2025", "accounts_receivable"] = 130.0  # +50 vs 80
    canonical.loc["2025", "inventory"] = 170.0  # +50 vs 120
    out = dechow_components(canonical).loc["2025"]
    assert out["dechow_ch_rec"] == pytest.approx(50.0 / 1000.0)
    assert out["dechow_ch_inv"] == pytest.approx(50.0 / 1000.0)
    # cash sales drop by the receivables jump: (1000−50)/1000 − 1
    assert out["dechow_ch_cs"] == pytest.approx(950.0 / 1000.0 - 1.0)
    # a missing balance input nulls F for that period — never imputed
    canonical.loc["2025", "marketable_securities"] = float("nan")
    assert pd.isna(dechow_components(canonical).loc["2025", "dechow_f"])


# ------------------------------------------------- quick-win indicators (C1)


def _quickwin_canonical() -> pd.DataFrame:
    """Four periods, hand-pickable numbers: revenue +10%/y, NI CAGR exactly
    10% over 3 years (1.331^(1/3) = 1.1), flat balance-sheet items."""
    from crible.compute.canonical import CANONICAL_FIELDS

    periods = ["2022", "2023", "2024", "2025"]
    base: dict[str, list[float]] = {f: [float("nan")] * 4 for f in CANONICAL_FIELDS}
    base.update(
        {
            "revenue": [1000.0, 1100.0, 1210.0, 1331.0],
            "cost_of_goods_sold": [600.0, 660.0, 726.0, 798.6],
            "net_income": [100.0, 110.0, 121.0, 133.1],
            "operating_cashflow": [120.0, 130.0, 140.0, 150.0],
            "free_cash_flow": [100.0, 105.0, 110.0, 115.0],
            "total_assets": [1000.0, 1000.0, 1000.0, 1000.0],
            "inventory": [100.0] * 4,
            "accounts_receivable": [50.0] * 4,
            "accounts_payable": [80.0] * 4,
            "dividends_paid": [-40.0, -44.0, -48.0, -52.0],
            "shares_outstanding": [110.0, 110.0, 110.0, 100.0],
            "total_equity": [500.0] * 4,
            "total_debt": [200.0] * 4,
            "cash_and_equivalents": [50.0] * 4,
            "earnings_before_interest_and_taxes": [150.0] * 4,
            "working_capital": [70.0] * 4,
            "net_ppe": [300.0] * 4,
        }
    )
    return pd.DataFrame(base, index=pd.Index(periods, name="period"))


def test_fr003_quick_win_extras_are_analytically_exact() -> None:
    canonical = _quickwin_canonical()
    price = pd.Series([float("nan")] * 3 + [10.0], index=canonical.index)
    out = compute_extras(canonical, price).loc["2025"]

    # Rule of 40 = revenue growth + FCF margin
    assert out["rule_of_40"] == pytest.approx(1331 / 1210 - 1 + 115 / 1331)
    # Sloan accruals = (NI − OCF) / average TA — cash-rich earnings go negative
    assert out["sloan_accruals"] == pytest.approx((133.1 - 150.0) / 1000.0)
    # PEG = P/E over the 3y CAGR in % : (1000/133.1) / (10)
    assert out["peg_ratio"] == pytest.approx((1000.0 / 133.1) / 10.0)
    # shareholder yield = (dividends + buyback value) / market cap
    assert out["shareholder_yield"] == pytest.approx((52.0 + 10.0 * 10.0) / 1000.0)
    # 3y CAGR columns: the fixture grows exactly 10%/y — and PEG divides by
    # EXACTLY the published earnings CAGR (one definition, never two)
    assert out["revenue_cagr_3y"] == pytest.approx(0.1)
    assert out["net_income_cagr_3y"] == pytest.approx(0.1)
    assert out["peg_ratio"] == pytest.approx(
        (1000.0 / 133.1) / (out["net_income_cagr_3y"] * 100)
    )
    assert pd.isna(compute_extras(_quickwin_canonical(), price).loc["2024", "revenue_cagr_3y"])

    # price applies to the LATEST period only — older rows stay NaN
    earlier = compute_extras(canonical, price).loc["2024"]
    assert pd.isna(earlier["peg_ratio"]) and pd.isna(earlier["shareholder_yield"])


def test_fr003_peg_undefined_for_shrinking_or_negative_earnings() -> None:
    canonical = _quickwin_canonical()
    canonical["net_income"] = [133.1, 121.0, 110.0, 100.0]  # shrinking → no PEG
    price = pd.Series([float("nan")] * 3 + [10.0], index=canonical.index)
    assert pd.isna(compute_extras(canonical, price).loc["2025", "peg_ratio"])

    canonical["net_income"] = [-50.0, -40.0, -30.0, -20.0]  # negative → no PEG
    out = compute_extras(canonical, price).loc["2025"]
    assert pd.isna(out["peg_ratio"])
    # the shared CAGR is undefined on negative endpoints too — never sign-flipped
    assert pd.isna(out["net_income_cagr_3y"])


def test_fr003_reflection_wires_cycle_payout_and_roic() -> None:
    from crible.compute.ratios import compute_ratios

    canonical = _quickwin_canonical()
    ratios = compute_ratios(canonical)
    row = ratios.loc["2025"]

    # CCC = DIO + DSO − DPO from the same published day components
    dio = 365 * 100.0 / 798.6
    dso = 365 * 50.0 / 1331.0
    dpo = 365 * 80.0 / 798.6
    assert row["cash_conversion_cycle"] == pytest.approx(dio + dso - dpo)
    assert row["operating_cycle"] == pytest.approx(dio + dso)
    assert row["dividend_payout_ratio"] == pytest.approx(52.0 / 133.1)
    assert row["return_on_invested_capital"] == pytest.approx((133.1 - 52.0) / (500.0 + 200.0))
    # the dividends alias must NOT wire the bogus total-dividends yield
    assert "dividend_yield" not in ratios.columns
    assert "dividend_capex_coverage_ratio" not in ratios.columns


# ------------------------------------------------------------------- snapshot


def test_fr003_snapshot_wide_row_deterministic_and_150_plus_columns(tmp_path) -> None:
    frames = {(s, "annual"): income_frame(rows, ["2023", "2024", "2025"]) for s, rows in IMPROVING.items()}

    first = build_symbol_snapshot("TEST.PA", frames, computed_at=1000.0)
    second = build_symbol_snapshot("TEST.PA", frames, computed_at=2000.0)

    assert len(first) == 3  # one row per period
    assert len(first.columns) >= 150

    # deterministic: identical values for every column except computed_at
    value_cols = [c for c in first.columns if c != "computed_at"]
    pd.testing.assert_frame_equal(first[value_cols], second[value_cols])

    # atomic publish + read round-trip
    path = publish_snapshot(first, tmp_path)
    assert path.name == "snapshot.parquet"
    assert not list(path.parent.glob(".tmp-*"))
    loaded = read_snapshot(tmp_path)
    assert len(loaded) == 3
    assert loaded["symbol"].unique().tolist() == ["TEST.PA"]


def test_fr003_raw_layer_round_trip_builds_snapshot(tmp_path) -> None:
    """Full round-trip through the raw layer: write_raw_statement adds meta
    columns (_symbol, _provider, …) that must never break canonical joins —
    regression test for the compute crash found in the zero-key E2E."""
    from crible.compute.snapshot import build_snapshot, latest_raw_frames
    from crible.ingest.raw import write_raw_statement

    for stmt, rows in IMPROVING.items():
        write_raw_statement(
            tmp_path, symbol="RT.PA", provider="yfinance", statement_type=stmt,
            freq="annual", frame=income_frame(rows, ["2023", "2024", "2025"]),
            fetched_at=1000.0,
        )
    frames = latest_raw_frames(tmp_path, "RT.PA", provider="yfinance")
    assert len(frames) == 3
    snapshot = build_snapshot(tmp_path)
    assert len(snapshot) == 3
    assert snapshot["symbol"].unique().tolist() == ["RT.PA"]
    assert snapshot.loc[snapshot["period"] == "2025", "piotroski_f"].iloc[0] == 9


def test_fr003_price_ratio_growths_and_ncav_duplicate_are_not_emitted() -> None:
    """Price-based ratios exist for the latest fiscal period only, so their
    YoY growth can never resolve — the snapshot no longer emits those
    always-NaN columns, nor net_current_asset_value (≡ extras.ncav)."""
    frames = {(s, "annual"): income_frame(rows, ["2023", "2024", "2025"]) for s, rows in IMPROVING.items()}
    snapshot = build_symbol_snapshot(
        "P.PA", frames, computed_at=1.0, price_quote=(10.0, "2025-12-31")
    )

    assert "price_to_earnings_ratio" in snapshot.columns  # the ratio itself stays
    assert "price_to_earnings_ratio_growth" not in snapshot.columns
    assert "market_cap_growth" not in snapshot.columns
    assert "revenue_growth" in snapshot.columns  # real growths stay
    # net_debt only resolves when a price is passed, but its VALUES are a
    # full series — the growth is real and must survive
    assert "net_debt_to_ebitda_ratio_growth" in snapshot.columns
    assert "ncav" in snapshot.columns
    assert "net_current_asset_value" not in snapshot.columns


def test_fr003_price_dependent_ratio_columns_reflect_the_wiring() -> None:
    from crible.compute.ratios import price_dependent_ratio_columns

    cols = price_dependent_ratio_columns()
    assert "price_to_earnings_ratio" in cols
    assert "market_cap" in cols
    assert "net_profit_margin" not in cols  # price-free ratio
    assert "net_debt_to_ebitda_ratio" not in cols  # price-gated but full-series


def test_fr003_stale_base_cache_columns_are_scrubbed() -> None:
    """The nightly restores base.parquet from the last release: retired
    columns must not resurrect through the kept (non-dirty) rows."""
    from crible.compute.snapshot import _scrub_retired_columns

    stale = pd.DataFrame(
        {
            "symbol": ["A"],
            "revenue_growth": [0.1],
            "market_cap_growth": [float("nan")],
            "net_current_asset_value": [1.0],
            "net_current_asset_value_growth": [float("nan")],
        }
    )
    clean = _scrub_retired_columns(stale)
    assert list(clean.columns) == ["symbol", "revenue_growth"]


def test_fr003_null_cells_carry_a_note_naming_the_missing_inputs() -> None:
    """FR-003 AC-2: the snapshot names the canonical inputs the provider did
    not supply — every NULL ratio is explainable."""
    frames = {
        ("income", "annual"): income_frame(
            {"TotalRevenue": [1000.0], "NetIncome": [80.0]}, ["2025"]
        )
    }
    snapshot = build_symbol_snapshot("X.PA", frames, computed_at=1.0)
    note = snapshot["missing_inputs"].iloc[0]
    assert "operating_cashflow" in note
    assert "total_assets" in note
    assert "revenue" not in note.split(",")  # supplied fields are not listed


# --------------------------------- FR-022 / F7: incremental compute


def test_incremental_compute_recomputes_only_dirty_symbols(tmp_path, monkeypatch) -> None:
    """F7 — build_snapshot_incremental must rebuild the per-symbol rows only for
    symbols whose raw changed, reusing the cached base for the rest, then
    re-finalize (ranks are cross-sectional) over the whole set."""
    import time

    import crible.compute.snapshot as snap
    from crible.ingest.raw import write_raw_statement

    frame = pd.DataFrame({"period": ["2024"], "TotalRevenue": [100.0]})
    for sym in ("AAA", "BBB"):
        write_raw_statement(
            tmp_path, symbol=sym, provider="yfinance",
            statement_type="income", freq="annual", frame=frame, fetched_at=1000.0,
        )

    first = snap.build_snapshot_incremental(tmp_path)  # no base → full build
    assert set(first["symbol"]) == {"AAA", "BBB"}
    assert (tmp_path / "snapshot" / "base.parquet").exists()

    # spy on the per-symbol stage to prove only the dirty symbol is rebuilt
    calls: list[list[str]] = []
    original = snap.build_symbol_rows

    def spy(data_dir, symbols):
        calls.append(list(symbols))
        return original(data_dir, symbols)

    monkeypatch.setattr(snap, "build_symbol_rows", spy)

    # change BBB only, with a fetched-at newer than the base build but still in
    # the past (raw is always fetched before the compute that follows it)
    time.sleep(0.02)
    write_raw_statement(
        tmp_path, symbol="BBB", provider="yfinance",
        statement_type="income", freq="annual",
        frame=pd.DataFrame({"period": ["2024"], "TotalRevenue": [250.0]}),
        fetched_at=time.time(),
    )
    second = snap.build_snapshot_incremental(tmp_path)

    assert calls == [["BBB"]]  # only the dirty symbol was recomputed
    assert set(second["symbol"]) == {"AAA", "BBB"}  # AAA reused from the base cache
    by_symbol = second.set_index("symbol")
    assert by_symbol.loc["BBB", "revenue"] == 250.0  # BBB reflects the change

    # a subsequent build with nothing changed → None (no republish)
    calls.clear()
    assert snap.build_snapshot_incremental(tmp_path) is None
    assert calls == []


def test_incremental_full_rebuild_on_engine_schema_bump(tmp_path, monkeypatch) -> None:
    """Kept (non-dirty) base rows carry the schema they were built with: a
    version bump (a deploy adding indicator columns) must dirty everything
    once, then stamp the rebuilt base so the next run is incremental again."""
    import crible.compute.snapshot as snap
    from crible.ingest.raw import write_raw_statement

    frame = pd.DataFrame({"period": ["2024"], "TotalRevenue": [100.0]})
    for sym in ("AAA", "BBB"):
        write_raw_statement(
            tmp_path, symbol=sym, provider="yfinance",
            statement_type="income", freq="annual", frame=frame, fetched_at=1000.0,
        )
    snap.build_snapshot_incremental(tmp_path)  # base + schema stamp
    assert (tmp_path / "snapshot" / "base-schema.json").exists()

    calls: list[list[str]] = []
    original = snap.build_symbol_rows
    monkeypatch.setattr(
        snap, "build_symbol_rows", lambda d, s: (calls.append(list(s)), original(d, s))[1]
    )

    # same engine version, nothing changed → no per-symbol work at all
    assert snap.build_snapshot_incremental(tmp_path) is None
    assert calls == []

    # a deploy bumps the engine schema → every symbol rebuilds once
    monkeypatch.setattr(snap, "ENGINE_SCHEMA_VERSION", snap.ENGINE_SCHEMA_VERSION + 1)
    result = snap.build_snapshot_incremental(tmp_path)
    assert sorted(calls[-1]) == ["AAA", "BBB"]
    assert set(result["symbol"]) == {"AAA", "BBB"}

    # the rebuilt base carries the new stamp → incremental again
    calls.clear()
    assert snap.build_snapshot_incremental(tmp_path) is None
    assert calls == []


def test_incremental_compute_rebuilds_all_when_the_price_distillate_refreshes(tmp_path, monkeypatch) -> None:
    """F8 — a refreshed prices-latest.parquet changes every symbol's baked-in
    price_quote, so incremental must rebuild all rows, not serve stale prices."""
    import time

    import crible.compute.snapshot as snap
    from crible.ingest.raw import write_raw_statement

    frame = pd.DataFrame({"period": ["2024"], "TotalRevenue": [100.0]})
    for sym in ("AAA", "BBB"):
        write_raw_statement(
            tmp_path, symbol=sym, provider="yfinance",
            statement_type="income", freq="annual", frame=frame, fetched_at=1000.0,
        )
    snap.build_snapshot_incremental(tmp_path)  # base built

    calls: list[list[str]] = []
    original = snap.build_symbol_rows
    monkeypatch.setattr(snap, "build_symbol_rows", lambda d, s: (calls.append(list(s)), original(d, s))[1])

    # a fresh price distillate lands after the base (the shape _price_quotes reads)
    time.sleep(0.02)
    pd.DataFrame(
        {"symbol": ["AAA"], "close": [10.0], "price_asof": ["2024-12-31"], "return_6m": [0.1]}
    ).to_parquet(tmp_path / "prices-latest.parquet", index=False)

    snap.build_snapshot_incremental(tmp_path)
    assert calls and sorted(calls[0]) == ["AAA", "BBB"]  # ALL symbols rebuilt, not none
