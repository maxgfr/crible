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
    # grid columns the preset surfaces on pick (identity columns are the
    # UI's own base) — every field the DSL filters on MUST be in here, so
    # a screen never hides the metric it screened by
    columns: tuple[str, ...] | None = None


_PRESETS = [
    Preset(
        id="piotroski-strong",
        name="Piotroski strong",
        description="Financially strengthening companies (F-Score at least 7 of 9)",
        dsl="piotroski_f >= 7",
        columns=("piotroski_f", "altman_z", "return_on_equity", "net_profit_margin", "debt_to_equity_ratio"),
    ),
    Preset(
        id="altman-safe",
        name="Altman safe zone",
        description="Bankruptcy-safe zone under the classic Z-Score (Z > 2.99)",
        dsl="altman_z > 2.99",
        columns=("altman_z", "piotroski_f", "current_ratio", "debt_to_equity_ratio", "interest_coverage_ratio"),
    ),
    Preset(
        id="beneish-red-flags",
        name="Beneish red flags",
        description="Possible earnings manipulation (M-Score above the -1.78 threshold)",
        dsl="beneish_m > -1.78",
        columns=("beneish_m", "montier_c", "piotroski_f", "revenue_growth", "net_income_growth"),
    ),
    Preset(
        id="classic-value",
        name="Classic value",
        description="Cheap on earnings and book value",
        dsl="price_to_earnings_ratio < 12 AND price_to_book_ratio < 1.5",
        columns=("price_to_earnings_ratio", "price_to_book_ratio", "earnings_yield", "weighted_dividend_yield", "market_cap"),
    ),
    Preset(
        id="quality",
        name="Quality",
        description="High return on equity with conservative leverage",
        dsl="return_on_equity > 0.15 AND debt_to_equity_ratio < 1",
        columns=("return_on_equity", "debt_to_equity_ratio", "return_on_capital_employed", "net_profit_margin", "piotroski_f"),
    ),
    Preset(
        id="top-ranked",
        name="Top ranked",
        description="Top quintile of the composite quality/value/momentum rank",
        dsl="composite_rank >= 80",
        columns=("composite_rank", "quality_rank", "value_rank", "momentum_rank", "piotroski_f", "altman_z"),
    ),
    Preset(
        id="magic-formula",
        name="Magic formula",
        description="Greenblatt's magic formula — top quintile blending earnings yield and return on capital",
        dsl="magic_formula_rank >= 80",
        columns=("magic_formula_rank", "greenblatt_earnings_yield", "greenblatt_roc", "market_cap"),
    ),
    Preset(
        id="graham-net-net",
        name="Graham net-net",
        description="Deep value: market cap under two-thirds of net current asset value (NCAV)",
        dsl="ncav_to_market_cap >= 1.5",
        columns=("ncav_to_market_cap", "ncav", "market_cap", "current_ratio", "price_to_book_ratio"),
    ),
    Preset(
        id="zmijewski-safe",
        name="Zmijewski safe",
        description="Under 50% modelled probability of financial distress (Zmijewski X < 0)",
        dsl="zmijewski_score < 0",
        columns=("zmijewski_score", "altman_z", "ohlson_o", "debt_to_equity_ratio", "current_ratio"),
    ),
    Preset(
        id="ohlson-safe",
        name="Ohlson safe",
        description="Under 50% modelled probability of distress on the 9-variable O-Score (O < 0)",
        dsl="ohlson_o < 0",
        columns=("ohlson_o", "zmijewski_score", "altman_z", "debt_to_equity_ratio"),
    ),
    Preset(
        id="montier-clean",
        name="Montier clean books",
        description="At most one of Montier's six accounting red flags (C-Score <= 1)",
        dsl="montier_c <= 1",
        columns=("montier_c", "beneish_m", "piotroski_f", "fcf_conversion"),
    ),
    Preset(
        id="top-quality",
        name="Top quality",
        description="Top quintile of the quality pillar rank",
        dsl="quality_rank >= 80",
        columns=("quality_rank", "piotroski_f", "altman_z", "composite_rank"),
    ),
    Preset(
        id="top-value",
        name="Top value",
        description="Top quintile of the value pillar rank",
        dsl="value_rank >= 80",
        columns=("value_rank", "earnings_yield", "price_to_book_ratio", "composite_rank"),
    ),
    Preset(
        id="top-momentum",
        name="Top momentum",
        description="Top quintile of the momentum pillar rank",
        dsl="momentum_rank >= 80",
        columns=("momentum_rank", "return_6m", "composite_rank"),
    ),
    Preset(
        id="greenblatt-factors",
        name="Greenblatt factors",
        description="Cheap and good in absolute terms: earnings yield (EBIT/EV) over 10% and return on capital over 20%",
        dsl="greenblatt_earnings_yield >= 0.1 AND greenblatt_roc >= 0.2",
        columns=("greenblatt_earnings_yield", "greenblatt_roc", "magic_formula_rank", "market_cap"),
    ),
    Preset(
        id="graham-defensive",
        name="Graham margin of safety",
        description="Price below the Graham number — a positive defensive margin of safety",
        dsl="graham_margin_of_safety > 0",
        columns=("graham_margin_of_safety", "graham_number", "price_to_earnings_ratio", "price_to_book_ratio"),
    ),
    Preset(
        id="cash-quality",
        name="Cash quality",
        description="Earnings backed by cash: EBITDA margin over 15%, FCF margin over 5%, FCF conversion above 1",
        dsl="ebitda_margin >= 0.15 AND fcf_margin >= 0.05 AND fcf_conversion >= 1",
        columns=("ebitda_margin", "fcf_margin", "fcf_conversion", "free_cash_flow", "operating_cashflow"),
    ),
    Preset(
        id="dividend-safety",
        name="Dividend safety",
        description="Dividend covered at least twice by net income (non-payers are excluded)",
        dsl="dividend_coverage >= 2",
        columns=("dividend_coverage", "weighted_dividend_yield", "fcf_margin", "net_income"),
    ),
    Preset(
        id="mohanram-growth",
        name="Mohanram growth quality",
        description="At least 5 of the 6 available G-Score signals (adapted starting point — the published cutoff is 6-of-8)",
        dsl="mohanram_g >= 5",
        columns=("mohanram_g", "mohanram_roa", "mohanram_cfo_roa", "mohanram_capex_intensity", "composite_rank"),
    ),
    Preset(
        id="momentum-12-1",
        name="Momentum 12-1",
        description="Classic Jegadeesh-Titman momentum: 12-month return skipping the last month, over 20%",
        dsl="return_12_1 >= 0.2",
        columns=("return_12_1", "return_6m", "momentum_rank", "high_52w_proximity", "volatility_1y"),
    ),
    Preset(
        id="rule-of-40",
        name="Rule of 40",
        description="Growth + FCF margin over 40% — the SaaS heuristic, cash-based variant",
        dsl="rule_of_40 >= 0.4",
        columns=("rule_of_40", "revenue_growth", "fcf_margin", "market_cap"),
    ),
    Preset(
        id="garp",
        name="GARP (PEG ≤ 1)",
        description="Growth at a reasonable price: P/E under the 3-year earnings CAGR (Lynch)",
        dsl="peg_ratio > 0 AND peg_ratio <= 1",
        columns=("peg_ratio", "price_to_earnings_ratio", "net_income_growth", "market_cap"),
    ),
    Preset(
        id="shareholder-yield",
        name="Shareholder yield",
        description="Dividends plus net buybacks over 5% of market cap — cash actually returned",
        dsl="shareholder_yield >= 0.05",
        columns=("shareholder_yield", "weighted_dividend_yield", "dividend_payout_ratio", "market_cap"),
    ),
    Preset(
        id="low-accruals",
        name="Low accruals",
        description="Earnings backed by cash: Sloan accruals at or below 5% of average assets",
        dsl="sloan_accruals <= 0.05",
        columns=("sloan_accruals", "income_quality_ratio", "fcf_conversion", "beneish_m"),
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
        columns=(
            "piotroski_f", "altman_z", "beneish_m", "zmijewski_score", "ohlson_o",
            "montier_c", "composite_rank", "quality_rank", "value_rank",
            "momentum_rank", "magic_formula_rank", "greenblatt_earnings_yield",
            "greenblatt_roc", "graham_margin_of_safety", "ebitda_margin",
            "fcf_margin", "fcf_conversion",
        ),
    ),
]

PRESETS: dict[str, Preset] = {p.id: p for p in _PRESETS}
