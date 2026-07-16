"""defeatbeta yahoo-finance-data dump — series + distillate from one HF
parquet per table. Yahoo-derived, assumed-risk tier: additional + fallback
only (audited precedence and crawled-bars priority are asserted here)."""

from __future__ import annotations

import pandas as pd
from typer.testing import CliRunner

from crible.cli import app
from crible.compute.snapshot import build_snapshot
from crible.ingest.defeatbeta import (
    ITEM_TO_YF,
    fundamentals_gap_symbols,
    import_defeatbeta,
    import_defeatbeta_fundamentals,
)
from crible.ingest.price_import import load_prices_latest
from crible.ingest.raw import write_raw_statement
from crible.price_series import _resolve

runner = CliRunner()


def _universe(tmp_path, symbols=("AAPL", "BRK-B")) -> None:
    pd.DataFrame({"symbol": list(symbols)}).to_parquet(tmp_path / "universe.parquet", index=False)


def _prices_table(tmp_path, name="stock_prices.parquet") -> str:
    """defeatbeta's exact schema: report_date is an ISO STRING, no adj_close;
    two symbols with >182 days of history, one unknown to the universe."""
    rows = []
    for symbol, base in (("AAPL", 100.0), ("ZZUNKNOWN", 5.0)):
        for month in range(1, 13):
            rows.append(
                {"symbol": symbol, "report_date": f"2026-{month:02d}-01",
                 "open": base, "close": base + month, "high": base, "low": base,
                 "volume": 1000}
            )
    path = tmp_path / name
    pd.DataFrame(rows).to_parquet(path, index=False)
    return str(path)


def _tables(tmp_path) -> dict[str, str]:
    return {"prices": _prices_table(tmp_path)}


def _tables_with_events(tmp_path) -> dict[str, str]:
    tables = _tables(tmp_path)
    events = {
        "dividends": pd.DataFrame(
            {"symbol": ["AAPL", "ZZUNKNOWN"], "report_date": ["2026-05-08", "2026-05-08"],
             "amount": [0.26, 1.0]}
        ),
        "splits": pd.DataFrame(
            {"symbol": ["AAPL"], "report_date": ["2020-08-31"], "split_factor": ["4:1"]}
        ),
        "shares": pd.DataFrame(
            {"symbol": ["AAPL"], "report_date": ["2026-03-31"],
             "shares_outstanding": [15_000_000_000]}
        ),
    }
    for name, frame in events.items():
        path = tmp_path / f"{name}.parquet"
        frame.to_parquet(path, index=False)
        tables[name] = str(path)
    return tables


def test_defeatbeta_import_distils_known_symbols(tmp_path) -> None:
    _universe(tmp_path)
    report = import_defeatbeta(tmp_path, tables=_tables(tmp_path))
    assert report.imported == 1 and report.skipped_unknown == 1

    table = load_prices_latest(tmp_path).set_index("symbol")
    row = table.loc["AAPL"]
    assert row["close"] == 112.0  # December close (100 + 12)
    assert row["price_asof"] == "2026-12-01"
    assert round(row["return_6m"], 6) == round(112.0 / 106.0 - 1.0, 6)
    assert row["source"] == "defeatbeta"


def test_defeatbeta_import_persists_the_series_store(tmp_path) -> None:
    """Windowed OHLCV in data/prices/defeatbeta.parquet — universe-filtered,
    adj_close NULL (defeatbeta bars are split-adjusted only, the Stooq rule)."""
    _universe(tmp_path)
    import_defeatbeta(tmp_path, tables=_tables(tmp_path))

    series = pd.read_parquet(tmp_path / "prices" / "defeatbeta.parquet")
    assert set(series["symbol"]) == {"AAPL"}
    assert list(series.columns) == [
        "symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "source",
    ]
    assert (series["source"] == "defeatbeta").all()
    assert series["adj_close"].isna().all()
    assert series["close"].notna().all() and series["volume"].notna().all()


def test_defeatbeta_import_writes_the_events_store(tmp_path) -> None:
    """Dividends/splits/shares land in data/events/ — universe-filtered, full
    history, split_factor kept as the raw 'a:b' string."""
    _universe(tmp_path)
    import_defeatbeta(tmp_path, tables=_tables_with_events(tmp_path))

    dividends = pd.read_parquet(tmp_path / "events" / "defeatbeta-dividends.parquet")
    assert set(dividends["symbol"]) == {"AAPL"}  # ZZUNKNOWN dropped
    assert list(dividends.columns) == ["symbol", "date", "amount", "source"]
    assert dividends.loc[0, "amount"] == 0.26

    splits = pd.read_parquet(tmp_path / "events" / "defeatbeta-splits.parquet")
    assert splits.loc[0, "split_factor"] == "4:1"  # pre-window history kept

    shares = pd.read_parquet(tmp_path / "events" / "defeatbeta-shares.parquet")
    assert shares.loc[0, "shares_outstanding"] == 15_000_000_000


def test_defeatbeta_import_without_event_tables_is_prices_only(tmp_path) -> None:
    _universe(tmp_path)
    import_defeatbeta(tmp_path, tables=_tables(tmp_path))
    assert not (tmp_path / "events").exists()


def test_defeatbeta_loses_price_ties_to_the_crawl_but_beats_the_dumps() -> None:
    """Crawled yfinance bars stay canonical on equal dates; among dumps the
    ~weekly defeatbeta outranks the ~monthly huggingface rotation."""
    def bars(source):
        return pd.DataFrame(
            {"symbol": "AAPL", "date": ["2026-07-01"], "open": 1.0, "high": 1.0,
             "low": 1.0, "close": 1.0, "adj_close": float("nan"), "volume": 1.0,
             "source": source}
        )

    against_crawl = _resolve(pd.concat([bars("yfinance"), bars("defeatbeta")]), 400)
    assert set(against_crawl["source"]) == {"yfinance"}

    against_dump = _resolve(pd.concat([bars("huggingface"), bars("defeatbeta")]), 400)
    assert set(against_dump["source"]) == {"defeatbeta"}


def _statements_table(tmp_path, symbols=("AAPL",)) -> str:
    """defeatbeta's LONG stock_statement schema, deviant names included."""
    rows = []
    for symbol in symbols:
        for period in ("2024-12-31", "2025-12-31"):
            year = float(period[:4])
            for finance_type, item, value in (
                ("income_statement", "total_revenue", 400.0 + year),
                ("income_statement", "net_income", 56.0),
                ("income_statement", "basic_average_shares", 10.0),
                ("income_statement", "ebit", 80.0),
                ("income_statement", "selling_gen_admin", 30.0),
                ("balance_sheet", "total_assets", 900.0),
                ("balance_sheet", "net_ppe", 250.0),
                ("balance_sheet", "stockholders_equity", 300.0),
                ("cash_flow", "operating_cash_flow", 90.0),
                ("cash_flow", "capital_expenditure", -20.0),
            ):
                rows.append(
                    {"symbol": symbol, "report_date": period, "item_name": item,
                     "item_value": value, "finance_type": finance_type,
                     "period_type": "annual"}
                )
    path = tmp_path / "stock_statement.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False)
    return str(path)


def test_item_map_covers_the_deviant_names() -> None:
    assert ITEM_TO_YF["total_revenue"] == "TotalRevenue"
    assert ITEM_TO_YF["ebit"] == "EBIT"
    assert ITEM_TO_YF["normalized_ebitda"] == "NormalizedEBITDA"
    assert ITEM_TO_YF["net_ppe"] == "NetPPE"
    assert ITEM_TO_YF["selling_gen_admin"] == "SellingGeneralAndAdministration"
    assert ITEM_TO_YF["cash_flow_from_continuing_operating_activities"] == (
        "CashFlowFromContinuingOperatingActivities"
    )


def test_fundamentals_pivot_to_yfinance_vocabulary(tmp_path) -> None:
    _universe(tmp_path)
    report = import_defeatbeta_fundamentals(tmp_path, table=_statements_table(tmp_path))
    assert report.imported == 1

    directory = tmp_path / "raw" / "provider=defeatbeta" / "symbol=AAPL"
    income = pd.read_parquet(sorted(directory.glob("income-annual-*.parquet"))[-1])
    assert income.loc[income["period"] == "2025-12-31", "TotalRevenue"].iloc[0] == 2425.0
    assert {"EBIT", "SellingGeneralAndAdministration", "BasicAverageShares"} <= set(income.columns)
    balance = pd.read_parquet(sorted(directory.glob("balance-annual-*.parquet"))[-1])
    assert "NetPPE" in balance.columns


def test_fundamentals_import_targets_gap_symbols_only(tmp_path) -> None:
    """AAPL has crawled yfinance statements, BRK-B has audited EDGAR raw —
    neither is a gap symbol; only the unserved listing gets defeatbeta raw."""
    pd.DataFrame({"symbol": ["AAPL", "BRK-B", "GAP1"]}).to_parquet(
        tmp_path / "universe.parquet", index=False
    )
    frame = pd.DataFrame({"period": ["2025-12-31"], "TotalRevenue": [1.0]})
    write_raw_statement(tmp_path, symbol="AAPL", provider="yfinance", statement_type="income",
                        freq="annual", frame=frame, fetched_at=1.0)
    write_raw_statement(tmp_path, symbol="BRK-B", provider="edgar", statement_type="income",
                        freq="annual", frame=frame, fetched_at=1.0)

    assert fundamentals_gap_symbols(tmp_path) == ["GAP1"]
    report = import_defeatbeta_fundamentals(
        tmp_path, table=_statements_table(tmp_path, symbols=("AAPL", "GAP1"))
    )
    assert report.imported == 1
    assert not (tmp_path / "raw" / "provider=defeatbeta" / "symbol=AAPL").exists()
    assert (tmp_path / "raw" / "provider=defeatbeta" / "symbol=GAP1").exists()


def test_snapshot_falls_back_to_defeatbeta_fundamentals(tmp_path) -> None:
    """A defeatbeta-only symbol gets real canonical fields + ratios, tagged
    provider=defeatbeta; a symbol with yfinance statements ignores them."""
    _universe(tmp_path)
    import_defeatbeta_fundamentals(tmp_path, table=_statements_table(tmp_path))

    snapshot = build_snapshot(tmp_path, symbols=["AAPL"]).set_index("period")
    row = snapshot.loc["2025-12-31"]
    assert row["provider"] == "defeatbeta"
    assert row["revenue"] == 2425.0
    assert row["net_income"] == 56.0

    # crawled yfinance statements present → they stay the base
    yf = pd.DataFrame({"period": ["2025-12-31"], "TotalRevenue": [9999.0]})
    write_raw_statement(tmp_path, symbol="AAPL", provider="yfinance", statement_type="income",
                        freq="annual", frame=yf, fetched_at=2.0)
    snapshot = build_snapshot(tmp_path, symbols=["AAPL"]).set_index("period")
    row = snapshot.loc["2025-12-31"]
    assert row["provider"] == "yfinance"
    assert row["revenue"] == 9999.0


def test_audited_reconciles_on_top_of_defeatbeta(tmp_path) -> None:
    """EDGAR values outrank the defeatbeta fallback and are recorded as
    audited provenance — the reconcile seam is source-agnostic."""
    _universe(tmp_path)
    import_defeatbeta_fundamentals(tmp_path, table=_statements_table(tmp_path))
    audited = pd.DataFrame({"period": ["2025-12-31"], "TotalRevenue": [3000.0]})
    write_raw_statement(tmp_path, symbol="AAPL", provider="edgar", statement_type="income",
                        freq="annual", frame=audited, fetched_at=2.0)

    snapshot = build_snapshot(tmp_path, symbols=["AAPL"]).set_index("period")
    row = snapshot.loc["2025-12-31"]
    assert row["revenue"] == 3000.0  # audited wins the >5% divergence
    assert "revenue" in row["audited_fields"]


def test_import_prices_cli_dispatches_defeatbeta(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    _universe(tmp_path)
    monkeypatch.setattr("crible.ingest.defeatbeta.DB_TABLES", _tables(tmp_path))

    result = runner.invoke(app, ["import-prices", "defeatbeta"])
    assert result.exit_code == 0, result.output
    assert "imported 1 symbols from defeatbeta" in result.output

    # the heartbeat records the import; the per-source age gate holds
    import json

    status = json.loads((tmp_path / "status.json").read_text())
    assert status["imports"]["defeatbeta"]["symbols"] == 1

    again = runner.invoke(app, ["import-prices", "defeatbeta", "--max-age-days", "6"])
    assert "nothing to do" in again.output


def test_defeatbeta_gate_ignores_other_dumps(tmp_path, monkeypatch) -> None:
    """A fresh huggingface import must NOT age-gate the defeatbeta schedule."""
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    _universe(tmp_path)

    hf_shard = tmp_path / "hf.parquet"
    frame = pd.read_parquet(_prices_table(tmp_path, name="src.parquet"))
    frame.assign(date=frame["report_date"], adj_close=frame["close"]).to_parquet(
        hf_shard, index=False
    )
    monkeypatch.setattr("crible.ingest.price_import.HF_SHARDS", [str(hf_shard)])
    monkeypatch.setattr("crible.ingest.defeatbeta.DB_TABLES", _tables(tmp_path))

    assert runner.invoke(app, ["import-prices", "huggingface"]).exit_code == 0
    result = runner.invoke(app, ["import-prices", "defeatbeta", "--max-age-days", "6"])
    assert result.exit_code == 0, result.output
    assert "imported 1 symbols from defeatbeta" in result.output
