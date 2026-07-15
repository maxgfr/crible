"""FR-016 — audited US figures from SEC EDGAR companyfacts (public domain).

The SEC publishes every XBRL fact ever filed, keyless, at
data.sec.gov/api/xbrl/companyfacts/CIK##########.json. We map a conservative
set of us-gaap concepts onto crible's canonical vocabulary and store them as
provider='edgar' raw statements — the audited US layer that outranks scraped
values at reconciliation time, symmetric with ESEF for the EU.

SEC fair-access policy: a declared User-Agent naming the operator with a
contact email — but WITHOUT a URL (the SEC Akamai WAF 403s any UA containing
an http(s) link). config.sec_user_agent() strips URLs defensively. The client
self-limits to 5 req/s on its own bucket — never the Yahoo budget.
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
# the whole US market's XBRL facts in one nightly archive (~1.4 GB) — the
# ADR-0005 scale-up path; never committed, processed then discarded
COMPANYFACTS_BULK_URL = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"

# bound the snapshot's growth: 8 fiscal years is plenty for trends and keeps
# the published parquet well under GitHub's 100 MiB file limit at ~10k issuers
MAX_FISCAL_YEARS = 8

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
    # pretax income (standard us-gaap tags, continuing operations — a small
    # documented deviation): unlocks the EBIT derivation (pretax + interest,
    # canonical.py) → Altman x3, Greenblatt yield, interest coverage for
    # audited-only US symbols
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest":
        ("PretaxIncome", "income"),
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments":
        ("PretaxIncome", "income"),
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
    # short-term investments — completes Dechow's RSST/FIN inputs on
    # reconciled crawled symbols (audited-only Dechow still needs total_debt,
    # deliberately unmapped). Ordered narrow-classic first.
    "ShortTermInvestments": ("OtherShortTermInvestments", "balance"),
    "MarketableSecuritiesCurrent": ("OtherShortTermInvestments", "balance"),
    "AvailableForSaleSecuritiesCurrent": ("OtherShortTermInvestments", "balance"),
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
    periods = sorted(values)[-MAX_FISCAL_YEARS:]
    for statement_type in ("income", "balance", "cashflow"):
        columns = [c for c, s in STATEMENT_OF.items() if s == statement_type]
        rows = []
        for period in periods:
            row: dict[str, Any] = {"period": period}
            row.update({c: values[period][c][1] for c in columns if c in values[period]})
            if len(row) > 1:
                rows.append(row)
        if rows:
            frames[(statement_type, "annual")] = pd.DataFrame(rows)
    return frames


def iter_bulk_companyfacts(zip_path, ciks: set[int]):
    """Yield (cik, companyfacts) for the wanted CIKs from the bulk archive.

    Members are named CIK##########.json; anything unparseable is skipped —
    one broken filing must never sink a 10k-issuer sweep.
    """
    import json
    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            stem = name.rsplit("/", 1)[-1]
            if not (stem.startswith("CIK") and stem.endswith(".json")):
                continue
            try:
                cik = int(stem[3:-5])
            except ValueError:
                continue
            if cik not in ciks:
                continue
            try:
                with archive.open(name) as handle:
                    yield cik, json.load(handle)
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("edgar bulk: skipping %s: %s", stem, exc)


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

    def download_bulk(self, dest) -> None:
        """Stream companyfacts.zip (~1.4 GB) to dest — temp-then-rename."""
        from pathlib import Path

        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".zip.tmp")
        with self._http.stream("GET", COMPANYFACTS_BULK_URL, headers=self._headers) as response:
            response.raise_for_status()
            with open(tmp, "wb") as out:
                for chunk in response.iter_bytes(1 << 20):
                    out.write(chunk)
        tmp.rename(dest)
