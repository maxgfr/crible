"""Name→LEI→ISIN backfill — FR-010 reach for listings FinanceDatabase ships
without an ISIN (13,556 of 31,196 European rows, counted 2026-07-16).

The GLEIF join keys on ISIN, so those rows can never resolve to an LEI and
the ESEF sweep skips their audited filings even when they sit on
filings.xbrl.org (e.g. OVH GROUPE, LEI 9695001J8OSOVX4TP939). This module
bridges the gap by NAME, conservatively:

- both sides are normalized (case, accents, punctuation, ONE trailing legal
  form such as SA/SE/PLC/AG) — nothing fuzzier than exact-after-normalizing;
- a normalized entity name shared by several DISTINCT LEIs is ambiguous and
  skipped — a wrong ISIN silently corrupts the audited layer, a missing one
  only keeps the status quo;
- several universe rows matching one entity is fine — dual listings share
  the LEI, exactly how the sweep already enriches them;
- the recovered ISIN comes from the reverse GLEIF mapping (LEI→ISINs,
  deterministic smallest), so the existing ISIN→LEI join resolves it right
  back — the sweep itself needs no change.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Iterable

import duckdb

log = logging.getLogger("crible.ingest.enrich.backfill")

# trailing legal forms stripped ONCE from the normalized name — conservative
# on purpose: only unambiguous company-form tokens, never real words
LEGAL_FORMS = {
    "SA", "SE", "SAS", "SCA", "PLC", "NV", "BV", "AG", "KGAA", "SPA", "SRL",
    "AB", "ASA", "OYJ", "OY", "GMBH", "AS", "SAB",
}


def normalize_company_name(name: str) -> str:
    """Uppercase, accent-fold, drop punctuation, strip ONE trailing legal form."""
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    tokens = re.sub(r"[^A-Z0-9 ]+", " ", folded.upper()).split()
    if len(tokens) > 1 and tokens[-1] in LEGAL_FORMS:
        tokens = tokens[:-1]
    return " ".join(tokens)


def backfill_missing_isins(
    con: duckdb.DuckDBPyConnection,
    entities: Iterable[tuple[str, str]],
    mapping: dict[str, str],
) -> dict:
    """Match ISIN-less European universe rows against ``entities`` (LEI, name)
    pairs by normalized name and write the recovered ISIN into ``companies``.

    Returns counts: backfilled / ambiguous / no_isin_for_lei / unmatched.
    """
    report = {"backfilled": 0, "ambiguous": 0, "no_isin_for_lei": 0, "unmatched": 0}

    nameless = con.execute(
        "SELECT symbol, name FROM companies"
        " WHERE region = 'europe' AND NOT delisted AND isin IS NULL"
    ).fetchall()
    if not nameless:
        return report

    # entity index: normalized name → LEI; same name on distinct LEIs = ambiguous
    by_name: dict[str, str] = {}
    ambiguous: set[str] = set()
    for lei, entity_name in entities:
        key = normalize_company_name(entity_name)
        if not key:
            continue
        if key in by_name and by_name[key] != lei:
            ambiguous.add(key)
            continue
        by_name[key] = lei

    # reverse GLEIF map: LEI → deterministic ISIN (smallest of its listings —
    # any of them resolves back to the same LEI in the forward join)
    isin_for_lei: dict[str, str] = {}
    for isin, lei in mapping.items():
        best = isin_for_lei.get(lei)
        if best is None or isin < best:
            isin_for_lei[lei] = isin

    for symbol, universe_name in nameless:
        key = normalize_company_name(universe_name or "")
        if key in ambiguous:
            report["ambiguous"] += 1
            continue
        lei = by_name.get(key)
        if lei is None:
            report["unmatched"] += 1
            continue
        isin = isin_for_lei.get(lei)
        if isin is None:
            report["no_isin_for_lei"] += 1
            continue
        con.execute(
            "UPDATE companies SET isin = ? WHERE symbol = ? AND isin IS NULL",
            [isin, symbol],
        )
        report["backfilled"] += 1
        log.info("backfill: %s '%s' → LEI %s → ISIN %s", symbol, universe_name, lei, isin)

    return report
