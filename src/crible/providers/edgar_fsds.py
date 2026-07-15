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


def _wanted_adsh(sub_reader, ciks: set[int]) -> dict[str, int]:
    """{adsh: cik} for annual (10-K/20-F/40-F, fp=FY) submissions of wanted CIKs."""
    wanted: dict[str, int] = {}
    for row in sub_reader:
        cik = _int(row.get("cik"))
        if cik in ciks and row.get("form") in ANNUAL_FORMS and row.get("fp") == "FY":
            wanted[row.get("adsh")] = cik
    return wanted


def _accumulate(wanted: dict[str, int], num_reader) -> dict[int, dict[tuple[str, str], tuple[float, int]]]:
    """Stream num rows → cik → (period, column) → (value, winning-concept rank).
    Only full-year durations (qtrs=4) / instants (qtrs=0), USD/shares, WHOLE
    entity (coreg empty — a co-registrant value must never be booked as the
    consolidated figure, F10)."""
    acc: dict[int, dict[tuple[str, str], tuple[float, int]]] = defaultdict(dict)
    for row in num_reader:
        cik = wanted.get(row.get("adsh"))
        if cik is None:
            continue
        if row.get("segments"):
            continue  # a disaggregated (by segment/geography) value, NOT the
            # consolidated total — only whole-entity facts (segments empty) are
            # the reported figure (real-data: GOOGL revenue $56.8B AsiaPacific
            # vs $350B consolidated). Mirrors ESEF's dimensional-fact skip.
        if row.get("coreg"):
            continue  # co-registrant, not the consolidated entity (F10)
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
    return acc


def _build_frames(acc) -> dict[int, dict[tuple[str, str], pd.DataFrame]]:
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


def frames_from_fsds(
    sub_text: str, num_text: str, ciks: set[int]
) -> dict[int, dict[tuple[str, str], pd.DataFrame]]:
    """Parse one FSDS quarter (sub.txt + num.txt as text) into canonical frames
    per wanted CIK — the in-memory API (tests). ``iter_fsds`` streams instead."""
    wanted = _wanted_adsh(csv.DictReader(io.StringIO(sub_text), delimiter="\t"), ciks)
    acc = _accumulate(wanted, csv.DictReader(io.StringIO(num_text), delimiter="\t"))
    return _build_frames(acc)


def iter_fsds(
    zip_path: Path | str, ciks: set[int]
) -> Iterator[tuple[int, dict[tuple[str, str], pd.DataFrame]]]:
    """Yield (cik, frames) for the wanted CIKs from a quarterly FSDS ZIP.

    num.txt (100s of MB) is streamed row by row, never read whole into memory
    (F11) — sub.txt is small and read first to learn the wanted submissions."""
    with zipfile.ZipFile(zip_path) as archive:
        names = {n.rsplit("/", 1)[-1]: n for n in archive.namelist()}
        if "sub.txt" not in names or "num.txt" not in names:
            log.warning("fsds: %s missing sub.txt/num.txt — skipped", zip_path)
            return
        with archive.open(names["sub.txt"]) as sub_raw:
            wanted = _wanted_adsh(
                csv.DictReader(io.TextIOWrapper(sub_raw, encoding="utf-8", errors="replace"), delimiter="\t"),
                ciks,
            )
        with archive.open(names["num.txt"]) as num_raw:
            acc = _accumulate(
                wanted,
                csv.DictReader(io.TextIOWrapper(num_raw, encoding="utf-8", errors="replace"), delimiter="\t"),
            )
    for cik, frames in _build_frames(acc).items():
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
