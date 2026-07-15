"""FR-009 — preset screens: plain, visible, editable DSL strings.

Every preset is an ordinary DSL query — no hidden logic anywhere. Thresholds
are published starting points (Piotroski ≥ 7; Altman safe zone Z > 2.99;
Beneish red flag M > -1.78), meant to be edited.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    description: str
    dsl: str


_PRESETS = [
    Preset(
        id="piotroski-strong",
        name="Piotroski strong",
        description="Financially strengthening companies (F-Score at least 7 of 9)",
        dsl="piotroski_f >= 7",
    ),
    Preset(
        id="altman-safe",
        name="Altman safe zone",
        description="Bankruptcy-safe zone under the classic Z-Score (Z > 2.99)",
        dsl="altman_z > 2.99",
    ),
    Preset(
        id="beneish-red-flags",
        name="Beneish red flags",
        description="Possible earnings manipulation (M-Score above the -1.78 threshold)",
        dsl="beneish_m > -1.78",
    ),
    Preset(
        id="classic-value",
        name="Classic value",
        description="Cheap on earnings and book value",
        dsl="price_to_earnings_ratio < 12 AND price_to_book_ratio < 1.5",
    ),
    Preset(
        id="quality",
        name="Quality",
        description="High return on equity with conservative leverage",
        dsl="return_on_equity > 0.15 AND debt_to_equity_ratio < 1",
    ),
    Preset(
        id="top-ranked",
        name="Top ranked",
        description="Top quintile of the composite quality/value/momentum rank",
        dsl="composite_rank >= 80",
    ),
    Preset(
        id="magic-formula",
        name="Magic formula",
        description="Greenblatt's magic formula — top quintile blending earnings yield and return on capital",
        dsl="magic_formula_rank >= 80",
    ),
    Preset(
        id="graham-net-net",
        name="Graham net-net",
        description="Deep value: market cap under two-thirds of net current asset value (NCAV)",
        dsl="ncav_to_market_cap >= 1.5",
    ),
    Preset(
        id="zmijewski-safe",
        name="Zmijewski safe",
        description="Under 50% modelled probability of financial distress (Zmijewski X < 0)",
        dsl="zmijewski_score < 0",
    ),
    Preset(
        id="ohlson-safe",
        name="Ohlson safe",
        description="Under 50% modelled probability of distress on the 9-variable O-Score (O < 0)",
        dsl="ohlson_o < 0",
    ),
    Preset(
        id="montier-clean",
        name="Montier clean books",
        description="At most one of Montier's six accounting red flags (C-Score <= 1)",
        dsl="montier_c <= 1",
    ),
    Preset(
        id="top-quality",
        name="Top quality",
        description="Top quintile of the quality pillar rank",
        dsl="quality_rank >= 80",
    ),
    Preset(
        id="top-value",
        name="Top value",
        description="Top quintile of the value pillar rank",
        dsl="value_rank >= 80",
    ),
    Preset(
        id="top-momentum",
        name="Top momentum",
        description="Top quintile of the momentum pillar rank",
        dsl="momentum_rank >= 80",
    ),
    Preset(
        id="greenblatt-factors",
        name="Greenblatt factors",
        description="Cheap and good in absolute terms: earnings yield (EBIT/EV) over 10% and return on capital over 20%",
        dsl="greenblatt_earnings_yield >= 0.1 AND greenblatt_roc >= 0.2",
    ),
    Preset(
        id="graham-defensive",
        name="Graham margin of safety",
        description="Price below the Graham number — a positive defensive margin of safety",
        dsl="graham_margin_of_safety > 0",
    ),
    Preset(
        id="cash-quality",
        name="Cash quality",
        description="Earnings backed by cash: EBITDA margin over 15%, FCF margin over 5%, FCF conversion above 1",
        dsl="ebitda_margin >= 0.15 AND fcf_margin >= 0.05 AND fcf_conversion >= 1",
    ),
    Preset(
        id="dividend-safety",
        name="Dividend safety",
        description="Dividend covered at least twice by net income (non-payers are excluded)",
        dsl="dividend_coverage >= 2",
    ),
    Preset(
        id="all-indicators",
        name="All indicators",
        description=(
            "Every indicator at its published threshold at once — an extremely strict"
            " starting template meant to be loosened; may match zero companies"
        ),
        dsl=(
            "piotroski_f >= 7 AND altman_z > 2.99 AND beneish_m < -1.78"
            " AND zmijewski_score < 0 AND ohlson_o < 0 AND montier_c <= 1"
            " AND composite_rank >= 80 AND quality_rank >= 80 AND value_rank >= 80"
            " AND momentum_rank >= 80 AND magic_formula_rank >= 80"
            " AND greenblatt_earnings_yield >= 0.1 AND greenblatt_roc >= 0.2"
            " AND graham_margin_of_safety > 0 AND ebitda_margin >= 0.15"
            " AND fcf_margin >= 0.05 AND fcf_conversion >= 1"
        ),
    ),
]

PRESETS: dict[str, Preset] = {p.id: p for p in _PRESETS}
