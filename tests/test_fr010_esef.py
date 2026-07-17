"""FR-010 — ESEF enrichment: GLEIF ISIN→LEI resolution, xBRL-JSON parsing,
audited-wins reconciliation with >5% discrepancy logging, unmatched counting.
"""

from __future__ import annotations

import pandas as pd
import pytest

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


# ------------------------------- dimensional RetainedEarnings recovery (SOCIE)


def _equity_fact(concept: str, value: str, extra: dict | None = None) -> dict:
    dims = {
        "concept": concept,
        "entity": "scheme:969500A1G9QKR8Q79815",
        "period": "2025-01-01T00:00:00",  # Jan-1 instant → FY2024 close
    }
    dims.update(extra or {})
    return {"value": value, "dimensions": dims}


_RE_MEMBER = {"ifrs-full:ComponentsOfEquityAxis": "ifrs-full:RetainedEarningsMember"}


def test_fr010_retained_earnings_recovered_from_equity_components_axis() -> None:
    """IFRS filers tag retained earnings almost only dimensionally (SOCIE,
    ComponentsOfEquityAxis) — the one narrow exception to the whole-entity
    rule, because Altman x2 (→ the Quality pillar) depends on it."""
    frames = facts_to_frames(
        {
            "facts": {
                "equity-component": _equity_fact("ifrs-full:Equity", "300", _RE_MEMBER),
            }
        }
    )
    balance = frames[("balance", "annual")].set_index("period")
    assert balance.loc["2024", "RetainedEarnings"] == 300.0
    # the dimensional fact feeds RetainedEarnings ONLY — never StockholdersEquity
    assert "StockholdersEquity" not in balance.columns

    # some filers tag the component with the RetainedEarnings concept itself
    frames = facts_to_frames(
        {"facts": {"re-component": _equity_fact("ifrs-full:RetainedEarnings", "310", _RE_MEMBER)}}
    )
    assert frames[("balance", "annual")].set_index("period").loc["2024", "RetainedEarnings"] == 310.0


def test_fr010_undimensioned_retained_earnings_outranks_dimensional_any_order() -> None:
    dimensional = _equity_fact("ifrs-full:Equity", "300", _RE_MEMBER)
    direct = _equity_fact("ifrs-full:RetainedEarnings", "280")
    for facts in ({"a": dimensional, "b": direct}, {"a": direct, "b": dimensional}):
        frames = facts_to_frames({"facts": facts})
        balance = frames[("balance", "annual")].set_index("period")
        assert balance.loc["2024", "RetainedEarnings"] == 280.0


def test_fr010_other_members_and_extra_axes_stay_skipped() -> None:
    frames = facts_to_frames(
        {
            "facts": {
                "other-member": _equity_fact(
                    "ifrs-full:Equity",
                    "500",
                    {"ifrs-full:ComponentsOfEquityAxis": "ifrs-full:IssuedCapitalMember"},
                ),
                "second-axis": _equity_fact(
                    "ifrs-full:Equity",
                    "600",
                    {**_RE_MEMBER, "ifrs-full:SegmentsAxis": "something"},
                ),
            }
        }
    )
    assert ("balance", "annual") not in frames


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
    # the merged frame MUST stay chronologically sorted (latest period last):
    # build_symbol_snapshot assigns the current price/return_6m to .iloc[-1]
    assert list(merged.index) == ["2022", "2023", "2024"]


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


def test_fr010_audited_only_symbol_carries_field_provenance(tmp_path) -> None:
    """F2/c3 — an audited-only listing (ESEF/EDGAR, no Yahoo scrape) must carry
    field-level audited provenance through build_snapshot, not an empty
    audited_fields — 'every number traceable to its source' is the value prop."""
    from crible.compute.snapshot import build_snapshot
    from crible.ingest.raw import write_raw_statement

    write_raw_statement(
        tmp_path, symbol="SAP.DE", provider="esef", statement_type="income", freq="annual",
        frame=pd.DataFrame({"period": ["2024"], "TotalRevenue": [34e9], "NetIncome": [6e9]}),
        fetched_at=1000.0,
    )
    snap = build_snapshot(tmp_path)
    row = snap[snap.symbol == "SAP.DE"].iloc[0]
    assert row["revenue"] == 34e9
    assert row["audited_fields"] and "revenue" in row["audited_fields"]


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


LEI_BARC = "LEIBARC000000000001X"  # fixture ISIN GB0031348658 (BARC.L)


def test_fr010_sweep_covers_the_gb_slice(tmp_path, monkeypatch) -> None:
    """filings.xbrl.org serves 2,885 GB filings under the same ESEF system
    (UK listed IFRS, fully-free) and the sweep walks the UNFILTERED index —
    this test forbids a future EU-only country filter from silently dropping
    the United Kingdom (which EUROPE_COUNTRIES deliberately includes)."""
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)

    class GbIndexClient:
        def filings_index(self, page_size: int = 100, page_number: int = 1):
            if page_number > 1:
                return [], 1
            return [{"attributes": {"json_url": f"/{LEI_BARC}/2025-12-31/barc.json",
                                    "country": "GB"}}], 1

        def fetch_xbrl_json(self, filing):
            return XBRL_JSON

    outcome = run_esef_sweep(
        limit=10, client=GbIndexClient(), mapping={"GB0031348658": LEI_BARC}
    )
    assert outcome["enriched"] == ["BARC.L"]
    assert list(tmp_path.glob("raw/provider=esef/symbol=BARC.L/*.parquet"))


def test_esef_outranks_companies_house_and_ch_backfills(tmp_path) -> None:
    """merge_audited argument order IS the precedence: filings.xbrl.org wins
    every period it reports; Companies House keeps the rest."""
    from crible.compute.snapshot import build_snapshot
    from crible.ingest.raw import write_raw_statement

    pd.DataFrame({"symbol": ["BARC.L"]}).to_parquet(tmp_path / "universe.parquet", index=False)
    write_raw_statement(
        tmp_path, symbol="BARC.L", provider="companies-house", statement_type="income",
        freq="annual",
        frame=pd.DataFrame({"period": ["2024-12-31", "2025-12-31"],
                            "TotalRevenue": [111.0, 222.0]}),
        fetched_at=1.0,
    )
    write_raw_statement(
        tmp_path, symbol="BARC.L", provider="esef", statement_type="income",
        freq="annual",
        frame=pd.DataFrame({"period": ["2025-12-31"], "TotalRevenue": [999.0]}),
        fetched_at=2.0,
    )
    snapshot = build_snapshot(tmp_path, symbols=["BARC.L"]).set_index("period")
    assert snapshot.loc["2025-12-31", "revenue"] == 999.0  # esef wins the period
    assert snapshot.loc["2024-12-31", "revenue"] == 111.0  # CH backfills the rest


def test_fr010_sweep_freshness_survives_a_fresh_operational_db(tmp_path, monkeypatch) -> None:
    """The CI amnesia fix: crible.duckdb never travels in the published
    dataset, so every nightly starts blank — the raw layer must re-seed
    esef_tasks or the sweep re-downloads the same newest filings forever
    (the observed ~115-symbol coverage plateau)."""
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    mapping = {"NL0011540547": LEI_ABN}
    first = FakeIndexClient()
    assert run_esef_sweep(limit=10, client=first, mapping=mapping)["enriched"] == ["ABN.AS"]
    assert first.json_fetches == 1

    # simulate the nightly: fresh operational DB, restored raw layer
    (tmp_path / "crible.duckdb").unlink()
    _seed_sweep_universe(tmp_path, monkeypatch)
    again = FakeIndexClient()
    outcome = run_esef_sweep(limit=10, client=again, mapping=mapping)
    assert outcome["enriched"] == []
    assert again.json_fetches == 0  # nothing re-downloaded inside the 90-day window


def test_fr010_index_sweep_stops_on_time_budget(tmp_path, monkeypatch) -> None:
    """A zero wall-clock budget (run_refresh --max-minutes reserve) stops the
    sweep before any document fetch; freshness state resumes it next run."""
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    client = FakeIndexClient()
    outcome = run_esef_sweep(
        limit=10, client=client, mapping={"NL0011540547": LEI_ABN}, time_budget_seconds=0,
    )
    assert outcome["stopped"] == "budget"
    assert outcome["enriched"] == []
    assert client.json_fetches == 0


def test_fr010_index_sweep_outage_records_and_resumes(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)

    class DownIndex:
        def filings_index(self, page_size: int = 100, page_number: int = 1):
            raise ConnectionError("filings.xbrl.org unreachable")

    outcome = run_esef_sweep(limit=10, client=DownIndex(), mapping={"NL0011540547": LEI_ABN})
    assert outcome["outage"] is not None
    assert list(tmp_path.glob("raw/provider=esef/**/*.parquet")) == []


# ------------------------------------------------- widened IFRS map (FR-010)

def _wide_fact(concept: str, value: float, *, year: int = 2024, instant: bool = False) -> dict:
    period = (
        f"{year + 1}-01-01T00:00:00"
        if instant
        else f"{year}-01-01T00:00:00/{year + 1}-01-01T00:00:00"
    )
    return {
        "value": str(value),
        "dimensions": {
            "concept": concept,
            "entity": "scheme:969500A1G9QKR8Q79815",
            "period": period,
        },
    }


def _wide_json(facts: list[dict]) -> dict:
    return {"facts": {f"f{i}": fact for i, fact in enumerate(facts)}}


def test_fr010_widened_ifrs_tags_fill_beneish_and_altman_inputs() -> None:
    frames = facts_to_frames(_wide_json([
        _wide_fact("ifrs-full:CostOfSales", 6e8),
        _wide_fact("ifrs-full:ProfitLossBeforeTax", 1.2e8),
        _wide_fact("ifrs-full:IncomeTaxExpenseContinuingOperations", 3e7),
        _wide_fact("ifrs-full:InterestExpense", 1e7),
        _wide_fact("ifrs-full:SellingGeneralAndAdministrativeExpense", 2e8),
        _wide_fact("ifrs-full:WeightedAverageShares", 1e9),
        _wide_fact("ifrs-full:Liabilities", 5e9, instant=True),
        _wide_fact("ifrs-full:PropertyPlantAndEquipment", 2e9, instant=True),
        _wide_fact("ifrs-full:Goodwill", 1e9, instant=True),
        _wide_fact("ifrs-full:TradeAndOtherCurrentPayablesToTradeSuppliers", 4e8, instant=True),
        _wide_fact("ifrs-full:LongtermBorrowings", 1.5e9, instant=True),
        _wide_fact("ifrs-full:AdjustmentsForDepreciationAndAmortisationExpense", 2.5e8),
        _wide_fact("ifrs-full:ProceedsFromIssuingShares", 5e7),
    ]))
    income = frames[("income", "annual")].set_index("period").loc["2024"]
    assert income["CostOfRevenue"] == 6e8
    assert income["PretaxIncome"] == 1.2e8
    assert income["TaxProvision"] == 3e7
    assert income["InterestExpense"] == 1e7
    assert income["SellingGeneralAndAdministration"] == 2e8
    assert income["BasicAverageShares"] == 1e9
    balance = frames[("balance", "annual")].set_index("period").loc["2024"]
    assert balance["TotalLiabilitiesNetMinorityInterest"] == 5e9
    assert balance["NetPPE"] == 2e9
    assert balance["Goodwill"] == 1e9
    assert balance["AccountsPayable"] == 4e8
    assert balance["LongTermDebt"] == 1.5e9
    cashflow = frames[("cashflow", "annual")].set_index("period").loc["2024"]
    assert cashflow["DepreciationAndAmortization"] == 2.5e8
    assert cashflow["CommonStockIssuance"] == 5e7


def test_fr010_capex_and_dividends_negate_to_the_yfinance_convention() -> None:
    frames = facts_to_frames(_wide_json([
        _wide_fact(
            "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", 9_447.0
        ),
        _wide_fact("ifrs-full:DividendsPaidClassifiedAsFinancingActivities", 1_000.0),
        _wide_fact("ifrs-full:ProceedsFromIssuingShares", 500.0),
    ]))
    cashflow = frames[("cashflow", "annual")].set_index("period").loc["2024"]
    assert cashflow["CapitalExpenditure"] == -9_447.0
    assert cashflow["CashDividendsPaid"] == -1_000.0
    assert cashflow["CommonStockIssuance"] == 500.0


def test_fr010_narrow_tag_outranks_broad_variant() -> None:
    both = facts_to_frames(_wide_json([
        _wide_fact("ifrs-full:PropertyPlantAndEquipment", 2e9, instant=True),
        _wide_fact("ifrs-full:PropertyPlantAndEquipmentIncludingRightofuseAssets", 2.4e9, instant=True),
        _wide_fact("ifrs-full:TradeAndOtherCurrentPayablesToTradeSuppliers", 4e8, instant=True),
        _wide_fact("ifrs-full:TradeAndOtherCurrentPayables", 6e8, instant=True),
    ]))
    balance = both[("balance", "annual")].set_index("period").loc["2024"]
    assert balance["NetPPE"] == 2e9
    assert balance["AccountsPayable"] == 4e8

    combined_only = facts_to_frames(_wide_json([
        _wide_fact("ifrs-full:PropertyPlantAndEquipmentIncludingRightofuseAssets", 2.4e9, instant=True),
    ]))
    assert combined_only[("balance", "annual")].set_index("period").loc["2024", "NetPPE"] == 2.4e9


def test_fr010_widened_esef_reaches_scores_end_to_end() -> None:
    facts = []
    for year, scale in ((2023, 1.0), (2024, 1.1)):
        facts += [
            _wide_fact("ifrs-full:Revenue", 1e9 * scale, year=year),
            _wide_fact("ifrs-full:ProfitLoss", 1e8 * scale, year=year),
            _wide_fact("ifrs-full:ProfitLossBeforeTax", 1.3e8 * scale, year=year),
            _wide_fact("ifrs-full:Assets", 2e9 * scale, year=year, instant=True),
            _wide_fact("ifrs-full:Liabilities", 1.2e9 * scale, year=year, instant=True),
            _wide_fact("ifrs-full:CashFlowsFromUsedInOperatingActivities", 2e8 * scale, year=year),
            _wide_fact(
                "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
                5e7 * scale, year=year,
            ),
            # dimensional SOCIE fact — the recovered RetainedEarnings path
            {
                "value": str(4e8 * scale),
                "dimensions": {
                    "concept": "ifrs-full:Equity",
                    "period": f"{year + 1}-01-01T00:00:00",
                    "ifrs-full:ComponentsOfEquityAxis": "ifrs-full:RetainedEarningsMember",
                },
            },
        ]
    frames = facts_to_frames(_wide_json(facts))
    snapshot = build_symbol_snapshot("EU.PA", frames, computed_at=1.0)
    latest = snapshot.iloc[-1]
    assert latest["free_cash_flow"] == 2e8 * 1.1 - 5e7 * 1.1
    assert latest["total_liabilities"] == 1.2e9 * 1.1
    assert latest["income_before_tax"] == 1.3e8 * 1.1
    # recovered retained earnings reaches Altman x2 (→ the Quality pillar)
    assert latest["retained_earnings"] == 4e8 * 1.1
    assert latest["altman_x2_re_ta"] == pytest.approx((4e8 * 1.1) / (2e9 * 1.1))


# ----------------------------------- deep history: multi-filing merge (FR-010)

_LEI = "969500A1G9QKR8Q79815"


def _history_filing(
    period_end: str, date_added: str, *, lei: str = _LEI, tag_period: bool = True
) -> dict:
    attrs = {
        "json_url": f"/{lei}/{period_end}/{date_added}.json",
        "date_added": date_added,
    }
    if tag_period:
        attrs["period_end"] = period_end
    return {"attributes": attrs}


def _revenue_doc(values_by_year: dict[int, float]) -> dict:
    return _wide_json(
        [_wide_fact("ifrs-full:Revenue", value, year=year) for year, value in values_by_year.items()]
    )


def test_fr010_select_history_filings_dedupes_orders_and_caps() -> None:
    from crible.providers.esef import select_history_filings

    fy2024 = _history_filing("2024-12-31", "2025-04-01")
    fy2024_amended = _history_filing("2024-12-31", "2025-06-01")
    fy2023 = _history_filing("2023-12-31", "2024-04-01")
    fy2022 = _history_filing("2022-12-31", "2023-04-01")
    scrambled = [fy2023, fy2024, fy2022, fy2024_amended]

    picked = select_history_filings(scrambled, 2)
    # amendments dedupe to the newest date_added; groups order newest-first
    assert picked == [fy2024_amended, fy2023]
    assert select_history_filings(scrambled, 10) == [fy2024_amended, fy2023, fy2022]

    # period_end falls back to the json_url path convention /<LEI>/<period_end>/…
    untagged = [
        _history_filing("2023-12-31", "2024-04-01", tag_period=False),
        _history_filing("2024-12-31", "2025-04-01", tag_period=False),
    ]
    assert [f["attributes"]["json_url"] for f in select_history_filings(untagged, 2)] == [
        untagged[1]["attributes"]["json_url"],
        untagged[0]["attributes"]["json_url"],
    ]


class _HistoryClient:
    """Serves one xbrl-json doc per filing, keyed by json_url; counts fetches."""

    def __init__(self, docs_by_url: dict[str, dict]) -> None:
        self.docs = docs_by_url
        self.fetched: list[str] = []

    def fetch_xbrl_json(self, filing: dict) -> dict | None:
        url = filing["attributes"]["json_url"]
        self.fetched.append(url)
        return self.docs.get(url)


def _history_fixture() -> tuple[_HistoryClient, list[dict]]:
    filings = [
        _history_filing("2024-12-31", "2025-04-01"),
        _history_filing("2023-12-31", "2024-04-01"),
        _history_filing("2022-12-31", "2023-04-01"),
    ]
    docs = {
        # each annual filing carries its reporting year + the comparative year;
        # the 2023 comparative in the newest filing DIFFERS from the older
        # filing's face value — the newest filing must win
        filings[0]["attributes"]["json_url"]: _revenue_doc({2024: 1100.0, 2023: 999.0}),
        filings[1]["attributes"]["json_url"]: _revenue_doc({2023: 1000.0, 2022: 900.0}),
        filings[2]["attributes"]["json_url"]: _revenue_doc({2022: 901.0, 2021: 800.0}),
    }
    return _HistoryClient(docs), filings


def test_fr010_fetch_history_frames_merges_older_filings_newest_wins() -> None:
    from crible.providers.esef import fetch_history_frames

    client, filings = _history_fixture()
    frames = fetch_history_frames(client, filings, history=3)
    income = frames[("income", "annual")].set_index("period")["TotalRevenue"]
    assert income.loc["2024"] == 1100.0
    assert income.loc["2023"] == 999.0  # newest filing wins the overlap
    assert income.loc["2022"] == 900.0  # first older filing backfills
    assert income.loc["2021"] == 800.0  # deepest filing adds one more year
    assert len(client.fetched) == 3


def test_fr010_history_one_short_circuits_to_the_newest_filing() -> None:
    from crible.providers.esef import fetch_history_frames

    client, filings = _history_fixture()
    frames = fetch_history_frames(client, filings, history=1)
    income = frames[("income", "annual")].set_index("period")["TotalRevenue"]
    assert set(income.index) == {"2023", "2024"}
    assert len(client.fetched) == 1


def _instant(concept: str, value: str, instant: str, extra: dict | None = None) -> dict:
    dims = {"concept": concept, "period": f"{instant}T00:00:00"}
    dims.update(extra or {})
    return {"value": value, "dimensions": dims}


def test_fr010_history_merge_is_cell_wise_socie_openings_never_shadow() -> None:
    """Every filing's SOCIE opening instants create a SPARSE row for the year
    before its comparatives (equity components only). A row-level year dedupe
    would let that sparse row shadow an older filing's FULL audited balance
    sheet for the same year — the merge must be cell-wise: the newest filing
    wins each cell it actually reports, older filings backfill the rest."""
    from crible.providers.esef import fetch_history_frames

    newest = _history_filing("2024-12-31", "2025-04-01")
    older = _history_filing("2022-12-31", "2023-04-01")
    docs = {
        newest["attributes"]["json_url"]: {
            "facts": {
                "a24": _instant("ifrs-full:Assets", "2000", "2025-01-01"),
                "e24": _instant("ifrs-full:Equity", "800", "2025-01-01"),
                "a23": _instant("ifrs-full:Assets", "1900", "2024-01-01"),
                "e23": _instant("ifrs-full:Equity", "795", "2024-01-01"),
                # SOCIE opening of the comparative year → a sparse 2022 row
                "e22-open": _instant("ifrs-full:Equity", "790", "2023-01-01"),
                "re22-open": _instant("ifrs-full:Equity", "400", "2023-01-01", _RE_MEMBER),
            }
        },
        older["attributes"]["json_url"]: {
            "facts": {
                "a22": _instant("ifrs-full:Assets", "1700", "2023-01-01"),
                "ca22": _instant("ifrs-full:CurrentAssets", "700", "2023-01-01"),
                "e22": _instant("ifrs-full:Equity", "801", "2023-01-01"),
                "re22": _instant("ifrs-full:RetainedEarnings", "401", "2023-01-01"),
            }
        },
    }
    frames = fetch_history_frames(_HistoryClient(docs), [newest, older], history=3)
    balance = frames[("balance", "annual")].set_index("period")
    assert balance.loc["2024", "TotalAssets"] == 2000.0
    # the older filing's full balance sheet reaches 2022 despite the SOCIE row
    assert balance.loc["2022", "TotalAssets"] == 1700.0
    assert balance.loc["2022", "CurrentAssets"] == 700.0
    # the newest filing still wins the cells it actually reports (restated)
    assert balance.loc["2022", "StockholdersEquity"] == 790.0
    assert balance.loc["2022", "RetainedEarnings"] == 400.0


def test_fr010_broken_older_filing_is_skipped_but_newest_failure_raises() -> None:
    """A deterministically-broken YEARS-OLD document must not wedge the sweep
    forever: older-filing fetch errors are isolated (the filer still enriches
    from the reachable filings and records its depth). The NEWEST document
    failing stays a real outage."""
    from crible.providers.esef import fetch_history_frames

    class Flaky(_HistoryClient):
        def __init__(self, docs, broken: str) -> None:
            super().__init__(docs)
            self.broken = broken

        def fetch_xbrl_json(self, filing):
            if filing["attributes"]["json_url"] == self.broken:
                raise ConnectionError("410 gone")
            return super().fetch_xbrl_json(filing)

    client, filings = _history_fixture()
    oldest_url = filings[2]["attributes"]["json_url"]
    frames = fetch_history_frames(Flaky(client.docs, oldest_url), filings, history=3)
    income = frames[("income", "annual")].set_index("period")["TotalRevenue"]
    assert set(income.index) == {"2022", "2023", "2024"}  # 2021 skipped, rest intact

    newest_url = filings[0]["attributes"]["json_url"]
    with pytest.raises(ConnectionError):
        fetch_history_frames(Flaky(client.docs, newest_url), filings, history=3)


def test_fr010_client_throttles_between_requests(monkeypatch) -> None:
    from crible.providers import esef as esef_module

    class _Http:
        def get(self, url, params=None):
            class _Resp:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"data": [], "meta": {"count": 0}}

            return _Resp()

    sleeps: list[float] = []
    ticks = iter([0.0, 0.1, 0.2])  # 2nd request arrives 0.1s after the 1st
    monkeypatch.setattr(esef_module.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(esef_module.time, "sleep", sleeps.append)

    client = esef_module.EsefClient(http=_Http(), min_interval=0.5)
    client.filings_index()
    client.filings_index()
    assert sleeps and sleeps[0] == pytest.approx(0.4)


# ------------------------- deep history: depth-gated cycle & sweep (FR-010)


def _deep_filings(lei: str) -> tuple[list[dict], dict[str, dict]]:
    filings = [
        _history_filing("2024-12-31", "2025-04-01", lei=lei),
        _history_filing("2023-12-31", "2024-04-01", lei=lei),
        _history_filing("2022-12-31", "2023-04-01", lei=lei),
    ]
    docs = {
        filings[0]["attributes"]["json_url"]: _revenue_doc({2024: 1100.0, 2023: 999.0}),
        filings[1]["attributes"]["json_url"]: _revenue_doc({2023: 1000.0, 2022: 900.0}),
        filings[2]["attributes"]["json_url"]: _revenue_doc({2022: 901.0, 2021: 800.0}),
    }
    return filings, docs


class _DeepClient:
    """LEI + index client whose single filer has three annual filings."""

    def __init__(self, lei: str) -> None:
        self.filings, self.docs = _deep_filings(lei)
        self.json_fetches = 0
        self.lei_calls = 0

    def filings_index(self, page_size: int = 100, page_number: int = 1):
        if page_number > 1:
            return [], 1
        return [self.filings[0]], 1

    def filings_for_lei(self, lei):
        self.lei_calls += 1
        return self.filings

    def fetch_xbrl_json(self, filing):
        self.json_fetches += 1
        return self.docs[filing["attributes"]["json_url"]]


def _esef_task_depth(tmp_path, symbol: str):
    import duckdb as _duckdb

    con = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    try:
        row = con.execute(
            "SELECT history_depth FROM esef_tasks WHERE symbol = ?", [symbol]
        ).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def test_fr010_cycle_merges_filing_history_and_records_depth(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_esef_cycle

    _seed_sweep_universe(tmp_path, monkeypatch)
    client = _DeepClient(LEI_ABN)
    outcome = run_esef_cycle(
        limit=10, client=client, mapping={"NL0011540547": LEI_ABN}, history=3
    )
    assert outcome["enriched"] == ["ABN.AS"]
    assert client.json_fetches == 3
    files = list(tmp_path.glob("raw/provider=esef/symbol=ABN.AS/income-annual-*.parquet"))
    assert len(files) == 1  # ONE merged frame — raw newest-only semantics untouched
    raw = pd.read_parquet(files[0])
    assert sorted(raw["period"].astype(str)) == ["2021", "2022", "2023", "2024"]
    assert raw.loc[raw["period"] == "2023", "TotalRevenue"].item() == 999.0  # newest wins
    assert (raw["_history_depth"] == 3).all()
    assert _esef_task_depth(tmp_path, "ABN.AS") == 3


def test_fr010_sweep_depth_gate_requeues_and_then_rests(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    mapping = {"NL0011540547": LEI_ABN}

    shallow = _DeepClient(LEI_ABN)
    assert run_esef_sweep(limit=10, client=shallow, mapping=mapping, history=1)["enriched"] == ["ABN.AS"]
    assert shallow.lei_calls == 0  # history=1 keeps the zero-extra-request path
    assert shallow.json_fetches == 1
    assert _esef_task_depth(tmp_path, "ABN.AS") == 1

    # raising the requested depth makes the fresh filer due again — once
    deep = _DeepClient(LEI_ABN)
    outcome = run_esef_sweep(limit=10, client=deep, mapping=mapping, history=3)
    assert outcome["enriched"] == ["ABN.AS"]
    assert deep.lei_calls == 1 and deep.json_fetches == 3
    files = list(tmp_path.glob("raw/provider=esef/symbol=ABN.AS/income-annual-*.parquet"))
    raw = pd.read_parquet(max(files, key=lambda f: f.name))
    assert sorted(raw["period"].astype(str)) == ["2021", "2022", "2023", "2024"]
    assert _esef_task_depth(tmp_path, "ABN.AS") == 3

    # satisfied depth: the next deep sweep fetches nothing
    rest = _DeepClient(LEI_ABN)
    assert run_esef_sweep(limit=10, client=rest, mapping=mapping, history=3)["enriched"] == []
    assert rest.lei_calls == 0 and rest.json_fetches == 0


def test_fr010_lowering_history_never_discards_backfilled_years(tmp_path, monkeypatch) -> None:
    """`--esef-history 1` after a depth-3 backfill must not forfeit the deep
    audited years: the write path merges over the existing raw and the
    recorded depth is monotone — prune_raw then deletes nothing precious."""
    from crible.ingest.raw import prune_raw
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    mapping = {"NL0011540547": LEI_ABN}
    assert run_esef_sweep(limit=10, client=_DeepClient(LEI_ABN), mapping=mapping, history=3)[
        "enriched"
    ] == ["ABN.AS"]

    # a shallower run while the filer is due again (refresh_seconds=0)
    run_esef_sweep(
        limit=10, client=_DeepClient(LEI_ABN), mapping=mapping, history=1, refresh_seconds=0
    )
    prune_raw(tmp_path)
    files = list(tmp_path.glob("raw/provider=esef/symbol=ABN.AS/income-annual-*.parquet"))
    raw = pd.read_parquet(max(files, key=lambda f: f.name))
    assert sorted(raw["period"].astype(str)) == ["2021", "2022", "2023", "2024"]
    assert _esef_task_depth(tmp_path, "ABN.AS") == 3  # depth never regresses


def test_fr010_legacy_raw_without_depth_column_seeds_as_depth_one(tmp_path, monkeypatch) -> None:
    """Pre-backfill raw files carry no _history_depth column — they must seed
    as legacy depth 1 so the first deep sweep re-enriches them once."""
    import time as _time

    from crible.ingest.raw import write_raw_statement
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    write_raw_statement(
        tmp_path, symbol="ABN.AS", provider="esef", statement_type="income", freq="annual",
        frame=pd.DataFrame({"period": ["2024"], "TotalRevenue": [1.0]}),
        fetched_at=_time.time(),  # fresh — only the depth clause can make it due
    )
    client = _DeepClient(LEI_ABN)
    outcome = run_esef_sweep(limit=10, client=client, mapping={"NL0011540547": LEI_ABN}, history=3)
    assert outcome["enriched"] == ["ABN.AS"]
    assert client.lei_calls == 1
    assert _esef_task_depth(tmp_path, "ABN.AS") == 3


def test_fr010_cycle_depth_gate_requeues_and_then_rests(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_esef_cycle

    _seed_sweep_universe(tmp_path, monkeypatch)
    mapping = {"NL0011540547": LEI_ABN}
    assert run_esef_cycle(limit=10, client=_DeepClient(LEI_ABN), mapping=mapping, history=1)[
        "enriched"
    ] == ["ABN.AS"]
    assert _esef_task_depth(tmp_path, "ABN.AS") == 1

    deep = _DeepClient(LEI_ABN)
    assert run_esef_cycle(limit=10, client=deep, mapping=mapping, history=3)["enriched"] == ["ABN.AS"]
    assert deep.json_fetches == 3
    assert _esef_task_depth(tmp_path, "ABN.AS") == 3

    rest = _DeepClient(LEI_ABN)
    assert run_esef_cycle(limit=10, client=rest, mapping=mapping, history=3)["enriched"] == []
    assert rest.json_fetches == 0


def test_fr010_sweep_depth_survives_a_fresh_operational_db(tmp_path, monkeypatch) -> None:
    """Recorded depth lives in the raw layer (_history_depth), not only in the
    operational DB — a nightly CI run starting blank must not re-backfill
    every filer."""
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    mapping = {"NL0011540547": LEI_ABN}
    first = _DeepClient(LEI_ABN)
    assert run_esef_sweep(limit=10, client=first, mapping=mapping, history=3)["enriched"] == ["ABN.AS"]

    (tmp_path / "crible.duckdb").unlink()
    _seed_sweep_universe(tmp_path, monkeypatch)
    again = _DeepClient(LEI_ABN)
    outcome = run_esef_sweep(limit=10, client=again, mapping=mapping, history=3)
    assert outcome["enriched"] == []
    assert again.lei_calls == 0 and again.json_fetches == 0


def test_fr010_sweep_max_age_zero_refetches_fresh_symbols(tmp_path, monkeypatch) -> None:
    """Backfill mode: refresh_seconds=0 ignores freshness so a widened
    concept map reaches ALREADY-fetched filings without waiting 90 days."""
    from crible.ingest.service import run_esef_sweep

    _seed_sweep_universe(tmp_path, monkeypatch)
    mapping = {"NL0011540547": LEI_ABN}
    assert run_esef_sweep(limit=10, client=FakeIndexClient(), mapping=mapping)["enriched"] == [
        "ABN.AS"
    ]
    redo = run_esef_sweep(limit=10, client=FakeIndexClient(), mapping=mapping, refresh_seconds=0)
    assert redo["enriched"] == ["ABN.AS"]
