"""EDINET (Japan) — audited JP filings, free-key opt-in.

EDINET is API-only and needs a free Subscription-Key, so it is a free-key
provider: OFF by default (the core stays keyless), never scraped. Its XBRL
instances are parsed for the jppfs concepts crible maps to canonical fields.
PDL1.0 → redistributable WITH attribution. Resolution is clean: a Yahoo JP
ticker (7203.T) maps to the 5-digit securities code (72030).
"""

from __future__ import annotations

from crible.providers.edinet import (
    EdinetProvider,
    parse_xbrl_instance,
    sec_code,
)

XBRL = """<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/cor">
  <xbrli:context id="CurrentYearDuration">
    <xbrli:period>
      <xbrli:startDate>2023-04-01</xbrli:startDate>
      <xbrli:endDate>2024-03-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <xbrli:context id="CurrentYearInstant">
    <xbrli:period><xbrli:instant>2024-03-31</xbrli:instant></xbrli:period>
  </xbrli:context>
  <xbrli:context id="Q1Duration">
    <xbrli:period>
      <xbrli:startDate>2023-04-01</xbrli:startDate>
      <xbrli:endDate>2023-06-30</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <jppfs_cor:NetSales contextRef="CurrentYearDuration" unitRef="JPY" decimals="-6">45095325000000</jppfs_cor:NetSales>
  <jppfs_cor:ProfitLoss contextRef="CurrentYearDuration" unitRef="JPY">4944933000000</jppfs_cor:ProfitLoss>
  <jppfs_cor:NetSales contextRef="Q1Duration" unitRef="JPY">10000000000000</jppfs_cor:NetSales>
  <jppfs_cor:Assets contextRef="CurrentYearInstant" unitRef="JPY">90114296000000</jppfs_cor:Assets>
</xbrli:xbrl>"""


def test_parse_xbrl_instance_extracts_full_year_facts() -> None:
    frames = parse_xbrl_instance(XBRL)
    income = frames[("income", "annual")].set_index("period")
    assert income.loc["2024", "TotalRevenue"] == 45095325000000.0
    assert income.loc["2024", "NetIncome"] == 4944933000000.0
    # the Q1 interim NetSales is never booked as an annual figure
    assert (income["TotalRevenue"] == 10000000000000.0).sum() == 0
    balance = frames[("balance", "annual")].set_index("period")
    assert balance.loc["2024", "TotalAssets"] == 90114296000000.0


def test_sec_code_maps_yahoo_jp_tickers() -> None:
    assert sec_code("7203.T") == "72030"
    assert sec_code("6758.T") == "67580"
    assert sec_code("AAPL") is None  # not a JP listing


def test_edinet_provider_is_off_without_a_key() -> None:
    provider = EdinetProvider()
    assert provider.kind == "free-key"
    assert provider.key_env_var == "CRIBLE_EDINET_KEY"
    assert provider.enabled({}) is False
    assert provider.enabled({"CRIBLE_EDINET_KEY": "abc"}) is True


def test_run_edinet_is_off_without_a_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("CRIBLE_EDINET_KEY", raising=False)
    from crible.ingest.enrichment import run_edinet

    outcome = run_edinet(["2024-06-25"])
    assert outcome["enriched"] == 0
    assert "EDINET disabled" in outcome["skipped"]


def test_run_edinet_writes_jp_raw_with_a_key(tmp_path, monkeypatch) -> None:
    import io
    import zipfile

    import duckdb
    import pandas as pd

    from crible.ingest.enrichment import run_edinet
    from crible.universe import bootstrap_universe

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(
        con,
        pd.DataFrame(
            {
                "symbol": ["7203.T"], "name": ["Toyota"], "country": ["Japan"],
                "sector": ["Auto"], "industry": ["X"], "exchange": ["JPX"], "currency": ["JPY"],
            }
        ),
    )
    con.close()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("XBRL/PublicDoc/jpcrp.xbrl", XBRL)
    doc_zip = buf.getvalue()

    class FakeClient:
        def list_documents(self, day):
            return [{"secCode": "72030", "docID": "S100AAAA"}]

        def fetch_document(self, doc_id):
            return doc_zip

    outcome = run_edinet(["2024-06-25"], client=FakeClient())
    assert outcome["enriched"] == 1
    assert list(tmp_path.glob("raw/provider=edinet/symbol=7203.T/*.parquet"))
