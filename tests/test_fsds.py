"""FR-017 — SEC Financial Statement Data Sets (FSDS) — deep 'as-filed' US history.

The quarterly FSDS ZIPs (sub.txt + num.txt, tab-separated) carry the flat
'as filed' numbers going back to 2009 — the historical depth companyfacts
(capped at 8 fiscal years) lacks. Public domain → fully redistributable. This
provider maps the us-gaap tags with EDGAR's own CONCEPT_MAP and keeps only
full-year durations (qtrs=4) / instants (qtrs=0), the F9 guard.
"""

from __future__ import annotations

import zipfile

from crible.providers.edgar_fsds import frames_from_fsds, iter_fsds


def _tsv(rows: list[list[str]]) -> str:
    return "\n".join("\t".join(r) for r in rows) + "\n"


SUB = _tsv(
    [
        ["adsh", "cik", "name", "form", "period", "fy", "fp"],
        ["0000320193-24-000001", "320193", "APPLE INC", "10-K", "20240930", "2024", "FY"],
        ["0000000000-24-000009", "999999", "OTHER CO", "10-K", "20240930", "2024", "FY"],
    ]
)

NUM = _tsv(
    [
        ["adsh", "tag", "version", "coreg", "ddate", "qtrs", "uom", "value", "footnote"],
        ["0000320193-24-000001", "Revenues", "us-gaap/2024", "", "20240930", "4", "USD", "391035000000", ""],
        ["0000320193-24-000001", "Revenues", "us-gaap/2024", "", "20230930", "4", "USD", "383285000000", ""],
        [
            "0000320193-24-000001",
            "Revenues",
            "us-gaap/2024",
            "",
            "20240630",
            "1",
            "USD",
            "85777000000",
            "",
        ],  # Q3 interim — dropped
        [
            "0000320193-24-000001",
            "NetIncomeLoss",
            "us-gaap/2024",
            "",
            "20240930",
            "4",
            "USD",
            "93736000000",
            "",
        ],
        ["0000320193-24-000001", "Assets", "us-gaap/2024", "", "20240930", "0", "USD", "364980000000", ""],
        [
            "0000320193-24-000001",
            "AssetsCurrent",
            "us-gaap/2024",
            "",
            "20240930",
            "0",
            "USD",
            "152987000000",
            "",
        ],
        ["0000000000-24-000009", "Revenues", "us-gaap/2024", "", "20240930", "4", "USD", "123.0", ""],
    ]
)


def test_frames_from_fsds_maps_full_year_facts_and_drops_interims() -> None:
    frames = frames_from_fsds(SUB, NUM, {320193})
    income = frames[320193][("income", "annual")].set_index("period")
    assert income.loc["2024-09-30", "TotalRevenue"] == 391035000000.0
    assert income.loc["2023-09-30", "TotalRevenue"] == 383285000000.0  # deep history
    assert income.loc["2024-09-30", "NetIncome"] == 93736000000.0
    # the qtrs=1 interim revenue never becomes an annual fact
    assert "2024-06-30" not in income.index
    balance = frames[320193][("balance", "annual")].set_index("period")
    assert balance.loc["2024-09-30", "TotalAssets"] == 364980000000.0
    assert balance.loc["2024-09-30", "CurrentAssets"] == 152987000000.0
    # a CIK outside the wanted set is never emitted
    assert 999999 not in frames


def test_frames_from_fsds_drops_segmented_rows() -> None:
    """Real FSDS num.txt carries a `segments` column; only whole-entity facts
    (segments empty) are the consolidated total. A segmented row (by geography /
    business) must NEVER be booked as the total — caught by real-data validation
    where GOOGL revenue came out $56.8B (AsiaPacific) instead of $350B. The
    segmented row is listed first to defeat first-writer-wins."""
    sub = _tsv(
        [
            ["adsh", "cik", "name", "form", "period", "fy", "fp"],
            ["A1", "1652044", "ALPHABET", "10-K", "20241231", "2024", "FY"],
        ]
    )
    num = _tsv(
        [
            ["adsh", "tag", "version", "ddate", "qtrs", "uom", "segments", "coreg", "value", "footnote"],
            [
                "A1",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "us-gaap/2024",
                "20241231",
                "4",
                "USD",
                "Geographical=AsiaPacific;",
                "",
                "56815000000",
                "",
            ],
            [
                "A1",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "us-gaap/2024",
                "20241231",
                "4",
                "USD",
                "",
                "",
                "350018000000",
                "",
            ],
        ]
    )
    income = frames_from_fsds(sub, num, {1652044})[1652044][("income", "annual")].set_index("period")
    assert income.loc["2024-12-31", "TotalRevenue"] == 350018000000.0  # consolidated, not a segment


def test_frames_from_fsds_drops_co_registrant_rows() -> None:
    """F10 — a co-registrant (coreg non-empty) value must never be booked as the
    consolidated figure; the coreg row is listed first to defeat first-writer-wins."""
    sub = _tsv(
        [
            ["adsh", "cik", "name", "form", "period", "fy", "fp"],
            ["A1", "320193", "APPLE", "10-K", "20240930", "2024", "FY"],
        ]
    )
    num = _tsv(
        [
            ["adsh", "tag", "version", "coreg", "ddate", "qtrs", "uom", "value", "footnote"],
            ["A1", "Revenues", "us-gaap/2024", "SUB", "20240930", "4", "USD", "5000000000", ""],
            ["A1", "Revenues", "us-gaap/2024", "", "20240930", "4", "USD", "391000000000", ""],
        ]
    )
    income = frames_from_fsds(sub, num, {320193})[320193][("income", "annual")].set_index("period")
    assert income.loc["2024-09-30", "TotalRevenue"] == 391000000000.0  # consolidated, not the 5e9 coreg


def test_iter_fsds_reads_the_zip(tmp_path) -> None:
    zip_path = tmp_path / "2024q1.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("sub.txt", SUB)
        archive.writestr("num.txt", NUM)
    got = dict(iter_fsds(zip_path, {320193}))
    assert set(got) == {320193}
    assert ("income", "annual") in got[320193]


def test_recent_quarters_returns_completed_quarters_newest_first() -> None:
    from datetime import date

    from crible.providers.edgar_fsds import recent_quarters

    # mid-Q3 2024 → the last completed quarters are Q2-2024, Q1-2024, Q4-2023
    assert recent_quarters(3, today=date(2024, 8, 15)) == [(2024, 2), (2024, 1), (2023, 4)]


class _ZipResp:
    def __init__(self, body: bytes) -> None:
        self.status_code = 200
        self._body = body
        self.headers = {}

    def raise_for_status(self):
        pass

    def iter_bytes(self, chunk_size: int = 0):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _ZipHttp:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def stream(self, method, url, headers=None):
        return _ZipResp(self.body)


def test_run_fsds_writes_edgar_fsds_raw(tmp_path, monkeypatch) -> None:
    import io

    import duckdb
    import pandas as pd

    from crible.ingest.enrichment import run_fsds
    from crible.universe import bootstrap_universe

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(
        con,
        pd.DataFrame(
            {
                "symbol": ["AAPL"],
                "name": ["Apple"],
                "country": ["United States"],
                "sector": ["Tech"],
                "industry": ["X"],
                "exchange": ["NMS"],
                "currency": ["USD"],
            }
        ),
    )
    con.close()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("sub.txt", SUB)
        archive.writestr("num.txt", NUM)

    outcome = run_fsds([(2024, 1)], ticker_map={"AAPL": 320193}, http=_ZipHttp(buf.getvalue()))

    assert outcome["enriched"] == 1
    assert list(tmp_path.glob("raw/provider=edgar-fsds/symbol=AAPL/*.parquet"))
    # and the mirror kept the archive for offline reuse
    assert (tmp_path / "mirror" / "edgar-fsds" / "2024q1.zip").exists()


def _fsds_zip(fiscal_ends: list[str], cik: str = "1652044", revenue0: float = 100.0) -> bytes:
    import io

    sub = _tsv(
        [
            ["adsh", "cik", "name", "form", "period", "fy", "fp"],
            [
                f"0000000000-{fiscal_ends[0][2:4]}-000001",
                cik,
                "ALPHABET",
                "10-K",
                fiscal_ends[0],
                fiscal_ends[0][:4],
                "FY",
            ],
        ]
    )
    rows = [["adsh", "tag", "version", "coreg", "ddate", "qtrs", "uom", "value", "footnote"]]
    for i, end in enumerate(fiscal_ends):
        rows.append(
            [
                f"0000000000-{fiscal_ends[0][2:4]}-000001",
                "Revenues",
                "us-gaap/2024",
                "",
                end,
                "4",
                "USD",
                str(revenue0 + i),
                "",
            ]
        )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("sub.txt", sub)
        archive.writestr("num.txt", _tsv(rows))
    return buf.getvalue()


class _QuarterHttp:
    """One archive per quarter URL."""

    def __init__(self, bodies: dict[str, bytes]) -> None:
        self.bodies = bodies

    def stream(self, method, url, headers=None):
        name = url.rsplit("/", 1)[-1].removesuffix(".zip").removesuffix("_notes")
        return _ZipResp(self.bodies[name])


def _us_universe(tmp_path, symbols: list[str]) -> None:
    import duckdb
    import pandas as pd

    from crible.universe import bootstrap_universe

    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(
        con,
        pd.DataFrame(
            {
                "symbol": symbols,
                "name": symbols,
                "country": ["United States"] * len(symbols),
                "sector": ["Tech"] * len(symbols),
                "industry": ["X"] * len(symbols),
                "exchange": ["NMS"] * len(symbols),
                "currency": ["USD"] * len(symbols),
            }
        ),
    )
    con.close()


def test_run_fsds_accumulates_history_across_quarters_and_share_classes(tmp_path, monkeypatch) -> None:
    """Two archives → 2021-2023 all present (the later write used to replace
    the earlier one), and GOOG + GOOGL (one CIK) both get the data."""
    from crible.compute.snapshot import latest_raw_frames
    from crible.ingest.enrichment import run_fsds
    from crible.providers.edgar_fsds import quarter_url

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    _us_universe(tmp_path, ["GOOG", "GOOGL"])
    bodies = {
        quarter_url(2024, 1).rsplit("/", 1)[-1].removesuffix(".zip"): _fsds_zip(
            ["20231231", "20221231"], revenue0=300.0
        ),
        quarter_url(2023, 1).rsplit("/", 1)[-1].removesuffix(".zip"): _fsds_zip(
            ["20221231", "20211231"], revenue0=200.0
        ),
    }
    run_fsds(
        [(2024, 1), (2023, 1)], ticker_map={"GOOG": 1652044, "GOOGL": 1652044}, http=_QuarterHttp(bodies)
    )

    for symbol in ("GOOG", "GOOGL"):
        income = latest_raw_frames(tmp_path, symbol, provider="edgar-fsds")[("income", "annual")]
        revenue = income.set_index("period")["TotalRevenue"]
        assert sorted(revenue.index) == ["2021-12-31", "2022-12-31", "2023-12-31"], symbol
        assert revenue["2022-12-31"] == 301.0  # the newer archive wins its periods

    # a later run on the old quarter alone keeps what the raw layer already has
    run_fsds([(2023, 1)], ticker_map={"GOOG": 1652044}, http=_QuarterHttp(bodies))
    income = latest_raw_frames(tmp_path, "GOOG", provider="edgar-fsds")[("income", "annual")]
    assert "2023-12-31" in set(income["period"])
