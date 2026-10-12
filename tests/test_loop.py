"""The `ingest --loop` service, offline: a table-driven scheduler on an
injected clock. Every task runs on its own interval, a task that raises
never stops the others, and the loop shares run_refresh's stages (universe
export, prune, deferral, heartbeat after compute)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from crible import config
from crible.ingest.service import LoopTask, Scheduler, run_loop

from tests.test_fr001_universe import fixture_frame
from tests.test_refresh import FakePriceProvider, FakeYfProvider


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.t = start
        self.slept: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def test_scheduler_runs_each_task_on_its_interval() -> None:
    clock = FakeClock()
    runs: list[tuple[str, float]] = []
    scheduler = Scheduler(
        [
            LoopTask("hourly", 3600, lambda: runs.append(("hourly", clock.t))),
            LoopTask("daily", 86400, lambda: runs.append(("daily", clock.t))),
        ],
        clock=clock.now,
    )
    for _ in range(5):  # five ticks, 30 minutes apart
        scheduler.run_due()
        clock.t += 1800
    assert [name for name, _ in runs].count("hourly") == 3  # t0, +1h, +2h
    assert [name for name, _ in runs].count("daily") == 1


def test_scheduler_survives_a_raising_task() -> None:
    clock = FakeClock()
    runs: list[str] = []

    def boom() -> None:
        raise RuntimeError("upstream down")

    scheduler = Scheduler(
        [LoopTask("broken", 60, boom), LoopTask("healthy", 60, lambda: runs.append("ok"))], clock=clock.now
    )
    outcome = scheduler.run_due()
    assert runs == ["ok"]
    assert "upstream down" in outcome["broken"]["outage"]
    clock.t += 61
    scheduler.run_due()
    assert runs == ["ok", "ok"]  # the broken task does not block the next tick


def test_scheduler_first_run_can_be_deferred() -> None:
    clock = FakeClock()
    runs: list[str] = []
    scheduler = Scheduler(
        [LoopTask("universe", 7 * 86400, lambda: runs.append("u"), last=clock.t)], clock=clock.now
    )
    scheduler.run_due()
    assert runs == []  # just bootstrapped — next refresh a week out


@pytest.fixture()
def loop_env(tmp_path, monkeypatch):
    """A first boot, fully offline: fixture universe, fake Yahoo, no network
    reference data (GLEIF/FX/ESEF/EDGAR stubbed)."""
    import crible.ingest.service as service

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CRIBLE_BOOTSTRAP_SAMPLE", "AIR.PA,SAP.DE")
    calls: dict[str, int] = {}

    def stub(name, value=None):
        def fn(*args, **kwargs):
            calls[name] = calls.get(name, 0) + 1
            return value if value is not None else {"enriched": [], "outage": None}

        return fn

    monkeypatch.setattr(service, "run_esef_cycle", stub("esef"))
    monkeypatch.setattr(service, "run_edgar_cycle", stub("edgar"))
    monkeypatch.setattr("crible.providers.gleif.fetch_gleif", stub("gleif", tmp_path / "none"))
    monkeypatch.setattr("crible.providers.fx.fetch_rates", stub("fx", {}))
    return tmp_path, calls


def test_run_loop_offline_two_ticks(loop_env) -> None:
    data, calls = loop_env
    clock = FakeClock()
    run_loop(
        max_ticks=2,
        clock=clock.now,
        sleep=clock.sleep,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        fetch_universe=fixture_frame,
    )
    # the shared stages the loop used to lack
    assert (data / "universe.parquet").exists()
    assert (data / "snapshot" / "snapshot.parquet").exists()
    heartbeat = json.loads((data / "status.json").read_text())
    assert heartbeat["providers"]["yfinance"] == "healthy"
    assert "coverage_pct" in heartbeat
    # reference data once, not every tick
    assert calls["gleif"] == 1 and calls["fx"] == 1
    assert calls["esef"] == 1 and calls["edgar"] == 1


def test_run_loop_keeps_going_when_a_stage_raises(loop_env, monkeypatch) -> None:
    import crible.ingest.service as service

    data, _ = loop_env

    def broken(*args, **kwargs):
        raise RuntimeError("edgar exploded")

    monkeypatch.setattr(service, "run_edgar_cycle", broken)
    clock = FakeClock()
    run_loop(
        max_ticks=2,
        clock=clock.now,
        sleep=clock.sleep,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        fetch_universe=fixture_frame,
    )
    assert (data / "snapshot" / "snapshot.parquet").exists()
    heartbeat = json.loads((data / "status.json").read_text())
    assert heartbeat["providers"]["edgar"] == "outage"


def test_run_loop_resumes_the_saved_budget(loop_env) -> None:
    """A restart must not double-spend the rolling hour."""
    import time as _time

    data, _ = loop_env
    data.mkdir(exist_ok=True)
    stamps = [_time.time() - 60] * 100
    (data / "budget-state.json").write_text(json.dumps({"window_seconds": 3600, "stamps": stamps}))
    clock = FakeClock(start=_time.time())
    run_loop(
        max_ticks=1,
        clock=clock.now,
        sleep=clock.sleep,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        fetch_universe=fixture_frame,
    )
    heartbeat = json.loads((data / "status.json").read_text())
    assert heartbeat["requests_last_hour"] >= 100
    assert config.data_dir() == data
    assert isinstance(pd.read_parquet(data / "universe.parquet"), pd.DataFrame)


def test_run_loop_computes_right_after_an_on_demand_fetch(loop_env, monkeypatch) -> None:
    """A user-requested symbol is published before the tick's crawl cycle
    (which may wait an hour on the token bucket)."""
    import crible.ingest.service as service
    from crible.ingest.requests import request_fetch

    data, _ = loop_env
    order: list[str] = []
    original_compute, original_once = service.run_compute, service.run_once
    monkeypatch.setattr(service, "run_compute", lambda: (order.append("compute"), original_compute())[1])

    def tracked_once(*args, **kwargs):
        order.append("targeted" if kwargs.get("symbols") else "cycle")
        return original_once(*args, **kwargs)

    monkeypatch.setattr(service, "run_once", tracked_once)
    run_loop(
        max_ticks=1,
        clock=FakeClock().now,
        sleep=lambda s: None,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        fetch_universe=fixture_frame,
    )
    request_fetch(data, "AIR.PA")
    order.clear()
    run_loop(
        max_ticks=1,
        clock=FakeClock().now,
        sleep=lambda s: None,
        provider=FakeYfProvider(),
        price_provider=FakePriceProvider(),
        fetch_universe=fixture_frame,
    )
    assert order[:3] == ["targeted", "compute", "cycle"]
