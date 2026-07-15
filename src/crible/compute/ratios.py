"""FR-003 — financetoolkit ratio auto-wiring.

Every ``get_*`` pure function across financetoolkit's five ratio modules is
wired automatically when ALL of its required parameters resolve from the
canonical vocabulary (plus derived averages and optional price-based inputs).
Functions with unresolvable required parameters are skipped — a mapping is
only made when the semantics are certain (a wrong mapping is worse than a
missing column).
"""

from __future__ import annotations

import functools
import inspect

import pandas as pd
from financetoolkit.ratios import (
    efficiency_model,
    liquidity_model,
    profitability_model,
    solvency_model,
    valuation_model,
)

RATIO_MODULES = [profitability_model, liquidity_model, solvency_model, efficiency_model, valuation_model]

# Resolvable but never emitted: net_current_asset_value duplicates extras.ncav;
# dividend_yield would be TOTAL dividends over the share price (bogus units —
# weighted_dividend_yield is the real one); dividend_capex_coverage mixes the
# negative canonical capex with positive dividends. The containment tool for
# anything the `dividends` alias accidentally wires.
RATIO_DENYLIST = frozenset({
    "net_current_asset_value",
    "dividend_yield",
    "dividend_capex_coverage_ratio",
})


def _avg(series: pd.Series) -> pd.Series:
    return (series + series.shift(1)) / 2


def build_inputs(canonical: pd.DataFrame, price: pd.Series | None = None) -> dict[str, pd.Series]:
    c = canonical
    inputs: dict[str, pd.Series] = {}

    def alias(names: list[str], series: pd.Series) -> None:
        for name in names:
            inputs[name] = series

    alias(["revenue", "sales", "total_revenue", "net_sales", "net_credit_sales"], c["revenue"])
    alias(["cost_of_goods_sold"], c["cost_of_goods_sold"])
    alias(["net_income"], c["net_income"])
    alias(["operating_income"], c["operating_income"])
    alias(["operating_expenses"], c["operating_expenses"])
    alias(["sga_expenses"], c["sga_expenses"])
    alias(
        [
            "operating_cash_flow",
            "cash_flow_from_operations",
            "operating_cashflow",
            "cash_flow_from_operating_activities",
            "operations_cash_flow",
        ],
        c["operating_cashflow"],
    )
    alias(["current_liabilities", "total_current_liabilities"], c["current_liabilities"])
    alias(["current_assets", "total_current_assets"], c["current_assets"])
    alias(["total_debt"], c["total_debt"])
    alias(["income_before_tax", "earnings_before_tax"], c["income_before_tax"])
    alias(["income_tax_expense", "tax_expense"], c["income_tax_expense"])
    alias(["interest_expense"], c["interest_expense"])
    alias(["total_assets"], c["total_assets"])
    alias(["earnings_before_interest_and_taxes"], c["earnings_before_interest_and_taxes"])
    alias(["free_cash_flow"], c["free_cash_flow"])
    alias(["depreciation_and_amortization"], c["depreciation_and_amortization"])
    alias(["cash_and_equivalents", "cash_and_cash_equivalents"], c["cash_and_equivalents"])
    alias(["marketable_securities"], c["marketable_securities"])
    alias(["accounts_receivable"], c["accounts_receivable"])
    alias(["accounts_payable"], c["accounts_payable"])
    alias(["inventory"], c["inventory"])
    alias(["total_equity", "total_shareholder_equity"], c["total_equity"])
    alias(["total_liabilities"], c["total_liabilities"])
    alias(["retained_earnings"], c["retained_earnings"])
    alias(["goodwill"], c["goodwill"])
    alias(["minority_interest"], c["minority_interest"])
    alias(["capital_expenditure", "capital_expenditures"], c["capital_expenditure"])
    alias(["dividends_paid"], c["dividends_paid"])
    alias(
        [
            "shares_outstanding",
            "common_shares_outstanding",
            "total_shares_outstanding",
            "average_outstanding_shares",
        ],
        c["shares_outstanding"],
    )

    inputs["average_total_assets"] = _avg(c["total_assets"])
    inputs["average_total_equity"] = _avg(c["total_equity"])
    inputs["average_inventory"] = _avg(c["inventory"])
    inputs["average_accounts_receivable"] = _avg(c["accounts_receivable"])
    inputs["average_accounts_payable"] = _avg(c["accounts_payable"])
    inputs["average_total_debt"] = _avg(c["total_debt"])
    inputs["average_total_liabilities"] = _avg(c["total_liabilities"])
    inputs["average_net_fixed_assets"] = _avg(c["net_ppe"])

    # The composite cycle functions take the day-ratio SERIES as parameters,
    # not raw fields — feed them the same published components reflection
    # already emits, so cash_conversion_cycle / operating_cycle wire up and
    # can never diverge from their displayed inputs.
    dio = efficiency_model.get_days_of_inventory_outstanding(
        inputs["average_inventory"], c["cost_of_goods_sold"]
    )
    dso = efficiency_model.get_days_of_sales_outstanding(
        inputs["average_accounts_receivable"], c["revenue"]
    )
    dpo = efficiency_model.get_days_of_accounts_payable_outstanding(
        c["cost_of_goods_sold"], inputs["average_accounts_payable"]
    )
    alias(["days_inventory", "days_of_inventory"], dio)
    alias(["days_sales_outstanding", "days_of_sales_outstanding"], dso)
    alias(["days_payables_outstanding"], dpo)
    # total dividends under the param name the payout/ROIC functions expect;
    # abs() tolerates either sign convention for the reported outflow
    inputs["dividends"] = c["dividends_paid"].abs()

    if price is not None:
        market_cap = price * c["shares_outstanding"]
        eps = c["net_income"] / c["shares_outstanding"]
        alias(["stock_price", "share_price", "market_price_per_share", "price_per_share"], price)
        alias(["market_cap", "market_capitalization"], market_cap)
        inputs["earnings_per_share"] = eps
        inputs["book_value_per_share"] = c["total_equity"] / c["shares_outstanding"]
        inputs["net_debt"] = c["total_debt"] - c["cash_and_equivalents"]
        inputs["enterprise_value"] = market_cap + c["total_debt"] - c["cash_and_equivalents"]

    return inputs


def compute_ratios(canonical: pd.DataFrame, price: pd.Series | None = None) -> pd.DataFrame:
    inputs = build_inputs(canonical, price)
    out: dict[str, pd.Series] = {}
    for module in RATIO_MODULES:
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("get_"):
                continue
            column = name[4:]
            if column in out or column in canonical.columns or column in RATIO_DENYLIST:
                continue
            params = inspect.signature(fn).parameters
            required = [p for p in params.values() if p.default is inspect.Parameter.empty]
            if not all(p.name in inputs for p in required):
                continue
            try:
                result = fn(**{p.name: inputs[p.name] for p in required})
            except Exception:  # noqa: BLE001 — a single ratio must never kill compute
                continue
            if isinstance(result, pd.Series):
                out[column] = result
    return pd.DataFrame(out, index=canonical.index)


@functools.lru_cache(maxsize=1)
def price_dependent_ratio_columns() -> frozenset[str]:
    """Ratio columns whose values price-derive and therefore exist for the
    LATEST fiscal period only (the price series is NaN elsewhere): their
    year-over-year growth can never resolve, so the snapshot must not
    generate those columns. Determined by running the real wiring on a
    synthetic 3-period company with a latest-only price — a column counts
    when every period but the last is NaN. Presence-only reflection would
    over-count: net_debt resolves ONLY when a price is passed yet its values
    are a full series, so net_debt_to_ebitda_ratio_growth is real."""
    from crible.compute.canonical import CANONICAL_FIELDS

    periods = pd.Index(["p1", "p2", "p3"])
    # distinct values per field so synthetic denominators never hit 0/0
    canonical = pd.DataFrame(
        {field: [i + 2.0, i + 3.0, i + 4.0] for i, field in enumerate(CANONICAL_FIELDS)},
        index=periods,
    )
    price = pd.Series([float("nan"), float("nan"), 5.0], index=periods)
    ratios = compute_ratios(canonical, price)
    return frozenset(ratios.columns[ratios.iloc[:-1].isna().all()])
