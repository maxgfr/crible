"""The primary keyless provider: Yahoo Finance via yfinance (FR-002, ADR-0004).

Thin wrapper: yfinance owns its curl_cffi session (never inject a caching
session); Yahoo depth is ~4 annual periods / 4-5 quarters. Rate-limit errors
are normalised to RateLimitedError so the crawler can back off; a per-call
watchdog is the crawler's job, not ours.
"""

from __future__ import annotations

import pandas as pd

from crible.providers.base import FetchResult, RateLimitedError, StatementPayload

RATE_LIMIT_MARKERS = ("429", "too many requests", "rate limit", "crumb")


def _normalise(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    if frame is None or frame.empty:
        return None
    out = frame.T.reset_index().rename(columns={"index": "period"})
    out["period"] = out["period"].astype(str)
    out.columns = [str(c) for c in out.columns]
    return out


class YFinanceProvider:
    id = "yfinance"
    kind = "keyless"

    def enabled(self, env: dict[str, str]) -> bool:
        return True

    def fetch_statements(self, symbol: str) -> FetchResult:
        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)
            statements: list[StatementPayload] = []
            getters = {
                "income": ticker.get_income_stmt,
                "balance": ticker.get_balance_sheet,
                "cashflow": ticker.get_cash_flow,
            }
            for statement_type, getter in getters.items():
                for freq in ("yearly", "quarterly"):
                    frame = _normalise(getter(freq=freq))
                    if frame is not None:
                        statements.append(
                            StatementPayload(
                                statement_type=statement_type,
                                freq="annual" if freq == "yearly" else "quarterly",
                                frame=frame,
                            )
                        )
            prices = ticker.history(period="1y", auto_adjust=False)
            prices = prices.reset_index() if prices is not None and not prices.empty else None
        except Exception as exc:  # noqa: BLE001 — classify then re-raise
            text = str(exc).lower()
            if any(marker in text for marker in RATE_LIMIT_MARKERS):
                raise RateLimitedError(str(exc)) from exc
            raise

        # 3 statement types × 2 freqs + 1 history call ≈ 7 Yahoo requests
        return FetchResult(symbol=symbol, provider=self.id, statements=statements, prices=prices, requests_used=7)
