"""The AuditedBulkProvider seam (F4) — the shared contract every audited source
(EDGAR, ESEF, and the later sources FSDS/Companies House/CVM/TWSE) implements:
resolve the universe to source ids, fetch canonical frames, write them as
provider-tagged raw that outranks the scraped base at reconciliation.
"""

from __future__ import annotations

import pandas as pd

from crible.providers.audited import (
    AuditedBulkProvider,
    merge_audited,
    write_audited_frames,
)


def test_audited_bulk_provider_protocol_is_satisfiable() -> None:
    class Dummy:
        id = "dummy"

        def resolve(self, companies):
            return ({c["symbol"]: c["symbol"] for c in companies}, [])

        def fetch(self, source_id):
            return {}

    assert isinstance(Dummy(), AuditedBulkProvider)


def test_merge_audited_prefers_primary_and_backfills_from_fallback() -> None:
    """Two audited sources for the same listing (companyfacts + FSDS): the
    primary wins on overlapping periods, the fallback only backfills periods it
    is missing (deeper history)."""
    primary = {
        ("income", "annual"): pd.DataFrame(
            {"period": ["2024"], "TotalRevenue": [100.0]}
        ),
    }
    fallback = {
        ("income", "annual"): pd.DataFrame(
            {"period": ["2019", "2024"], "TotalRevenue": [40.0, 999.0]}
        ),
    }
    merged = merge_audited(primary, fallback)
    frame = merged[("income", "annual")].set_index("period")
    assert frame.loc["2024", "TotalRevenue"] == 100.0  # primary wins the overlap
    assert frame.loc["2019", "TotalRevenue"] == 40.0   # fallback backfills the gap


def test_merge_audited_keeps_two_fiscal_years_labelled_inside_one_calendar_year() -> None:
    """52/53-week filers (AAP: FY2021 ends 2022-01-01, FY2022 ends 2022-12-31)
    put two REAL fiscal years in one calendar year. The year-prefix dedupe must
    stay a cross-source guard only — applying it inside a frame would delete a
    genuine year, which is why align_periods, not merge_audited, is where the
    duplicate-label collision gets handled."""
    primary = {
        ("income", "annual"): pd.DataFrame(
            {"period": ["2022-01-01", "2022-12-31"], "TotalRevenue": [10998.0, 9148.0]}
        ),
    }
    frame = merge_audited(primary)[("income", "annual")]
    assert list(frame["period"]) == ["2022-01-01", "2022-12-31"]


def test_write_audited_frames_writes_provider_tagged_raw(tmp_path) -> None:
    frames = {
        ("income", "annual"): pd.DataFrame({"period": ["2024"], "TotalRevenue": [100.0]}),
        ("balance", "annual"): pd.DataFrame({"period": ["2024"], "TotalAssets": [500.0]}),
    }
    written = write_audited_frames(
        tmp_path, symbol="AIR.PA", provider_id="edgar-fsds", frames=frames, fetched_at=1000.0
    )
    assert written == 2
    files = list((tmp_path / "raw" / "provider=edgar-fsds" / "symbol=AIR.PA").glob("*.parquet"))
    assert len(files) == 2
