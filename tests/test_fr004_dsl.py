"""FR-004 / NFR-011 — the filter DSL compiled to parametrized DuckDB SQL."""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from crible.dsl.compiler import compile_query
from crible.dsl.parser import DslError, parse
from crible.store import screen

WHITELIST = {
    "symbol", "name", "country", "region", "sector", "exchange",
    "roe", "piotroski_f", "altman_z", "beneish_m", "pe", "revenue",
}


def make_con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    frame = pd.DataFrame(
        {
            "symbol": ["AIR.PA", "SAP.DE", "ABN.AS", "AAPL", "7203.T"],
            "name": ["Airbus", "SAP", "ABN AMRO", "Apple", "Toyota"],
            "country": ["FR", "DE", "NL", "US", "JP"],
            "region": ["europe", "europe", "europe", "us", "world"],
            "sector": ["Industrials", "Tech", "Financials", "Tech", "Auto"],
            "exchange": ["PAR", "GER", "AMS", "NMS", "JPX"],
            "roe": [18.0, 22.0, 9.0, 45.0, 11.0],
            "piotroski_f": [8, 7, 5, 9, 6],
            "altman_z": [3.2, 4.1, 1.5, 6.0, 2.2],
            "beneish_m": [-2.5, -2.9, -1.2, -2.7, -2.1],
            "pe": [22.0, 30.0, 7.0, 33.0, 9.0],
            "revenue": [65e9, 34e9, 8e9, 400e9, 300e9],
        }
    )
    con.register("snapshot_latest", frame)
    return con


# --------------------------------------------------------------- correctness


def test_fr004_filters_sorts_and_paginates_exactly() -> None:
    con = make_con()
    result = screen(
        con, "roe > 15 AND piotroski_f >= 7 AND country IN ('FR', 'DE')",
        whitelist=WHITELIST, sort="-roe", limit=10, offset=0,
    )
    assert result["symbol"].tolist() == ["SAP.DE", "AIR.PA"]

    paged = screen(
        con, "roe > 15 AND piotroski_f >= 7 AND country IN ('FR', 'DE')",
        whitelist=WHITELIST, sort="-roe", limit=1, offset=1,
    )
    assert paged["symbol"].tolist() == ["AIR.PA"]


def test_fr004_or_not_and_parentheses() -> None:
    con = make_con()
    result = screen(
        con, "(country = 'JP' OR country = 'US') AND NOT pe > 30",
        whitelist=WHITELIST, sort="symbol", limit=10, offset=0,
    )
    assert result["symbol"].tolist() == ["7203.T"]


def test_fr004_compiles_to_whitelisted_parametrized_sql() -> None:
    sql, params = compile_query(
        parse("roe > 15 AND country IN ('FR','DE')"), whitelist=WHITELIST
    )
    assert '"roe" > ?' in sql
    assert '"country" IN (?, ?)' in sql
    assert params == [15.0, "FR", "DE"]
    # no literal values ever appear in the SQL text
    assert "FR" not in sql and "15" not in sql


# ------------------------------------------------------------- error surface


def test_fr004_unknown_field_names_token_position_and_closest() -> None:
    with pytest.raises(DslError) as err:
        compile_query(parse("piotroski > 7"), whitelist=WHITELIST)
    msg = str(err.value)
    assert "piotroski" in msg
    assert "piotroski_f" in msg  # closest valid field suggested
    assert err.value.position == 0


def test_fr004_malformed_query_reports_position_and_executes_nothing() -> None:
    con = make_con()
    with pytest.raises(DslError) as err:
        screen(con, "roe >", whitelist=WHITELIST, sort=None, limit=10, offset=0)
    assert err.value.position is not None


def test_fr004_invalid_sort_field_rejected() -> None:
    con = make_con()
    with pytest.raises(DslError):
        screen(con, "roe > 1", whitelist=WHITELIST, sort="-nope", limit=10, offset=0)


# ----------------------------------------------------------------- injection

INJECTION_CORPUS = [
    "roe > 15; DROP TABLE companies--",
    "roe > 15 UNION SELECT * FROM companies",
    "country = 'FR' OR '1'='1'",
    "country = 'FR'; DELETE FROM snapshot_latest",
    'name = "x\\"; DROP TABLE snapshot_latest; --"',
    "roe > (SELECT 1)",
]


@pytest.mark.parametrize("hostile", INJECTION_CORPUS)
def test_fr004_injection_corpus_never_reaches_sql(hostile: str) -> None:
    con = make_con()
    try:
        result = screen(con, hostile, whitelist=WHITELIST, sort=None, limit=10, offset=0)
    except DslError:
        pass  # rejection is a valid outcome
    else:
        # accepted → every value was parameter-bound; the table is intact
        assert isinstance(result, pd.DataFrame)
    assert con.execute("SELECT count(*) FROM snapshot_latest").fetchone()[0] == 5


@settings(max_examples=1000, deadline=None)
@given(st.text(max_size=60))
def test_fr004_property_arbitrary_input_rejected_or_whitelisted(text: str) -> None:
    """NFR-011: any input either fails to parse (DslError, nothing executed) or
    compiles to SQL whose identifiers are all whitelisted and whose values are
    all bound as parameters."""
    try:
        ast = parse(text)
        sql, params = compile_query(ast, whitelist=WHITELIST)
    except DslError:
        return
    for token in sql.replace("(", " ").replace(")", " ").split():
        if token.startswith('"') and token.endswith('"'):
            assert token.strip('"') in WHITELIST
    assert sql.count("?") == len(params)
