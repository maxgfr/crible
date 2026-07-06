"""FR-014 — the EODHD stub plugin: proves the single planned paid switch
without paying.

With EODHD_KEY set, initialization validates the key via one metadata call
(/api/user) and reports the detected tier. A free-tier key (20 calls/day,
fundamentals pay-gated — grounded in the SRD) yields 'insufficient tier for
fundamentals' and the plugin stays disabled; a paid Fundamentals-feed key
would activate it. Full endpoint schemas + field mapping live in
docs/prds/eodhd.md."""

from __future__ import annotations

import logging

log = logging.getLogger("crible.providers.eodhd")

USER_ENDPOINT = "https://eodhd.com/api/user"
# subscription names that include the Fundamentals feed (validated in the PRD;
# re-checked at purchase time)
FUNDAMENTALS_TIERS = {"fundamentals", "all-in-one", "all_in_one", "extended"}


class EodhdProvider:
    id = "eodhd"
    kind = "paid"
    key_env_var = "EODHD_KEY"
    requests_per_fetch = 10  # one fundamentals call costs 10 API calls at EODHD

    def __init__(self, env: dict[str, str] | None = None, http=None) -> None:
        import os

        self._env = env if env is not None else dict(os.environ)
        self._http = http
        self._tier: str | None = None
        self._validated = False

    def _client(self):
        if self._http is None:
            import httpx

            self._http = httpx.Client(timeout=15)
        return self._http

    def detected_tier(self) -> str | None:
        """One metadata call — never spends fundamentals quota (FR-014 AC-2)."""
        if self._validated:
            return self._tier
        self._validated = True
        key = self._env.get(self.key_env_var)
        if not key:
            return None
        try:
            response = self._client().get(USER_ENDPOINT, params={"api_token": key, "fmt": "json"})
            response.raise_for_status()
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            log.error("eodhd key validation failed: %s — plugin stays disabled", exc)
            self._tier = None
            return None
        self._tier = str(body.get("subscriptionType") or body.get("subscription") or "free").lower()
        return self._tier

    def enabled(self, env: dict[str, str]) -> bool:
        if not env.get(self.key_env_var):
            return False
        tier = self.detected_tier()
        if tier is None:
            return False
        if not any(marker in tier for marker in FUNDAMENTALS_TIERS):
            log.info(
                "provider eodhd: key valid but tier %r has insufficient tier for fundamentals"
                " — plugin stays disabled (the switch path is proven; see docs/prds/eodhd.md)",
                tier,
            )
            return False
        log.info("provider eodhd: tier %r includes fundamentals — plugin ACTIVE", tier)
        return True

    def fetch_statements(self, symbol: str):  # pragma: no cover — paid path
        raise NotImplementedError(
            "EODHD fundamentals fetching activates with a paid Fundamentals-feed key; "
            "endpoint schemas and field mapping are specified in docs/prds/eodhd.md"
        )
