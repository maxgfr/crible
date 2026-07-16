"""Top-10k global companies — cap census schema, dedup, slice, priority.

The companies table carries the numeric-cap layer (cap_eur/company_group/
primary_listing/cap_rank_global/top10k); these tests pin the schema
migration and the BY NAME restore that keeps old last-good parquets loading.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from crible.universe import (
    SCHEMA,
    bootstrap_universe,
    ensure_cap_columns,
    export_universe_parquet,
    restore_universe_from_parquet,
)

OLD_SCHEMA = """
CREATE TABLE companies (
    symbol           VARCHAR PRIMARY KEY,
    name             VARCHAR,
    isin             VARCHAR,
    country          VARCHAR,
    country_name     VARCHAR,
    region           VARCHAR NOT NULL,
    crawl_priority   TINYINT NOT NULL,
    sector           VARCHAR,
    industry         VARCHAR,
    exchange         VARCHAR,
    currency         VARCHAR,
    market_cap_class VARCHAR,
    delisted         BOOLEAN DEFAULT FALSE,
    updated_at       TIMESTAMP DEFAULT now()
)
"""


def _fd_frame(symbols=("AAPL",)) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"symbol": s, "name": s, "country": "United States", "sector": "T",
             "industry": "T", "exchange": "NMS", "currency": "USD",
             "market_cap": "Mega Cap", "isin": None}
            for s in symbols
        ]
    )


def test_restore_accepts_an_old_schema_parquet(tmp_path) -> None:
    """The first nightly after a schema widening restores a last-good
    universe.parquet written by the OLD code — BY NAME, never positional."""
    old = duckdb.connect()
    old.execute(OLD_SCHEMA)
    old.execute(
        "INSERT INTO companies (symbol, region, crawl_priority) VALUES ('AAPL', 'us', 8)"
    )
    old.execute(f"COPY companies TO '{(tmp_path / 'universe.parquet').as_posix()}' (FORMAT parquet)")

    fresh = duckdb.connect()
    assert restore_universe_from_parquet(fresh, tmp_path / "universe.parquet") == 1
    cap_eur, top10k = fresh.execute("SELECT cap_eur, top10k FROM companies").fetchone()
    assert cap_eur is None
    assert top10k in (False, None)  # widened column: default or NULL, never an error


def test_cap_columns_round_trip_through_the_parquet(tmp_path) -> None:
    con = duckdb.connect()
    bootstrap_universe(con, _fd_frame())
    con.execute(
        "UPDATE companies SET cap_eur = 1e12, cap_source = 'tradingview',"
        " company_group = 'g1', primary_listing = TRUE, cap_rank_global = 1,"
        " top10k = TRUE WHERE symbol = 'AAPL'"
    )
    export_universe_parquet(con, tmp_path)

    fresh = duckdb.connect()
    restore_universe_from_parquet(fresh, tmp_path / "universe.parquet")
    row = fresh.execute(
        "SELECT cap_eur, cap_source, company_group, primary_listing,"
        " cap_rank_global, top10k FROM companies"
    ).fetchone()
    assert row == (1e12, "tradingview", "g1", True, 1, True)


def test_rebootstrap_never_clobbers_the_cap_layer() -> None:
    """The nightly upsert refreshes FinanceDatabase fields; the census layer
    is deliberately absent from its SET list."""
    con = duckdb.connect()
    bootstrap_universe(con, _fd_frame())
    con.execute("UPDATE companies SET cap_eur = 5.0, top10k = TRUE WHERE symbol = 'AAPL'")
    bootstrap_universe(con, _fd_frame())  # nightly re-run
    assert con.execute("SELECT cap_eur, top10k FROM companies").fetchone() == (5.0, True)


def test_ensure_cap_columns_migrates_a_live_table() -> None:
    con = duckdb.connect()
    con.execute(OLD_SCHEMA)
    ensure_cap_columns(con)
    columns = {r[0] for r in con.execute("DESCRIBE companies").fetchall()}
    assert {"cap_eur", "company_group", "primary_listing", "cap_rank_global", "top10k"} <= columns
    ensure_cap_columns(con)  # idempotent


def test_new_schema_matches_ensure_columns() -> None:
    con = duckdb.connect()
    con.execute(SCHEMA)
    before = con.execute("DESCRIBE companies").fetchall()
    ensure_cap_columns(con)
    assert con.execute("DESCRIBE companies").fetchall() == before
