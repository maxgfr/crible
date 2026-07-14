"""The AuditedBulkProvider seam (F4) — the shared contract every audited source
(EDGAR, ESEF, and the Phase-2 sources FSDS/Companies House/EDINET) implements:
resolve the universe to source ids, fetch canonical frames, write them as
provider-tagged raw that outranks the scraped base at reconciliation.
"""

from __future__ import annotations

import pandas as pd

from crible.providers.audited import AuditedBulkProvider, write_audited_frames


def test_audited_bulk_provider_protocol_is_satisfiable() -> None:
    class Dummy:
        id = "dummy"

        def resolve(self, companies):
            return ({c["symbol"]: c["symbol"] for c in companies}, [])

        def fetch(self, source_id):
            return {}

    assert isinstance(Dummy(), AuditedBulkProvider)


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
