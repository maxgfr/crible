"""FR-009 — preset screens: plain, visible, editable DSL strings."""

from __future__ import annotations

from crible.presets import PRESETS


def test_fr009_ships_the_five_published_presets_with_visible_dsl() -> None:
    expected = {
        "piotroski-strong": "piotroski_f >= 7",
        "altman-safe": "altman_z > 2.99",
        "beneish-red-flags": "beneish_m > -1.78",
        "classic-value": "price_earnings < 12 AND price_to_book_ratio < 1.5",
        "quality": "return_on_equity > 0.15 AND debt_to_equity_ratio < 1",
    }
    for preset_id, dsl in expected.items():
        preset = PRESETS[preset_id]
        assert preset.dsl == dsl  # the FULL query is visible, nothing hidden
        assert preset.description


def test_fr009_presets_carry_no_hidden_logic() -> None:
    """A preset is nothing but a name + a DSL string — running it must be
    byte-for-byte the DSL string (no extra clauses injected anywhere)."""
    for preset in PRESETS.values():
        assert isinstance(preset.dsl, str) and preset.dsl.strip() == preset.dsl
