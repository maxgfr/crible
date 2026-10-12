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
    # 3 statement types × 2 freqs + 1 history call + 1 profile call (the
    # statements' currency) — charged against the budget up front
    requests_per_fetch = 8

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

        # the statements' currency (BREN.JK files in USD, quotes in IDR) and
        # the price's (CCEP.L is listed "EUR" but trades in pence): the
        # snapshot prices the company in the first from the second. Best
        # effort — an unknown currency only means no conversion, never a
        # failed fetch
        info = _profile(ticker) if statements else {}
        currency = _text(info.get("financialCurrency"))
        if currency:
            statements = [
                StatementPayload(p.statement_type, p.freq, p.frame.assign(_currency=currency))
                for p in statements
            ]
        quoted_in = _text(info.get("currency"))
        if quoted_in and prices is not None:
            prices = prices.assign(_quote_currency=quoted_in)
        return FetchResult(symbol=symbol, provider=self.id, statements=statements, prices=prices)


def _profile(ticker) -> dict:
    try:
        info = ticker.get_info()
    except Exception:  # noqa: BLE001 — optional metadata, see the caller
        return {}
    return info if isinstance(info, dict) else {}


def _text(value) -> str | None:
    return (str(value).strip() or None) if value else None
