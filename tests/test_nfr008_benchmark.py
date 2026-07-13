"""NFR-008 — the normative performance environment: a synthetic full-size
snapshot (~161k rows × ~200 columns). Every preset and a battery of screens
must answer with p95 < 1 s end-to-end. (FR-004 AC-4 points here.)

The bounds are normative for the reference machine. Slower shared CI runners
declare an explicit budget multiplier via CRIBLE_BENCH_FACTOR (ci.yml sets 3)
instead of silently weakening the local contract."""

from __future__ import annotations

import os
import time

import duckdb
import pytest

from crible.presets import PRESETS
from crible.store import screen, whitelist_from_relation

ROWS = 161_000
FILLER_COLUMNS = 180
BENCH_FACTOR = float(os.environ.get("CRIBLE_BENCH_FACTOR", "1"))


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
        bound = 1.0 * BENCH_FACTOR
        assert p95(timings) < bound, f"{preset.id}: p95 {p95(timings):.3f}s ≥ {bound}s"


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
    bound = 1.0 * BENCH_FACTOR
    assert p95(timings) < bound, f"battery p95 {p95(timings):.3f}s ≥ {bound}s"


def test_nfr008_rank_build_cost_bounded_on_full_universe() -> None:
    """FR-015 write-path guard: attach_ranks over the full synthetic universe
    stays bounded (< 5 s) so a compute regression is caught before the crawl."""
    import numpy as np
    import pandas as pd

    from crible.compute.ranks import attach_ranks

    rng = np.random.default_rng(15)
    n = ROWS
    frame = pd.DataFrame(
        {
            "symbol": [f"SYM{i}" for i in range(n)],
            "period": ["2025-12-31"] * n,
            "region": np.take(["europe", "us", "asia", "world"], rng.integers(0, 4, n)),
            "sector": np.take(["Industrials", "Tech", "Financials", "Health", "Energy"], rng.integers(0, 5, n)),
            "piotroski_f": rng.integers(0, 10, n),
            "altman_z": rng.uniform(-1, 7, n),
            "earnings_yield": rng.uniform(-0.05, 0.15, n),
            "price_to_book_ratio": rng.uniform(0.2, 8, n),
            "return_6m": rng.uniform(-0.5, 0.8, n),
        }
    )
    started = time.perf_counter()
    ranked = attach_ranks(frame)
    elapsed = time.perf_counter() - started
    assert ranked["composite_rank"].notna().all()
    bound = 5.0 * BENCH_FACTOR
    assert elapsed < bound, f"attach_ranks on {n} rows took {elapsed:.2f}s ≥ {bound}s"


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
    bound = 0.5 * BENCH_FACTOR
    assert p95(timings) < bound, f"API p95 {p95(timings):.3f}s ≥ {bound}s"
