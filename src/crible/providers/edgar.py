"""FR-016 — audited US figures from SEC EDGAR companyfacts (public domain).

The SEC publishes every XBRL fact ever filed, keyless, at
data.sec.gov/api/xbrl/companyfacts/CIK##########.json. We map a conservative
set of us-gaap concepts onto crible's canonical vocabulary and store them as
provider='edgar' raw statements — the audited US layer that outranks scraped
values at reconciliation time, symmetric with ESEF for the EU.

SEC fair-access policy: a declared User-Agent with contact info and at most
10 requests/second. The client self-limits to 5 req/s on its own bucket —
never the Yahoo budget.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import pandas as pd

from crible.ingest.budget import TokenBucket

log = logging.getLogger("crible.providers.edgar")

COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

ANNUAL_FORMS = ("10-K", "20-F", "40-F")
# a full-year duration, with slack for 52/53-week fiscal calendars
FULL_YEAR_DAYS = (320, 400)

# us-gaap concept → (yfinance-vocabulary column, statement type), so
# compute/canonical.py picks the values up unchanged. Ordered: for a column
# fed by several concepts (revenue, cost of revenue), the FIRST concept that
# reported a period keeps it. Debt/dividends/EBIT are deliberately omitted —
# no single clean us-gaap concept; reconcile only overrides what audited has.
CONCEPT_MAP: dict[str, tuple[str, str]] = {
    # income statement (duration facts)
    "Revenues": ("TotalRevenue", "income"),
    "RevenueFromContractWithCustomerExcludingAssessedTax": ("TotalRevenue", "income"),
    "SalesRevenueNet": ("TotalRevenue", "income"),
    "CostOfRevenue": ("CostOfRevenue", "income"),
    "CostOfGoodsAndServicesSold": ("CostOfRevenue", "income"),
    "GrossProfit": ("GrossProfit", "income"),
    "OperatingIncomeLoss": ("OperatingIncome", "income"),
    "NetIncomeLoss": ("NetIncome", "income"),
    "IncomeTaxExpenseBenefit": ("TaxProvision", "income"),
    "InterestExpense": ("InterestExpense", "income"),
    "WeightedAverageNumberOfSharesOutstandingBasic": ("BasicAverageShares", "income"),
    # balance sheet (instant facts)
    "Assets": ("TotalAssets", "balance"),
    "AssetsCurrent": ("CurrentAssets", "balance"),
    "Liabilities": ("TotalLiabilitiesNetMinorityInterest", "balance"),
    "LiabilitiesCurrent": ("CurrentLiabilities", "balance"),
    "StockholdersEquity": ("StockholdersEquity", "balance"),
    "RetainedEarningsAccumulatedDeficit": ("RetainedEarnings", "balance"),
    "InventoryNet": ("Inventory", "balance"),
    "AccountsReceivableNetCurrent": ("AccountsReceivable", "balance"),
    "AccountsPayableCurrent": ("AccountsPayable", "balance"),
    "CashAndCashEquivalentsAtCarryingValue": ("CashAndCashEquivalents", "balance"),
    "PropertyPlantAndEquipmentNet": ("NetPPE", "balance"),
    "Goodwill": ("Goodwill", "balance"),
    # cash flow (duration facts)
    "NetCashProvidedByUsedInOperatingActivities": ("OperatingCashFlow", "cashflow"),
    "PaymentsToAcquirePropertyPlantAndEquipment": ("CapitalExpenditure", "cashflow"),
}

# SEC reports capex as a positive payment; the canonical (yfinance) convention
# is a negative outflow — build_canonical derives FCF as ocf + capex
NEGATED_CONCEPTS = {"PaymentsToAcquirePropertyPlantAndEquipment"}

# canonical (yfinance-vocabulary) column → statement type, for frame assembly
STATEMENT_OF = {column: stmt for column, stmt in CONCEPT_MAP.values()}

SHARE_COLUMNS = {"BasicAverageShares"}


def _full_year(start: str, end: str) -> bool:
    try:
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    except ValueError:
        return False
    return FULL_YEAR_DAYS[0] <= days <= FULL_YEAR_DAYS[1]


def facts_to_frames(companyfacts: dict[str, Any]) -> dict[tuple[str, str], pd.DataFrame]:
    """companyfacts JSON → raw frames keyed by (statement_type, 'annual').

    Only annual-report facts are kept (forms 10-K/20-F/40-F with fp=FY, in
    USD/shares; duration facts must span a full fiscal year) — conservative
    by design, the ESEF rule: an audited number we are not sure about is a
    number we do not take. The latest-filed value wins per period; the period
    label is the fiscal END date ("2024-09-28"), which align_periods matches
    to yfinance's dated periods.
    """
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    # values[period][column] = (filed, value); claimed pins the winning concept
    values: dict[str, dict[str, tuple[str, float]]] = {}
    claimed: dict[tuple[str, str], str] = {}
    for concept, (column, _) in CONCEPT_MAP.items():
        units = gaap.get(concept, {}).get("units", {})
        unit_key = "shares" if column in SHARE_COLUMNS else "USD"
        for entry in units.get(unit_key, []):
            if entry.get("form") not in ANNUAL_FORMS or entry.get("fp") != "FY":
                continue
            period = entry.get("end")
            if not period:
                continue
            start = entry.get("start")
            if start is not None and not _full_year(start, period):
                continue  # a quarterly duration re-reported inside a 10-K
            try:
                value = float(entry["val"])
            except (KeyError, TypeError, ValueError):
                continue
            if concept in NEGATED_CONCEPTS:
                value = -value
            owner = claimed.get((period, column))
            if owner is not None and owner != concept:
                continue  # an earlier-listed concept already supplies this column
            filed = str(entry.get("filed", ""))
            current = values.setdefault(period, {}).get(column)
            if current is None or filed >= current[0]:
                values[period][column] = (filed, value)
                claimed[(period, column)] = concept

    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for statement_type in ("income", "balance", "cashflow"):
        columns = [c for c, s in STATEMENT_OF.items() if s == statement_type]
        rows = []
        for period in sorted(values):
            row: dict[str, Any] = {"period": period}
            row.update({c: values[period][c][1] for c in columns if c in values[period]})
            if len(row) > 1:
                rows.append(row)
        if rows:
            frames[(statement_type, "annual")] = pd.DataFrame(rows)
    return frames


def resolve_ciks(
    companies: list[dict], tickers: dict[str, int]
) -> tuple[dict[str, int], list[str]]:
    """symbol→CIK for listings whose ticker appears in the SEC directory;
    plus unmatched symbols — counted, never errored (the ESEF AC-4 pattern).
    The SEC directory uses dash-form tickers (BRK-B), matching the universe.
    """
    resolved: dict[str, int] = {}
    unmatched: list[str] = []
    for company in companies:
        symbol = company["symbol"]
        cik = tickers.get(str(symbol).strip().upper())
        if cik is not None:
            resolved[symbol] = cik
        else:
            unmatched.append(symbol)
    return resolved, unmatched


class EdgarClient:
    """Thin network client — kept separate so tests inject fixtures.

    Sends the declared User-Agent on every request (SEC fair-access) and
    paces itself with a dedicated 5 req/s bucket.
    """

    def __init__(self, http=None, user_agent: str | None = None) -> None:
        from crible import config

        if http is None:
            import httpx

            http = httpx.Client(timeout=30, follow_redirects=True)
        self._http = http
        self._headers = {"User-Agent": user_agent or config.sec_user_agent()}
        self._bucket = TokenBucket(capacity=5, window_seconds=1)

    def _get_json(self, url: str) -> dict:
        while not self._bucket.try_acquire():
            time.sleep(max(self._bucket.seconds_until_available(), 0.05))
        response = self._http.get(url, headers=self._headers)
        response.raise_for_status()
        return response.json()

    def company_tickers(self) -> dict[str, int]:
        """{ticker: cik} from the SEC's directory (dash-form tickers)."""
        payload = self._get_json(COMPANY_TICKERS_URL)
        return {
            str(entry["ticker"]).strip().upper(): int(entry["cik_str"])
            for entry in payload.values()
            if entry.get("ticker") and entry.get("cik_str") is not None
        }

    def companyfacts(self, cik: int) -> dict:
        return self._get_json(COMPANYFACTS_URL.format(cik=int(cik)))
