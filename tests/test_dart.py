"""Audited Korea — OpenDART. Pinned: IFRS concept-id mapping with Korean-label
fallback, parent-equity/net-income precedence, CFS-over-OFS, the no-key gate,
and multi-year accumulation into one frame-set."""

from __future__ import annotations

import io
import zipfile

import duckdb
import pandas as pd

from crible.providers.dart import frames_from_accounts, parse_corp_codes


def _row(sj_div, account_id, amount, account_nm="", thstrm_dt="2025.01.01 ~ 2025.12.31"):
    return {"sj_div": sj_div, "account_id": account_id, "account_nm": account_nm,
            "thstrm_amount": amount, "thstrm_dt": thstrm_dt}


def test_frames_map_concepts_labels_and_precedence() -> None:
    rows = [
        _row("IS", "ifrs-full_Revenue", "1,000"),
        _row("IS", "ifrs-full_ProfitLoss", "90"),
        _row("IS", "ifrs-full_ProfitLossAttributableToOwnersOfParent", "80"),  # wins
        _row("IS", "dart_OperatingIncomeLoss", "150"),
        # untagged standard account → Korean-label fallback
        _row("BS", "-표준계정코드 미사용-", "500", account_nm="자산총계",
             thstrm_dt="2025.12.31 현재"),
        _row("BS", "ifrs-full_EquityAttributableToOwnersOfParent", "300",
             thstrm_dt="2025.12.31 현재"),
        _row("BS", "ifrs-full_Equity", "310", thstrm_dt="2025.12.31 현재"),  # loses
        _row("CF", "ifrs-full_CashFlowsFromUsedInOperatingActivities", "70"),
        _row("SCE", "ifrs-full_Equity", "999"),  # equity-changes statement ignored
    ]
    frames = frames_from_accounts(rows, "2025")
    income = frames[("income", "annual")].set_index("period")
    assert income.loc["2025-12-31", "TotalRevenue"] == 1000.0  # raw KRW, no scaling
    assert income.loc["2025-12-31", "NetIncome"] == 80.0  # owners-of-parent wins
    assert income.loc["2025-12-31", "OperatingIncome"] == 150.0
    balance = frames[("balance", "annual")].set_index("period")
    assert balance.loc["2025-12-31", "TotalAssets"] == 500.0  # label fallback
    assert balance.loc["2025-12-31", "StockholdersEquity"] == 300.0  # parent wins
    assert frames[("cashflow", "annual")].set_index("period").loc[
        "2025-12-31", "OperatingCashFlow"] == 70.0


def test_period_comes_from_thstrm_dt_with_year_fallback() -> None:
    fiscal = frames_from_accounts(
        [_row("BS", "ifrs-full_Assets", "5", thstrm_dt="2025.03.31 현재")], "2024"
    )
    assert list(fiscal[("balance", "annual")]["period"]) == ["2025-03-31"]
    fallback = frames_from_accounts(
        [_row("BS", "ifrs-full_Assets", "5", thstrm_dt="")], "2024"
    )
    assert list(fallback[("balance", "annual")]["period"]) == ["2024-12-31"]


def test_parse_corp_codes_keeps_listed_only() -> None:
    xml = ("<result><list><corp_code>00126380</corp_code><corp_name>삼성전자</corp_name>"
           "<stock_code>005930</stock_code></list>"
           "<list><corp_code>99999999</corp_code><corp_name>비상장</corp_name>"
           "<stock_code> </stock_code></list></result>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as bundle:
        bundle.writestr("CORPCODE.xml", xml.encode("utf-8"))
    assert parse_corp_codes(buf.getvalue()) == {"005930": "00126380"}


class FakeDartClient:
    """CFS empty for 2024 → OFS fallback; both years served."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def corp_codes(self):
        return {"005930": "00126380"}

    def fnltt_all(self, corp_code, year, fs_div):
        self.calls.append((corp_code, year, fs_div))
        if year == "2024" and fs_div == "CFS":
            return []  # no consolidated that year → OFS fallback
        return [_row("IS", "ifrs-full_Revenue", "100" if year == "2025" else "50",
                     thstrm_dt=f"{year}.01.01 ~ {year}.12.31")]


def _seed_kr_universe(tmp_path, monkeypatch) -> None:
    from crible.universe import bootstrap_universe

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, pd.DataFrame([
        {"symbol": "005930.KS", "name": "Samsung", "country": "South Korea",
         "sector": "IT", "industry": "Semi", "exchange": "KSC", "currency": "KRW",
         "market_cap": "Mega Cap", "isin": None},
    ]))
    con.close()


def test_run_dart_accumulates_years_with_cfs_over_ofs(tmp_path, monkeypatch) -> None:
    from crible.ingest.enrichment import run_dart

    _seed_kr_universe(tmp_path, monkeypatch)
    monkeypatch.setattr("crible.ingest.enrich.kr.date",
                        type("D", (), {"today": staticmethod(lambda: __import__("datetime").date(2026, 7, 16))}))
    client = FakeDartClient()
    outcome = run_dart(years=2, limit=10, client=client)
    assert outcome["enriched"] == 1

    files = sorted(tmp_path.glob("raw/provider=dart/symbol=005930.KS/income-annual-*.parquet"))
    assert len(files) == 1
    income = pd.read_parquet(files[-1]).set_index("period")
    assert {"2025-12-31", "2024-12-31"} <= set(income.index)  # both years, one frame
    assert ("00126380", "2024", "OFS") in client.calls  # the CFS→OFS fallback fired

    # freshness: a re-run inside the 30-day window skips the symbol entirely
    again = run_dart(years=2, limit=10, client=FakeDartClient())
    assert again["enriched"] == 0


def test_run_dart_gates_without_key_and_limit_zero(tmp_path, monkeypatch) -> None:
    from crible.ingest.enrichment import run_dart

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("CRIBLE_DART_KEY", raising=False)
    assert run_dart(limit=0)["skipped"] == "limit 0"
    assert "DART disabled" in run_dart(limit=5)["skipped"]