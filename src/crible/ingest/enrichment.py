"""Audited enrichment cycles — region-split facade.

The per-region cycles live under ``ingest/enrich/`` (us/eu/uk/jp); this module
re-exports them so existing imports (`from crible.ingest.enrichment import
run_fsds`, …) keep working. Extracted from service.py (F4), then split by region
to keep each file small.
"""

from __future__ import annotations

from crible.ingest.enrich.br import run_cvm
from crible.ingest.enrich.eu import run_esef_cycle, run_esef_sweep
from crible.ingest.enrich.jp import run_edinet
from crible.ingest.enrich.tw import run_twse
from crible.ingest.enrich.uk import load_uk_company_numbers, run_companies_house
from crible.ingest.enrich.us import run_edgar_bulk, run_edgar_cycle, run_fsds

__all__ = [
    "run_esef_cycle", "run_esef_sweep", "run_edgar_cycle", "run_edgar_bulk",
    "run_fsds", "run_companies_house", "run_edinet", "load_uk_company_numbers",
    "run_cvm", "run_twse",
]
