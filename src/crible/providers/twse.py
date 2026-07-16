"""Audited Taiwan — TWSE OpenAPI (fully-free, Taiwan OGDL v1 ≈ CC BY 4.0).

openapi.twse.com.tw serves the WHOLE listed market's quarterly statements as
keyless JSON — but only the LATEST period per company: history must be
accumulated forward (the raw layer is the store — it travels in the
data-latest tarball; `data/mirror` does not). Day-one coverage is therefore
one period per company, growing every quarter; deep back-history never
appears. Stated in docs.

Income statements are CUMULATIVE year-to-date, so only Q4 rows (= the full
fiscal year) become annual income; balance sheets are instants — Q4 lands in
the annual frame, Q1–Q3 in the quarterly frame so a partial quarter never
degrades the screener's latest annual row. Years are ROC (+1911), values TWD
thousands (×1000; TWD has no ECB rate → `*_eur` stays NULL, documented).

TPEx (.TWO) twins are a follow-up: their OpenAPI path needs its own probe.
The TWSE ToS carves these open-data feeds out of its anti-scraping clause.
Attribution: data from TWSE OpenAPI, Taiwan Stock Exchange.
"""

from __future__ import annotations

import pandas as pd

INCOME_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci"
BALANCE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap07_L_ci"

ROC_OFFSET = 1911
QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}
THOUSANDS = 1000.0

# Chinese field → (yfinance column, rank) — lower rank wins per column.
# General-industry (_ci) vocabulary, probed live 2026-07-16.
INCOME_FIELDS = {
    "營業收入": ("TotalRevenue", 0),
    "營業成本": ("CostOfRevenue", 0),
    "營業毛利（毛損）淨額": ("GrossProfit", 0),
    "營業費用": ("OperatingExpense", 0),
    "營業利益（損失）": ("OperatingIncome", 0),
    "稅前淨利（淨損）": ("PretaxIncome", 0),
    "所得稅費用（利益）": ("TaxProvision", 0),
    "本期淨利（淨損）": ("NetIncome", 0),
    "繼續營業單位本期淨利（淨損）": ("NetIncome", 1),
}
BALANCE_FIELDS = {
    "流動資產": ("CurrentAssets", 0),
    "資產總額": ("TotalAssets", 0),
    "流動負債": ("CurrentLiabilities", 0),
    "負債總額": ("TotalLiabilitiesNetMinorityInterest", 0),
    "保留盈餘": ("RetainedEarnings", 0),
    "歸屬於母公司業主之權益合計": ("StockholdersEquity", 0),
    "權益總額": ("StockholdersEquity", 1),
}


def roc_period(year: str, quarter: str) -> str | None:
    """ROC '115' + '1' → '2026-03-31'; None on garbage."""
    end = QUARTER_END.get(str(quarter).strip())
    try:
        western = int(str(year).strip()) + ROC_OFFSET
    except ValueError:
        return None
    return f"{western}-{end}" if end else None


def _values(row: dict, fields: dict[str, tuple[str, int]]) -> dict[str, float]:
    picked: dict[str, tuple[int, float]] = {}
    for name, (column, rank) in fields.items():
        raw = str(row.get(name, "") or "").replace(",", "").strip()
        if not raw:
            continue
        try:
            value = float(raw) * THOUSANDS
        except ValueError:
            continue
        current = picked.get(column)
        if current is None or rank < current[0]:
            picked[column] = (rank, value)
    return {column: value for column, (_, value) in picked.items()}


def frames_from_reports(
    income_rows: list[dict], balance_rows: list[dict], code: str
) -> dict[tuple[str, str], pd.DataFrame]:
    """One company's latest-period rows → crible raw frames. Q4 = the fiscal
    year (annual income + balance); Q1–Q3 balances go quarterly."""
    annual_income: dict[str, dict[str, float]] = {}
    annual_balance: dict[str, dict[str, float]] = {}
    quarterly_balance: dict[str, dict[str, float]] = {}

    for row in income_rows:
        if str(row.get("公司代號", "")).strip() != code:
            continue
        quarter = str(row.get("季別", "")).strip()
        period = roc_period(row.get("年度", ""), quarter)
        if period is None or quarter != "4":
            continue  # cumulative YTD: only Q4 IS the full year
        values = _values(row, INCOME_FIELDS)
        if values:
            annual_income[period] = values
    for row in balance_rows:
        if str(row.get("公司代號", "")).strip() != code:
            continue
        quarter = str(row.get("季別", "")).strip()
        period = roc_period(row.get("年度", ""), quarter)
        if period is None:
            continue
        values = _values(row, BALANCE_FIELDS)
        if not values:
            continue
        (annual_balance if quarter == "4" else quarterly_balance)[period] = values

    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for key, periods in (
        (("income", "annual"), annual_income),
        (("balance", "annual"), annual_balance),
        (("balance", "quarterly"), quarterly_balance),
    ):
        if periods:
            frames[key] = pd.DataFrame(
                [{"period": period, **values} for period, values in sorted(periods.items())]
            )
    return frames
