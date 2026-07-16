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


# --- the cap table: precedence, EUR conversion, carryover -------------------

NOW = 1_800_000_000.0  # 2027-01-15 — fixture asofs are relative to this
FRESH = "2027-01-10"
STALE = "2026-10-01"
RATES = {"USD": 1.10, "KRW": 1500.0}


def _uni(rows) -> pd.DataFrame:
    defaults = {"isin": None, "country": "US", "market_cap_class": None}
    return pd.DataFrame([{**defaults, "symbol": r.pop("symbol"), **r} for r in rows])


def _census(rows) -> pd.DataFrame:
    defaults = {"census_isin": None, "market_cap": float("nan"), "currency": "USD",
                "census_volume": float("nan"), "census_country": "america", "cap_asof": FRESH}
    return pd.DataFrame([{**defaults, "symbol": r.pop("symbol"), **r} for r in rows])


def test_cap_precedence_census_snapshot_carryover() -> None:
    from crible.universe_caps import build_cap_table

    universe = _uni([{"symbol": "FRESH"}, {"symbol": "STALE"}, {"symbol": "PREV"},
                     {"symbol": "NONE"}])
    census = _census([
        {"symbol": "FRESH", "market_cap": 110.0},
        {"symbol": "STALE", "market_cap": 220.0, "cap_asof": STALE},
    ])
    snaps = pd.DataFrame(
        [{"symbol": "STALE", "snap_cap": 330.0, "snap_currency": "USD", "snap_asof": "2027-01-05"}]
    )
    previous = pd.DataFrame(
        [{"symbol": "PREV", "cap_eur": 42.0, "cap_asof": "2026-06-30",
          "cap_source": "tradingview", "top10k": True}]
    )
    caps = build_cap_table(universe, census, snaps, previous, RATES, NOW).set_index("symbol")

    assert caps.loc["FRESH", "cap_source"] == "tradingview"
    assert round(caps.loc["FRESH", "cap_eur"], 6) == 100.0  # 110 USD / 1.10
    assert caps.loc["STALE", "cap_source"] == "snapshot"  # stale census loses
    assert caps.loc["STALE", "cap_eur"] == 300.0
    assert caps.loc["PREV", "cap_source"] == "carryover"
    assert caps.loc["PREV", "cap_asof"] == "2026-06-30"  # original asof travels
    assert pd.isna(caps.loc["NONE", "cap_source"])
    assert pd.isna(caps.loc["NONE", "cap_eur"])


def test_missing_rate_yields_null_never_imputed() -> None:
    from crible.universe_caps import build_cap_table

    universe = _uni([{"symbol": "X.BK"}])
    census = _census([{"symbol": "X.BK", "market_cap": 1e9, "currency": "THB"}])
    caps = build_cap_table(universe, census, None, None, RATES, NOW).set_index("symbol")
    assert pd.isna(caps.loc["X.BK", "cap_eur"]) and pd.isna(caps.loc["X.BK", "cap_source"])


def test_grouping_prefers_universe_isin_then_census_then_symbol() -> None:
    from crible.universe_caps import build_cap_table

    universe = _uni([
        {"symbol": "A.PA", "isin": "FR001"},
        {"symbol": "B.DE", "isin": None},          # census ISIN fills in
        {"symbol": "C.MI", "isin": None},          # no ISIN anywhere
    ])
    census = _census([
        {"symbol": "B.DE", "census_isin": "FR001", "market_cap": 1.0},
    ])
    caps = build_cap_table(universe, census, None, None, RATES, NOW).set_index("symbol")
    assert caps.loc["A.PA", "company_group"] == "FR001"
    assert caps.loc["B.DE", "company_group"] == "FR001"  # deduped with A.PA
    assert caps.loc["C.MI", "company_group"] == "sym:C.MI"


def test_primary_listing_tie_breaks() -> None:
    from crible.universe_caps import build_cap_table, pick_primary

    universe = _uni([
        # one group across two countries: the home venue beats the foreign one
        {"symbol": "SAP.DE", "isin": "DE001", "country": "DE"},
        {"symbol": "SAPUS", "isin": "DE001", "country": "DE"},
        # one group, two same-country venues: TV caps are the COMPANY's (equal
        # across venues) → volume decides, then symbol asc
        {"symbol": "AA.L", "isin": "GB001", "country": "GB"},
        {"symbol": "AB.L", "isin": "GB001", "country": "GB"},
    ])
    census = _census([
        {"symbol": "SAP.DE", "market_cap": 100.0, "census_country": "germany"},
        {"symbol": "SAPUS", "market_cap": 100.0, "census_country": "america",
         "census_volume": 999.0},
        {"symbol": "AA.L", "market_cap": 50.0, "census_country": "uk"},
        {"symbol": "AB.L", "market_cap": 50.0, "census_country": "uk",
         "census_volume": 10.0},
    ])
    caps = pick_primary(build_cap_table(universe, census, None, None, RATES, NOW))
    primaries = set(caps.loc[caps["primary_listing"], "symbol"])
    assert "SAP.DE" in primaries and "SAPUS" not in primaries  # home beats volume
    assert "AB.L" in primaries and "AA.L" not in primaries  # volume breaks the cap tie
    assert caps.groupby("company_group")["primary_listing"].sum().eq(1).all()


def test_top10k_hysteresis_and_class_floor(monkeypatch) -> None:
    import crible.universe_caps as uc

    monkeypatch.setattr(uc, "TOP10K_SIZE", 2)
    monkeypatch.setattr(uc, "TOP10K_EXIT_RANK", 3)

    universe = _uni([
        {"symbol": "R1"}, {"symbol": "R2"}, {"symbol": "R3"}, {"symbol": "R4"},
        {"symbol": "FLOOR", "market_cap_class": "Mega Cap"},
        {"symbol": "TINY", "market_cap_class": "Nano Cap"},
    ])
    census = _census([
        {"symbol": "R1", "market_cap": 400.0}, {"symbol": "R2", "market_cap": 300.0},
        {"symbol": "R3", "market_cap": 200.0}, {"symbol": "R4", "market_cap": 100.0},
    ])
    caps = uc.pick_primary(uc.build_cap_table(universe, census, None, None, RATES, NOW))

    # no previous members: strict top-2 + the cap-less Mega floor
    first = uc.assign_top10k(caps, previous_members=set()).set_index("symbol")
    assert list(first.loc[["R1", "R2", "R3", "R4"], "top10k"]) == [True, True, False, False]
    assert first.loc["FLOOR", "top10k"] and first.loc["FLOOR", "_floor"]
    assert not first.loc["TINY", "top10k"]
    assert first.loc["R3", "cap_rank_global"] == 3

    # R3 was a member → stays at rank 3 (≤ exit bound); R4 stays out
    second = uc.assign_top10k(caps, previous_members={"R3", "R4"}).set_index("symbol")
    assert second.loc["R3", "top10k"]
    assert not second.loc["R4", "top10k"]  # rank 4 > exit bound even as a previous member


def test_apply_cap_census_end_to_end(tmp_path, monkeypatch) -> None:
    """Census parquet on disk → cap layer + membership + priority override in
    companies; the queue re-seed propagates it; a fresh DB carries the
    membership over through the exported universe.parquet."""
    import time as _time
    from datetime import date

    import crible.universe_caps as uc
    from crible.ingest.queue import CrawlQueue
    from crible.ingest.service import prioritize_sample

    monkeypatch.setattr(uc, "TOP10K_SIZE", 1)
    monkeypatch.setattr(uc, "TOP10K_EXIT_RANK", 1)

    con = duckdb.connect()
    frame = pd.DataFrame([
        {"symbol": "TOP.PA", "name": "Top", "country": "France", "sector": "T",
         "industry": "T", "exchange": "PAR", "currency": "EUR",
         "market_cap": "Mega Cap", "isin": "FR001"},
        {"symbol": "MID.DE", "name": "Mid", "country": "Germany", "sector": "T",
         "industry": "T", "exchange": "GER", "currency": "EUR",
         "market_cap": "Nano Cap", "isin": "DE001"},
        {"symbol": "NOCAP", "name": "No", "country": "United States", "sector": "T",
         "industry": "T", "exchange": "NMS", "currency": "USD",
         "market_cap": None, "isin": None},
    ])
    bootstrap_universe(con, frame)

    (tmp_path / "caps").mkdir(parents=True)
    asof = date.today().isoformat()
    pd.DataFrame([
        {"symbol": "TOP.PA", "isin": "FR001", "market_cap": 1e12, "currency": "EUR",
         "volume": 1.0, "country": "france", "asof": asof},
        {"symbol": "MID.DE", "isin": "DE001", "market_cap": 10.0, "currency": "EUR",
         "volume": 1.0, "country": "germany", "asof": asof},
    ]).to_parquet(tmp_path / "caps" / "tradingview.parquet", index=False)

    report = uc.apply_cap_census(con, tmp_path, rates={}, now=_time.time())
    assert report is not None and report.member_groups == 1 and report.ranked_groups == 2

    rows = dict(con.execute(
        "SELECT symbol, crawl_priority FROM companies"
    ).fetchall())
    assert rows["TOP.PA"] == 0          # rank-1 member primary → tier 0
    assert rows["MID.DE"] == 0 + 5 + 8  # europe nano, shifted base
    assert rows["NOCAP"] == 8 + 6 + 8   # us unknown-class, shifted base
    top = con.execute("SELECT top10k, cap_eur FROM companies WHERE symbol='TOP.PA'").fetchone()
    assert top == (True, 1e12)

    # the queue re-seed copies the override and keeps the -1 sentinel
    queue = CrawlQueue(con)
    prioritize_sample(con, ["NOCAP"])
    queue.seed_from_universe()
    task_prio = dict(con.execute("SELECT symbol, priority FROM crawl_tasks").fetchall())
    assert task_prio["TOP.PA"] == 0 and task_prio["NOCAP"] == -1

    # carryover: export → fresh DB, census file gone → membership survives
    export_universe_parquet(con, tmp_path)
    (tmp_path / "caps" / "tradingview.parquet").unlink()
    fresh = duckdb.connect()
    bootstrap_universe(fresh, frame)  # nightly re-bootstrap resets priorities
    report2 = uc.apply_cap_census(fresh, tmp_path, rates={}, now=_time.time())
    assert report2 is not None and report2.member_groups == 1
    carried = fresh.execute(
        "SELECT top10k, cap_source, crawl_priority FROM companies WHERE symbol='TOP.PA'"
    ).fetchone()
    assert carried == (True, "carryover", 0)


def test_apply_cap_census_is_a_noop_before_any_census(tmp_path) -> None:
    from crible.universe_caps import apply_cap_census

    con = duckdb.connect()
    bootstrap_universe(con, _fd_frame())
    before = con.execute("SELECT crawl_priority FROM companies").fetchone()
    assert apply_cap_census(con, tmp_path, rates={}) is None
    assert con.execute("SELECT crawl_priority FROM companies").fetchone() == before


def test_top10k_stats_counts_groups_not_listings(tmp_path) -> None:
    """Coverage is per COMPANY: one served listing covers its whole group."""
    from datetime import date

    from crible.ingest.raw import write_raw_statement
    from crible.ingest.service import _top10k_stats

    con = duckdb.connect()
    con.execute(SCHEMA)
    rows = [
        # group G1: two listings, only A.PA has audited raw
        ("A.PA", "G1", 1, True, True), ("A.F", "G1", 1, False, True),
        # group G2: priced via the distillate, floor member (no rank)
        ("B.DE", "G2", None, True, True),
        # non-member: never counted
        ("C.MI", "G3", 500, True, False),
    ]
    for symbol, group, rank, primary, member in rows:
        con.execute(
            "INSERT INTO companies (symbol, region, crawl_priority, company_group,"
            " cap_rank_global, primary_listing, top10k, cap_asof, cap_source)"
            " VALUES (?, 'europe', 1, ?, ?, ?, ?, ?, 'tradingview')",
            [symbol, group, rank, primary, member, date.today().isoformat()],
        )
    write_raw_statement(
        tmp_path, symbol="A.PA", provider="edgar", statement_type="income",
        freq="annual", frame=pd.DataFrame({"period": ["2025"], "TotalRevenue": [1.0]}),
        fetched_at=1.0,
    )
    pd.DataFrame(
        [{"symbol": "B.DE", "close": 5.0, "price_asof": date.today().isoformat(),
          "source": "tradingview", "imported_at": 1.0}]
    ).to_parquet(tmp_path / "prices-latest.parquet", index=False)

    block = _top10k_stats(con, tmp_path)["coverage_top10k"]
    assert block["total_groups"] == 2 and block["listings"] == 3
    assert block["fundamentals_covered"] == 1 and block["audited_covered"] == 1
    assert block["priced"] == 1 and block["price_fresh_7d"] == 1
    assert block["unranked_mega_large"] == 1  # G2 has no rank → floor report
    assert block["fundamentals_covered_pct"] == 50.0 and block["priced_pct"] == 50.0


def test_check_coverage_gates_on_the_block(tmp_path, monkeypatch) -> None:
    import json

    from typer.testing import CliRunner

    from crible.cli import app

    runner = CliRunner()
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))

    # exit 2: no block at all (alarming once the pipeline is wired)
    assert runner.invoke(app, ["check-coverage"]).exit_code == 2

    block = {"total_groups": 2, "fundamentals_covered_pct": 50.0, "priced_pct": 50.0}
    (tmp_path / "status.json").write_text(json.dumps({"coverage_top10k": block}))
    ok = runner.invoke(app, ["check-coverage", "--min-fundamentals", "40", "--min-priced", "40"])
    assert ok.exit_code == 0, ok.output
    below = runner.invoke(app, ["check-coverage", "--min-fundamentals", "60", "--min-priced", "40"])
    assert below.exit_code == 1
    assert "below threshold" in below.output


def test_no_ranking_means_no_floor_and_no_members() -> None:
    from crible.universe_caps import assign_top10k, build_cap_table, pick_primary

    universe = _uni([{"symbol": "A", "market_cap_class": "Mega Cap"}, {"symbol": "B"}])
    caps = pick_primary(build_cap_table(universe, None, None, None, RATES, NOW))
    out = assign_top10k(caps, previous_members=set())
    assert not out["top10k"].any()  # pre-census: guaranteed no-op
