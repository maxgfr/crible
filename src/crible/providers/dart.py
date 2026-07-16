"""Audited South Korea — OpenDART (free-key opt-in, EDINET-style).

The keyless bulk archives exist (opendart.fss.or.kr/disclosureinfo/fnltt/dwld,
FY/HY/TQ/FQ × BS/PL/CF/CE ZIPs, 2015→) but their download endpoint serves an
error page to non-browser clients — probed 2026-07-16. The shipped path is
the free-key OpenDART API (20k req/day): ``corpCode.xml`` maps 6-digit stock
codes to DART corp_codes, ``fnlttSinglAcntAll`` returns every account of the
annual report with its IFRS concept id — the same concept-mapping discipline
as ESEF, with a Korean-label fallback for untagged standard accounts.
Consolidated (CFS) preferred, separate (OFS) only when CFS has no data.
Values are raw KRW. Off without ``CRIBLE_DART_KEY``; the bulk client stays a
dated TODO.
"""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

import pandas as pd

KEY_ENV_VAR = "CRIBLE_DART_KEY"
CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
FNLTT_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
ANNUAL_REPORT = "11011"

_STATEMENTS = {"BS": "balance", "IS": "income", "CF": "cashflow"}

# IFRS concept id → (yfinance column, rank); the ESEF discipline. OpenDART
# tags both ifrs-full_* and legacy ifrs_* — normalize the prefix first.
CONCEPT_MAP = {
    "Revenue": ("TotalRevenue", 0),
    "CostOfSales": ("CostOfRevenue", 0),
    "GrossProfit": ("GrossProfit", 0),
    "ProfitLossFromOperatingActivities": ("OperatingIncome", 0),
    "ProfitLossBeforeTax": ("PretaxIncome", 0),
    "IncomeTaxExpenseContinuingOperations": ("TaxProvision", 0),
    "ProfitLossAttributableToOwnersOfParent": ("NetIncome", 0),
    "ProfitLoss": ("NetIncome", 1),
    "Assets": ("TotalAssets", 0),
    "CurrentAssets": ("CurrentAssets", 0),
    "CurrentLiabilities": ("CurrentLiabilities", 0),
    "Liabilities": ("TotalLiabilitiesNetMinorityInterest", 0),
    "EquityAttributableToOwnersOfParent": ("StockholdersEquity", 0),
    "Equity": ("StockholdersEquity", 1),
    "RetainedEarnings": ("RetainedEarnings", 0),
    "Inventories": ("Inventory", 0),
    "TradeAndOtherCurrentReceivables": ("AccountsReceivable", 0),
    "CashAndCashEquivalents": ("CashAndCashEquivalents", 0),
    "CashFlowsFromUsedInOperatingActivities": ("OperatingCashFlow", 0),
}
# dart_* extension concepts commonly used instead of the ifrs-full ones
CONCEPT_MAP["OperatingIncomeLoss"] = ("OperatingIncome", 1)

# Korean-label fallback for '-표준계정코드 미사용-' (untagged) standard accounts
LABEL_MAP = {
    "매출액": ("TotalRevenue", 2),
    "영업이익": ("OperatingIncome", 2),
    "당기순이익": ("NetIncome", 2),
    "자산총계": ("TotalAssets", 2),
    "부채총계": ("TotalLiabilitiesNetMinorityInterest", 2),
    "자본총계": ("StockholdersEquity", 2),
    "유동자산": ("CurrentAssets", 2),
    "유동부채": ("CurrentLiabilities", 2),
    "영업활동현금흐름": ("OperatingCashFlow", 2),
}


def _concept(account_id: str) -> str | None:
    if not account_id or account_id.startswith("-"):
        return None
    return account_id.split("_", 1)[-1]  # ifrs-full_Revenue / dart_X → tail


def _period_end(row: dict, year: str) -> str:
    """'2024.01.01 ~ 2024.12.31' or '2024.12.31 현재' → '2024-12-31';
    falls back to the business year's calendar end."""
    text = str(row.get("thstrm_dt", "") or "")
    dates = re.findall(r"(\d{4})[./](\d{2})[./](\d{2})", text)
    if dates:
        y, m, d = dates[-1]
        return f"{y}-{m}-{d}"
    return f"{year}-12-31"


def frames_from_accounts(
    rows: list[dict], year: str
) -> dict[tuple[str, str], pd.DataFrame]:
    """One company-year of fnlttSinglAcntAll rows → crible raw frames."""
    values: dict[str, dict[str, dict[str, tuple[int, float]]]] = {}
    for row in rows:
        statement = _STATEMENTS.get(str(row.get("sj_div", "")))
        if statement is None:
            continue
        mapped = None
        concept = _concept(str(row.get("account_id", "")))
        if concept is not None:
            mapped = CONCEPT_MAP.get(concept)
        if mapped is None:
            mapped = LABEL_MAP.get(str(row.get("account_nm", "")).strip())
        if mapped is None:
            continue
        column, rank = mapped
        raw = str(row.get("thstrm_amount", "") or "").replace(",", "").strip()
        try:
            value = float(raw)
        except ValueError:
            continue
        period = _period_end(row, year)
        slot = values.setdefault(statement, {}).setdefault(period, {})
        current = slot.get(column)
        if current is None or rank < current[0]:
            slot[column] = (rank, value)

    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for statement, periods in values.items():
        frames[(statement, "annual")] = pd.DataFrame(
            [
                {"period": period, **{c: v for c, (_, v) in columns.items()}}
                for period, columns in sorted(periods.items())
            ]
        )
    return frames


def parse_corp_codes(zip_bytes: bytes) -> dict[str, str]:
    """corpCode.xml ZIP → {6-digit stock_code: corp_code} (listed only)."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as bundle:
        with bundle.open(bundle.namelist()[0]) as handle:
            tree = ElementTree.parse(handle)
    mapping: dict[str, str] = {}
    for entry in tree.iter("list"):
        stock = (entry.findtext("stock_code") or "").strip()
        corp = (entry.findtext("corp_code") or "").strip()
        if stock and corp:
            mapping[stock.zfill(6)] = corp
    return mapping


class DartProvider:
    """The free-key catalog entry (inventory + activation gate). Ingestion is
    the bulk-ish ``run_dart`` cycle, not a per-symbol crawl."""

    id = "dart"
    kind = "free-key"
    key_env_var = KEY_ENV_VAR
    requests_per_fetch = 1

    def enabled(self, env: dict[str, str]) -> bool:
        return bool(env.get(self.key_env_var))

    def fetch_statements(self, symbol: str):  # pragma: no cover - not the ingest path
        raise NotImplementedError("DART is ingested by run_dart, not the crawler")


class DartApiClient:
    """Thin keyed transport — everything parseable stays in module functions."""

    def __init__(self, key: str, http=None) -> None:
        import httpx

        self.key = key
        self.http = http or httpx.Client(timeout=60)

    def corp_codes(self) -> dict[str, str]:
        response = self.http.get(CORP_CODE_URL, params={"crtfc_key": self.key})
        response.raise_for_status()
        return parse_corp_codes(response.content)

    def fnltt_all(self, corp_code: str, year: str, fs_div: str) -> list[dict]:
        """One company-year of accounts; [] when DART reports no data (013)."""
        response = self.http.get(
            FNLTT_URL,
            params={"crtfc_key": self.key, "corp_code": corp_code, "bsns_year": year,
                    "reprt_code": ANNUAL_REPORT, "fs_div": fs_div},
        )
        response.raise_for_status()
        payload = response.json()
        status = str(payload.get("status", ""))
        if status == "013":  # no data for this year/scope
            return []
        if status != "000":
            raise RuntimeError(f"OpenDART {status}: {payload.get('message', '')}")
        return payload.get("list", [])
