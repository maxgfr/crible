"""SEC Financial Statement Data Sets — deep 'as-filed' US history (public domain).

companyfacts (provider='edgar') gives the latest restated US figures but crible
caps it at 8 fiscal years; the quarterly FSDS ZIPs carry the flat 'as filed'
numbers back to 2009. This provider parses one quarterly ZIP's sub.txt + num.txt
into crible's canonical frames under provider='edgar-fsds', reusing EDGAR's
us-gaap CONCEPT_MAP, and reconcile merges it *under* companyfacts (merge_audited:
companyfacts wins recent periods, FSDS backfills the deep history). Fully
redistributable — US-government work.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from crible.providers.edgar import (
    ANNUAL_FORMS,
    CONCEPT_MAP,
    NEGATED_CONCEPTS,
    SHARE_COLUMNS,
    STATEMENT_OF,
)

log = logging.getLogger("crible.providers.edgar_fsds")

# declared precedence for column collisions — the concept listed first in
# EDGAR's CONCEPT_MAP wins (same rule as companyfacts)
CONCEPT_RANK = {concept: rank for rank, concept in enumerate(CONCEPT_MAP)}


def _int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def frames_from_fsds(
    sub_text: str, num_text: str, ciks: set[int]
) -> dict[int, dict[tuple[str, str], pd.DataFrame]]:
    """Parse one FSDS quarter (sub.txt + num.txt as text) into canonical frames
    per wanted CIK. Only annual (form 10-K/20-F/40-F, fp=FY) submissions, only
    full-year durations (qtrs=4) and instants (qtrs=0), USD/shares units."""
    wanted: dict[str, int] = {}  # adsh -> cik
    for row in csv.DictReader(io.StringIO(sub_text), delimiter="\t"):
        cik = _int(row.get("cik"))
        if cik in ciks and row.get("form") in ANNUAL_FORMS and row.get("fp") == "FY":
            wanted[row.get("adsh")] = cik

    # cik -> (period, column) -> (value, winning-concept rank)
    acc: dict[int, dict[tuple[str, str], tuple[float, int]]] = defaultdict(dict)
    for row in csv.DictReader(io.StringIO(num_text), delimiter="\t"):
        cik = wanted.get(row.get("adsh"))
        if cik is None:
            continue
        tag = row.get("tag")
        mapped = CONCEPT_MAP.get(tag)
        if mapped is None:
            continue
        column, statement = mapped
        want_uom = "shares" if column in SHARE_COLUMNS else "USD"
        if row.get("uom") != want_uom:
            continue
        qtrs = str(row.get("qtrs"))
        if statement == "balance":
            if qtrs != "0":
                continue  # a balance-sheet fact is an instant
        elif qtrs != "4":
            continue  # income/cashflow: full-year duration only (drops interims)
        value = _float(row.get("value"))
        if value is None:
            continue
        if tag in NEGATED_CONCEPTS:
            value = -value
        ddate = str(row.get("ddate") or "")
        if len(ddate) != 8 or not ddate.isdigit():
            continue
        period = f"{ddate[:4]}-{ddate[4:6]}-{ddate[6:8]}"
        rank = CONCEPT_RANK[tag]
        key = (period, column)
        prev = acc[cik].get(key)
        if prev is not None and prev[1] <= rank:
            continue  # an equal-or-earlier-precedence concept already set this cell
        acc[cik][key] = (value, rank)

    result: dict[int, dict[tuple[str, str], pd.DataFrame]] = {}
    for cik, cells in acc.items():
        by_period: dict[str, dict[str, float]] = defaultdict(dict)
        for (period, column), (value, _) in cells.items():
            by_period[period][column] = value
        frames: dict[tuple[str, str], pd.DataFrame] = {}
        for statement in ("income", "balance", "cashflow"):
            columns = [c for c, s in STATEMENT_OF.items() if s == statement]
            rows = []
            for period in sorted(by_period):
                row = {"period": period}
                row.update({c: by_period[period][c] for c in columns if c in by_period[period]})
                if len(row) > 1:
                    rows.append(row)
            if rows:
                frames[(statement, "annual")] = pd.DataFrame(rows)
        if frames:
            result[cik] = frames
    return result


def iter_fsds(
    zip_path: Path | str, ciks: set[int]
) -> Iterator[tuple[int, dict[tuple[str, str], pd.DataFrame]]]:
    """Yield (cik, frames) for the wanted CIKs from a quarterly FSDS ZIP."""
    with zipfile.ZipFile(zip_path) as archive:
        names = {n.rsplit("/", 1)[-1]: n for n in archive.namelist()}
        if "sub.txt" not in names or "num.txt" not in names:
            log.warning("fsds: %s missing sub.txt/num.txt — skipped", zip_path)
            return
        sub_text = archive.read(names["sub.txt"]).decode("utf-8", errors="replace")
        num_text = archive.read(names["num.txt"]).decode("utf-8", errors="replace")
    for cik, frames in frames_from_fsds(sub_text, num_text, ciks).items():
        yield cik, frames


FSDS_INDEX = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"


def quarter_url(year: int, quarter: int) -> str:
    """The public download URL for one quarterly FSDS archive."""
    return f"{FSDS_INDEX}/{year}q{quarter}.zip"


def resolve_quarters(quarters: Iterable[tuple[int, int]]) -> list[str]:
    return [quarter_url(y, q) for y, q in quarters]


def recent_quarters(n: int, today=None) -> list[tuple[int, int]]:
    """The ``n`` most recently COMPLETED calendar quarters, newest first — the
    FSDS archive for the current quarter is not published until it closes."""
    from datetime import date

    today = today or date.today()
    year, quarter = today.year, (today.month - 1) // 3 + 1
    out: list[tuple[int, int]] = []
    for _ in range(max(n, 0)):
        quarter -= 1
        if quarter == 0:
            quarter, year = 4, year - 1
        out.append((year, quarter))
    return out
