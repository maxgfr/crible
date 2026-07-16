"""NFR-007 across process boundaries — the rolling budget must survive a run.

The token bucket lives in process memory: two GitHub workflows chained less
than an hour apart would EACH start with an empty window and spend 330
requests — 660/h at the boundary, over Yahoo's tolerance. Persisting the
stamps (wall-clock) in the dataset lets the next run resume the window
exactly where the previous one left it, making back-to-back scheduled crawls
(the marathon plan) safe.
"""

from __future__ import annotations

import json

from crible.ingest.budget import TokenBucket, load_bucket, save_bucket


def test_bucket_state_round_trips_across_a_process_boundary(tmp_path) -> None:
    """Process A spends 5 requests and saves; process B (different monotonic
    origin, 10 wall-clock minutes later) restores and still sees them."""
    path = tmp_path / "budget-state.json"

    a = TokenBucket(capacity=10, window_seconds=3600, now=lambda: 50_000.0)
    assert a.try_acquire(5)
    save_bucket(a, path, wall_now=1_000_000.0)

    b = load_bucket(
        path, capacity=10, window_seconds=3600,
        now=lambda: 3.0, wall_now=1_000_600.0,  # +10 min wall, fresh monotonic
    )
    assert b.used_in_window() == 5
    assert b.try_acquire(5)
    assert not b.try_acquire(1)  # 10/10 — the boundary can NOT double-spend


def test_bucket_state_evicts_stamps_older_than_the_window(tmp_path) -> None:
    path = tmp_path / "budget-state.json"
    a = TokenBucket(capacity=10, window_seconds=3600, now=lambda: 0.0)
    assert a.try_acquire(4)
    save_bucket(a, path, wall_now=1_000_000.0)

    # two hours later the old window is gone — a full budget again
    b = load_bucket(path, capacity=10, window_seconds=3600, wall_now=1_007_200.0)
    assert b.used_in_window() == 0
    assert b.try_acquire(10)


def test_load_bucket_without_state_file_starts_fresh(tmp_path) -> None:
    bucket = load_bucket(tmp_path / "missing.json", capacity=7)
    assert bucket.capacity == 7
    assert bucket.used_in_window() == 0


def test_load_bucket_survives_a_corrupt_state_file(tmp_path) -> None:
    path = tmp_path / "budget-state.json"
    path.write_text("{ not json")
    bucket = load_bucket(path, capacity=7)
    assert bucket.used_in_window() == 0


def test_save_bucket_writes_wall_clock_stamps(tmp_path) -> None:
    path = tmp_path / "budget-state.json"
    bucket = TokenBucket(capacity=5, window_seconds=3600, now=lambda: 100.0)
    bucket.try_acquire(2)
    save_bucket(bucket, path, wall_now=1_000_000.0)

    state = json.loads(path.read_text())
    assert state["stamps"] == [1_000_000.0, 1_000_000.0]
    assert state["window_seconds"] == 3600


def test_run_refresh_persists_then_restores_the_window(tmp_path, monkeypatch) -> None:
    """Two chained refreshes: the second starts with the first one's spending
    already in its window (crawl finds nothing due → its own spend is 0, so a
    non-zero heartbeat can only come from the restored state)."""
    import json

    from crible.ingest.service import run_refresh
    from tests.test_fr001_universe import fixture_frame
    from tests.test_refresh import FakeEdgarDirectory, FakePriceProvider, FakeYfProvider

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CRIBLE_BOOTSTRAP_SAMPLE", "AIR.PA,SAP.DE")
    kwargs = dict(
        deadline_seconds=60, fetch_universe=fixture_frame,
        price_provider=FakePriceProvider(), edgar_client=FakeEdgarDirectory(),
    )

    first = run_refresh(provider=FakeYfProvider(), **kwargs)
    assert first["fetched"] == 8
    state_path = tmp_path / "budget-state.json"
    assert state_path.exists()
    assert len(json.loads(state_path.read_text())["stamps"]) > 0

    second = run_refresh(provider=FakeYfProvider(), **kwargs)
    assert second["fetched"] == 0  # everything fresh — no crawl spend of its own
    heartbeat = json.loads((tmp_path / "status.json").read_text())
    assert heartbeat["requests_last_hour"] > 0  # …restored, not reset


def test_run_once_resumes_and_persists_the_window_when_it_owns_the_budget(tmp_path, monkeypatch) -> None:
    """Two `ingest --once` invocations minutes apart share ONE rolling hour."""
    import json

    from crible.ingest.service import run_once
    from tests.test_refresh import FakeYfProvider
    from tests.test_service import _seed_universe

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    (tmp_path / "crible.duckdb").parent.mkdir(parents=True, exist_ok=True)
    _seed_universe(["AIR.PA", "MC.PA"])

    run_once(limit=1, provider=FakeYfProvider())
    state = json.loads((tmp_path / "budget-state.json").read_text())
    assert len(state["stamps"]) == 1

    run_once(limit=1, provider=FakeYfProvider())
    state = json.loads((tmp_path / "budget-state.json").read_text())
    assert len(state["stamps"]) == 2  # accumulated, not reset
