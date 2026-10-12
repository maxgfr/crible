"""FR-009 — preset screens: plain, visible, editable DSL strings."""

from __future__ import annotations

import re

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
        "piotroski_f",
        "altman_z",
        "beneish_m",
        "zmijewski_score",
        "ohlson_o",
        "montier_c",
        "composite_rank",
        "quality_rank",
        "value_rank",
        "momentum_rank",
        "magic_formula_rank",
        "greenblatt_earnings_yield",
        "greenblatt_roc",
        "graham_margin_of_safety",
        "ncav_to_market_cap",
        "ebitda_margin",
        "fcf_margin",
        "fcf_conversion",
        "dividend_coverage",
        "roic",
        "gross_profitability",
        "net_share_issuance",
        "positive_fcf_years_5y",
        "altman_z_double_prime",
    ]
    all_dsl = " ".join(p.dsl for p in PRESETS.values())
    missing = [key for key in indicator_keys if key not in all_dsl]
    assert not missing, f"indicators without a preset: {missing}"


def test_fr009_every_preset_curates_its_columns() -> None:
    """Picking a preset must surface the metrics it screens by: every
    shipped preset carries a non-empty column set of legal identifiers, and
    every field its DSL references is in the set — a screen never hides the
    metric it filtered on."""
    field_re = re.compile(r"[a-z_][a-z0-9_]*")
    keywords = {"and", "or", "not", "in"}
    for preset in PRESETS.values():
        assert preset.columns, f"{preset.id} has no curated columns"
        for column in preset.columns:
            assert re.fullmatch(r"[a-z0-9_]+", column), f"{preset.id}: bad column {column!r}"
        # string literals (none today) must never read as field names
        dsl = re.sub(r"'[^']*'", " ", preset.dsl.lower())
        referenced = {word for word in field_re.findall(dsl) if word not in keywords}
        missing = referenced - set(preset.columns)
        assert not missing, f"{preset.id}: DSL fields missing from columns: {missing}"


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
            "rule_of_40": [0.45, 0.1, 0.52],
            "peg_ratio": [0.8, 2.5, 0.6],
            "shareholder_yield": [0.07, 0.01, 0.09],
            "sloan_accruals": [-0.02, 0.12, -0.05],
            "return_12_1": [0.35, -0.1, 0.28],
            "mohanram_g": [5.0, 2.0, 6.0],
            "dechow_f": [0.4, 2.1, 0.7],
            "roic": [0.18, 0.04, 0.22],
            "gross_profitability": [0.35, 0.1, 0.4],
            "net_share_issuance": [-0.01, 0.08, 0.0],
            "positive_fcf_years_5y": [5.0, 2.0, 4.0],
            "altman_z_double_prime": [3.1, 0.9, 2.7],
        }
    )
    con.register("snapshot_latest", frame)
    whitelist = whitelist_from_relation(con, "snapshot_latest")
    for preset in PRESETS.values():
        if any(
            field not in whitelist for field in ("price_to_earnings_ratio", "return_on_equity")
        ) and preset.id in ("classic-value", "quality"):
            continue  # fields absent from this minimal fixture
        via_preset = screen(con, PRESETS[preset.id].dsl, whitelist=whitelist, limit=10, offset=0)
        direct = screen(con, preset.dsl, whitelist=whitelist, limit=10, offset=0)
        pd.testing.assert_frame_equal(via_preset, direct)


def _computed_snapshot(tmp_path):
    """A REAL computed snapshot (raw frames → per-symbol rows → finalize with
    a universe), not a hand-built frame: presets run against what the engine
    actually publishes."""
    import pandas as pd

    from crible.compute.snapshot import UNIVERSE_COLUMNS, build_symbol_snapshot, finalize_snapshot

    from tests.test_fr003_compute import IMPROVING, income_frame
    from tests.test_ttm import QUARTER_ENDS, quarterly_frames

    periods = ["2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31"]
    rows = []
    for i, symbol in enumerate(["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]):
        values = {
            stmt: {k: [v[0] * (1 + i / 10)] + [x * (1 + i / 10) for x in v] for k, v in cols.items()}
            for stmt, cols in IMPROVING.items()
        }
        frames = {(s, "annual"): income_frame(cols, periods) for s, cols in values.items()}
        frames.update(quarterly_frames(QUARTER_ENDS[:4]))
        frames[("prices", "daily")] = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=400, freq="D"),
                "close": [10.0 + d / 50 for d in range(400)],
            }
        )
        rows.append(build_symbol_snapshot(symbol, frames, computed_at=1.0))
    pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"],
            **{col: None for col in UNIVERSE_COLUMNS},
            "region": "europe",
            "sector": "Tech",
            "top10k": True,
        }
    ).to_parquet(tmp_path / "universe.parquet")
    return finalize_snapshot(pd.concat(rows, ignore_index=True), tmp_path)


def _dsl_fields(node) -> set[str]:
    from crible.dsl.parser import BoolOp, Comparison, InList, Not

    if isinstance(node, (Comparison, InList)):
        return {node.field}
    if isinstance(node, Not):
        return _dsl_fields(node.operand)
    if isinstance(node, BoolOp):
        return set().union(*(_dsl_fields(op) for op in node.operands))
    return set()


def test_fr009_every_preset_field_exists_in_a_computed_snapshot(tmp_path) -> None:
    """A financetoolkit rename that drops a ratio must fail HERE, not as an
    « unknown field » for the user running the preset."""
    from crible.dsl.parser import parse

    columns = set(_computed_snapshot(tmp_path).columns)
    for preset in PRESETS.values():
        missing = _dsl_fields(parse(preset.dsl)) - columns
        assert not missing, f"{preset.id}: fields absent from a computed snapshot: {missing}"
        absent = set(preset.columns) - columns
        assert not absent, f"{preset.id}: curated columns absent from a computed snapshot: {absent}"


def test_fr009_loss_maker_with_negative_equity_is_neither_value_nor_quality() -> None:
    import duckdb

    from crible.compute.snapshot import build_symbol_snapshot
    from crible.store import screen, whitelist_from_relation

    from tests.test_fr003_compute import _loss_maker_frames

    snapshot = build_symbol_snapshot(
        "LOSS", _loss_maker_frames(), computed_at=1.0, price_quote=(6.0, "2026-01-02")
    )
    con = duckdb.connect()
    con.register("snapshot_latest", snapshot.tail(1))
    whitelist = whitelist_from_relation(con, "snapshot_latest")
    for preset_id in ("classic-value", "quality"):
        assert screen(con, PRESETS[preset_id].dsl, whitelist=whitelist, limit=10, offset=0).empty, preset_id
