"""FR-013 / FR-014 — keyed provider plugins: gating, self-disable on bad keys,
SimFin fact storage, and the EODHD tier-detection stub."""

from __future__ import annotations

import logging


from crible.providers.base import ProviderRegistry
from crible.providers.eodhd import EodhdProvider
from crible.providers.fmp_free import FmpFreeProvider
from crible.providers.simfin import SimFinProvider


class FakeResponse:
    def __init__(self, status_code: int, body) -> None:
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    def __init__(self, responses) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url, params=None, **_):
        self.calls.append(url)
        return self.responses.pop(0)


SIMFIN_PAYLOAD = [
    {
        "ticker": "AAPL",
        "statements": [
            {
                "statement": "PL",
                "columns": ["Fiscal Year", "Revenue", "Net Income"],
                "data": [[2024, 391000, 94000], [2023, 383000, 97000]],
            },
            {
                "statement": "BS",
                "columns": ["Fiscal Year", "Total Assets"],
                "data": [[2024, 364000]],
            },
        ],
    }
]


def test_fr013_no_keys_means_every_keyed_plugin_disables_with_one_log_line(caplog) -> None:
    registry = ProviderRegistry(env={})
    plugins = [SimFinProvider(env={}), FmpFreeProvider(env={}), EodhdProvider(env={})]
    with caplog.at_level(logging.INFO, logger="crible.providers"):
        active = registry.activate(plugins)
    assert active == []
    disabled = [r for r in caplog.records if "disabled (no key configured)" in r.message]
    assert len(disabled) == 3


def test_fr013_simfin_valid_key_stores_annual_facts_with_provider_tag() -> None:
    http = FakeHttp([FakeResponse(200, SIMFIN_PAYLOAD)])
    provider = SimFinProvider(env={"SIMFIN_KEY": "k"}, http=http)
    assert provider.enabled({"SIMFIN_KEY": "k"})
    result = provider.fetch_statements("AAPL")
    assert result.provider == "simfin"
    kinds = {s.statement_type for s in result.statements}
    assert kinds == {"income", "balance"}
    income = next(s for s in result.statements if s.statement_type == "income")
    assert list(income.frame["period"]) == ["2024", "2023"]


def test_fr013_invalid_key_self_disables_with_clear_log_and_no_crash(caplog) -> None:
    http = FakeHttp([FakeResponse(401, {})])
    provider = SimFinProvider(env={"SIMFIN_KEY": "bad"}, http=http)
    with caplog.at_level(logging.ERROR):
        result = provider.fetch_statements("AAPL")
    assert result.statements == []
    assert provider._session_disabled
    assert not provider.enabled({"SIMFIN_KEY": "bad"})  # disabled for the session
    assert any("SIMFIN_KEY" in r.message for r in caplog.records)


def test_fr014_eodhd_free_key_reports_insufficient_tier_and_stays_disabled(caplog) -> None:
    http = FakeHttp([FakeResponse(200, {"subscriptionType": "free"})])
    provider = EodhdProvider(env={"EODHD_KEY": "freekey"}, http=http)
    with caplog.at_level(logging.INFO):
        assert provider.enabled({"EODHD_KEY": "freekey"}) is False
    assert any("insufficient tier for fundamentals" in r.message for r in caplog.records)
    # exactly ONE metadata call — never spends fundamentals quota
    assert http.calls == ["https://eodhd.com/api/user"]


def test_fr014_eodhd_fundamentals_tier_would_activate() -> None:
    http = FakeHttp([FakeResponse(200, {"subscriptionType": "Fundamentals Data Feed"})])
    provider = EodhdProvider(env={"EODHD_KEY": "paidkey"}, http=http)
    assert provider.enabled({"EODHD_KEY": "paidkey"}) is True


def test_fr013_fmp_free_invalid_key_self_disables() -> None:
    http = FakeHttp([FakeResponse(403, {})])
    provider = FmpFreeProvider(env={"FMP_KEY": "bad"}, http=http)
    result = provider.fetch_statements("AAPL")
    assert result.statements == []
    assert not provider.enabled({"FMP_KEY": "bad"})
