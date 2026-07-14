"""EDINET (Japan) — audited JP filings via the free-key EDINET API.

EDINET is API-only and requires a free Subscription-Key, so it is a *free-key*
provider: OFF by default (crible's core stays keyless and the published dataset
never depends on it), never scraped — the API is mandatory. Its XBRL instances
are parsed for the jppfs concepts crible maps to canonical fields, keeping only
full-year figures. Licensed PDL1.0 → redistributable WITH attribution (recorded
in the Providers view and DATA-SOURCES.md when enabled).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date

import pandas as pd

log = logging.getLogger("crible.providers.edinet")

API_BASE = "https://api.edinet-fsa.go.jp/api/v2"
KEY_ENV_VAR = "CRIBLE_EDINET_KEY"
FULL_YEAR_DAYS = (320, 400)

# jppfs concept local-name (lowercased) → (canonical column, statement)
CONCEPT_MAP: dict[str, tuple[str, str]] = {
    "netsales": ("TotalRevenue", "income"),
    "revenue": ("TotalRevenue", "income"),
    "operatingrevenue1": ("TotalRevenue", "income"),
    "netsalesofcompletedconstructioncontracts": ("TotalRevenue", "income"),
    "grossprofit": ("GrossProfit", "income"),
    "operatingincome": ("OperatingIncome", "income"),
    "profitloss": ("NetIncome", "income"),
    "profitlossattributabletoownersofparent": ("NetIncome", "income"),
    "assets": ("TotalAssets", "balance"),
    "currentassets": ("CurrentAssets", "balance"),
    "netassets": ("StockholdersEquity", "balance"),
    "equity": ("StockholdersEquity", "balance"),
    "cashandcashequivalents": ("CashAndCashEquivalents", "balance"),
}
STATEMENT_OF = {column: stmt for column, stmt in CONCEPT_MAP.values()}
CONCEPT_RANK = {local: rank for rank, local in enumerate(CONCEPT_MAP)}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _full_year(start: str, end: str) -> bool:
    try:
        return FULL_YEAR_DAYS[0] <= (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days <= FULL_YEAR_DAYS[1]
    except ValueError:
        return False


def _period(ctx: dict | None, statement: str) -> str | None:
    if not ctx:
        return None
    instant = ctx.get("instant")
    if statement == "balance":
        if not instant:
            return None
        end = instant
    else:
        if instant or not ctx.get("end"):
            return None
        end = ctx["end"]
        if ctx.get("start") and not _full_year(ctx["start"], end):
            return None
    year = end[:4]
    if not year.isdigit():
        return None
    return str(int(year) - 1) if end[5:10] == "01-01" else year


def parse_xbrl_instance(xml) -> dict[tuple[str, str], pd.DataFrame]:
    """EDINET XBRL instance → canonical frames keyed by (statement, 'annual')."""
    root = ET.fromstring(xml if isinstance(xml, bytes) else xml.encode("utf-8"))

    contexts: dict[str, dict[str, str]] = {}
    for ctx in root.iter():
        if _local(ctx.tag) != "context":
            continue
        cid = ctx.get("id")
        if not cid:
            continue
        info: dict[str, str] = {}
        for elem in ctx.iter():
            local = _local(elem.tag)
            field = {"startdate": "start", "enddate": "end", "instant": "instant"}.get(local)
            if field and elem.text:
                info[field] = elem.text.strip()
        contexts[cid] = info

    values: dict[str, dict[str, float]] = {}
    claimed: dict[tuple[str, str], int] = {}
    for elem in root.iter():
        ctxref = elem.get("contextRef")
        if not ctxref:
            continue
        mapped = CONCEPT_MAP.get(_local(elem.tag))
        if mapped is None:
            continue
        if (elem.get("unitRef") or "").upper() not in ("JPY", ""):
            continue  # monetary facts only
        column, statement = mapped
        period = _period(contexts.get(ctxref), statement)
        if period is None:
            continue
        try:
            value = float(elem.text)
        except (TypeError, ValueError):
            continue
        rank = CONCEPT_RANK[_local(elem.tag)]
        key = (period, column)
        if key in claimed and claimed[key] <= rank:
            continue
        values.setdefault(period, {})[column] = value
        claimed[key] = rank

    frames: dict[tuple[str, str], pd.DataFrame] = {}
    for statement in ("income", "balance", "cashflow"):
        columns = [c for c, s in STATEMENT_OF.items() if s == statement]
        rows = []
        for period in sorted(values):
            row = {"period": period}
            row.update({c: values[period][c] for c in columns if c in values[period]})
            if len(row) > 1:
                rows.append(row)
        if rows:
            frames[(statement, "annual")] = pd.DataFrame(rows)
    return frames


def frames_from_document_zip(zip_bytes: bytes) -> dict[tuple[str, str], pd.DataFrame]:
    """Extract the primary XBRL instance from an EDINET submission ZIP and parse
    it. Prefers the PublicDoc instance; the largest .xbrl wins ties."""
    import io
    import zipfile

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        candidates = [n for n in archive.namelist() if n.lower().endswith(".xbrl")]
        if not candidates:
            return {}
        candidates.sort(key=lambda n: ("publicdoc" not in n.lower(), -archive.getinfo(n).file_size))
        return parse_xbrl_instance(archive.read(candidates[0]))


def sec_code(symbol: str) -> str | None:
    """Yahoo JP ticker → 5-char EDINET securities code (7203.T → 72030), or None
    for a non-JP listing. Since 2024 the TSE also issues 4-char ALPHANUMERIC
    codes (130A.T → 130A0), so the base is not required to be all digits (F6)."""
    if not symbol:
        return None
    base, _, suffix = symbol.partition(".")
    if suffix.upper() not in ("T", "JP"):
        return None
    base = base.upper()
    if len(base) == 4 and base.isalnum():
        return f"{base}0"
    if base.isdigit() and 1 <= len(base) <= 5:
        return base.ljust(5, "0")[:5]
    return None


class EdinetProvider:
    """The free-key provider entry (catalog/inventory + activation gate). The
    actual ingestion is the bulk-ish ``run_edinet`` cycle, not a per-symbol
    crawl, so fetch_statements is not the ingestion path."""

    id = "edinet"
    kind = "free-key"
    key_env_var = KEY_ENV_VAR
    requests_per_fetch = 1

    def enabled(self, env: dict[str, str]) -> bool:
        return bool(env.get(self.key_env_var))

    def fetch_statements(self, symbol: str):  # pragma: no cover - not the ingest path
        raise NotImplementedError("EDINET is ingested by run_edinet, not the crawler")


class EdinetClient:
    """Thin API client — kept separate so tests inject fixtures. Requires the
    free Subscription-Key; refuses to run without it."""

    def __init__(self, key: str, http=None) -> None:
        if not key:
            raise ValueError("EDINET requires a free Subscription-Key (CRIBLE_EDINET_KEY)")
        self._key = key
        if http is None:
            import httpx

            http = httpx.Client(timeout=30, follow_redirects=True)
        self._http = http

    def list_documents(self, day: str) -> list[dict]:
        response = self._http.get(
            f"{API_BASE}/documents.json",
            params={"date": day, "type": 2, "Subscription-Key": self._key},
        )
        response.raise_for_status()
        return response.json().get("results", [])

    def fetch_document(self, doc_id: str) -> bytes:
        response = self._http.get(
            f"{API_BASE}/documents/{doc_id}",
            params={"type": 1, "Subscription-Key": self._key},
        )
        response.raise_for_status()
        return response.content
