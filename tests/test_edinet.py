"""FR-020 — EDINET (Japan) — audited JP filings, free-key opt-in.

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


XBRL_CONSOL = """<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
            xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/cor">
  <xbrli:context id="CurrentYearDuration">
    <xbrli:period><xbrli:startDate>2023-04-01</xbrli:startDate><xbrli:endDate>2024-03-31</xbrli:endDate></xbrli:period>
  </xbrli:context>
  <xbrli:context id="CurrentYearDuration_NonConsolidatedMember">
    <xbrli:period><xbrli:startDate>2023-04-01</xbrli:startDate><xbrli:endDate>2024-03-31</xbrli:endDate></xbrli:period>
    <xbrli:scenario>
      <xbrldi:explicitMember dimension="jppfs_cor:ConsolidatedOrNonConsolidatedAxis">jppfs_cor:NonConsolidatedMember</xbrldi:explicitMember>
    </xbrli:scenario>
  </xbrli:context>
  <jppfs_cor:NetSales contextRef="CurrentYearDuration_NonConsolidatedMember" unitRef="JPY">30000000000000</jppfs_cor:NetSales>
  <jppfs_cor:NetSales contextRef="CurrentYearDuration" unitRef="JPY">45000000000000</jppfs_cor:NetSales>
</xbrli:xbrl>"""


def test_parse_xbrl_instance_prefers_consolidated_over_nonconsolidated() -> None:
    """P2 — 連結 (consolidated) must win over 単体 (non-consolidated): the group
    figure is the reported one. The non-consolidated row is listed first to
    defeat first-writer-wins."""
    income = parse_xbrl_instance(XBRL_CONSOL)[("income", "annual")].set_index("period")
    assert income.loc["2024", "TotalRevenue"] == 45000000000000.0  # consolidated, not 30e12


XBRL_INTERIM_BAL = """<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:jppfs_cor="http://disclosure.edinet-fsa.go.jp/taxonomy/jppfs/cor">
  <xbrli:context id="CurrentQuarterInstant">
    <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period>
  </xbrli:context>
  <xbrli:context id="CurrentYearInstant">
    <xbrli:period><xbrli:instant>2024-03-31</xbrli:instant></xbrli:period>
  </xbrli:context>
  <jppfs_cor:Assets contextRef="CurrentQuarterInstant" unitRef="JPY">80000000000000</jppfs_cor:Assets>
  <jppfs_cor:Assets contextRef="CurrentYearInstant" unitRef="JPY">90000000000000</jppfs_cor:Assets>
</xbrli:xbrl>"""


def test_parse_xbrl_instance_rejects_interim_balance_context() -> None:
    """P2 — a quarter-end balance instant must not be booked as an annual figure."""
    balance = parse_xbrl_instance(XBRL_INTERIM_BAL)[("balance", "annual")].set_index("period")
    assert "2023" not in balance.index  # the CurrentQuarterInstant is dropped
    assert balance.loc["2024", "TotalAssets"] == 90000000000000.0


def test_run_edinet_only_processes_annual_securities_reports(tmp_path, monkeypatch) -> None:
    """P2 — only annual securities reports (docTypeCode 120) are ingested; a
    quarterly report (140) for the same issuer is skipped."""
    import io
    import zipfile

    import duckdb
    import pandas as pd

    from crible.ingest.enrichment import run_edinet
    from crible.universe import bootstrap_universe

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    con = duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(con, pd.DataFrame({
        "symbol": ["7203.T"], "name": ["Toyota"], "country": ["Japan"],
        "sector": ["Auto"], "industry": ["X"], "exchange": ["JPX"], "currency": ["JPY"],
    }))
    con.close()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("XBRL/PublicDoc/jpcrp.xbrl", XBRL)
    doc_zip = buf.getvalue()

    class FakeClient:
        def __init__(self):
            self.fetched = []

        def list_documents(self, day):
            return [
                {"secCode": "72030", "docID": "Q1", "docTypeCode": "140"},  # quarterly
                {"secCode": "72030", "docID": "A1", "docTypeCode": "120"},  # annual
            ]

        def fetch_document(self, doc_id):
            self.fetched.append(doc_id)
            return doc_zip

    client = FakeClient()
    run_edinet(["2024-06-25"], client=client)
    assert client.fetched == ["A1"]  # only the annual report was fetched


def test_sec_code_maps_yahoo_jp_tickers() -> None:
    assert sec_code("7203.T") == "72030"
    assert sec_code("6758.T") == "67580"
    assert sec_code("130A.T") == "130A0"  # 2024+ alphanumeric TSE code (F6)
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
            return [{"secCode": "72030", "docID": "S100AAAA", "docTypeCode": "120"}]

        def fetch_document(self, doc_id):
            return doc_zip

    outcome = run_edinet(["2024-06-25"], client=FakeClient())
    assert outcome["enriched"] == 1
    assert list(tmp_path.glob("raw/provider=edinet/symbol=7203.T/*.parquet"))
