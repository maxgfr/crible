"""Audited Taiwan — TWSE OpenAPI. Pinned rules: ROC year +1911, TWD
thousands ×1000, cumulative-YTD income → Q4-only annual, Q1-Q3 balances go
quarterly, and the raw layer IS the forward-accumulation store."""

from __future__ import annotations

import json

import duckdb
import pandas as pd

from crible.providers.twse import frames_from_reports, roc_period


def _income_row(code="2330", year="114", quarter="4", revenue="1000", net="200"):
    return {"出表日期": "1150717", "年度": year, "季別": quarter, "公司代號": code,
            "公司名稱": "X", "營業收入": revenue, "營業成本": "600",
            "營業毛利（毛損）淨額": "400", "營業費用": "100",
            "營業利益（損失）": "300", "稅前淨利（淨損）": "250",
            "所得稅費用（利益）": "50", "本期淨利（淨損）": net,
            "繼續營業單位本期淨利（淨損）": "999"}


def _balance_row(code="2330", year="115", quarter="1", assets="5000"):
    return {"出表日期": "1150717", "年度": year, "季別": quarter, "公司代號": code,
            "公司名稱": "X", "流動資產": "2000", "資產總額": assets,
            "流動負債": "800", "負債總額": "1500", "保留盈餘": "900",
            "歸屬於母公司業主之權益合計": "3300", "權益總額": "3500"}


def test_roc_period_conversion() -> None:
    assert roc_period("114", "4") == "2025-12-31"
    assert roc_period("115", "1") == "2026-03-31"
    assert roc_period("garbage", "1") is None and roc_period("115", "9") is None


def test_frames_pin_the_ground_rules() -> None:
    income = [_income_row(quarter="4"), _income_row(quarter="2", year="115")]  # Q2 dropped
    balance = [_balance_row(quarter="1", year="115"), _balance_row(quarter="4", year="114")]
    frames = frames_from_reports(income, balance, "2330")

    annual = frames[("income", "annual")].set_index("period")
    assert list(annual.index) == ["2025-12-31"]  # cumulative YTD: only Q4 is the year
    assert annual.loc["2025-12-31", "TotalRevenue"] == 1_000_000.0  # thousands ×1000
    assert annual.loc["2025-12-31", "NetIncome"] == 200_000.0  # rank 0 beats the fallback

    annual_balance = frames[("balance", "annual")].set_index("period")
    assert annual_balance.loc["2025-12-31", "StockholdersEquity"] == 3_300_000.0  # parent equity wins
    quarterly = frames[("balance", "quarterly")].set_index("period")
    assert list(quarterly.index) == ["2026-03-31"]  # Q1 instant stays OUT of annual

    assert frames_from_reports(income, balance, "9999") == {}


class _JsonHttp:
    def __init__(self, by_url: dict[str, list]) -> None:
        self.by_url = by_url

    def stream(self, method, url, headers=None):
        for fragment, rows in self.by_url.items():
            if fragment in url:
                return _Resp(json.dumps(rows).encode("utf-8"))
        return _Resp(b"[]")


class _Resp:
    def __init__(self, body: bytes) -> None:
        self.status_code = 200
        self._body = body
        self.headers = {}

    def raise_for_status(self):
        pass

    def iter_bytes(self, chunk_size: int = 0):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _seed_tw_universe(tmp_path, monkeypatch) -> None:
    from crible.universe import bootstrap_universe

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, pd.DataFrame([
        {"symbol": "2330.TW", "name": "TSMC", "country": "Taiwan", "sector": "IT",
         "industry": "Semi", "exchange": "TAI", "currency": "TWD",
         "market_cap": "Mega Cap", "isin": None},
    ]))
    con.close()


def test_run_twse_accumulates_forward_in_the_raw_layer(tmp_path, monkeypatch) -> None:
    """Snapshot endpoints forget history: run 1 writes FY2025; run 2 (the
    next year's snapshot) must hold BOTH periods in one frame."""
    from crible.ingest.enrichment import run_twse

    _seed_tw_universe(tmp_path, monkeypatch)
    first = _JsonHttp({"t187ap06": [_income_row(year="114")],
                       "t187ap07": [_balance_row(year="114", quarter="4")]})
    outcome = run_twse(limit=10, http=first)
    assert outcome["enriched"] == 1

    # a year later: the endpoint now serves FY2026 only — mirror must refetch
    import shutil
    shutil.rmtree(tmp_path / "mirror" / "twse")
    second = _JsonHttp({"t187ap06": [_income_row(year="115", revenue="2000")],
                        "t187ap07": [_balance_row(year="115", quarter="4")]})
    outcome = run_twse(limit=10, http=second)
    assert outcome["enriched"] == 1

    files = sorted(tmp_path.glob("raw/provider=twse/symbol=2330.TW/income-annual-*.parquet"))
    income = pd.read_parquet(files[-1]).set_index("period")
    assert {"2025-12-31", "2026-12-31"} <= set(income.index)  # history accumulated
    assert income.loc["2026-12-31", "TotalRevenue"] == 2_000_000.0


def test_run_twse_limit_zero_is_a_pure_noop(tmp_path, monkeypatch) -> None:
    from crible.ingest.enrichment import run_twse

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    assert run_twse(limit=0)["skipped"] == "limit 0"
    assert not (tmp_path / "mirror").exists()
