"""FR-010 — audited EU figures from filings.xbrl.org (keyless ESEF repository).

Filings are indexed by LEI (JSON:API at /api/filings); each filing exposes an
xBRL-JSON document whose facts carry IFRS concepts. We map a conservative set
of IFRS concepts onto crible's canonical vocabulary and store them as
provider='esef' raw statements — the audited layer that outranks scraped
values at reconciliation time.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import pandas as pd

from crible.providers.audited import merge_audited

log = logging.getLogger("crible.providers.esef")

FILINGS_API = "https://filings.xbrl.org/api/filings"
ENTITIES_API = "https://filings.xbrl.org/api/entities"

# a full-year duration, with slack for 52/53-week fiscal calendars (as EDGAR)
FULL_YEAR_DAYS = (320, 400)

# IFRS concept (ifrs-full unless prefixed) → (canonical field, statement type).
# Ordered narrow/classic before broad variants (CONCEPT_RANK below). Fill
# rates vary by filer far more than us-gaap (ESEF anchors face lines to
# entity extensions) — availability grounded on a 30-filing live scan
# (2026-07-17). Documented omissions: GrossPPE (dimensional-only in IFRS —
# the carrying-amount axis is dropped with every dimensional fact),
# FinanceCosts (broader than interest: FX, discount unwinding — would
# overstate the EBIT derivation), ShorttermBorrowings (misses the current
# portion of long-term debt), NumberOfSharesOutstanding (0/30 undimensioned
# live), DepreciationPropertyPlantAndEquipment (depreciation only — would
# understate D&A). Facts without dimensions may be parent-company figures
# when a filer submits separate-only statements — pre-existing exposure.
CONCEPT_MAP: dict[str, tuple[str, str]] = {
    # income statement (duration facts)
    "ifrs-full:Revenue": ("TotalRevenue", "income"),
    "ifrs-full:RevenueFromContractsWithCustomers": ("TotalRevenue", "income"),
    "ifrs-full:GrossProfit": ("GrossProfit", "income"),
    "ifrs-full:CostOfSales": ("CostOfRevenue", "income"),
    "ifrs-full:ProfitLossFromOperatingActivities": ("OperatingIncome", "income"),
    "ifrs-full:ProfitLoss": ("NetIncome", "income"),
    "ifrs-full:ProfitLossAttributableToOwnersOfParent": ("NetIncome", "income"),
    # pretax + tax + interest → EBIT derivation (canonical.py) → Altman x3,
    # Greenblatt, interest coverage — when the filer tags interest at all
    "ifrs-full:ProfitLossBeforeTax": ("PretaxIncome", "income"),
    "ifrs-full:IncomeTaxExpenseContinuingOperations": ("TaxProvision", "income"),
    "ifrs-full:InterestExpense": ("InterestExpense", "income"),
    # SG&A → Beneish SGAI; function-of-expense filers tagging
    # DistributionCosts + AdministrativeExpense separately keep honest NaN
    # (no fabricated sums)
    "ifrs-full:SellingGeneralAndAdministrativeExpense":
        ("SellingGeneralAndAdministration", "income"),
    "ifrs-full:WeightedAverageShares": ("BasicAverageShares", "income"),
    # balance sheet (instant facts)
    "ifrs-full:Assets": ("TotalAssets", "balance"),
    "ifrs-full:CurrentAssets": ("CurrentAssets", "balance"),
    "ifrs-full:CurrentLiabilities": ("CurrentLiabilities", "balance"),
    "ifrs-full:Liabilities": ("TotalLiabilitiesNetMinorityInterest", "balance"),
    "ifrs-full:Equity": ("StockholdersEquity", "balance"),
    "ifrs-full:EquityAttributableToOwnersOfParent": ("StockholdersEquity", "balance"),
    "ifrs-full:RetainedEarnings": ("RetainedEarnings", "balance"),
    "ifrs-full:Inventories": ("Inventory", "balance"),
    "ifrs-full:TradeAndOtherCurrentReceivables": ("AccountsReceivable", "balance"),
    "ifrs-full:TradeAndOtherCurrentPayablesToTradeSuppliers": ("AccountsPayable", "balance"),
    # broad fallback includes accruals — documented approximation, symmetric
    # with the broad receivables mapping above
    "ifrs-full:TradeAndOtherCurrentPayables": ("AccountsPayable", "balance"),
    "ifrs-full:CashAndCashEquivalents": ("CashAndCashEquivalents", "balance"),
    # IAS 16 carrying amount is net by definition; the IFRS 16 combined
    # presentation (ROU assets included) is the ESEF mirror of edgar's
    # ASC 842 fallback pair — narrow tag wins when both are filed
    "ifrs-full:PropertyPlantAndEquipment": ("NetPPE", "balance"),
    "ifrs-full:PropertyPlantAndEquipmentIncludingRightofuseAssets": ("NetPPE", "balance"),
    "ifrs-full:Goodwill": ("Goodwill", "balance"),
    # borrowings, not NoncurrentLiabilities (provisions, deferred tax and
    # pensions would corrupt Beneish LVGI and any debt ratio)
    "ifrs-full:LongtermBorrowings": ("LongTermDebt", "balance"),
    "ifrs-full:CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings":
        ("CurrentDebt", "balance"),
    # cash flow (duration facts)
    "ifrs-full:CashFlowsFromUsedInOperatingActivities": ("OperatingCashFlow", "cashflow"),
    "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities":
        ("CapitalExpenditure", "cashflow"),
    "ifrs-full:PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets":
        ("CapitalExpenditure", "cashflow"),
    "ifrs-full:DividendsPaidClassifiedAsFinancingActivities": ("CashDividendsPaid", "cashflow"),
    # D&A: cash-flow reconciliation line first (the edgar DD&A-first pattern)
    "ifrs-full:AdjustmentsForDepreciationAndAmortisationExpense":
        ("DepreciationAndAmortization", "cashflow"),
    "ifrs-full:DepreciationAndAmortisationExpense": ("DepreciationAndAmortization", "cashflow"),
    "ifrs-full:ProceedsFromIssuingShares": ("CommonStockIssuance", "cashflow"),
}

# xbrl-json outflow concepts carry positive magnitudes (the calculation
# linkbase subtracts them — verified live: 14/14 capex and 12/12 dividends
# facts positive on the 2026-07-17 scan); canonical convention is negative
NEGATED_CONCEPTS = {
    "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
    "ifrs-full:PurchaseOfPropertyPlantAndEquipmentIntangibleAssetsOtherThanGoodwillInvestmentPropertyAndOtherNoncurrentAssets",
    "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
}

# The one narrow exception to the whole-entity rule: IFRS filers tag retained
# earnings almost only dimensionally (SOCIE, ComponentsOfEquityAxis), so the
# blanket dimensional skip starves Altman x2 → the Quality pillar for EU names.
# A fact qualifies only when its SINGLE extra dimension is this exact
# axis/member pair — extension axes/members never match the ifrs-full QNames
# and stay conservatively dropped. No double-counting: the value fills one
# canonical column, never a sum. IAS 8 restatements can make the Jan-1 opening
# instant differ from the prior close — same exposure class as the documented
# parent-company caveat above.
_EQUITY_COMPONENTS_AXIS = "ifrs-full:ComponentsOfEquityAxis"
DIMENSIONAL_RECOVERY: dict[tuple[str, str, str], tuple[str, str]] = {
    ("ifrs-full:Equity", _EQUITY_COMPONENTS_AXIS, "ifrs-full:RetainedEarningsMember"):
        ("RetainedEarnings", "balance"),
    ("ifrs-full:RetainedEarnings", _EQUITY_COMPONENTS_AXIS, "ifrs-full:RetainedEarningsMember"):
        ("RetainedEarnings", "balance"),
}

# canonical (yfinance-vocabulary) column → statement type, for frame assembly
STATEMENT_OF = {canonical: stmt for canonical, stmt in CONCEPT_MAP.values()}

# declared precedence for column collisions: when several IFRS concepts feed the
# same canonical column (e.g. ProfitLoss vs ProfitLossAttributableToOwnersOfParent
# → NetIncome), the concept listed FIRST in CONCEPT_MAP wins — deterministically,
# never by JSON order (F10).
CONCEPT_RANK = {concept: rank for rank, concept in enumerate(CONCEPT_MAP)}


def facts_to_frames(xbrl_json: dict[str, Any]) -> dict[tuple[str, str], pd.DataFrame]:
    """xBRL-JSON → raw frames keyed by (statement_type, 'annual').

    Only full-year instant/duration facts without extra dimensions are kept —
    conservative by design: an audited number we are not sure about is a
    number we do not take.
    """
    facts = xbrl_json.get("facts", {})
    values: dict[str, dict[str, float]] = {}
    claimed: dict[tuple[str, str], int] = {}  # (year, column) → winning concept rank
    for fact in facts.values():
        dimensions = fact.get("dimensions", {})
        concept = dimensions.get("concept")
        extra = [k for k in dimensions if k not in ("concept", "entity", "period", "unit", "language")]
        if extra:
            # segmented/dimensional fact — whole-entity only, except the
            # declared DIMENSIONAL_RECOVERY pairs (single known axis/member)
            if len(extra) != 1:
                continue
            mapped = DIMENSIONAL_RECOVERY.get((concept, extra[0], str(dimensions.get(extra[0]))))
            if mapped is None:
                continue
            rank = len(CONCEPT_MAP)  # below every direct concept — undimensioned wins
        else:
            mapped = CONCEPT_MAP.get(concept)
            if mapped is None:
                continue
            rank = CONCEPT_RANK[concept]
        period = dimensions.get("period", "")
        year = _fiscal_year(period)
        if year is None:
            continue
        try:
            value = float(fact.get("value"))
        except (TypeError, ValueError):
            continue
        if concept in NEGATED_CONCEPTS:
            if value < 0:
                # diagnostic only — ESEF sign errors are a known data-quality
                # issue; the unconditional negation (edgar precedent) stands
                log.warning("esef: negated concept %s already negative (%s)", concept, value)
            value = -value
        column, _ = mapped
        key = (year, column)
        if key in claimed and claimed[key] <= rank:
            continue  # an equal-or-earlier-precedence concept already set this column
        values.setdefault(year, {})[column] = value
        claimed[key] = rank

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


def _full_year(start: str, end: str) -> bool:
    try:
        span = (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days
    except ValueError:
        return False
    return FULL_YEAR_DAYS[0] <= span <= FULL_YEAR_DAYS[1]


def _fiscal_year(period: str) -> str | None:
    """xBRL-JSON period → fiscal year string, or None if it is not a full year.

    Durations look like '2024-01-01T00:00:00/2025-01-01T00:00:00', instants
    like '2025-01-01T00:00:00'. A duration is accepted only when it spans a
    full fiscal year (320-400 days, EDGAR's 52/53-week slack) — an interim
    (quarter/half-year) duration must NEVER be booked as an annual audited
    figure (F9). Instants (balance-sheet facts) are point-in-time and always
    tag the year that just closed.
    """
    if not period:
        return None
    if "/" in period:
        start, end = period.split("/", 1)
        if not _full_year(start, end):
            return None
    else:
        end = period
    year = end[:4]
    if not year.isdigit():
        return None
    # a Jan-1 instant/end belongs to the fiscal year that just closed
    month_day = end[5:10]
    if month_day == "01-01":
        return str(int(year) - 1)
    return year


def filing_lei(filing: dict) -> str | None:
    """The filer's LEI — the first path segment of json_url (stable filings
    repository convention: /<LEI>/<period_end>/…)."""
    url = str(filing.get("attributes", {}).get("json_url") or "")
    segment = url.lstrip("/").split("/", 1)[0]
    return segment if len(segment) == 20 and segment.isalnum() else None


def _filing_period_end(filing: dict) -> str:
    """Reporting period of a filing — the period_end attribute, falling back
    to the second json_url path segment (/<LEI>/<period_end>/…)."""
    attributes = filing.get("attributes", {})
    period = str(attributes.get("period_end") or "")
    if period:
        return period
    parts = str(attributes.get("json_url") or "").lstrip("/").split("/")
    return parts[1] if len(parts) > 1 else ""


def select_history_filings(filings: list[dict], history: int) -> list[dict]:
    """The filer's N most recent reporting periods, one filing each.

    Amendments and multi-language duplicates share a period_end — the newest
    date_added wins within each group; groups order newest period first."""
    by_period: dict[str, dict] = {}
    for filing in filings:
        period = _filing_period_end(filing)
        if not period:
            continue
        current = by_period.get(period)
        added = str(filing.get("attributes", {}).get("date_added") or "")
        current_added = str(current.get("attributes", {}).get("date_added") or "") if current else ""
        if current is None or added > current_added:
            by_period[period] = filing
    return [by_period[p] for p in sorted(by_period, reverse=True)[:history]]


def fetch_history_frames(
    client: "EsefClient", filings: list[dict], history: int
) -> dict[tuple[str, str], pd.DataFrame]:
    """Fetch + parse the filer's N most recent filings and merge their annual
    frames: each older filing backfills ~1 audited year (its comparatives),
    the newest filing wins every overlap. ``history <= 1`` keeps the
    pre-backfill single-filing path (the API's newest-first order), as do
    filings whose metadata yields no reporting period at all."""
    picked = filings[:1] if history <= 1 else (select_history_filings(filings, history) or filings[:1])
    frame_dicts = []
    for filing in picked:
        xbrl = client.fetch_xbrl_json(filing)
        frames = facts_to_frames(xbrl) if xbrl else {}
        if frames:
            frame_dicts.append(frames)
    if not frame_dicts:
        return {}
    return merge_audited(frame_dicts[0], *frame_dicts[1:])


class EsefClient:
    """Thin network client — kept separate so tests inject fixtures.

    ``min_interval`` throttles consecutive requests (filings.xbrl.org
    publishes no hard limit; ~2 req/s is polite) — the history backfill
    multiplies fetches per filer, so politeness lives here, once."""

    def __init__(self, http=None, min_interval: float = 0.5) -> None:
        import httpx

        self._http = http or httpx.Client(timeout=30, follow_redirects=True)
        self._min_interval = min_interval
        self._last_request: float | None = None

    def _get(self, url: str, **kwargs):
        if self._last_request is not None and self._min_interval > 0:
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
        response = self._http.get(url, **kwargs)
        self._last_request = time.monotonic()
        return response

    def filings_index(self, page_size: int = 100, page_number: int = 1) -> tuple[list[dict], int]:
        """One page of the FULL filings index, newest first.

        The whole EU/EEA gisement is enumerable (~25k filings) — walking it
        beats guessing per-LEI: every entry is a real filing."""
        params = {
            "page[size]": page_size,
            "page[number]": page_number,
            "sort": "-date_added",
        }
        response = self._get(FILINGS_API, params=params)
        response.raise_for_status()
        payload = response.json()
        count = int(payload.get("meta", {}).get("count", 0) or 0)
        return payload.get("data", []), count

    def entities_index(
        self, page_size: int = 100, page_number: int = 1
    ) -> tuple[list[tuple[str, str]], int]:
        """One page of the entities index as (LEI, name) pairs.

        Feeds the name→LEI→ISIN backfill (FR-010 reach): every ESEF filer is
        listed here even when FinanceDatabase ships its listing without an
        ISIN. Rows without an identifier are dropped."""
        params = {"page[size]": page_size, "page[number]": page_number}
        response = self._get(ENTITIES_API, params=params)
        response.raise_for_status()
        payload = response.json()
        count = int(payload.get("meta", {}).get("count", 0) or 0)
        pairs = []
        for row in payload.get("data", []):
            attributes = row.get("attributes", {})
            lei, name = attributes.get("identifier"), attributes.get("name")
            # the live index also carries filers keyed by national codes
            # (e.g. 8-digit Ukrainian EDRPOU) — only a real LEI can join GLEIF
            if lei and name and len(lei) == 20 and lei.isalnum():
                pairs.append((lei, name))
        return pairs, count

    def filings_for_lei(self, lei: str) -> list[dict]:
        import json

        params = {
            "filter": json.dumps(
                [{"name": "entity.identifier", "op": "eq", "val": lei}]
            ),
            "sort": "-date_added",
        }
        response = self._get(FILINGS_API, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def fetch_xbrl_json(self, filing: dict) -> dict | None:
        attributes = filing.get("attributes", {})
        json_url = attributes.get("json_url")
        if not json_url:
            return None
        if json_url.startswith("/"):
            json_url = "https://filings.xbrl.org" + json_url
        response = self._get(json_url)
        response.raise_for_status()
        return response.json()

    def filing_page_url(self, filing: dict) -> str | None:
        attributes = filing.get("attributes", {})
        for key in ("viewer_url", "package_url", "json_url"):
            if attributes.get(key):
                url = attributes[key]
                return "https://filings.xbrl.org" + url if url.startswith("/") else url
        return None
