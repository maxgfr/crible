"""FIX-007 / F8 — keyless FX normalization (ECB rates via Frankfurter).

Ratios are currency-neutral, but absolute magnitudes (revenue, assets…) are in
each company's reporting currency, so cross-currency size screens are
impossible. crible mirrors the ECB daily reference rates and adds companion
`*_eur` columns — never imputed: an unknown currency or missing rate leaves the
column NULL.
"""

from __future__ import annotations

import json
import math

import pandas as pd

from crible.providers.fx import attach_fx, fetch_rates, to_eur

RATES = {"USD": 1.08, "GBP": 0.85}  # units per 1 EUR (Frankfurter/ECB convention)


def test_to_eur_converts_by_the_reporting_currency() -> None:
    assert to_eur(108.0, "USD", RATES) == 100.0  # 108 USD / 1.08 = 100 EUR
    assert to_eur(100.0, "EUR", RATES) == 100.0  # EUR passes through
    assert to_eur(85.0, "GBP", RATES) == 100.0
    # never imputed: unknown currency or non-numeric → None
    assert to_eur(100.0, "JPY", RATES) is None
    assert to_eur(None, "USD", RATES) is None
    assert to_eur(float("nan"), "USD", RATES) is None


def test_attach_fx_adds_eur_companions_without_touching_ratios() -> None:
    snapshot = pd.DataFrame(
        {
            "symbol": ["AAPL", "MC.PA", "X.T"],
            "currency": ["USD", "EUR", "JPY"],
            "revenue": [108.0, 50.0, 1000.0],
            "return_on_equity": [0.3, 0.2, 0.1],  # currency-neutral — must be untouched
        }
    )
    out = attach_fx(snapshot, data_dir=None, rates=RATES)

    assert out.loc[0, "revenue_eur"] == 100.0  # USD → EUR
    assert out.loc[1, "revenue_eur"] == 50.0   # EUR passthrough
    assert math.isnan(out.loc[2, "revenue_eur"])  # JPY has no rate → NULL, not imputed
    # the currency-neutral ratio is byte-for-byte unchanged
    pd.testing.assert_series_equal(out["return_on_equity"], snapshot["return_on_equity"])


def test_attach_fx_fills_only_the_latest_period_per_symbol() -> None:
    """F12 — only the current spot rate is mirrored, so *_eur is filled for the
    latest period only; historical periods stay NULL rather than get today's
    rate applied to a five-year-old figure."""
    snapshot = pd.DataFrame(
        {
            "symbol": ["AAPL", "AAPL"],
            "period": ["2019", "2024"],
            "currency": ["USD", "USD"],
            "revenue": [216.0, 432.0],
        }
    )
    out = attach_fx(snapshot, data_dir=None, rates=RATES).set_index("period")
    assert out.loc["2024", "revenue_eur"] == 400.0  # 432 / 1.08, latest period
    assert math.isnan(out.loc["2019", "revenue_eur"])  # historical → NULL, not spot-rated


class _Resp:
    def __init__(self, body: bytes) -> None:
        self.status_code = 200
        self._body = body
        self.headers = {}

    def raise_for_status(self) -> None:
        pass

    def iter_bytes(self, chunk_size: int = 0):
        yield self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Http:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def stream(self, method, url, headers=None):
        return _Resp(self.body)


def test_fetch_rates_mirrors_and_parses_ecb_rates(tmp_path) -> None:
    body = json.dumps({"base": "EUR", "date": "2026-07-14", "rates": RATES}).encode()
    rates = fetch_rates(tmp_path, http=_Http(body))
    assert rates["USD"] == 1.08 and rates["GBP"] == 0.85
    # landed in the local mirror so a later run can read it offline
    assert (tmp_path / "mirror" / "fx" / "rates.json").exists()
