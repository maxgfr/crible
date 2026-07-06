"""FR-001 — Worldwide universe built from FinanceDatabase.

Unit tests run on fixture frames (no network); the real FinanceDatabase
download path is exercised by the zero-key E2E suite.
"""

import duckdb
import pandas as pd
import pytest

from crible.universe import UniverseSourceError, bootstrap_universe, refresh_universe

FIXTURE_ROWS = [
    # symbol, name, country, sector, industry, exchange, currency, market_cap, isin, delisted
    ("ABN.AS", "ABN AMRO", "Netherlands", "Financials", "Banks", "AMS", "EUR", "Mid Cap", "NL0011540547", False),
    ("AIR.PA", "Airbus", "France", "Industrials", "Aerospace & Defense", "PAR", "EUR", "Large Cap", "NL0000235190", False),
    ("SAP.DE", "SAP", "Germany", "Information Technology", "Software", "GER", "EUR", "Large Cap", "DE0007164600", False),
    ("NESN.SW", "Nestlé", "Switzerland", "Consumer Staples", "Food Products", "EBS", "CHF", "Large Cap", "CH0038863350", False),
    ("BARC.L", "Barclays", "United Kingdom", "Financials", "Banks", "LSE", "GBP", "Large Cap", "GB0031348658", False),
    ("AAPL", "Apple", "United States", "Information Technology", "Hardware", "NMS", "USD", "Large Cap", "US0378331005", False),
    ("7203.T", "Toyota", "Japan", "Consumer Discretionary", "Automobiles", "JPX", "JPY", "Large Cap", "JP3633400001", False),
    ("DEAD.PA", "Delisted SA", "France", "Industrials", "Machinery", "PAR", "EUR", "Small Cap", None, True),
    (None, "No Symbol Corp", "France", "Industrials", "Machinery", "PAR", "EUR", "Small Cap", None, False),
]


def fixture_frame() -> pd.DataFrame:
    return pd.DataFrame(
        FIXTURE_ROWS,
        columns=[
            "symbol", "name", "country", "sector", "industry",
            "exchange", "currency", "market_cap", "isin", "delisted",
        ],
    )


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def test_fr001_bootstrap_loads_universe_with_yahoo_symbols_and_regions(con) -> None:
    report = bootstrap_universe(con, fixture_frame())

    rows = con.execute(
        "SELECT symbol, country, region, crawl_priority FROM companies ORDER BY symbol"
    ).fetchall()
    by_symbol = {r[0]: r for r in rows}

    # the row without a symbol is dropped, everything else lands
    assert report.loaded == 8
    assert len(rows) == 8
    assert None not in by_symbol

    # region tagging: EU/EEA + UK + CH => europe (highest priority tier)
    for sym in ("ABN.AS", "AIR.PA", "SAP.DE", "NESN.SW", "BARC.L"):
        assert by_symbol[sym][2] == "europe"
        assert by_symbol[sym][3] == 0
    assert by_symbol["AAPL"][2] == "us"
    assert by_symbol["AAPL"][3] == 1
    assert by_symbol["7203.T"][2] == "world"
    assert by_symbol["7203.T"][3] == 2

    # every retained row carries the metadata FR-001 promises
    complete = con.execute(
        "SELECT count(*) FROM companies WHERE country IS NOT NULL AND sector IS NOT NULL"
        " AND exchange IS NOT NULL AND region IS NOT NULL"
    ).fetchone()[0]
    assert complete == 8


def test_fr001_bootstrap_is_idempotent_upsert(con) -> None:
    bootstrap_universe(con, fixture_frame())
    first = con.execute("SELECT count(*) FROM companies").fetchone()[0]

    # second run with a renamed company must not duplicate rows and must update
    frame = fixture_frame()
    frame.loc[frame["symbol"] == "AAPL", "name"] = "Apple Inc."
    bootstrap_universe(con, frame)

    assert con.execute("SELECT count(*) FROM companies").fetchone()[0] == first
    assert (
        con.execute("SELECT name FROM companies WHERE symbol = 'AAPL'").fetchone()[0]
        == "Apple Inc."
    )


def test_fr001_unreachable_source_leaves_existing_universe_untouched(con) -> None:
    bootstrap_universe(con, fixture_frame())
    before = con.execute("SELECT count(*) FROM companies").fetchone()[0]

    def failing_fetch() -> pd.DataFrame:
        raise ConnectionError("github unreachable")

    with pytest.raises(UniverseSourceError) as err:
        refresh_universe(con, fetch=failing_fetch)

    assert "FinanceDatabase" in str(err.value)
    assert con.execute("SELECT count(*) FROM companies").fetchone()[0] == before


def test_fr001_bootstrap_rejects_frame_missing_required_columns(con) -> None:
    bad = pd.DataFrame({"symbol": ["X"], "name": ["X Corp"]})
    with pytest.raises(UniverseSourceError):
        bootstrap_universe(con, bad)
    assert con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'companies'"
    ).fetchone()[0] == 0
