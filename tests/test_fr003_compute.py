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
from crible.compute.scores import altman, piotroski
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
