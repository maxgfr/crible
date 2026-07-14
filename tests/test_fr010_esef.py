"""FR-010 — ESEF enrichment: GLEIF ISIN→LEI resolution, xBRL-JSON parsing,
audited-wins reconciliation with >5% discrepancy logging, unmatched counting.
"""

from __future__ import annotations

import pandas as pd

from crible.compute.reconcile import reconcile
from crible.compute.snapshot import build_symbol_snapshot
from crible.providers.esef import facts_to_frames
from crible.providers.gleif import load_isin_lei_map, resolve_leis

from tests.test_fr003_compute import income_frame


# ---------------------------------------------------------------------- gleif

GLEIF_CSV = """LEI,ISIN
969500A1G9QKR8Q79815,FR0000121014
529900D6BF99LW9R2E68,DE0007164600
"""


def test_fr010_gleif_mapping_parses_and_resolves(tmp_path) -> None:
    path = tmp_path / "isin-lei.csv"
    path.write_text(GLEIF_CSV)
    mapping = load_isin_lei_map(path)
    assert mapping["FR0000121014"] == "969500A1G9QKR8Q79815"

    companies = [
        {"symbol": "MC.PA", "isin": "FR0000121014"},
        {"symbol": "SAP.DE", "isin": "DE0007164600"},
        {"symbol": "NOISIN.PA", "isin": None},
        {"symbol": "NOLEI.MI", "isin": "IT0000000000"},
    ]
    resolved, unmatched = resolve_leis(companies, mapping)
    assert resolved == {"MC.PA": "969500A1G9QKR8Q79815", "SAP.DE": "529900D6BF99LW9R2E68"}
    # FR-010 AC-4: unmatched are COUNTED, never errored
    assert unmatched == ["NOISIN.PA", "NOLEI.MI"]


# ----------------------------------------------------------------- xBRL-JSON

XBRL_JSON = {
    "facts": {
        "f1": {
            "value": "1000000",
            "dimensions": {
                "concept": "ifrs-full:Revenue",
                "entity": "scheme:969500A1G9QKR8Q79815",
                "period": "2024-01-01T00:00:00/2025-01-01T00:00:00",
            },
        },
        "f2": {
            "value": "80000",
            "dimensions": {
                "concept": "ifrs-full:ProfitLoss",
                "entity": "scheme:969500A1G9QKR8Q79815",
                "period": "2024-01-01T00:00:00/2025-01-01T00:00:00",
            },
        },
        "f3": {
            "value": "2000000",
            "dimensions": {
                "concept": "ifrs-full:Assets",
                "entity": "scheme:969500A1G9QKR8Q79815",
                "period": "2025-01-01T00:00:00",
            },
        },
        "f4-segmented": {
            "value": "999",
            "dimensions": {
                "concept": "ifrs-full:Revenue",
                "entity": "scheme:x",
                "period": "2024-01-01T00:00:00/2025-01-01T00:00:00",
                "ifrs-full:SegmentsAxis": "something",
            },
        },
        "f5-unmapped": {
            "value": "5",
            "dimensions": {"concept": "ifrs-full:NumberOfEmployees", "period": "2025-01-01T00:00:00"},
        },
    }
}


def test_fr010_xbrl_json_facts_map_to_canonical_annual_frames() -> None:
    frames = facts_to_frames(XBRL_JSON)
    income = frames[("income", "annual")].set_index("period")
    balance = frames[("balance", "annual")].set_index("period")
    assert income.loc["2024", "TotalRevenue"] == 1000000.0
    assert income.loc["2024", "NetIncome"] == 80000.0
    assert balance.loc["2024", "TotalAssets"] == 2000000.0  # Jan-1 instant → FY just closed
    # segmented and unmapped facts are conservatively dropped
    assert (income["TotalRevenue"] == 999).sum() == 0


# ------------------------------------------- F9: interim never stored as annual

INTERIM_JSON = {
    "facts": {
        "annual": {
            "value": "1000",
            "dimensions": {
                "concept": "ifrs-full:Revenue",
                "period": "2024-01-01T00:00:00/2025-01-01T00:00:00",  # full year
            },
        },
        "interim": {  # H1 2025 — must NEVER be stored as the 2025 annual figure
            "value": "600",
            "dimensions": {
                "concept": "ifrs-full:Revenue",
                "period": "2025-01-01T00:00:00/2025-07-01T00:00:00",  # ~181 days
            },
        },
    }
}


def test_fr010_interim_duration_never_stored_as_annual() -> None:
    """F9 — a half-year duration tagged by its end year would otherwise be
    stored as an *audited* annual figure and then override the scraped value at
    reconciliation, silently corrupting the flagship number. Only full-year
    durations (EDGAR's 320-400 day window) are annual."""
    frames = facts_to_frames(INTERIM_JSON)
    income = frames[("income", "annual")].set_index("period")
    assert income.loc["2024", "TotalRevenue"] == 1000.0
    assert "2025" not in income.index  # the interim is dropped, not booked as FY


# --------------------------------------------- F10: deterministic collisions

COLLISION_JSON = {
    "facts": {
        "pl": {
            "value": "600000",
            "dimensions": {
                "concept": "ifrs-full:ProfitLoss",
                "period": "2024-01-01T00:00:00/2025-01-01T00:00:00",
            },
        },
        "pl_owners": {
            "value": "500000",
            "dimensions": {
                "concept": "ifrs-full:ProfitLossAttributableToOwnersOfParent",
                "period": "2024-01-01T00:00:00/2025-01-01T00:00:00",
            },
        },
    }
}


def test_fr010_concept_collision_resolves_by_declared_precedence() -> None:
    """F10 — two IFRS concepts map to NetIncome; the winner must be the one
    declared first in CONCEPT_MAP (ProfitLoss), deterministically, not whichever
    the JSON happened to list last."""
    frames = facts_to_frames(COLLISION_JSON)
    income = frames[("income", "annual")].set_index("period")
    assert income.loc["2024", "NetIncome"] == 600000.0


# ------------------------------------------------------------- reconciliation


def test_fr010_audited_value_wins_and_discrepancy_over_5pct_is_logged(caplog) -> None:
    scraped = pd.DataFrame({"revenue": [100.0], "net_income": [10.0]}, index=["2024"])
    audited = pd.DataFrame({"revenue": [110.0]}, index=["2024"])
    with caplog.at_level("WARNING"):
        result = reconcile(scraped, audited, symbol="MC.PA")
    assert result.merged.loc["2024", "revenue"] == 110.0  # audited wins
    assert result.merged.loc["2024", "net_income"] == 10.0  # untouched
    assert result.audited_fields == {"2024": ["revenue"]}
    assert len(result.discrepancies) == 1
    entry = result.discrepancies[0]
    assert entry["scraped"] == 100.0 and entry["audited"] == 110.0
    assert any("MC.PA" in r.message and "audited wins" in r.message for r in caplog.records)


def test_fr010_reconcile_adds_audited_only_periods_deeper_than_scraped() -> None:
    """F6 — audited history deeper than the scraped window (SEC FSDS / EDGAR
    backfill) must be ADDED to the merged frame, not dropped: a scraped symbol
    must keep its full audited history, otherwise the flagship deep-history
    feature is silently inert for every scraped US large-cap."""
    scraped = pd.DataFrame({"revenue": [100.0]}, index=["2024"])
    audited = pd.DataFrame({"revenue": [80.0, 90.0, 110.0]}, index=["2022", "2023", "2024"])
    result = reconcile(scraped, audited, symbol="X")
    merged = result.merged
    assert merged.loc["2024", "revenue"] == 110.0  # audited overrides the overlap
    assert merged.loc["2023", "revenue"] == 90.0   # deeper history is added…
    assert merged.loc["2022", "revenue"] == 80.0   # …not truncated to the scraped window
    assert "2022" in result.audited_fields and "2023" in result.audited_fields


def test_fr010_small_differences_override_silently() -> None:
    scraped = pd.DataFrame({"revenue": [108.0]}, index=["2024"])
    audited = pd.DataFrame({"revenue": [110.0]}, index=["2024"])
    result = reconcile(scraped, audited)
    assert result.merged.loc["2024", "revenue"] == 110.0
    assert result.discrepancies == []  # < 5%: override without noise


def test_fr010_audited_year_labels_align_to_dated_scraped_periods() -> None:
    """ESEF labels periods by fiscal year ("2024") while yfinance uses dates
    ("2024-12-31") — align_periods must bridge them or the audited layer
    never overrides anything (the Finding-A fix)."""
    scraped_frames = {
        ("income", "annual"): income_frame(
            {"TotalRevenue": [1000.0, 1100.0]}, ["2023-12-31", "2024-12-31"]
        ),
    }
    audited_frames = {
        ("income", "annual"): income_frame({"TotalRevenue": [1200.0]}, ["2024"]),
    }
    snapshot = build_symbol_snapshot(
        "MC.PA", scraped_frames, audited_frames=audited_frames, computed_at=1.0
    )
    by_period = snapshot.set_index("period")
    assert by_period.loc["2024-12-31", "revenue"] == 1200.0
    assert "revenue" in by_period.loc["2024-12-31", "audited_fields"]
    assert "2024" not in by_period.index


def test_fr010_snapshot_marks_audited_provenance() -> None:
    scraped_frames = {
        ("income", "annual"): income_frame(
            {"TotalRevenue": [1000.0, 1100.0], "NetIncome": [50.0, 60.0]}, ["2023", "2024"]
        ),
        ("balance", "annual"): income_frame({"TotalAssets": [500.0, 550.0]}, ["2023", "2024"]),
    }
    audited_frames = {
        ("income", "annual"): income_frame({"TotalRevenue": [1200.0]}, ["2024"]),
    }
    snapshot = build_symbol_snapshot(
        "MC.PA", scraped_frames, audited_frames=audited_frames, computed_at=1.0
    )
    by_period = snapshot.set_index("period")
    assert by_period.loc["2024", "revenue"] == 1200.0
    assert "revenue" in by_period.loc["2024", "audited_fields"]
    assert by_period.loc["2023", "audited_fields"] is None or by_period.loc["2023", "audited_fields"] != by_period.loc["2024", "audited_fields"]


# (the outage path is exercised for real by
#  test_fr010_service_cycle_outage_records_and_resumes below)


def test_fr010_service_enrichment_cycle_writes_esef_raw_and_counts_unmatched(tmp_path, monkeypatch) -> None:
    """FR-010 — the enrichment cycle end-to-end (offline): EU companies with a
    resolvable LEI get provider='esef' raw frames; unmatched are counted."""
    import duckdb as _duckdb

    from crible.ingest.service import run_esef_cycle
    from crible.universe import bootstrap_universe
    from tests.test_fr001_universe import fixture_frame

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    con.close()

    class FakeClient:
        def filings_for_lei(self, lei):
            return [{"attributes": {"json_url": "/x.json"}}]

        def fetch_xbrl_json(self, filing):
            return XBRL_JSON

    # ISINs from the universe fixture: ABN.AS + AIR.PA resolve, others don't
    mapping = {"NL0011540547": "LEI-ABN", "NL0000235190": "LEI-AIR"}
    outcome = run_esef_cycle(limit=10, client=FakeClient(), mapping=mapping)

    assert sorted(outcome["enriched"]) == ["ABN.AS", "AIR.PA"]
    assert outcome["unmatched"] >= 3  # EU listings without a resolvable ISIN→LEI
    files = list(tmp_path.glob("raw/provider=esef/symbol=*/*.parquet"))
    assert len(files) >= 4  # income + balance per enriched symbol


def test_fr010_service_cycle_outage_records_and_resumes(tmp_path, monkeypatch) -> None:
    import duckdb as _duckdb

    from crible.ingest.service import run_esef_cycle
    from crible.universe import bootstrap_universe
    from tests.test_fr001_universe import fixture_frame

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    con.close()

    class DownClient:
        def filings_for_lei(self, lei):
            raise ConnectionError("filings.xbrl.org unreachable")

        def fetch_xbrl_json(self, filing):
            raise AssertionError("never reached")

    outcome = run_esef_cycle(limit=10, client=DownClient(), mapping={"NL0011540547": "LEI-ABN"})
    assert outcome["outage"] is not None
    assert list(tmp_path.glob("raw/provider=esef/**/*.parquet")) == []  # no partial writes


def test_fr010_service_cycle_idles_without_gleif_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    from crible.ingest.service import run_esef_cycle

    outcome = run_esef_cycle()
    assert outcome["skipped"] is not None and "isin-lei" in outcome["skipped"].lower()


# ---------------------------------------------------------------- index sweep

LEI_ABN = "LEIABN0000000000001X"  # fixture ISIN NL0011540547 (ABN.AS)


def test_fr010_filing_lei_extracts_the_first_json_url_segment() -> None:
    from crible.providers.esef import filing_lei

    assert filing_lei({"attributes": {"json_url": f"/{LEI_ABN}/2025-12-31/x.json"}}) == LEI_ABN
    assert filing_lei({"attributes": {"json_url": "/short/2025/x.json"}}) is None
    assert filing_lei({"attributes": {}}) is None


class FakeIndexClient:
    """Two-entry index: one filer in the universe, one outside it."""

    def __init__(self) -> None:
        self.json_fetches = 0

    def filings_index(self, page_size: int = 100, page_number: int = 1):
        if page_number > 1:
            return [], 2
        return (
            [
                {"attributes": {"json_url": f"/{LEI_ABN}/2025-12-31/abn.json"}},
                {"attributes": {"json_url": "/UNKNOWNLEI0000000001/2025-12-31/other.json"}},
            ],
            2,
        )

    def fetch_xbrl_json(self, filing):
        self.json_fetches += 1
        return XBRL_JSON


def _seed_sweep_universe(tmp_path, monkeypatch) -> None:
    import duckdb as _duckdb

    from crible.universe import bootstrap_universe
    from tests.test_fr001_universe import fixture_frame

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    con.close()


def test_fr010_index_sweep_enriches_known_filers_and_skips_the_rest(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    client = FakeIndexClient()
    mapping = {"NL0011540547": LEI_ABN}

    outcome = run_esef_sweep(limit=10, client=client, mapping=mapping)
    assert outcome["enriched"] == ["ABN.AS"]
    assert outcome["skipped_unknown"] == 1  # real filer, not in the universe
    assert client.json_fetches == 1  # the unknown filer costs NO document fetch
    assert list(tmp_path.glob("raw/provider=esef/symbol=ABN.AS/*.parquet"))

    # steady state: everything fresh → the sweep fetches nothing again
    again = run_esef_sweep(limit=10, client=FakeIndexClient(), mapping=mapping)
    assert again["enriched"] == []


def test_fr010_index_sweep_outage_records_and_resumes(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)

    class DownIndex:
        def filings_index(self, page_size: int = 100, page_number: int = 1):
            raise ConnectionError("filings.xbrl.org unreachable")

    outcome = run_esef_sweep(limit=10, client=DownIndex(), mapping={"NL0011540547": LEI_ABN})
    assert outcome["outage"] is not None
    assert list(tmp_path.glob("raw/provider=esef/**/*.parquet")) == []
