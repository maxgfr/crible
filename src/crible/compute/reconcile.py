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


def align_periods(audited: pd.DataFrame, scraped_index: pd.Index) -> pd.DataFrame:
    """Relabel audited periods onto the scraped label of the same fiscal year.

    Providers label the same fiscal period differently — ESEF by year
    ("2024"), EDGAR and yfinance by end date ("2024-09-28" vs "2024-09-30") —
    and ``reconcile`` skips audited periods absent from the scraped index, so
    without alignment the audited layer never overrides anything. Matching is
    by the 4-digit year prefix; an audited period is left untouched when it
    already matches, when the year is ambiguous (several scraped periods), or
    when the target label is already taken — conservative by design.
    """
    scraped_labels = {str(label) for label in scraped_index}
    by_year: dict[str, list[str]] = {}
    for label in scraped_labels:
        by_year.setdefault(label[:4], []).append(label)
    renames: dict[str, str] = {}
    audited_labels = {str(label) for label in audited.index}
    for label in audited.index:
        text = str(label)
        candidates = by_year.get(text[:4], [])
        if text in scraped_labels or len(candidates) != 1:
            continue
        target = candidates[0]
        if target not in audited_labels:
            renames[label] = target
    return audited.rename(index=renames) if renames else audited


@dataclass
class Reconciliation:
    merged: pd.DataFrame
    audited_fields: dict[str, list[str]] = field(default_factory=dict)  # period → fields
    discrepancies: list[dict] = field(default_factory=list)


def reconcile(scraped: pd.DataFrame, audited: pd.DataFrame, symbol: str = "?") -> Reconciliation:
    merged = scraped.copy()
    # audited history deeper than the scraped window (SEC FSDS / EDGAR backfill)
    # must be ADDED, not dropped — otherwise the flagship deep-history feature is
    # silently inert for every scraped symbol (F6). New periods start all-NaN and
    # take the audited values below.
    extra_periods = [p for p in audited.index if p not in merged.index]
    if extra_periods:
        merged = merged.reindex(list(merged.index) + extra_periods)
    audited_fields: dict[str, list[str]] = {}
    discrepancies: list[dict] = []

    for period in audited.index:
        for column in audited.columns:
            audited_value = audited.loc[period, column]
            if pd.isna(audited_value):
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
