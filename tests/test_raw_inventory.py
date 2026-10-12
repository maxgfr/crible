"""RawInventory — one scandir pass answers every raw-layer question the
readers used to glob for on their own."""

from __future__ import annotations

import pandas as pd

from crible.ingest.raw import RawInventory, write_raw_statement


def _write(tmp_path, provider, symbol, statement_type, freq, fetched_at):
    write_raw_statement(
        tmp_path,
        symbol=symbol,
        provider=provider,
        statement_type=statement_type,
        freq=freq,
        frame=pd.DataFrame({"period": ["2025"], "x": [1.0]}),
        fetched_at=fetched_at,
    )


def test_inventory_answers_from_one_scan(tmp_path) -> None:
    _write(tmp_path, "yfinance", "AIR.PA", "income", "annual", 100.0)
    _write(tmp_path, "yfinance", "AIR.PA", "income", "annual", 200.0)
    _write(tmp_path, "yfinance", "AIR.PA", "prices", "daily", 300.0)
    _write(tmp_path, "edgar", "AAPL", "balance", "annual", 50.0)
    _write(tmp_path, "yfinance", "DEAD", "meta", "none", 10.0)
    _write(tmp_path, "yfinance", "BARS", "prices", "daily", 10.0)
    (
        tmp_path
        / "raw"
        / "provider=yfinance"
        / "symbol=AIR.PA"
        / ".tmp-income-annual-000000000999000.parquet"
    ).write_bytes(b"")

    inventory = RawInventory.scan(tmp_path)
    assert inventory.symbols() == {"AIR.PA", "AAPL", "DEAD", "BARS"}
    assert inventory.symbols("edgar") == {"AAPL"}
    newest = inventory.files("yfinance", "AIR.PA")[("income", "annual")]
    assert newest.name == "income-annual-000000000200000.parquet"
    assert inventory.newest_stamp("AIR.PA") == 300.0
    assert inventory.newest_stamp("AIR.PA", types=("income", "balance", "cashflow")) == 200.0
    assert inventory.statement_symbols() == {"AIR.PA", "AAPL"}
    assert inventory.statement_symbols(exclude=("edgar",)) == {"AIR.PA"}
    assert inventory.priced_symbols() == {"AIR.PA", "BARS"}


def test_inventory_of_a_missing_raw_layer_is_empty(tmp_path) -> None:
    assert RawInventory.scan(tmp_path).symbols() == set()


def test_newest_stamp_is_not_a_scan_per_call() -> None:
    """Asked once per symbol per compute: a scan of every entry each time
    was O(N²) — 45 s of a 49 s no-op compute at 27k symbols."""
    import time
    from pathlib import Path

    inventory = RawInventory()
    for i in range(30_000):
        inventory.entries[("yfinance", f"S{i}")] = {("income", "annual"): (float(i), Path("x"))}
    started = time.perf_counter()
    for i in range(30_000):
        inventory.newest_stamp(f"S{i}")
    assert time.perf_counter() - started < 1.0
    assert inventory.newest_stamp("S42") == 42.0 and inventory.newest_stamp("missing") == 0.0
