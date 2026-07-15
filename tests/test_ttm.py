"""TTM v1 — four clean quarters sum onto the latest snapshot row; anything
less (or gapped) is NaN, never a wrong sum."""

from __future__ import annotations

import pandas as pd
import pytest

from crible.compute.snapshot import build_symbol_snapshot
from crible.compute.ttm import ttm_from_quarterly, ttm_ratios

from tests.test_fr003_compute import IMPROVING, income_frame

QUARTER_ENDS = ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]


def quarterly_frames(periods: list[str], *, revenue=None, ni=None, ocf=None, capex=None):
    n = len(periods)
    revenue = revenue if revenue is not None else [100.0 + 10 * i for i in range(n)]
    ni = ni if ni is not None else [10.0 + i for i in range(n)]
    ocf = ocf if ocf is not None else [12.0 + i for i in range(n)]
    capex = capex if capex is not None else [-2.0] * n
    return {
        ("income", "quarterly"): income_frame(
            {"TotalRevenue": revenue, "NetIncome": ni}, periods
        ),
        ("cashflow", "quarterly"): income_frame(
            {"OperatingCashFlow": ocf, "CapitalExpenditure": capex}, periods
        ),
    }


def test_ttm_sums_exactly_the_last_four_quarters() -> None:
    frames = quarterly_frames(QUARTER_ENDS)  # five quarters → the oldest drops
    ttm = ttm_from_quarterly(frames)
    assert ttm["ttm_revenue"] == pytest.approx(110.0 + 120.0 + 130.0 + 140.0)
    assert ttm["ttm_net_income"] == pytest.approx(11.0 + 12.0 + 13.0 + 14.0)
    assert ttm["ttm_operating_cashflow"] == pytest.approx(13.0 + 14.0 + 15.0 + 16.0)
    # FCF falls back to OCF + capex per quarter (canonical derivation)
    assert ttm["ttm_free_cash_flow"] == pytest.approx((13.0 - 2) + (14 - 2) + (15 - 2) + (16 - 2))


def test_ttm_needs_four_quarters() -> None:
    assert ttm_from_quarterly(quarterly_frames(QUARTER_ENDS[:3])) == {}
    assert ttm_from_quarterly({}) == {}


def test_ttm_rejects_gapped_or_overlong_spans() -> None:
    # a missing middle quarter stretches the 4-quarter span past a year
    gapped = ["2024-06-30", "2024-12-31", "2025-06-30", "2025-12-31"]
    assert ttm_from_quarterly(quarterly_frames(gapped)) == {}
    # annual periods masquerading as quarters are rejected too
    annual = ["2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"]
    assert ttm_from_quarterly(quarterly_frames(annual)) == {}


def test_ttm_missing_core_quarter_disqualifies_fcf_gap_nulls_fcf_only() -> None:
    # one NaN OCF quarter inside the window → that row drops from the core →
    # the span check fails → {} (correctness beats coverage)
    frames = quarterly_frames(
        QUARTER_ENDS[1:], ocf=[13.0, float("nan"), 15.0, 16.0]
    )
    assert ttm_from_quarterly(frames) == {}
    # core intact but one capex missing → only the FCF sum is NaN
    frames = quarterly_frames(QUARTER_ENDS[1:], capex=[-2.0, float("nan"), -2.0, -2.0])
    ttm = ttm_from_quarterly(frames)
    assert ttm["ttm_revenue"] > 0
    assert pd.isna(ttm["ttm_free_cash_flow"])


def test_ttm_ratios_hand_computed_and_guarded() -> None:
    ttm = {"ttm_revenue": 500.0, "ttm_net_income": 50.0, "ttm_free_cash_flow": 40.0}
    ratios = ttm_ratios(ttm, market_cap=1000.0)
    assert ratios["price_to_earnings_ttm"] == pytest.approx(20.0)
    assert ratios["price_to_sales_ttm"] == pytest.approx(2.0)
    assert ratios["ttm_fcf_yield"] == pytest.approx(0.04)
    # negative earnings → no P/E; no market cap → nothing
    assert pd.isna(ttm_ratios({**ttm, "ttm_net_income": -5.0}, 1000.0)["price_to_earnings_ttm"])
    assert all(pd.isna(v) for v in ttm_ratios(ttm, float("nan")).values())


def test_ttm_lands_on_the_latest_snapshot_row_only() -> None:
    frames = {
        (s, "annual"): income_frame(rows, ["2023", "2024", "2025"]) for s, rows in IMPROVING.items()
    }
    frames.update(quarterly_frames(QUARTER_ENDS))
    snapshot = build_symbol_snapshot(
        "T.PA", frames, computed_at=1.0, price_quote=(10.0, "2025-12-31")
    )
    latest = snapshot.iloc[-1]
    assert latest["ttm_revenue"] == pytest.approx(500.0)
    assert snapshot.iloc[0:-1]["ttm_revenue"].isna().all()
    # annual-only symbols carry NaN TTM — reach honesty, no fabrication
    annual_only = build_symbol_snapshot(
        "A.PA",
        {(s, "annual"): income_frame(rows, ["2023", "2024", "2025"]) for s, rows in IMPROVING.items()},
        computed_at=1.0,
    )
    assert annual_only["ttm_revenue"].isna().all()
