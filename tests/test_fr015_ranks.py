"""FR-015 — composite quality/value/momentum rank across the universe.

Percentile ranks (0-100) within a peer group (region×sector, global fallback),
computed at snapshot build time from columns crible already publishes — no new
data source, no API key. Pillars with a missing input stay NULL (never
imputed); the composite blends the available pillars and records omissions.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from crible.compute.ranks import MIN_PEERS, attach_ranks, price_return
from crible.store import screen, whitelist_from_relation

RANK_COLUMNS = ["quality_rank", "value_rank", "momentum_rank", "composite_rank"]


def latest_frame() -> pd.DataFrame:
    """Six europe×Tech companies, monotonically better fundamentals A→F."""
    n = 6
    return pd.DataFrame(
        {
            "symbol": [f"C{i}.PA" for i in range(n)],
            "period": ["2025-12-31"] * n,
            "region": ["europe"] * n,
            "sector": ["Tech"] * n,
            "piotroski_f": [3, 4, 5, 6, 7, 8],
            "altman_z": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
            "earnings_yield": [0.02, 0.03, 0.04, 0.05, 0.06, 0.07],
            "price_to_book_ratio": [9.0, 7.0, 5.0, 3.0, 2.0, 1.0],
            "return_6m": [-0.2, -0.1, 0.0, 0.1, 0.2, 0.3],
        }
    )


# ------------------------------------------------------------------ AC-1


def test_fr015_percentiles_within_peer_group_and_reproducible() -> None:
    frame = latest_frame()
    once = attach_ranks(frame.copy())
    twice = attach_ranks(frame.copy())

    for col in RANK_COLUMNS:
        assert col in once.columns
        assert once[col].between(0, 100).all()
    # better fundamentals on every pillar → strictly higher composite
    ordered = once.sort_values("symbol")["composite_rank"].tolist()
    assert ordered == sorted(ordered)
    assert ordered[-1] > ordered[0]
    # documented, reproducible formula: identical ranks on the same snapshot
    pd.testing.assert_frame_equal(once, twice)
    assert (once["rank_peer_group"] == "europe×Tech").all()


def test_fr015_multi_period_ranks_only_the_latest_row() -> None:
    frame = latest_frame()
    old = frame.copy()
    old["period"] = "2024-12-31"
    both = attach_ranks(pd.concat([frame, old], ignore_index=True))
    latest = both[both["period"] == "2025-12-31"]
    stale = both[both["period"] == "2024-12-31"]
    assert latest["composite_rank"].notna().all()
    assert stale["composite_rank"].isna().all()


# ------------------------------------------------------------------ AC-2


def test_fr015_missing_input_nulls_the_pillar_and_records_the_omission() -> None:
    frame = latest_frame()
    frame.loc[0, "altman_z"] = float("nan")  # quality input missing for C0.PA
    ranked = attach_ranks(frame)
    row = ranked[ranked["symbol"] == "C0.PA"].iloc[0]

    assert pd.isna(row["quality_rank"])  # never imputed
    assert pd.notna(row["value_rank"]) and pd.notna(row["momentum_rank"])
    # composite is the blend of the AVAILABLE pillars only
    assert row["composite_rank"] == (row["value_rank"] + row["momentum_rank"]) / 2
    assert row["rank_missing_pillars"] == "quality"
    # fully-populated peers record no omission
    full = ranked[ranked["symbol"] != "C0.PA"]
    assert full["rank_missing_pillars"].isna().all()


def test_fr015_small_peer_group_falls_back_to_global() -> None:
    frame = latest_frame()
    frame.loc[0:1, "sector"] = "Micro"  # 2 « Micro » < MIN_PEERS
    ranked = attach_ranks(frame)
    micro = ranked[ranked["sector"] == "Micro"]
    assert (micro["rank_peer_group"] == "global").all()
    assert micro["composite_rank"].notna().all()
    assert MIN_PEERS > 2


# ------------------------------------------------------------------ momentum input


def test_fr015_return_6m_from_daily_bars() -> None:
    dates = pd.date_range("2025-01-02", periods=260, freq="B")
    bars = pd.DataFrame({"Date": dates.astype(str), "Close": [100.0 + i * 0.5 for i in range(260)]})
    r = price_return(bars, days=182)
    last = 100.0 + 259 * 0.5
    cutoff = pd.Timestamp(dates[-1]) - pd.Timedelta(days=182)
    base = float(bars[pd.to_datetime(bars["Date"]) <= cutoff]["Close"].iloc[-1])
    assert abs(r - (last / base - 1)) < 1e-9

    short = pd.DataFrame({"Date": dates[:20].astype(str), "Close": [100.0] * 20})
    assert pd.isna(price_return(short, days=182))


# ------------------------------------------------------------------ AC-3 (screening surface)


def test_fr015_rank_columns_screen_through_the_dsl() -> None:
    ranked = attach_ranks(latest_frame())
    con = duckdb.connect()
    con.register("snapshot_latest", ranked)
    whitelist = whitelist_from_relation(con, "snapshot_latest")
    assert {"composite_rank", "quality_rank", "value_rank", "momentum_rank"} <= whitelist

    top = screen(con, "composite_rank >= 80", whitelist=whitelist, sort="-composite_rank", limit=10, offset=0)
    assert top["symbol"].tolist() == ["C5.PA", "C4.PA"]


def test_fr015_pre_upgrade_snapshot_gets_a_recompute_hint() -> None:
    """The shipped top-ranked preset must not strand a pre-FR-015 snapshot on
    « no similar field exists » — the error says HOW to get the column."""
    import pytest

    from crible.dsl.parser import DslError

    con = duckdb.connect()
    con.register("snapshot_latest", pd.DataFrame({"symbol": ["A"], "piotroski_f": [8]}))
    whitelist = whitelist_from_relation(con, "snapshot_latest")
    with pytest.raises(DslError) as err:
        screen(con, "composite_rank >= 80", whitelist=whitelist, limit=10, offset=0)
    assert "crible compute" in str(err.value)


def test_fr015_top_ranked_preset_ships() -> None:
    from crible.presets import PRESETS

    preset = PRESETS.get("top-ranked")
    assert preset is not None
    assert "composite_rank" in preset.dsl
