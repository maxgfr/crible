"""Trailing-twelve-months figures — v1, columns on the latest row.

Quarterly statements are crawled (yfinance fetches yearly AND quarterly) but
compute only ever consumed the annual frames. v1 sums the last four clean
quarters into TTM flow figures plus a curated set of price ratios, landed as
COLUMNS on the latest snapshot row — never extra rows, so snapshot_latest's
one-row-per-symbol semantics hold for every consumer (runtime views, ranks,
the drawer's period table).

Reach honesty: the audited providers (EDGAR companyfacts, ESEF) emit
annual-only frames today, so TTM rides the yfinance-crawled tier — hundreds
of symbols, large caps first under the cap-tiered crawl priority. The named
v2 is EDGAR 10-Q extraction. Balance items are point-in-time and excluded by
design; provider restatements can make a TTM sum drift from the annual
figure — never reconciled, documented.
"""

from __future__ import annotations

import pandas as pd

TTM_FLOWS = ["ttm_revenue", "ttm_net_income", "ttm_operating_cashflow", "ttm_free_cash_flow"]
TTM_RATIOS = ["price_to_earnings_ttm", "price_to_sales_ttm", "ttm_fcf_yield"]
TTM_COLUMNS = [*TTM_FLOWS, *TTM_RATIOS]

# four quarterly period-ends must span roughly a year, first to last —
# guards against gaps, duplicated quarters and semi-annual reporters
MIN_SPAN_DAYS = 240
MAX_SPAN_DAYS = 300

_CORE = ["revenue", "net_income", "operating_cashflow"]


def ttm_from_quarterly(frames: dict[tuple[str, str], pd.DataFrame]) -> dict[str, float]:
    """{ttm_revenue, ttm_net_income, ttm_operating_cashflow,
    ttm_free_cash_flow} from the quarterly raw frames — {} when fewer than
    four clean, properly spaced quarters exist (NaN beats a wrong sum)."""
    from crible.compute.canonical import build_canonical

    quarterly = build_canonical(frames, freq="quarterly")
    if quarterly.empty:
        return {}
    flows = quarterly[[*_CORE, "free_cash_flow"]].copy()
    core = flows.dropna(subset=_CORE)
    if len(core) < 4:
        return {}
    last4 = core.tail(4)
    dates = pd.to_datetime(pd.Index(last4.index).astype(str), errors="coerce")
    if dates.isna().any():
        return {}
    span = (dates.max() - dates.min()).days
    if not (MIN_SPAN_DAYS <= span <= MAX_SPAN_DAYS):
        return {}
    fcf = last4["free_cash_flow"]
    return {
        "ttm_revenue": float(last4["revenue"].sum()),
        "ttm_net_income": float(last4["net_income"].sum()),
        "ttm_operating_cashflow": float(last4["operating_cashflow"].sum()),
        # a single missing quarter nulls the FCF sum — never fabricated
        "ttm_free_cash_flow": float(fcf.sum()) if fcf.notna().all() else float("nan"),
    }


def ttm_ratios(ttm: dict[str, float], market_cap: float) -> dict[str, float]:
    """The curated price ratios over the TTM flows (latest row only; the
    price is never back-dated). No reflection re-run — three ratios, spelled
    out, negative-earnings P/E undefined like everywhere else."""
    out = {col: float("nan") for col in TTM_RATIOS}
    if pd.isna(market_cap) or market_cap <= 0 or not ttm:
        return out
    net_income = ttm.get("ttm_net_income", float("nan"))
    if pd.notna(net_income) and net_income > 0:
        out["price_to_earnings_ttm"] = market_cap / net_income
    revenue = ttm.get("ttm_revenue", float("nan"))
    if pd.notna(revenue) and revenue > 0:
        out["price_to_sales_ttm"] = market_cap / revenue
    fcf = ttm.get("ttm_free_cash_flow", float("nan"))
    if pd.notna(fcf):
        out["ttm_fcf_yield"] = fcf / market_cap
    return out
