"""Companies House UK — audited accounts from the free Accounts Data Product.

The product is a ZIP of iXBRL (inline-XBRL, XHTML) accounts named by company
number. crible parses the FRC-taxonomy concepts it maps to canonical fields
with a dependency-free stdlib parser, keeps only full-year figures, and writes
provider='companies-house' raw — the audited UK layer that ESEF (EU/EEA only)
does not cover post-Brexit. Assumed-risk redistribution (no explicit licence).
"""

from __future__ import annotations

import io
import zipfile

from crible.providers.companies_house import iter_accounts, parse_ixbrl

IXBRL = """<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:xbrli="http://www.xbrl.org/2003/instance">
<body>
<ix:header><ix:resources>
  <xbrli:context id="D2023">
    <xbrli:period>
      <xbrli:startDate>2023-01-01</xbrli:startDate>
      <xbrli:endDate>2023-12-31</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
  <xbrli:context id="I2023">
    <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period>
  </xbrli:context>
  <xbrli:context id="H2023">
    <xbrli:period>
      <xbrli:startDate>2023-01-01</xbrli:startDate>
      <xbrli:endDate>2023-06-30</xbrli:endDate>
    </xbrli:period>
  </xbrli:context>
</ix:resources></ix:header>
<p>Turnover <ix:nonFraction name="core:TurnoverRevenue" contextRef="D2023"
   unitRef="GBP" decimals="0">1,500,000</ix:nonFraction></p>
<p>Profit <ix:nonFraction name="core:ProfitLoss" contextRef="D2023"
   unitRef="GBP" decimals="0">200,000</ix:nonFraction></p>
<p>Interim turnover <ix:nonFraction name="core:TurnoverRevenue" contextRef="H2023"
   unitRef="GBP" decimals="0">700,000</ix:nonFraction></p>
<p>Net assets <ix:nonFraction name="core:NetAssetsLiabilities" contextRef="I2023"
   unitRef="GBP" decimals="0">3,000,000</ix:nonFraction></p>
</body></html>"""


def test_parse_ixbrl_extracts_full_year_canonical_facts() -> None:
    frames = parse_ixbrl(IXBRL)
    income = frames[("income", "annual")].set_index("period")
    assert income.loc["2023", "TotalRevenue"] == 1_500_000.0
    assert income.loc["2023", "NetIncome"] == 200_000.0
    balance = frames[("balance", "annual")].set_index("period")
    assert balance.loc["2023", "StockholdersEquity"] == 3_000_000.0
    # the H1 interim turnover (6-month context) is never booked as annual
    assert (income["TotalRevenue"] == 700_000.0).sum() == 0


def test_iter_accounts_reads_wanted_company_numbers(tmp_path) -> None:
    zip_path = tmp_path / "accounts.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("Prod223_1234567.html", IXBRL)
        archive.writestr("Prod223_9999999.html", "<html><body>no facts</body></html>")
    got = dict(iter_accounts(zip_path, {"01234567"}))
    assert "01234567" in got  # zero-padded to 8 digits, matched from the filename
    assert ("income", "annual") in got["01234567"]
    assert "09999999" not in got


def test_iter_accounts_extracts_company_number_not_the_filing_date(tmp_path) -> None:
    """F7 — the REAL Accounts Data Product names files
    Prod<batch>_<seq>_<companynumber>_<YYYYMMDD>.html. The company number must be
    extracted, not the trailing filing date — otherwise the UK layer resolves
    nothing on real files (the single-token fixture masked this)."""
    zip_path = tmp_path / "accounts.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("Prod223_0081_08094273_20230331.html", IXBRL)
        archive.writestr("Prod224_0002_SC123456_20240229.html", IXBRL)
    got = dict(iter_accounts(zip_path, {"08094273", "SC123456"}))
    assert "08094273" in got  # the company number, NOT the date 20230331
    assert "SC123456" in got  # Scottish alpha-prefixed number preserved


class _ZipResp:
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


class _ZipHttp:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def stream(self, method, url, headers=None):
        return _ZipResp(self.body)


def test_run_companies_house_writes_uk_raw(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    from crible.ingest.enrichment import run_companies_house

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("Prod223_01234567.html", IXBRL)

    outcome = run_companies_house(
        {"ULVR.L": "01234567"}, url="https://x/accounts.zip", http=_ZipHttp(buf.getvalue())
    )

    assert outcome["enriched"] == 1
    assert list(tmp_path.glob("raw/provider=companies-house/symbol=ULVR.L/*.parquet"))
