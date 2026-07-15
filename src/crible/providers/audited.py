"""The AuditedBulkProvider seam — the contract every audited source implements.

crible's audited layer (figures from official filings that outrank scraped
Yahoo values at reconciliation) is US EDGAR + EU ESEF today, and grows to SEC
FSDS, UK Companies House and JP EDINET. They differ only in HOW they resolve a
listing to a source id (CIK, LEI, company number…) and fetch its facts; the
rest — writing provider-tagged raw, freshness bookkeeping, reconciliation — is
identical. This module names that shared contract so each new source plugs in
beside the others instead of growing one file (F4), and reads from the local
mirror (``ingest.mirror``) so the audited layer is self-hosted at the call level.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import pandas as pd

from crible.ingest.raw import write_raw_statement


@runtime_checkable
class AuditedBulkProvider(Protocol):
    id: str  # the raw provider tag, e.g. "edgar", "esef", "edgar-fsds"

    def resolve(self, companies: list[dict]) -> tuple[dict[str, object], list[str]]:
        """universe rows → ({symbol: source_id}, unmatched_symbols). Unmatched
        listings are counted, never errored (the ESEF/EDGAR AC-4 pattern)."""
        ...

    def fetch(self, source_id: object) -> dict[tuple[str, str], pd.DataFrame]:
        """source_id → canonical raw frames keyed by (statement_type, freq),
        in crible's yfinance-vocabulary — the same shape reconcile consumes."""
        ...


def merge_audited(
    primary: dict[tuple[str, str], pd.DataFrame],
    *fallbacks: dict[tuple[str, str], pd.DataFrame],
) -> dict[tuple[str, str], pd.DataFrame]:
    """Merge several audited frame-dicts for one listing, per statement/freq.

    The primary source wins on every period it reports; each fallback only
    backfills periods the merge does not yet have (e.g. SEC FSDS adding
    pre-8-year history under companyfacts). Frames are keyed by
    (statement_type, freq) with a ``period`` column."""
    out: dict[tuple[str, str], pd.DataFrame] = {k: v.copy() for k, v in primary.items()}
    for fallback in fallbacks:
        for key, frame in fallback.items():
            if key not in out:
                out[key] = frame.copy()
                continue
            have = set(out[key]["period"].astype(str))
            extra = frame[~frame["period"].astype(str).isin(have)]
            if len(extra):
                out[key] = pd.concat([out[key], extra], ignore_index=True)
    return out


def write_audited_frames(
    data_dir: Path | str,
    *,
    symbol: str,
    provider_id: str,
    frames: dict[tuple[str, str], pd.DataFrame],
    fetched_at: float,
    skip_identical: bool = False,
) -> int:
    """Persist an audited provider's canonical frames as provider-tagged raw
    (the audited layer reconcile prefers over scraped). Returns the count of
    frames processed — the one place every audited cycle funnels its writes
    through. ``skip_identical`` passes through to the raw layer (re-fetch-
    everything providers must not re-stamp unchanged data)."""
    written = 0
    for (statement_type, freq), frame in frames.items():
        write_raw_statement(
            data_dir,
            symbol=symbol,
            provider=provider_id,
            statement_type=statement_type,
            freq=freq,
            frame=frame,
            fetched_at=fetched_at,
            skip_identical=skip_identical,
        )
        written += 1
    return written
