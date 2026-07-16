"""Audited Brazil — CVM open-data DFP bulk (fully-free, ODbL).

dados.cvm.gov.br publishes every listed company's annual statements (DFP,
2010→) as keyless yearly ZIPs of semicolon CSVs, ISO-8859-1, BRL. The chart
of accounts is FIXED (`CD_CONTA`), so mapping to crible's yfinance-vocabulary
raw is a code table, not a heuristic. Rules, each pinned by a test:

- ``ORDEM_EXERC == 'ÚLTIMO'`` only (drops the restated prior-year duplicate);
- ``ESCALA_MOEDA == 'MIL'`` → ×1000 (values ship in BRL thousands);
- consolidated (``_con``) members win; individual (``_ind``) only fills
  companies absent from consolidated (consolidated-first, like every audited source);
- costs stored negative are NEGATED into crible's positive-cost convention
  (the EDGAR NEGATED_CONCEPTS precedent);
- v1 is annual-only: the ITR quarterlies are cumulative windows (a later,
  separate effort — same care as the TWSE YTD income statements).

Licence: ODbL (attribution + share-alike for the database). Attribution:
*Contém dados públicos da CVM — Comissão de Valores Mobiliários.*
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pandas as pd

DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"
FCA_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{year}.zip"
FIRST_DFP_YEAR = 2010

# statement member label → crible statement type
_MEMBER_STATEMENTS = {"BPA": "balance", "BPP": "balance", "DRE": "income",
                      "DFC_MD": "cashflow", "DFC_MI": "cashflow"}

# CD_CONTA → (yfinance column, rank, negate). Lower rank wins when several
# codes feed one column (3.11.01 'attributable to parent' over 3.11). Costs
# and taxes ship negative in the DRE → negate into the positive convention.
CODE_MAP: dict[str, tuple[str, int, bool]] = {
    # BPA — assets
    "1": ("TotalAssets", 0, False),
    "1.01": ("CurrentAssets", 0, False),
    "1.01.01": ("CashAndCashEquivalents", 0, False),
    "1.01.03": ("AccountsReceivable", 0, False),
    "1.01.04": ("Inventory", 0, False),
    # BPP — liabilities & equity
    "2.01": ("CurrentLiabilities", 0, False),
    "2.02.01": ("LongTermDebt", 0, False),
    "2.03": ("StockholdersEquity", 0, False),
    # DRE — income statement
    "3.01": ("TotalRevenue", 0, False),
    "3.02": ("CostOfRevenue", 0, True),
    "3.03": ("GrossProfit", 0, False),
    "3.05": ("OperatingIncome", 0, False),
    "3.07": ("PretaxIncome", 0, False),
    "3.08": ("TaxProvision", 0, True),
    "3.11.01": ("NetIncome", 0, False),
    "3.11": ("NetIncome", 1, False),
    # DFC — cash flow (direct and indirect methods share the top code)
    "6.01": ("OperatingCashFlow", 0, False),
}


def _member_kind(name: str) -> tuple[str, str] | None:
    """'dfp_cia_aberta_DRE_con_2024.csv' → ('DRE', 'con'); None otherwise."""
    stem = name.rsplit("/", 1)[-1]
    if not stem.startswith("dfp_cia_aberta_") or not stem.endswith(".csv"):
        return None
    parts = stem[len("dfp_cia_aberta_"):-len(".csv")].rsplit("_", 2)
    if len(parts) != 3 or parts[1] not in ("con", "ind"):
        return None
    return (parts[0], parts[1]) if parts[0] in _MEMBER_STATEMENTS else None


def _rows(bundle: zipfile.ZipFile, member: str):
    with bundle.open(member) as handle:
        yield from csv.DictReader(
            io.TextIOWrapper(handle, encoding="latin-1", errors="replace"), delimiter=";"
        )


def parse_dfp(
    zip_path: Path | str, wanted: set[str]
) -> dict[str, dict[tuple[str, str], pd.DataFrame]]:
    """One DFP yearly ZIP → {CNPJ: frames} for the wanted companies.

    Consolidated members win whole statements; ``ÚLTIMO`` rows only; MIL
    scaling; ranked code map. Frames carry a ``period`` column (fiscal year
    end date) in crible's yfinance vocabulary.
    """
    # values[cnpj][statement][period][column] = (rank, value)
    values: dict[str, dict[str, dict[str, dict[str, tuple[int, float]]]]] = {}
    consolidated: set[tuple[str, str]] = set()  # (cnpj, statement) served by _con

    def _ingest(member_rows, statement: str, scope: str) -> None:
        for row in member_rows:
            cnpj = row.get("CNPJ_CIA", "")
            if cnpj not in wanted or row.get("ORDEM_EXERC") != "ÚLTIMO":
                continue
            if scope == "ind" and (cnpj, statement) in consolidated:
                continue
            mapped = CODE_MAP.get(row.get("CD_CONTA", ""))
            if mapped is None:
                continue
            column, rank, negate = mapped
            try:
                value = float(row.get("VL_CONTA", ""))
            except (TypeError, ValueError):
                continue
            if row.get("ESCALA_MOEDA") == "MIL":
                value *= 1000.0
            if negate:
                value = -value
            period = row.get("DT_FIM_EXERC", "")
            if not period:
                continue
            if scope == "con":
                consolidated.add((cnpj, statement))
            slot = values.setdefault(cnpj, {}).setdefault(statement, {}).setdefault(period, {})
            current = slot.get(column)
            if current is None or rank < current[0]:
                slot[column] = (rank, value)

    with zipfile.ZipFile(zip_path) as bundle:
        members = [(m, _member_kind(m)) for m in bundle.namelist()]
        # consolidated first — the individual pass sees what they claimed
        for scope in ("con", "ind"):
            for member, kind in members:
                if kind is None or kind[1] != scope:
                    continue
                _ingest(_rows(bundle, member), _MEMBER_STATEMENTS[kind[0]], scope)

    frames: dict[str, dict[tuple[str, str], pd.DataFrame]] = {}
    for cnpj, statements in values.items():
        out: dict[tuple[str, str], pd.DataFrame] = {}
        for statement, periods in statements.items():
            records = [
                {"period": period, **{col: val for col, (_, val) in columns.items()}}
                for period, columns in sorted(periods.items())
            ]
            out[(statement, "annual")] = pd.DataFrame(records)
        frames[cnpj] = out
    return frames


def resolve_cvm(
    symbols: list[str], fca_zip: Path | str
) -> tuple[dict[str, str], list[str]]:
    """Universe ``.SA`` symbols → CNPJ via the FCA trading-code register
    (``Codigo_Negociacao``; one company ⇒ several tickers, all enriched —
    the ESEF dual-listing pattern). Unmatched are counted, never errored."""
    code_to_cnpj: dict[str, str] = {}
    with zipfile.ZipFile(fca_zip) as bundle:
        for member in bundle.namelist():
            if "valor_mobiliario" not in member:
                continue
            for row in _rows(bundle, member):
                code = (row.get("Codigo_Negociacao") or "").strip().upper()
                if not code or (row.get("Data_Fim_Negociacao") or "").strip():
                    continue  # delisted line
                cnpj = row.get("CNPJ_Companhia", "")
                if cnpj:
                    code_to_cnpj[code] = cnpj
    mapping: dict[str, str] = {}
    unmatched: list[str] = []
    for symbol in symbols:
        code = symbol[:-3].upper() if symbol.upper().endswith(".SA") else symbol.upper()
        cnpj = code_to_cnpj.get(code)
        if cnpj:
            mapping[symbol] = cnpj
        else:
            unmatched.append(symbol)
    return mapping, unmatched
