"""FR-003 — canonical financial fields extracted from raw provider frames.

Raw frames (one per statement type/freq, as written by the ingest raw layer)
have a ``period`` column plus one column per line item using the provider's
vocabulary (yfinance names like ``TotalRevenue``). This module maps them onto
a canonical, provider-agnostic vocabulary chosen to feed financetoolkit's
pure ratio functions directly.
"""

from __future__ import annotations

import pandas as pd

# canonical field -> candidate provider column names, first match wins
FIELD_CANDIDATES: dict[str, list[str]] = {
    # income statement
    "revenue": ["TotalRevenue", "OperatingRevenue", "Total Revenue"],
    "cost_of_goods_sold": ["CostOfRevenue", "ReconciledCostOfRevenue"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncome", "TotalOperatingIncomeAsReported"],
    "operating_expenses": ["OperatingExpense"],
    "sga_expenses": ["SellingGeneralAndAdministration", "SellingGeneralAndAdministrative"],
    "earnings_before_interest_and_taxes": ["EBIT"],
    "ebitda": ["EBITDA", "NormalizedEBITDA"],
    "income_before_tax": ["PretaxIncome"],
    "income_tax_expense": ["TaxProvision"],
    "net_income": ["NetIncome", "NetIncomeCommonStockholders"],
    "interest_expense": ["InterestExpense"],
    "depreciation_and_amortization": [
        "DepreciationAndAmortization",
        "ReconciledDepreciation",
        "DepreciationAmortizationDepletion",
    ],
    "shares_outstanding": ["BasicAverageShares", "OrdinarySharesNumber", "ShareIssued"],
    # balance sheet
    "total_assets": ["TotalAssets"],
    "current_assets": ["CurrentAssets"],
    "current_liabilities": ["CurrentLiabilities"],
    "cash_and_equivalents": ["CashAndCashEquivalents"],
    "marketable_securities": ["OtherShortTermInvestments"],
    "accounts_receivable": ["AccountsReceivable", "Receivables"],
    "accounts_payable": ["AccountsPayable", "Payables"],
    "inventory": ["Inventory"],
    "net_ppe": ["NetPPE"],
    "gross_ppe": ["GrossPPE"],
    "total_debt": ["TotalDebt"],
    "long_term_debt": ["LongTermDebt", "LongTermDebtAndCapitalLeaseObligation"],
    "total_liabilities": ["TotalLiabilitiesNetMinorityInterest"],
    "total_equity": ["StockholdersEquity", "CommonStockEquity"],
    "retained_earnings": ["RetainedEarnings"],
    "working_capital": ["WorkingCapital"],
    "minority_interest": ["MinorityInterest"],
    "goodwill": ["Goodwill"],
    # cash flow
    "operating_cashflow": ["OperatingCashFlow", "CashFlowFromContinuingOperatingActivities"],
    "capital_expenditure": ["CapitalExpenditure"],
    "free_cash_flow": ["FreeCashFlow"],
    "dividends_paid": ["CashDividendsPaid", "CommonStockDividendPaid"],
    "common_stock_issuance": ["CommonStockIssuance"],
}

CANONICAL_FIELDS = list(FIELD_CANDIDATES)


def build_canonical(frames: dict[tuple[str, str], pd.DataFrame], freq: str = "annual") -> pd.DataFrame:
    """Merge raw statement frames for one symbol into a canonical frame.

    Returns a DataFrame indexed by period (ascending), one column per
    canonical field; fields the provider did not supply are NaN — never
    imputed (FR-003 failure path).
    """
    merged: pd.DataFrame | None = None
    for statement_type in ("income", "balance", "cashflow"):
        frame = frames.get((statement_type, freq))
        if frame is None or frame.empty:
            continue
        # drop raw-layer metadata columns (_symbol, _provider, …) before joining
        frame = frame[[c for c in frame.columns if not str(c).startswith("_")]]
        indexed = frame.set_index("period")
        indexed = indexed[~indexed.index.duplicated(keep="last")]
        merged = indexed if merged is None else merged.join(indexed, how="outer", rsuffix="_dup")

    if merged is None:
        return pd.DataFrame(columns=CANONICAL_FIELDS)

    out = pd.DataFrame(index=merged.index.astype(str))
    for field, candidates in FIELD_CANDIDATES.items():
        series = None
        for name in candidates:
            if name in merged.columns:
                series = pd.to_numeric(merged[name], errors="coerce")
                break
        out[field] = series if series is not None else float("nan")

    # transparent derivations (documented, no imputation beyond arithmetic identity)
    if out["gross_profit"].isna().all():
        out["gross_profit"] = out["revenue"] - out["cost_of_goods_sold"]
    if out["cost_of_goods_sold"].isna().all():
        out["cost_of_goods_sold"] = out["revenue"] - out["gross_profit"]
    if out["working_capital"].isna().all():
        out["working_capital"] = out["current_assets"] - out["current_liabilities"]
    if out["free_cash_flow"].isna().all():
        # yfinance capital_expenditure is negative
        out["free_cash_flow"] = out["operating_cashflow"] + out["capital_expenditure"]
    if out["earnings_before_interest_and_taxes"].isna().all():
        out["earnings_before_interest_and_taxes"] = (
            out["income_before_tax"] + out["interest_expense"]
        )
    if out["ebitda"].isna().all():
        out["ebitda"] = (
            out["earnings_before_interest_and_taxes"] + out["depreciation_and_amortization"]
        )

    return out.sort_index()
