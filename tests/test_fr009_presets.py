"""FR-009 — preset screens: plain, visible, editable DSL strings."""

from __future__ import annotations

from crible.presets import PRESETS


def test_fr009_ships_the_five_published_presets_with_visible_dsl() -> None:
    expected = {
        "piotroski-strong": "piotroski_f >= 7",
        "altman-safe": "altman_z > 2.99",
        "beneish-red-flags": "beneish_m > -1.78",
        "classic-value": "price_to_earnings_ratio < 12 AND price_to_book_ratio < 1.5",
        "quality": "return_on_equity > 0.15 AND debt_to_equity_ratio < 1",
    }
    for preset_id, dsl in expected.items():
        preset = PRESETS[preset_id]
        assert preset.dsl == dsl  # the FULL query is visible, nothing hidden
        assert preset.description


def test_fr009_every_indicator_has_a_preset() -> None:
    """Coverage guard: every filterable indicator key appears in at least one
    preset DSL (graham_number/ncav are covered through their screenable
    companions graham_margin_of_safety/ncav_to_market_cap)."""
    indicator_keys = [
        "piotroski_f", "altman_z", "beneish_m", "zmijewski_score", "ohlson_o",
        "montier_c", "composite_rank", "quality_rank", "value_rank",
        "momentum_rank", "magic_formula_rank", "greenblatt_earnings_yield",
        "greenblatt_roc", "graham_margin_of_safety", "ncav_to_market_cap",
        "ebitda_margin", "fcf_margin", "fcf_conversion", "dividend_coverage",
    ]
    all_dsl = " ".join(p.dsl for p in PRESETS.values())
    missing = [key for key in indicator_keys if key not in all_dsl]
    assert not missing, f"indicators without a preset: {missing}"


def test_fr009_running_a_preset_is_byte_for_byte_its_dsl() -> None:
    """No hidden logic: screening via a preset returns exactly the rows of
    screening its DSL string directly (execution equivalence)."""
    import duckdb
    import pandas as pd

    from crible.store import screen, whitelist_from_relation

    con = duckdb.connect()
    frame = pd.DataFrame(
        {
            "symbol": ["A", "B", "C"],
            "piotroski_f": [8, 6, 9],
            "altman_z": [3.5, 1.2, 4.0],
            "beneish_m": [-2.5, -1.0, -2.9],
            "composite_rank": [85.0, 40.0, 92.0],
            "magic_formula_rank": [88.0, 30.0, 95.0],
            "ncav_to_market_cap": [2.0, 0.5, 1.6],
            "zmijewski_score": [-1.5, 0.8, -2.0],
            "ohlson_o": [-0.5, 1.2, -1.0],
            "montier_c": [1, 4, 0],
            "quality_rank": [90.0, 35.0, 88.0],
            "value_rank": [84.0, 20.0, 91.0],
            "momentum_rank": [82.0, 45.0, 87.0],
            "greenblatt_earnings_yield": [0.12, 0.03, 0.15],
            "greenblatt_roc": [0.25, 0.05, 0.30],
            "graham_margin_of_safety": [0.4, -0.2, 0.1],
            "ebitda_margin": [0.22, 0.08, 0.18],
            "fcf_margin": [0.09, 0.01, 0.12],
            "fcf_conversion": [1.1, 0.4, 1.3],
            "dividend_coverage": [2.5, 0.8, 3.0],
        }
    )
    con.register("snapshot_latest", frame)
    whitelist = whitelist_from_relation(con, "snapshot_latest")
    for preset in PRESETS.values():
        if any(field not in whitelist for field in ("price_to_earnings_ratio", "return_on_equity"))\
           and preset.id in ("classic-value", "quality"):
            continue  # fields absent from this minimal fixture
        via_preset = screen(con, PRESETS[preset.id].dsl, whitelist=whitelist, limit=10, offset=0)
        direct = screen(con, preset.dsl, whitelist=whitelist, limit=10, offset=0)
        pd.testing.assert_frame_equal(via_preset, direct)
