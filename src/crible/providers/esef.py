"""FR-010 — audited EU figures from filings.xbrl.org (keyless ESEF repository).

Filings are indexed by LEI (JSON:API at /api/filings); each filing exposes an
xBRL-JSON document whose facts carry IFRS concepts. We map a conservative set
of IFRS concepts onto crible's canonical vocabulary and store them as
provider='esef' raw statements — the audited layer that outranks scraped
values at reconciliation time.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

log = logging.getLogger("crible.providers.esef")

FILINGS_API = "https://filings.xbrl.org/api/filings"

# IFRS concept (ifrs-full unless prefixed) → (canonical field, statement type)
CONCEPT_MAP: dict[str, tuple[str, str]] = {
    "ifrs-full:Revenue": ("TotalRevenue", "income"),
    "ifrs-full:RevenueFromContractsWithCustomers": ("TotalRevenue", "income"),
    "ifrs-full:GrossProfit": ("GrossProfit", "income"),
    "ifrs-full:ProfitLossFromOperatingActivities": ("OperatingIncome", "income"),
    "ifrs-full:ProfitLoss": ("NetIncome", "income"),
    "ifrs-full:ProfitLossAttributableToOwnersOfParent": ("NetIncome", "income"),
    "ifrs-full:Assets": ("TotalAssets", "balance"),
    "ifrs-full:CurrentAssets": ("CurrentAssets", "balance"),
    "ifrs-full:CurrentLiabilities": ("CurrentLiabilities", "balance"),
    "ifrs-full:Equity": ("StockholdersEquity", "balance"),
    "ifrs-full:EquityAttributableToOwnersOfParent": ("StockholdersEquity", "balance"),
    "ifrs-full:RetainedEarnings": ("RetainedEarnings", "balance"),
    "ifrs-full:Inventories": ("Inventory", "balance"),
    "ifrs-full:TradeAndOtherCurrentReceivables": ("AccountsReceivable", "balance"),
    "ifrs-full:CashAndCashEquivalents": ("CashAndCashEquivalents", "balance"),
    "ifrs-full:CashFlowsFromUsedInOperatingActivities": ("OperatingCashFlow", "cashflow"),
}

# canonical (yfinance-vocabulary) column → statement type, for frame assembly
STATEMENT_OF = {canonical: stmt for canonical, stmt in CONCEPT_MAP.values()}


def facts_to_frames(xbrl_json: dict[str, Any]) -> dict[tuple[str, str], pd.DataFrame]:
    """xBRL-JSON → raw frames keyed by (statement_type, 'annual').

    Only full-year instant/duration facts without extra dimensions are kept —
    conservative by design: an audited number we are not sure about is a
    number we do not take.
    """
    facts = xbrl_json.get("facts", {})
    values: dict[str, dict[str, float]] = {}
    for fact in facts.values():
        dimensions = fact.get("dimensions", {})
        concept = dimensions.get("concept")
        mapped = CONCEPT_MAP.get(concept)
        if mapped is None:
            continue
        if any(k not in ("concept", "entity", "period", "unit", "language") for k in dimensions):
            continue  # segmented/dimensional fact — skip, whole-entity only
        period = dimensions.get("period", "")
        year = _fiscal_year(period)
        if year is None:
            continue
        try:
            value = float(fact.get("value"))
        except (TypeError, ValueError):
            continue
        column, _ = mapped
        values.setdefault(year, {})[column] = value

    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for statement_type in ("income", "balance", "cashflow"):
        columns = [c for c, s in STATEMENT_OF.items() if s == statement_type]
        rows = []
        for year in sorted(values):
            row = {"period": year}
            row.update({c: values[year][c] for c in columns if c in values[year]})
            if len(row) > 1:
                rows.append(row)
        if rows:
            frames[(statement_type, "annual")] = pd.DataFrame(rows)
    return frames


def _fiscal_year(period: str) -> str | None:
    """xBRL-JSON period → fiscal year string.

    Durations look like '2024-01-01T00:00:00/2025-01-01T00:00:00', instants
    like '2025-01-01T00:00:00'. We tag the year that ENDS the period.
    """
    if not period:
        return None
    end = period.split("/")[-1]
    year = end[:4]
    if not year.isdigit():
        return None
    # a Jan-1 instant/end belongs to the fiscal year that just closed
    month_day = end[5:10]
    if month_day == "01-01":
        return str(int(year) - 1)
    return year


class EsefClient:
    """Thin network client — kept separate so tests inject fixtures."""

    def __init__(self, http=None) -> None:
        import httpx

        self._http = http or httpx.Client(timeout=30, follow_redirects=True)

    def filings_for_lei(self, lei: str) -> list[dict]:
        import json

        params = {
            "filter": json.dumps(
                [{"name": "entity.identifier", "op": "eq", "val": lei}]
            ),
            "sort": "-date_added",
        }
        response = self._http.get(FILINGS_API, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def fetch_xbrl_json(self, filing: dict) -> dict | None:
        attributes = filing.get("attributes", {})
        json_url = attributes.get("json_url")
        if not json_url:
            return None
        if json_url.startswith("/"):
            json_url = "https://filings.xbrl.org" + json_url
        response = self._http.get(json_url)
        response.raise_for_status()
        return response.json()

    def filing_page_url(self, filing: dict) -> str | None:
        attributes = filing.get("attributes", {})
        for key in ("viewer_url", "package_url", "json_url"):
            if attributes.get(key):
                url = attributes[key]
                return "https://filings.xbrl.org" + url if url.startswith("/") else url
        return None
