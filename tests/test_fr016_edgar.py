"""FR-016 — EDGAR enrichment: ticker→CIK resolution, companyfacts parsing
(FY annual frames + discrete-quarter frames, latest-filed wins, capex sign,
YTD dropped), SEC fair-access User-Agent, period alignment with dated
scraped periods, audited provenance.
"""

from __future__ import annotations

import pandas as pd

from crible.compute.reconcile import align_periods
from crible.compute.snapshot import build_snapshot, build_symbol_snapshot
from crible.ingest.raw import write_raw_statement
from crible.providers.edgar import EdgarClient, facts_to_frames, resolve_ciks

from tests.test_fr003_compute import income_frame


def _fact(start, end, val, *, form="10-K", fp="FY", filed="2024-11-01"):
    entry = {"end": end, "val": val, "form": form, "fp": fp, "filed": filed}
    if start is not None:
        entry["start"] = start
    return entry


COMPANYFACTS = {
    "cik": 320193,
    "entityName": "APPLE INC",
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        _fact("2023-10-01", "2024-09-28", 391_035_000_000.0),
                        # an earlier filing of the same period loses to latest-filed
                        _fact("2023-10-01", "2024-09-28", 390_000_000_000.0, filed="2024-10-15"),
                        # a DISCRETE Q4 duration re-reported inside the 10-K → quarterly frame
                        _fact("2024-06-30", "2024-09-28", 94_930_000_000.0),
                        # a discrete 10-Q quarter → quarterly frame (not annual)
                        _fact("2023-10-01", "2023-12-30", 119_575_000_000.0, form="10-Q", fp="Q1"),
                    ]
                },
            },
            "NetIncomeLoss": {
                "units": {"USD": [_fact("2023-10-01", "2024-09-28", 93_736_000_000.0)]}
            },
            "Assets": {"units": {"USD": [_fact(None, "2024-09-28", 364_980_000_000.0)]}},
            "NetCashProvidedByUsedInOperatingActivities": {
                "units": {"USD": [_fact("2023-10-01", "2024-09-28", 118_254_000_000.0)]}
            },
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "units": {"USD": [_fact("2023-10-01", "2024-09-28", 9_447_000_000.0)]}
            },
            "WeightedAverageNumberOfSharesOutstandingBasic": {
                "units": {"shares": [_fact("2023-10-01", "2024-09-28", 15_343_783_000.0)]}
            },
            "ShortTermInvestments": {
                "units": {"USD": [_fact(None, "2024-09-28", 35_228_000_000.0)]}
            },
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest": {
                "units": {"USD": [_fact("2023-10-01", "2024-09-28", 123_485_000_000.0)]}
            },
        }
    },
}


# ------------------------------------------------------------------ directory


def test_fr016_ticker_cik_resolution_matches_and_counts_unmatched() -> None:
    tickers = {"AAPL": 320193, "BRK-B": 1067983}
    companies = [{"symbol": "AAPL"}, {"symbol": "BRK-B"}, {"symbol": "ZZZZ"}]
    resolved, unmatched = resolve_ciks(companies, tickers)
    assert resolved == {"AAPL": 320193, "BRK-B": 1067983}
    # FR-016: unmatched are COUNTED, never errored (the ESEF AC-4 pattern)
    assert unmatched == ["ZZZZ"]


# --------------------------------------------------------------- companyfacts


def test_fr016_companyfacts_map_to_canonical_annual_frames() -> None:
    frames = facts_to_frames(COMPANYFACTS)
    income = frames[("income", "annual")].set_index("period")
    balance = frames[("balance", "annual")].set_index("period")
    cashflow = frames[("cashflow", "annual")].set_index("period")
    # latest-filed wins; the discrete quarters stay OUT of the annual frame
    assert list(income.index) == ["2024-09-28"]
    assert income.loc["2024-09-28", "TotalRevenue"] == 391_035_000_000.0
    assert income.loc["2024-09-28", "NetIncome"] == 93_736_000_000.0
    assert income.loc["2024-09-28", "BasicAverageShares"] == 15_343_783_000.0
    assert balance.loc["2024-09-28", "TotalAssets"] == 364_980_000_000.0
    # short-term investments land under the yfinance vocabulary column
    assert balance.loc["2024-09-28", "OtherShortTermInvestments"] == 35_228_000_000.0
    # pretax income unlocks the canonical EBIT derivation for audited-only US
    assert income.loc["2024-09-28", "PretaxIncome"] == 123_485_000_000.0
    # capex sign flips to the yfinance convention (negative outflow → FCF = ocf + capex)
    assert cashflow.loc["2024-09-28", "CapitalExpenditure"] == -9_447_000_000.0
    assert cashflow.loc["2024-09-28", "OperatingCashFlow"] == 118_254_000_000.0


def test_fr016_companyfacts_emit_discrete_quarterly_frames() -> None:
    """TTM v2: discrete 70-100-day durations (10-Qs + the Q4 re-reported
    inside the 10-K) land in (statement, 'quarterly'); YTD spans are dropped,
    never differenced."""
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            _fact("2023-10-01", "2023-12-30", 100.0, form="10-Q", fp="Q1"),
                            _fact("2023-12-31", "2024-03-30", 110.0, form="10-Q", fp="Q2"),
                            _fact("2024-03-31", "2024-06-29", 120.0, form="10-Q", fp="Q3"),
                            # Q4 discrete duration re-reported inside the 10-K
                            _fact("2024-06-30", "2024-09-28", 130.0),
                            # a 6-month YTD duration MUST be dropped, never differenced
                            _fact("2023-10-01", "2024-03-30", 210.0, form="10-Q", fp="Q2"),
                        ]
                    }
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            _fact("2023-10-01", "2023-12-30", 20.0, form="10-Q", fp="Q1"),
                            _fact("2023-12-31", "2024-03-30", 21.0, form="10-Q", fp="Q2"),
                        ]
                    }
                },
                "PaymentsToAcquirePropertyPlantAndEquipment": {
                    "units": {
                        "USD": [_fact("2023-10-01", "2023-12-30", 5.0, form="10-Q", fp="Q1")]
                    }
                },
            }
        }
    }
    frames = facts_to_frames(facts)
    income = frames[("income", "quarterly")].set_index("period")
    assert list(income.index) == ["2023-12-30", "2024-03-30", "2024-06-29", "2024-09-28"]
    assert income["TotalRevenue"].tolist() == [100.0, 110.0, 120.0, 130.0]  # YTD absent
    cashflow = frames[("cashflow", "quarterly")].set_index("period")
    assert cashflow.loc["2023-12-30", "OperatingCashFlow"] == 20.0
    # capex sign flips in the quarterly frame too
    assert cashflow.loc["2023-12-30", "CapitalExpenditure"] == -5.0
    # balance stays annual-only (point-in-time — the TTM excludes it)
    assert ("balance", "quarterly") not in frames


def test_fr016_first_listed_concept_keeps_the_column() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [_fact("2024-01-01", "2024-12-31", 100.0)]}},
                "SalesRevenueNet": {"units": {"USD": [_fact("2024-01-01", "2024-12-31", 999.0)]}},
            }
        }
    }
    income = facts_to_frames(facts)[("income", "annual")].set_index("period")
    assert income.loc["2024-12-31", "TotalRevenue"] == 100.0


# -------------------------------------------------------------- service cycle


def _seed_universe(tmp_path, monkeypatch) -> None:
    import duckdb as _duckdb

    from crible.universe import bootstrap_universe
    from tests.test_fr001_universe import fixture_frame

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, fixture_frame())
    con.close()


def test_fr016_service_cycle_writes_edgar_raw_and_counts_unmatched(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_edgar_cycle

    _seed_universe(tmp_path, monkeypatch)

    class FakeClient:
        def company_tickers(self):
            raise AssertionError("ticker_map injected — the directory is not re-fetched")

        def companyfacts(self, cik):
            assert cik == 320193
            return COMPANYFACTS

    outcome = run_edgar_cycle(limit=10, client=FakeClient(), ticker_map={"AAPL": 320193})
    assert outcome["enriched"] == ["AAPL"]
    assert outcome["unmatched"] == 0  # AAPL is the fixture's only US listing
    files = list(tmp_path.glob("raw/provider=edgar/symbol=AAPL/*.parquet"))
    assert len(files) == 4  # income + balance + cashflow + quarterly income
    # the fixture's two discrete-quarter revenue facts (the Q1 10-Q and the
    # Q4-inside-10-K) now feed a quarterly income frame instead of being dropped


def test_fr016_service_cycle_outage_records_and_resumes(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_edgar_cycle

    _seed_universe(tmp_path, monkeypatch)

    class DownClient:
        def companyfacts(self, cik):
            raise ConnectionError("data.sec.gov unreachable")

    outcome = run_edgar_cycle(limit=10, client=DownClient(), ticker_map={"AAPL": 320193})
    assert outcome["outage"] is not None
    assert list(tmp_path.glob("raw/provider=edgar/**/*.parquet")) == []  # no partial writes


def test_fr016_directory_outage_is_recorded_not_raised(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_edgar_cycle

    _seed_universe(tmp_path, monkeypatch)

    class DownDirectory:
        def company_tickers(self):
            raise ConnectionError("www.sec.gov unreachable")

    outcome = run_edgar_cycle(limit=10, client=DownDirectory())
    assert outcome["outage"] is not None and "company_tickers" in outcome["outage"]


# ----------------------------------------------------------------------- bulk


def _bulk_zip(tmp_path, members: dict[str, dict]):
    import json
    import zipfile

    path = tmp_path / "companyfacts.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("README.txt", "not a filing")  # ignored
        for name, payload in members.items():
            archive.writestr(name, json.dumps(payload))
    return path


def test_fr016_bulk_ingests_every_resolved_us_issuer(tmp_path, monkeypatch) -> None:
    """ADR-0005 scale-up: one archive → the audited layer for every resolved
    US listing; unresolved CIKs are skipped; the task is marked fetched so
    the per-CIK cycle finds nothing due afterwards."""
    import duckdb as _duckdb

    from crible.ingest.service import run_edgar_bulk, run_edgar_cycle

    _seed_universe(tmp_path, monkeypatch)
    zip_path = _bulk_zip(
        tmp_path,
        {
            "CIK0000320193.json": COMPANYFACTS,
            "CIK0000000001.json": COMPANYFACTS,  # not in the ticker map — skipped
        },
    )
    outcome = run_edgar_bulk(zip_path=zip_path, ticker_map={"AAPL": 320193}, download=False)
    assert outcome["enriched"] == 1
    assert outcome["outage"] is None
    files = list(tmp_path.glob("raw/provider=edgar/symbol=AAPL/*.parquet"))
    assert len(files) == 4  # income + balance + cashflow + quarterly income
    # the fixture's two discrete-quarter revenue facts (the Q1 10-Q and the
    # Q4-inside-10-K) now feed a quarterly income frame instead of being dropped

    con = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    fetched = con.execute(
        "SELECT last_fetched_at FROM edgar_tasks WHERE symbol = 'AAPL'"
    ).fetchone()[0]
    con.close()
    assert fetched is not None

    class NeverCalled:
        def companyfacts(self, cik):
            raise AssertionError("bulk marked AAPL fetched — nothing is due")

    followup = run_edgar_cycle(limit=10, client=NeverCalled(), ticker_map={"AAPL": 320193})
    assert followup["enriched"] == []

    # nightly re-run over the SAME archive: identical data is never
    # re-stamped, so unchanged issuers stay clean for incremental compute
    rerun = run_edgar_bulk(zip_path=zip_path, ticker_map={"AAPL": 320193}, download=False)
    assert rerun["enriched"] == 1  # processed, but…
    assert len(list(tmp_path.glob("raw/provider=edgar/symbol=AAPL/*.parquet"))) == 4  # …no new files


def test_fr016_cycle_freshness_survives_a_fresh_operational_db(tmp_path, monkeypatch) -> None:
    """Same CI amnesia fix as ESEF: a fresh crible.duckdb re-derives
    edgar_tasks freshness from the restored raw layer."""
    from crible.ingest.service import run_edgar_cycle

    _seed_universe(tmp_path, monkeypatch)

    class OneShotClient:
        def companyfacts(self, cik):
            return COMPANYFACTS

    outcome = run_edgar_cycle(limit=10, client=OneShotClient(), ticker_map={"AAPL": 320193})
    assert outcome["enriched"] == ["AAPL"]

    (tmp_path / "crible.duckdb").unlink()
    _seed_universe(tmp_path, monkeypatch)

    class NeverCalled:
        def companyfacts(self, cik):
            raise AssertionError("freshness was re-seeded from raw — nothing is due")

    followup = run_edgar_cycle(limit=10, client=NeverCalled(), ticker_map={"AAPL": 320193})
    assert followup["enriched"] == []


def test_fr016_bulk_without_archive_and_download_disabled_skips(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_edgar_bulk

    _seed_universe(tmp_path, monkeypatch)
    outcome = run_edgar_bulk(
        zip_path=tmp_path / "missing.zip", ticker_map={"AAPL": 320193}, download=False
    )
    assert outcome["skipped"] is not None
    assert list(tmp_path.glob("raw/provider=edgar/**/*.parquet")) == []


def test_fr016_facts_cap_at_eight_fiscal_years() -> None:
    facts = {
        "facts": {
            "us-gaap": {
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            _fact(f"{year}-01-01", f"{year}-12-31", float(year))
                            for year in range(2010, 2026)
                        ]
                    }
                }
            }
        }
    }
    income = facts_to_frames(facts)[("income", "annual")]
    assert len(income) == 8  # bounded history keeps the snapshot publishable
    assert list(income["period"])[0] == "2018-12-31"
    assert list(income["period"])[-1] == "2025-12-31"


# ---------------------------------------------------------------- fair access


def test_fr016_client_sends_declared_user_agent() -> None:
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}

    class FakeHttp:
        def __init__(self):
            self.headers_seen: list[dict] = []

        def get(self, url, headers=None, **_):
            self.headers_seen.append(dict(headers or {}))
            return FakeResponse()

    http = FakeHttp()
    client = EdgarClient(http=http, user_agent="crible-test (test@example.com)")
    assert client.company_tickers() == {"AAPL": 320193}
    assert http.headers_seen[0]["User-Agent"] == "crible-test (test@example.com)"


def test_fr016_sec_user_agent_never_contains_a_url() -> None:
    """The SEC Akamai WAF 403s any User-Agent carrying an http(s) URL — the
    silent-EDGAR-outage root cause. The shipped default must be URL-free, and
    an env value with a URL is stripped defensively."""
    from crible import config

    assert "://" not in config.DEFAULT_SEC_USER_AGENT
    assert "://" not in config.sec_user_agent()


def test_fr016_sec_user_agent_strips_a_url_from_the_env(monkeypatch) -> None:
    from crible import config

    monkeypatch.setenv(
        "CRIBLE_SEC_USER_AGENT", "crible (me@example.com; +https://github.com/x/y)"
    )
    ua = config.sec_user_agent()
    assert "://" not in ua and "github.com" not in ua
    assert ua.startswith("crible") and "me@example.com" in ua


# ---------------------------------------------------------- period alignment


def test_fr016_audited_periods_align_to_dated_scraped_periods() -> None:
    """The Finding-A fix: EDGAR's fiscal end ("2024-09-28") must reconcile
    with yfinance's dated period ("2024-09-30") — same fiscal year."""
    scraped = {
        ("income", "annual"): income_frame(
            {"TotalRevenue": [95.0, 100.0], "NetIncome": [9.0, 10.0]},
            ["2023-09-30", "2024-09-30"],
        ),
    }
    audited = {
        ("income", "annual"): income_frame({"TotalRevenue": [120.0]}, ["2024-09-28"]),
    }
    snapshot = build_symbol_snapshot("AAPL", scraped, audited_frames=audited, computed_at=1.0)
    by_period = snapshot.set_index("period")
    assert by_period.loc["2024-09-30", "revenue"] == 120.0  # audited wins, aligned label
    assert "revenue" in by_period.loc["2024-09-30", "audited_fields"]
    assert "2024-09-28" not in by_period.index  # no phantom extra period


def test_fr016_align_periods_leaves_ambiguous_years_untouched() -> None:
    audited = pd.DataFrame({"revenue": [1.0]}, index=["2024-09-28"])
    scraped_index = pd.Index(["2024-03-31", "2024-09-30"])  # two scraped periods in 2024
    aligned = align_periods(audited, scraped_index)
    assert list(aligned.index) == ["2024-09-28"]  # ambiguous — conservative


# ----------------------------------------------------------------- provenance


def test_fr016_snapshot_provenance_for_audited_only_symbols(tmp_path) -> None:
    frame = pd.DataFrame(
        {"period": ["2024-09-28"], "TotalRevenue": [391.0], "NetIncome": [93.0]}
    )
    write_raw_statement(
        tmp_path, symbol="AAPL", provider="edgar", statement_type="income",
        freq="annual", frame=frame, fetched_at=1_000.0,
    )
    snapshot = build_snapshot(tmp_path, symbols=["AAPL"])
    assert set(snapshot["provider"]) == {"edgar"}  # not mislabeled yfinance
