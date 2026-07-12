"""NFR-008 — the normative performance environment: a synthetic full-size
snapshot (~161k rows × ~200 columns). Every preset and a battery of screens
must answer with p95 < 1 s end-to-end. (FR-004 AC-4 points here.)"""

from __future__ import annotations

import time

import duckdb
import pytest

from crible.presets import PRESETS
from crible.store import screen, whitelist_from_relation

ROWS = 161_000
FILLER_COLUMNS = 180


@pytest.fixture(scope="module")
def con(tmp_path_factory) -> duckdb.DuckDBPyConnection:
    path = tmp_path_factory.mktemp("bench") / "snapshot.parquet"
    fillers = ",\n".join(
        f"random() * 100 - 50 AS ratio_{i:03d}" for i in range(FILLER_COLUMNS)
    )
    connection = duckdb.connect()
    connection.execute(
        f"""
        COPY (
            SELECT
                'SYM' || i AS symbol,
                '2025' AS period,
                list_extract(['FR','DE','NL','IT','ES','GB','US','JP','CN','BR'], 1 + i % 10) AS country,
                list_extract(['Industrials','Tech','Financials','Health','Energy'], 1 + i % 5) AS sector,
                CAST(floor(random() * 10) AS TINYINT) AS piotroski_f,
                random() * 8 - 1 AS altman_z,
                random() * 4 - 4 AS beneish_m,
                random() * 0.6 - 0.1 AS return_on_equity,
                random() * 40 AS price_to_earnings_ratio,
                random() * 5 AS price_to_book_ratio,
                random() * 3 AS debt_to_equity_ratio,
                random() * 100 AS composite_rank,
                random() * 100 AS quality_rank,
                random() * 100 AS value_rank,
                random() * 100 AS momentum_rank,
                {fillers}
            FROM range({ROWS}) t(i)
        ) TO '{path.as_posix()}' (FORMAT parquet)
        """
    )
    connection.execute(
        f"CREATE VIEW snapshot_latest AS SELECT * FROM read_parquet('{path.as_posix()}')"
    )
    return connection


def p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[max(0, int(len(ordered) * 0.95) - 1)]


def test_nfr008_every_preset_screens_the_full_universe_under_1s(con) -> None:
    whitelist = whitelist_from_relation(con, "snapshot_latest")
    for preset in PRESETS.values():
        timings = []
        for _ in range(5):
            started = time.perf_counter()
            screen(con, preset.dsl, whitelist=whitelist, sort="-piotroski_f", limit=100, offset=0)
            timings.append(time.perf_counter() - started)
        assert p95(timings) < 1.0, f"{preset.id}: p95 {p95(timings):.3f}s ≥ 1s"


def test_nfr008_adhoc_screen_battery_p95_under_1s(con) -> None:
    whitelist = whitelist_from_relation(con, "snapshot_latest")
    queries = [
        "piotroski_f >= 7 AND country IN ('FR','DE') AND return_on_equity > 0.15",
        "(altman_z > 2.99 OR piotroski_f >= 8) AND NOT beneish_m > -1.78",
        "ratio_001 > 0 AND ratio_050 < 10 AND ratio_179 > -20 AND sector = 'Tech'",
        "country IN ('FR','DE','NL','IT','ES','GB') AND debt_to_equity_ratio < 1",
    ]
    timings = []
    for query in queries:
        for _ in range(3):
            started = time.perf_counter()
            rows = screen(con, query, whitelist=whitelist, sort=None, limit=200, offset=0)
            timings.append(time.perf_counter() - started)
        assert rows is not None
    assert p95(timings) < 1.0, f"battery p95 {p95(timings):.3f}s ≥ 1s"


def test_nfr008_api_layer_p95_under_500ms_warm(con, tmp_path_factory, monkeypatch) -> None:
    """FR-006 AC-1 / NFR-001: the API layer itself (FastAPI + engine) answers
    full-universe screens in p95 < 500 ms warm, measured on the synthetic
    full-size snapshot."""
    from fastapi.testclient import TestClient

    from crible.api.main import create_app

    data_dir = tmp_path_factory.mktemp("bench-api")
    (data_dir / "snapshot").mkdir(parents=True)
    con.execute(
        f"COPY (SELECT * FROM snapshot_latest) TO '{(data_dir / 'snapshot' / 'snapshot.parquet').as_posix()}' (FORMAT parquet)"
    )
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(data_dir))
    client = TestClient(create_app())

    client.post("/api/screen", json={"query": "piotroski_f >= 7"})  # warm-up
    timings = []
    for _ in range(5):
        started = time.perf_counter()
        response = client.post(
            "/api/screen",
            json={"query": "piotroski_f >= 7 AND country IN ('FR','DE')", "page_size": 100},
        )
        timings.append(time.perf_counter() - started)
        assert response.status_code == 200 and response.json()["total"] > 0
    assert p95(timings) < 0.5, f"API p95 {p95(timings):.3f}s ≥ 500ms"
