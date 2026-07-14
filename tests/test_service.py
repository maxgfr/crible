"""FIX-003 / F1 — the self-hosted `ingest --loop` must keep ONE rolling rate
budget across cycles (NFR-007, 330 req/h), not reset it every cycle.

`run_loop` calls `run_once` each cycle; `run_once` used to build a fresh
`TokenBucket` every call, so the polite hourly budget was reset every few
seconds and busted in steady state (Yahoo bans). The fix lets the caller own a
long-lived budget (and provider) that `run_once` reuses — mirroring the shared
bucket `run_refresh` already relies on.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from crible import config
from crible.ingest.budget import TokenBucket
from crible.ingest.service import run_once
from crible.universe import bootstrap_universe

from tests.test_refresh import FakeYfProvider


def _seed_universe(symbols: list[str]) -> None:
    frame = pd.DataFrame(
        {
            "symbol": symbols,
            "name": symbols,
            "country": ["France"] * len(symbols),
            "sector": ["Industrials"] * len(symbols),
            "industry": ["X"] * len(symbols),
            "exchange": ["PA"] * len(symbols),
            "currency": ["EUR"] * len(symbols),
        }
    )
    con = duckdb.connect(str(config.database_path()))
    bootstrap_universe(con, frame)
    con.close()


@pytest.fixture()
def service_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    config.database_path().parent.mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_run_once_reuses_a_caller_owned_budget(service_env) -> None:
    _seed_universe(["AIR.PA", "MC.PA", "OR.PA", "SAP.DE"])
    # frozen clock → the window never evicts, so accumulation is unambiguous
    budget = TokenBucket(capacity=330, window_seconds=3600, now=lambda: 1000.0)
    provider = FakeYfProvider()

    run_once(limit=2, budget=budget, provider=provider)
    run_once(limit=2, budget=budget, provider=provider)

    # two cycles × two fetches accumulate in ONE window — the loop's budget is
    # not reset each cycle. With the F1 bug the caller's budget is ignored (0).
    assert budget.used_in_window() == 4
    assert len(provider.calls) == 4
