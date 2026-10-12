"""reconcile — the vectorised merge must match the original cell-by-cell walk
exactly (merged frame, provenance, discrepancy list), on random frames."""

from __future__ import annotations

import numpy as np
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from crible.compute.reconcile import DISCREPANCY_THRESHOLD, reconcile


def _legacy_reconcile(scraped: pd.DataFrame, audited: pd.DataFrame, symbol: str = "?"):
    """The pre-vectorisation implementation, frozen as the reference."""
    merged = scraped.copy()
    extra_periods = [p for p in audited.index if p not in merged.index]
    if extra_periods:
        merged = merged.reindex(list(merged.index) + extra_periods).sort_index()
    audited_fields: dict[str, list[str]] = {}
    discrepancies: list[dict] = []
    for period in audited.index:
        for column in audited.columns:
            audited_value = audited.loc[period, column]
            if pd.isna(audited_value):
                continue
            scraped_value = merged.loc[period, column] if column in merged.columns else float("nan")
            if pd.notna(scraped_value) and audited_value != 0:
                relative = abs(scraped_value - audited_value) / abs(audited_value)
                if relative > DISCREPANCY_THRESHOLD:
                    discrepancies.append(
                        {
                            "symbol": symbol,
                            "field": column,
                            "period": str(period),
                            "scraped": float(scraped_value),
                            "audited": float(audited_value),
                            "relative": round(relative, 4),
                        }
                    )
            merged.loc[period, column] = audited_value
            audited_fields.setdefault(str(period), []).append(column)
    return merged, audited_fields, discrepancies


# reported amounts: cents up to ±10^9 (denormal-scale floats are not data)
CELL = st.one_of(st.just(float("nan")), st.just(0.0), st.integers(-(10**11), 10**11).map(lambda c: c / 100))
YEARS = [str(y) for y in range(2015, 2026)]
COLUMNS = ["revenue", "net_income", "total_assets", "goodwill", "inventory"]


@st.composite
def frames(draw) -> tuple[pd.DataFrame, pd.DataFrame]:
    def frame(columns: list[str]) -> pd.DataFrame:
        periods = sorted(draw(st.sets(st.sampled_from(YEARS), min_size=1, max_size=6)))
        values = {c: [draw(CELL) for _ in periods] for c in columns}
        return pd.DataFrame(values, index=pd.Index(periods, name="period"), dtype=float)

    scraped_cols = draw(st.lists(st.sampled_from(COLUMNS), min_size=1, max_size=5, unique=True))
    audited_cols = draw(st.lists(st.sampled_from(COLUMNS), min_size=1, max_size=5, unique=True))
    return frame(scraped_cols), frame(audited_cols)


@settings(max_examples=300, deadline=None)
@given(frames())
def test_reconcile_matches_the_cell_by_cell_reference(pair) -> None:
    scraped, audited = pair
    merged, fields, discrepancies = _legacy_reconcile(scraped, audited, symbol="S")
    result = reconcile(scraped, audited, symbol="S")
    pd.testing.assert_frame_equal(result.merged, merged, check_dtype=False)
    assert result.audited_fields == fields
    assert result.discrepancies == discrepancies


def test_reconcile_is_faster_than_the_cell_by_cell_walk() -> None:
    """15 periods × 39 fields cost ~15 ms per symbol cell by cell (≈5 min
    over 20k). Relative bound: robust to a loaded CI runner."""
    import time

    rng = np.random.default_rng(1)
    periods = pd.Index([str(y) for y in range(2011, 2026)], name="period")
    columns = [f"f{i}" for i in range(39)]
    scraped = pd.DataFrame(rng.normal(100, 10, (15, 39)), index=periods, columns=columns)
    audited = scraped * (1 + rng.normal(0, 0.005, (15, 39)))  # filings agree within 5 %

    def clock(fn) -> float:
        fn(scraped, audited)  # warm-up
        started = time.perf_counter()
        for _ in range(10):
            fn(scraped, audited)
        return time.perf_counter() - started

    assert clock(reconcile) * 3 < clock(_legacy_reconcile)
