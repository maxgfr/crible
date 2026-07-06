"""FR-010 — reconciliation: audited ESEF values outrank scraped Yahoo values.

Where both exist for the same field and period and differ by more than 5%
(relative to the audited value), the audited value wins and the discrepancy is
logged with both values, the field and the period. The snapshot records which
fields are audited per period (provenance)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

log = logging.getLogger("crible.compute.reconcile")

DISCREPANCY_THRESHOLD = 0.05


@dataclass
class Reconciliation:
    merged: pd.DataFrame
    audited_fields: dict[str, list[str]] = field(default_factory=dict)  # period → fields
    discrepancies: list[dict] = field(default_factory=list)


def reconcile(scraped: pd.DataFrame, audited: pd.DataFrame, symbol: str = "?") -> Reconciliation:
    merged = scraped.copy()
    audited_fields: dict[str, list[str]] = {}
    discrepancies: list[dict] = []

    for period in audited.index:
        for column in audited.columns:
            audited_value = audited.loc[period, column]
            if pd.isna(audited_value):
                continue
            if period not in merged.index:
                continue
            scraped_value = merged.loc[period, column] if column in merged.columns else float("nan")
            if pd.notna(scraped_value) and audited_value != 0:
                relative = abs(scraped_value - audited_value) / abs(audited_value)
                if relative > DISCREPANCY_THRESHOLD:
                    entry = {
                        "symbol": symbol,
                        "field": column,
                        "period": str(period),
                        "scraped": float(scraped_value),
                        "audited": float(audited_value),
                        "relative": round(relative, 4),
                    }
                    discrepancies.append(entry)
                    log.warning(
                        "reconcile %s %s@%s: scraped %.4g vs audited %.4g (%.1f%%) — audited wins",
                        symbol, column, period, scraped_value, audited_value, relative * 100,
                    )
            merged.loc[period, column] = audited_value
            audited_fields.setdefault(str(period), []).append(column)

    return Reconciliation(merged=merged, audited_fields=audited_fields, discrepancies=discrepancies)
