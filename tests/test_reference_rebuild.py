"""Incremental compute and the reference data a base row bakes in.

A kept row was rebuilt only when its raw files or its price distillate moved.
The per-symbol stage also reads the ECB rates, the listing currency, the
statements' currency mirror and the split events — none of which moved a raw
stamp. Measured on the published dataset against a full rebuild: 4,417 rows
with another market cap (ADIL off by exactly its 25:1 split), 1,141 rows
without the reporting currency the mirror had since supplied.

Every reference input a row depends on is now recorded with the base; a
symbol whose inputs moved is dirty like one whose raw moved.
"""

from __future__ import annotations

import json
import time

import pandas as pd
import pytest

import crible.compute.snapshot as snap
from crible.ingest.raw import write_raw_statement


def _company(data_dir, symbol: str, *, currency: str | None = "USD", close: float = 50.0) -> None:
    """One priced company: statements (tagged with their currency) + bars."""
    statements = {
        "income": {
            "TotalRevenue": [900.0, 1000.0],
            "NetIncome": [90.0, 100.0],
            "BasicAverageShares": [10.0, 10.0],
        },
        "balance": {"StockholdersEquity": [450.0, 500.0], "TotalAssets": [900.0, 1000.0]},
    }
    for statement, values in statements.items():
        frame = pd.DataFrame({"period": ["2024-12-31", "2025-12-31"], **values})
        if currency:
            frame["_currency"] = currency
        write_raw_statement(
            data_dir,
            symbol=symbol,
            provider="yfinance",
            statement_type=statement,
            freq="annual",
            frame=frame,
            fetched_at=1000.0,
        )
    write_raw_statement(
        data_dir,
        symbol=symbol,
        provider="yfinance",
        statement_type="prices",
        freq="daily",
        frame=pd.DataFrame({"Date": ["2026-03-02", "2026-03-03"], "Close": [close, close]}),
        fetched_at=1000.0,
    )


def _universe(data_dir, currencies: dict[str, str]) -> None:
    pd.DataFrame({"symbol": list(currencies), "currency": list(currencies.values())}).to_parquet(
        data_dir / "universe.parquet"
    )


def _rates(data_dir, rates: dict[str, float]) -> None:
    path = data_dir / "mirror" / "fx" / "rates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rates": rates}))


def _splits(data_dir, events: list[tuple[str, str, str]]) -> None:
    path = data_dir / "events" / "defeatbeta-splits.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(events, columns=["symbol", "date", "split_factor"]).to_parquet(path)


@pytest.fixture()
def rebuilt(monkeypatch):
    """The symbols handed to the per-symbol stage, call by call."""
    calls: list[list[str]] = []
    original = snap.build_symbol_rows

    def spy(data_dir, symbols, **kwargs):
        calls.append(sorted(symbols))
        return original(data_dir, symbols, **kwargs)

    monkeypatch.setattr(snap, "build_symbol_rows", spy)
    return calls


def _latest(snapshot: pd.DataFrame, symbol: str) -> pd.Series:
    return snapshot[snapshot["symbol"] == symbol].sort_values("period").iloc[-1]


def test_rates_that_arrive_after_the_base_rebuild_the_listings_they_price(tmp_path, rebuilt) -> None:
    """A base built before the FX mirror exists: the EUR line of a USD filer
    has no price in dollars, so no multiple. The mirror arrives — that row
    must be rebuilt, and only that one."""
    _company(tmp_path, "DOM", currency="USD")
    _company(tmp_path, "FOR.DE", currency="USD")
    _universe(tmp_path, {"DOM": "USD", "FOR.DE": "EUR"})
    first = snap.publish_incremental(tmp_path)
    assert pd.isna(_latest(first, "FOR.DE")["market_cap"])  # no rate → no mixed-currency multiple
    assert _latest(first, "DOM")["market_cap"] == pytest.approx(500.0)

    rebuilt.clear()
    _rates(tmp_path, {"USD": 1.25})
    second = snap.publish_incremental(tmp_path)
    assert rebuilt == [["FOR.DE"]]
    assert _latest(second, "FOR.DE")["market_cap"] == pytest.approx(50.0 * 1.25 * 10)
    assert _latest(second, "DOM")["market_cap"] == pytest.approx(500.0)

    rebuilt.clear()
    assert snap.publish_incremental(tmp_path) is None  # settled
    assert rebuilt == []


def test_a_rate_that_drifts_rebuilds_past_the_tolerance_only(tmp_path, rebuilt) -> None:
    """Rates move every day. Rebuilding every cross-currency row nightly would
    cost a tenth of a full build for a fraction of a percent: a row is rebuilt
    once the factor it was built with is more than 1 % off."""
    _company(tmp_path, "FOR.DE", currency="USD")
    _universe(tmp_path, {"FOR.DE": "EUR"})
    _rates(tmp_path, {"USD": 1.25})
    first = snap.publish_incremental(tmp_path)
    assert _latest(first, "FOR.DE")["market_cap"] == pytest.approx(625.0)

    rebuilt.clear()
    _rates(tmp_path, {"USD": 1.2550})  # +0.4 %
    snap.publish_incremental(tmp_path)
    assert rebuilt == []

    _rates(tmp_path, {"USD": 1.30})  # +4 % against the factor the row holds
    third = snap.publish_incremental(tmp_path)
    assert rebuilt == [["FOR.DE"]]
    assert _latest(third, "FOR.DE")["market_cap"] == pytest.approx(650.0)


def test_a_split_file_that_lands_later_rebases_the_market_cap(tmp_path, rebuilt) -> None:
    """ADIL on the published dataset: the split events arrived after its row
    was built, and the market cap stayed 25× too small."""
    _company(tmp_path, "ADIL", close=2.0)
    _company(tmp_path, "OTHER")
    first = snap.publish_incremental(tmp_path)
    assert _latest(first, "ADIL")["market_cap"] == pytest.approx(20.0)

    rebuilt.clear()
    _splits(tmp_path, [("ADIL", "2026-02-10", "25:1")])
    second = snap.publish_incremental(tmp_path)
    assert rebuilt == [["ADIL"]]
    assert _latest(second, "ADIL")["market_cap"] == pytest.approx(2.0 * 25 * 10)


def test_a_statement_currency_the_mirror_supplies_later_reaches_the_row(tmp_path, rebuilt) -> None:
    """1,141 published rows had no reporting currency although the mirror
    knew it: they predated the mirror and nothing ever rebuilt them."""
    _company(tmp_path, "BREN.JK", currency=None)
    _universe(tmp_path, {"BREN.JK": "IDR"})
    _rates(tmp_path, {"USD": 1.1, "IDR": 18_000.0})
    first = snap.publish_incremental(tmp_path)
    assert pd.isna(_latest(first, "BREN.JK")["reporting_currency"])

    rebuilt.clear()
    mirror = tmp_path / "mirror" / "defeatbeta" / "company_tickers.json"
    mirror.parent.mkdir(parents=True)
    mirror.write_text(json.dumps({"0": {"ticker": "BREN.JK", "financial_currency": "USD"}}))
    second = snap.publish_incremental(tmp_path)
    assert rebuilt == [["BREN.JK"]]
    row = _latest(second, "BREN.JK")
    assert row["reporting_currency"] == "USD"
    assert row["market_cap"] == pytest.approx(50.0 / 18_000.0 * 1.1 * 10)


def test_a_listing_currency_corrected_in_the_universe_reprices_the_row(tmp_path, rebuilt) -> None:
    _company(tmp_path, "VOD.L", currency="GBP", close=80.0)
    _universe(tmp_path, {"VOD.L": "USD"})  # wrong: read as dollars, no rate → no price
    first = snap.publish_incremental(tmp_path)
    assert pd.isna(_latest(first, "VOD.L")["market_cap"])

    rebuilt.clear()
    time.sleep(0.02)
    _universe(tmp_path, {"VOD.L": "GBP"})  # .L in GBP quotes in pence
    second = snap.publish_incremental(tmp_path)
    assert rebuilt == [["VOD.L"]]
    assert _latest(second, "VOD.L")["market_cap"] == pytest.approx(0.80 * 10)


def test_a_base_from_before_the_record_is_rebuilt_once(tmp_path, rebuilt) -> None:
    """A base cache restored from a release that predates the reference
    record cannot say what its rows were built with: one full rebuild."""
    _company(tmp_path, "AAA")
    _company(tmp_path, "BBB")
    snap.publish_incremental(tmp_path)
    (tmp_path / "snapshot" / snap.BASE_REFERENCE_NAME).unlink()

    rebuilt.clear()
    assert snap.publish_incremental(tmp_path) is not None
    assert rebuilt == [["AAA", "BBB"]]
    rebuilt.clear()
    assert snap.publish_incremental(tmp_path) is None
    assert rebuilt == []


def test_a_mirror_missing_from_the_data_dir_is_not_a_change(tmp_path, rebuilt) -> None:
    """The published tarball carries no mirror/ and the marathon runs with
    --no-fetch-fx: an ABSENT input says nothing about what moved — it used to
    read as « moved » and rebuild good rows into degraded ones (a JPY filer
    lost its currency, a EUR line its market cap)."""
    import shutil

    _company(tmp_path, "TM", currency=None)
    _company(tmp_path, "FOR.DE", currency="USD")
    _universe(tmp_path, {"TM": "JPY", "FOR.DE": "EUR"})
    _rates(tmp_path, {"USD": 1.25, "JPY": 160.0})
    mirror = tmp_path / "mirror" / "defeatbeta" / "company_tickers.json"
    mirror.parent.mkdir(parents=True)
    mirror.write_text(json.dumps({"0": {"ticker": "TM", "financial_currency": "JPY"}}))
    _splits(tmp_path, [("FOR.DE", "2020-01-02", "2:1")])
    first = snap.publish_incremental(tmp_path)
    assert _latest(first, "TM")["reporting_currency"] == "JPY"
    assert _latest(first, "FOR.DE")["market_cap"] == pytest.approx(625.0)

    rebuilt.clear()
    shutil.rmtree(tmp_path / "mirror")
    (tmp_path / "events" / "defeatbeta-splits.parquet").unlink()
    snap.publish_incremental(tmp_path)
    assert rebuilt == []  # nothing is known to have moved: nothing is rebuilt


def test_a_warrant_outside_the_universe_settles(tmp_path, rebuilt) -> None:
    """ABCD and its warrant ABCDW in raw, neither in the universe: refreshing
    only the warrant built it as a company (the census saw the dirty symbols
    only), and the reference check then rebuilt it on every run."""
    _company(tmp_path, "ABCD")
    _company(tmp_path, "ABCDW", close=0.05)
    first = snap.publish_incremental(tmp_path)
    assert "ABCDW" not in set(first["symbol"])

    time.sleep(0.02)
    write_raw_statement(
        tmp_path,
        symbol="ABCDW",
        provider="yfinance",
        statement_type="prices",
        freq="daily",
        frame=pd.DataFrame({"Date": ["2026-03-04"], "Close": [0.06]}),
        fetched_at=time.time(),
    )
    second = snap.publish_incremental(tmp_path)
    assert second is None or "ABCDW" not in set(second["symbol"])
    rebuilt.clear()
    assert snap.publish_incremental(tmp_path) is None
    assert rebuilt == []


def test_a_symbol_with_no_readable_frames_settles(tmp_path, rebuilt) -> None:
    """A raw directory no reader takes frames from records no currencies: a
    rate change must not flag it forever."""
    _company(tmp_path, "AAA")
    write_raw_statement(
        tmp_path,
        symbol="ODD",
        provider="someone-else",
        statement_type="income",
        freq="annual",
        frame=pd.DataFrame({"period": ["2025-12-31"], "TotalRevenue": [1.0]}),
        fetched_at=1000.0,
    )
    _rates(tmp_path, {"USD": 1.1})
    snap.publish_incremental(tmp_path)
    rebuilt.clear()
    _rates(tmp_path, {"USD": 1.3})
    snap.publish_incremental(tmp_path)
    assert "ODD" not in sum(rebuilt, [])
    rebuilt.clear()
    assert snap.publish_incremental(tmp_path) is None


def test_compute_lock_leaves_a_missing_data_dir_alone(tmp_path) -> None:
    """A mistyped --data-dir: compute must not create it (and its lock file,
    which `crible clean` then refuses to remove)."""
    missing = tmp_path / "typo"
    with snap.compute_lock(missing):
        pass
    assert not missing.exists()


def test_compute_lock_without_lock_support_still_computes(tmp_path, monkeypatch) -> None:
    """flock unsupported (ENOLCK on some network filesystems) is no « other
    compute running »: compute goes on unlocked instead of never running."""
    import errno
    import fcntl

    def unsupported(handle, flags):
        raise OSError(errno.ENOLCK, "No locks available")

    monkeypatch.setattr(fcntl, "flock", unsupported)
    with snap.compute_lock(tmp_path):
        pass  # no ComputeBusy


def test_an_undated_bar_never_becomes_the_price() -> None:
    from crible.compute.snapshot import latest_close

    bars = pd.DataFrame(
        {"Date": ["2026-06-01", None, "garbage", "2026-06-02"], "Close": [10.0, 11.0, 12.0, 20.0]}
    )
    assert latest_close({("prices", "daily"): bars}) == (20.0, "2026-06-02")
    undated = pd.DataFrame({"Date": [None, None], "Close": [10.0, 11.0]})
    assert latest_close({("prices", "daily"): undated}) is None
