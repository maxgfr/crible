"""FR-013 — FMP free-tier plugin: schema validation only (US-only, 250 req/day
on the free tier — its role is validating provider schemas, not feeding the
screener). Stored facts carry provider='fmp_free'."""

from __future__ import annotations

import logging

import pandas as pd

from crible.providers.base import FetchResult, StatementPayload

log = logging.getLogger("crible.providers.fmp_free")

API_BASE = "https://financialmodelingprep.com/api/v3"
ENDPOINTS = {
    "income": "income-statement",
    "balance": "balance-sheet-statement",
    "cashflow": "cash-flow-statement",
}


class FmpFreeProvider:
    id = "fmp_free"
    kind = "free-key"
    key_env_var = "FMP_KEY"
    requests_per_fetch = 3

    def __init__(self, env: dict[str, str] | None = None, http=None) -> None:
        import os

        self._env = env if env is not None else dict(os.environ)
        self._http = http
        self._session_disabled = False

    def enabled(self, env: dict[str, str]) -> bool:
        return bool(env.get(self.key_env_var)) and not self._session_disabled

    def _client(self):
        if self._http is None:
            import httpx

            self._http = httpx.Client(timeout=30)
        return self._http

    def fetch_statements(self, symbol: str) -> FetchResult:
        if self._session_disabled:
            return FetchResult(symbol=symbol, provider=self.id, statements=[], requests_used=0)
        key = self._env.get(self.key_env_var, "")
        statements: list[StatementPayload] = []
        for statement_type, endpoint in ENDPOINTS.items():
            response = self._client().get(
                f"{API_BASE}/{endpoint}/{symbol}", params={"apikey": key, "limit": 5}
            )
            if response.status_code in (401, 403):
                self._session_disabled = True
                log.error(
                    "provider fmp_free disabled for this session: key rejected (%d) — fix %s",
                    response.status_code,
                    self.key_env_var,
                )
                return FetchResult(symbol=symbol, provider=self.id, statements=[], requests_used=1)
            response.raise_for_status()
            rows = response.json()
            if isinstance(rows, list) and rows:
                frame = pd.DataFrame(rows)
                if "date" in frame.columns:
                    frame = frame.rename(columns={"date": "period"})
                    frame["period"] = frame["period"].astype(str).str[:4]
                statements.append(
                    StatementPayload(statement_type=statement_type, freq="annual", frame=frame)
                )
        return FetchResult(symbol=symbol, provider=self.id, statements=statements, requests_used=3)
