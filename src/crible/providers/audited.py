"""The shared audited-layer helpers.

crible's audited layer (figures from official filings that outrank scraped
Yahoo values at reconciliation) is US EDGAR + FSDS, EU ESEF, UK Companies
House, BR CVM and TW TWSE. They differ only in HOW they resolve a listing to a
source id (CIK, LEI, company number…) and fetch its facts; merging per-source
frames and writing provider-tagged raw is identical, and lives here (F4).
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from crible.ingest.raw import write_raw_statement


def merge_audited(
    primary: dict[tuple[str, str], pd.DataFrame],
    *fallbacks: dict[tuple[str, str], pd.DataFrame],
) -> dict[tuple[str, str], pd.DataFrame]:
    """Merge several audited frame-dicts for one listing, per statement/freq.

    The primary source wins on every period it reports; each fallback only
    backfills periods the merge does not yet have (e.g. SEC FSDS adding
    pre-8-year history under companyfacts). Frames are keyed by
    (statement_type, freq) with a ``period`` column.

    Annual periods dedupe by YEAR, not exact label: FSDS stamps 52/53-week
    fiscal years -12-31 while companyfacts keeps the true end date
    (2024-12-28), and the exact-label dedupe let the relabeled twin through
    as a phantom extra year with identical values — Beneish ratios collapsed
    to exactly 1.0 (observed live on HSIC, 2026-07-17). Quarterly frames
    keep the exact-label dedupe (several quarters share a year). Residual:
    a fiscal year ending in early January still labels across the year
    boundary — the same known limitation align_periods carries."""
    out: dict[tuple[str, str], pd.DataFrame] = {k: v.copy() for k, v in primary.items()}
    for fallback in fallbacks:
        for key, frame in fallback.items():
            if key not in out:
                out[key] = frame.copy()
                continue
            have = set(out[key]["period"].astype(str))
            periods = frame["period"].astype(str)
            mask = ~periods.isin(have)
            if key[1] == "annual":
                have_years = {p[:4] for p in have}
                mask &= ~periods.str[:4].isin(have_years)
            extra = frame[mask]
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
    frames actually WRITTEN — an identical frame ``skip_identical`` left in
    place does not count — the one place every audited cycle funnels its
    writes through. ``skip_identical`` passes through to the raw layer
    (re-fetch-everything providers must not re-stamp unchanged data)."""
    stamp = f"{int(fetched_at * 1000):015d}"
    written = 0
    for (statement_type, freq), frame in frames.items():
        path = write_raw_statement(
            data_dir,
            symbol=symbol,
            provider=provider_id,
            statement_type=statement_type,
            freq=freq,
            frame=frame,
            fetched_at=fetched_at,
            skip_identical=skip_identical,
        )
        written += path.stem.endswith(stamp)
    return written
