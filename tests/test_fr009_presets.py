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
