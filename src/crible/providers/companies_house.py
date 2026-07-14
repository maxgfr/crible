"""Companies House UK — audited accounts from the free Accounts Data Product.

The product is a daily/monthly ZIP of iXBRL (inline-XBRL / XHTML) accounts named
by company number. crible extracts the FRC-taxonomy concepts it maps to its
canonical vocabulary with a dependency-free stdlib parser (html.parser — no lxml),
keeps only full-year figures (interims never become annual, the F9 guard), and
writes provider='companies-house' raw. This is the audited UK layer ESEF does
not cover (EU/EEA only, post-Brexit). Redistribution is an assumed risk — the
product pages state no explicit reuse licence — so it lives in the documented
assumed-risk dataset tier alongside the price dumps.
"""

from __future__ import annotations

import logging
import re
import zipfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterator

import pandas as pd

log = logging.getLogger("crible.providers.companies_house")

FULL_YEAR_DAYS = (320, 400)

# FRC / UK-GAAP concept local-name (lowercased) → (canonical column, statement).
# Matched by local part so it survives taxonomy-namespace churn.
CONCEPT_MAP: dict[str, tuple[str, str]] = {
    "turnoverrevenue": ("TotalRevenue", "income"),
    "turnover": ("TotalRevenue", "income"),
    "revenuefromcontractswithcustomers": ("TotalRevenue", "income"),
    "grossprofitloss": ("GrossProfit", "income"),
    "operatingprofitloss": ("OperatingIncome", "income"),
    "profitloss": ("NetIncome", "income"),
    "profitlossforperiod": ("NetIncome", "income"),
    "totalassets": ("TotalAssets", "balance"),
    "assets": ("TotalAssets", "balance"),
    "currentassets": ("CurrentAssets", "balance"),
    "netassetsliabilities": ("StockholdersEquity", "balance"),
    "equity": ("StockholdersEquity", "balance"),
    "shareholderfunds": ("StockholdersEquity", "balance"),
    "cashbankonhand": ("CashAndCashEquivalents", "balance"),
    "cashcashequivalents": ("CashAndCashEquivalents", "balance"),
}
STATEMENT_OF = {column: stmt for column, stmt in CONCEPT_MAP.values()}
CONCEPT_RANK = {local: rank for rank, local in enumerate(CONCEPT_MAP)}


def _full_year(start: str, end: str) -> bool:
    try:
        return FULL_YEAR_DAYS[0] <= (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days <= FULL_YEAR_DAYS[1]
    except ValueError:
        return False


class _IxbrlParser(HTMLParser):
    """Collect xbrli:context periods and ix:nonFraction facts. html.parser
    lowercases tag and attribute names, so everything is matched lowercased."""

    _DATE_TAGS = {"xbrli:startdate": "start", "startdate": "start",
                  "xbrli:enddate": "end", "enddate": "end",
                  "xbrli:instant": "instant", "instant": "instant"}
    _CTX_TAGS = {"xbrli:context", "context"}
    _FACT_TAGS = {"ix:nonfraction", "nonfraction"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.contexts: dict[str, dict[str, str]] = {}
        self.facts: list[dict] = []
        self._ctx_id: str | None = None
        self._field: str | None = None
        self._fact: dict | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self._CTX_TAGS:
            self._ctx_id = a.get("id")
            if self._ctx_id is not None:
                self.contexts.setdefault(self._ctx_id, {})
        elif tag in self._DATE_TAGS:
            self._field = self._DATE_TAGS[tag]
            self._buf = []
        elif tag in self._FACT_TAGS:
            self._fact = {
                "name": a.get("name"), "context": a.get("contextref"),
                "sign": a.get("sign"), "scale": a.get("scale"),
            }
            self._buf = []

    def handle_data(self, data):
        if self._field is not None or self._fact is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag in self._DATE_TAGS and self._field is not None:
            if self._ctx_id is not None:
                self.contexts[self._ctx_id][self._field] = "".join(self._buf).strip()
            self._field = None
            self._buf = []
        elif tag in self._CTX_TAGS:
            self._ctx_id = None
        elif tag in self._FACT_TAGS and self._fact is not None:
            self._fact["text"] = "".join(self._buf).strip()
            self.facts.append(self._fact)
            self._fact = None
            self._buf = []


def _value(fact: dict) -> float | None:
    text = fact.get("text", "").replace(",", "").replace("\xa0", "").strip()
    try:
        value = float(text)
    except ValueError:
        return None
    scale = fact.get("scale")
    if scale:
        try:
            value *= 10 ** int(scale)
        except ValueError:
            pass
    if fact.get("sign") == "-":
        value = -value
    return value


def _period(ctx: dict | None, statement: str) -> str | None:
    """Context → fiscal year, enforcing statement/period-kind consistency and
    the full-year guard for durations."""
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


def parse_ixbrl(html) -> dict[tuple[str, str], pd.DataFrame]:
    """Inline-XBRL accounts → canonical frames keyed by (statement, 'annual')."""
    parser = _IxbrlParser()
    parser.feed(html if isinstance(html, str) else html.decode("utf-8", errors="replace"))

    values: dict[str, dict[str, float]] = {}
    claimed: dict[tuple[str, str], int] = {}
    for fact in parser.facts:
        name = fact.get("name")
        if not name:
            continue
        local = name.split(":")[-1].lower()
        mapped = CONCEPT_MAP.get(local)
        if mapped is None:
            continue
        column, statement = mapped
        period = _period(parser.contexts.get(fact.get("context")), statement)
        if period is None:
            continue
        value = _value(fact)
        if value is None:
            continue
        rank = CONCEPT_RANK[local]
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


def _company_number(filename: str) -> str | None:
    """The 8-char company number embedded in an accounts filename, or None.

    Real Accounts Data Product names look like
    ``Prod<batch>_<seq>_<companynumber>_<YYYYMMDD>.html`` — the trailing YYYYMMDD
    is the FILING DATE, not the number (F7). Company numbers are 8 chars: 8
    digits, or a 2-letter jurisdiction prefix (SC/NI/OC/GB/GE/FC…) + 6 digits."""
    stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    tokens = stem.split("_")
    if tokens and re.fullmatch(r"(19|20)\d{6}", tokens[-1]):
        tokens = tokens[:-1]  # drop the trailing filing-date token
    for token in reversed(tokens):
        match = re.search(r"([A-Z]{2}\d{6}|\d{6,8})", token)
        if match:
            number = match.group(1)
            return number.zfill(8) if number.isdigit() else number
    return None


def iter_accounts(
    zip_path: Path | str, company_numbers: set[str]
) -> Iterator[tuple[str, dict[tuple[str, str], pd.DataFrame]]]:
    """Yield (company_number, frames) for wanted companies in an Accounts Data
    Product ZIP. A broken file is skipped, never fatal."""
    wanted = {n.zfill(8) for n in company_numbers}
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith((".html", ".xhtml", ".htm")):
                continue
            number = _company_number(name)
            if number is None or number not in wanted:
                continue
            try:
                frames = parse_ixbrl(archive.read(name))
            except Exception as exc:  # noqa: BLE001 — one bad filing never sinks the sweep
                log.warning("companies-house: skipping %s: %s", name, exc)
                continue
            if frames:
                yield number, frames
