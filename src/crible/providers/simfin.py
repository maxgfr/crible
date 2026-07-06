"""FR-013 — SimFin plugin (free key): bulk US fundamentals.

Free tier: ~5,000 US stocks, 20+ years of history via API/bulk download; the
official Python client is dormant, so we call the REST API directly. Facts are
stored as provider='simfin' raw statements alongside yfinance data — never
overwriting fresher facts (raw layer is append-only, reconciliation is
provider-aware). An invalid key self-disables the plugin for the session."""

from __future__ import annotations

import logging

import pandas as pd

from crible.providers.base import FetchResult, StatementPayload

log = logging.getLogger("crible.providers.simfin")

API_BASE = "https://prod.simfin.com/api/v3"
STATEMENT_KINDS = {"PL": "income", "BS": "balance", "CF": "cashflow"}


class SimFinProvider:
    id = "simfin"
    kind = "free-key"
    key_env_var = "SIMFIN_KEY"
    requests_per_fetch = 1

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

            self._http = httpx.Client(
                timeout=30,
                headers={"Authorization": self._env.get(self.key_env_var, "")},
            )
        return self._http

    def fetch_statements(self, symbol: str) -> FetchResult:
        if self._session_disabled:
            return FetchResult(symbol=symbol, provider=self.id, statements=[], requests_used=0)
        response = self._client().get(
            f"{API_BASE}/companies/statements/compact",
            params={"ticker": symbol, "statements": "PL,BS,CF", "period": "FY"},
        )
        if response.status_code in (401, 403):
            # FR-013 AC-2: invalid key → self-disable with a clear log line
            self._session_disabled = True
            log.error(
                "provider simfin disabled for this session: key rejected (%d) — fix %s",
                response.status_code,
                self.key_env_var,
            )
            return FetchResult(symbol=symbol, provider=self.id, statements=[], requests_used=1)
        response.raise_for_status()
        return FetchResult(
            symbol=symbol,
            provider=self.id,
            statements=list(self._parse(response.json())),
            requests_used=1,
        )

    @staticmethod
    def _parse(payload) -> list[StatementPayload]:
        statements: list[StatementPayload] = []
        for company in payload if isinstance(payload, list) else []:
            for block in company.get("statements", []):
                kind = STATEMENT_KINDS.get(block.get("statement"))
                if kind is None:
                    continue
                columns = block.get("columns", [])
                rows = block.get("data", [])
                if not columns or not rows:
                    continue
                frame = pd.DataFrame(rows, columns=columns)
                period_col = next(
                    (c for c in ("Fiscal Year", "fiscal_year", "Report Date") if c in frame.columns),
                    None,
                )
                if period_col:
                    frame = frame.rename(columns={period_col: "period"})
                    frame["period"] = frame["period"].astype(str)
                statements.append(StatementPayload(statement_type=kind, freq="annual", frame=frame))
        return statements
