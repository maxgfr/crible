"""FR-014 — the EODHD PRD (detailed) + FMP Ultimate PRD (rejected summary)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fr014_eodhd_prd_contains_grounded_facts_payloads_mapping_and_switch() -> None:
    prd = (ROOT / "docs/prds/eodhd.md").read_text()
    # grounded free-tier facts + to-revalidate paid figures
    assert "20 API calls/day" in prd
    assert "REVALIDATE AT PURCHASE" in prd
    assert "€59.99" in prd and "100,000" in prd
    # recorded sample payloads captured via the demo token
    assert "demo" in prd and "AAPL.US" in prd
    assert "41 yearly periods" in prd  # verified depth
    assert "adjusted_close" in prd  # real EOD payload excerpt
    # field-by-field mapping to crible's raw schema
    assert "totalStockholderEquity" in prd and "total_equity" in prd
    # exact activation steps
    assert "EODHD_KEY" in prd and "insufficient tier" in prd


def test_fr014_fmp_ultimate_prd_documents_the_rejected_alternative() -> None:
    prd = (ROOT / "docs/prds/fmp-ultimate.md").read_text()
    assert "REJECTED" in prd
    assert "$149" in prd
    assert "fmp_free" in prd  # the schema-validation path that already exists
