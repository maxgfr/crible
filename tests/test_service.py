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


def _frame(symbols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
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


def test_maybe_refresh_universe_refreshes_when_due_and_skips_when_fresh(service_env) -> None:
    """FIX-001 / F5 — the self-hosted loop only bootstrapped once, so new
    listings and delistings froze forever. A periodic (weekly) refresh keeps
    the universe current; it must run only when the interval has elapsed."""
    from crible.ingest.service import maybe_refresh_universe

    con = duckdb.connect(str(config.database_path()))
    bootstrap_universe(con, _frame(["AIR.PA"]))
    calls: list[int] = []

    def fake_fetch() -> pd.DataFrame:
        calls.append(1)
        return _frame(["AIR.PA", "MC.PA"])  # a new listing appeared upstream

    # not due yet → no fetch, timestamp unchanged
    t = maybe_refresh_universe(con, last_refresh=1000.0, now=1000.0 + 3600, fetch=fake_fetch)
    assert t == 1000.0 and calls == []

    # due → refresh runs, the new listing is upserted, queue re-seeded
    t = maybe_refresh_universe(con, last_refresh=1000.0, now=1000.0 + 8 * 86400, fetch=fake_fetch)
    assert t == 1000.0 + 8 * 86400 and len(calls) == 1
    assert con.execute("SELECT count(*) FROM companies").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM crawl_tasks WHERE symbol = 'MC.PA'").fetchone()[0] == 1
    con.close()


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
