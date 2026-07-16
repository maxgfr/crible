"""Name→LEI→ISIN backfill for the audited-EU layer (FR-010 reach).

FinanceDatabase ships 13,556 of 31,196 European listings without an ISIN
(1,560 of 2,882 FR — counted 2026-07-16), so the GLEIF ISIN→LEI join can
never resolve them and the ESEF sweep skips their audited filings even when
they sit on filings.xbrl.org (e.g. OVH GROUPE, LEI 9695001J8OSOVX4TP939).
The backfill matches those rows against the filings.xbrl.org entities index
by conservatively normalized name, then recovers an ISIN through the
reverse GLEIF mapping — after which the existing sweep needs no change.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from crible.universe import bootstrap_universe


def _frame(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "country": "France", "sector": "Information Technology", "industry": "IT",
        "exchange": "PAR", "currency": "EUR", "market_cap": None, "isin": None,
        "delisted": False,
    }
    return pd.DataFrame([{**defaults, "name": r["symbol"], **r} for r in rows])


@pytest.fixture()
def con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect()


def test_bootstrap_preserves_a_known_isin_when_upstream_has_none(con) -> None:
    """The nightly re-bootstrap must not erase a backfilled ISIN: upstream
    NULL means 'unknown', not 'no ISIN' — a locally resolved value wins."""
    bootstrap_universe(con, _frame([{"symbol": "OVH.PA", "name": "OVH Groupe SA"}]))
    con.execute("UPDATE companies SET isin = 'FR0014005HJ9' WHERE symbol = 'OVH.PA'")

    bootstrap_universe(con, _frame([{"symbol": "OVH.PA", "name": "OVH Groupe SA"}]))

    assert con.execute(
        "SELECT isin FROM companies WHERE symbol = 'OVH.PA'"
    ).fetchone()[0] == "FR0014005HJ9"

    # a real upstream ISIN still wins over the local value
    bootstrap_universe(
        con, _frame([{"symbol": "OVH.PA", "name": "OVH Groupe SA", "isin": "FR0014005HJ8"}])
    )
    assert con.execute(
        "SELECT isin FROM companies WHERE symbol = 'OVH.PA'"
    ).fetchone()[0] == "FR0014005HJ8"


# ------------------------------------------------------------------ backfill


OVH_LEI = "9695001J8OSOVX4TP939"
OVH_ISIN = "FR0014005HJ9"


def _isin(con, symbol: str) -> str | None:
    return con.execute("SELECT isin FROM companies WHERE symbol = ?", [symbol]).fetchone()[0]


def test_backfill_matches_normalized_names_and_recovers_the_isin(con) -> None:
    """The OVH case end-to-end: filings.xbrl.org says 'OVH GROUPE', the
    universe says 'OVH Groupe SA' — normalization (case, accents, trailing
    legal form) must bridge them, the reverse GLEIF map recovers the ISIN."""
    from crible.ingest.enrich.backfill import backfill_missing_isins

    bootstrap_universe(con, _frame([
        {"symbol": "OVH.PA", "name": "OVH Groupe SA"},
        {"symbol": "STAY.PA", "name": "Société Anonyme Unrelated"},
    ]))

    report = backfill_missing_isins(
        con,
        entities=[(OVH_LEI, "OVH GROUPE"), ("LEI-ELSEWHERE-000000", "SOMEONE ELSE AG")],
        mapping={OVH_ISIN: OVH_LEI, "FR0000000001": "LEI-OTHER-0000000000"},
    )

    assert _isin(con, "OVH.PA") == OVH_ISIN
    assert _isin(con, "STAY.PA") is None
    assert report["backfilled"] == 1


def test_backfill_skips_names_shared_by_distinct_leis(con) -> None:
    """A wrong ISIN silently corrupts the audited layer; a missing one only
    keeps the status quo — same normalized name on two LEIs must be skipped."""
    from crible.ingest.enrich.backfill import backfill_missing_isins

    bootstrap_universe(con, _frame([{"symbol": "GEN.PA", "name": "Generale Holding"}]))

    report = backfill_missing_isins(
        con,
        entities=[("LEI-A-000000000000000", "GENERALE HOLDING SA"),
                  ("LEI-B-000000000000000", "Générale Holding")],
        mapping={"FR0000000010": "LEI-A-000000000000000",
                 "FR0000000011": "LEI-B-000000000000000"},
    )

    assert _isin(con, "GEN.PA") is None
    assert report["backfilled"] == 0
    assert report["ambiguous"] == 1


def test_backfill_never_overwrites_and_is_idempotent(con) -> None:
    from crible.ingest.enrich.backfill import backfill_missing_isins

    bootstrap_universe(con, _frame([
        {"symbol": "OVH.PA", "name": "OVH Groupe SA"},
        {"symbol": "AIR.PA", "name": "Airbus SE", "isin": "NL0000235190"},
    ]))
    entities = [(OVH_LEI, "OVH GROUPE"), ("LEI-AIRBUS-00000000000", "AIRBUS")]
    mapping = {OVH_ISIN: OVH_LEI, "XX0000000001": "LEI-AIRBUS-00000000000"}

    first = backfill_missing_isins(con, entities=entities, mapping=mapping)
    second = backfill_missing_isins(con, entities=entities, mapping=mapping)

    assert _isin(con, "AIR.PA") == "NL0000235190"  # real ISIN untouched
    assert _isin(con, "OVH.PA") == OVH_ISIN
    assert first["backfilled"] == 1
    assert second["backfilled"] == 0  # nothing left to do


def test_backfill_counts_leis_the_gleif_file_does_not_know(con) -> None:
    from crible.ingest.enrich.backfill import backfill_missing_isins

    bootstrap_universe(con, _frame([{"symbol": "NEW.PA", "name": "Fresh Filer"}]))

    report = backfill_missing_isins(
        con, entities=[("LEI-FRESH-000000000000", "FRESH FILER")], mapping={}
    )

    assert _isin(con, "NEW.PA") is None
    assert report["no_isin_for_lei"] == 1


def test_backfill_dual_listings_share_the_entity(con) -> None:
    """Two universe rows for one company (e.g. .PA + .IL cross-listing) both
    recover an ISIN — the sweep groups them under the one LEI anyway."""
    from crible.ingest.enrich.backfill import backfill_missing_isins

    bootstrap_universe(con, _frame([
        {"symbol": "OVH.PA", "name": "OVH Groupe SA"},
        {"symbol": "0ABC.IL", "name": "OVH Groupe SA", "country": "United Kingdom"},
    ]))

    report = backfill_missing_isins(
        con, entities=[(OVH_LEI, "OVH GROUPE")], mapping={OVH_ISIN: OVH_LEI}
    )

    assert _isin(con, "OVH.PA") == OVH_ISIN
    assert _isin(con, "0ABC.IL") == OVH_ISIN
    assert report["backfilled"] == 2


# ------------------------------------------------------------ entities index


class FakeEntitiesHttp:
    """JSON:API /api/entities double, same shape as filings.xbrl.org."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict | None = None, **_kw):
        self.requests.append((url, params or {}))

        class _Resp:
            status_code = 200

            def raise_for_status(self) -> None: ...

            def json(self) -> dict:
                return {
                    "data": [
                        {"attributes": {"identifier": OVH_LEI, "name": "OVH GROUPE"}},
                        {"attributes": {"identifier": None, "name": "BROKEN ROW"}},
                        # the live index carries Ukrainian filers keyed by an
                        # 8-digit EDRPOU code, not an LEI (probed 2026-07-16)
                        {"attributes": {"identifier": "05538856", "name": "НЕ-LEI РЯДОК"}},
                    ],
                    "meta": {"count": 9042},
                }

        return _Resp()


def test_entities_index_pages_the_lei_name_pairs() -> None:
    from crible.providers.esef import EsefClient

    client = EsefClient(http=FakeEntitiesHttp())
    entities, count = client.entities_index(page_size=200, page_number=3)

    # rows without a REAL LEI (missing, or a non-LEI national code) are dropped
    assert entities == [(OVH_LEI, "OVH GROUPE")]
    assert count == 9042
    url, params = client._http.requests[0]
    assert url.endswith("/api/entities")
    assert params["page[size]"] == 200
    assert params["page[number]"] == 3


# ------------------------------------------------------------- sweep wiring


class BackfillingIndexClient:
    """Sweep double: OVH files on filings.xbrl.org while its universe row has
    no ISIN — only the name→LEI backfill can connect the two."""

    def __init__(self) -> None:
        self.json_fetches = 0

    def entities_index(self, page_size: int = 100, page_number: int = 1):
        if page_number > 1:
            return [], 1
        return [(OVH_LEI, "OVH GROUPE")], 1

    def filings_index(self, page_size: int = 100, page_number: int = 1):
        if page_number > 1:
            return [], 1
        return [{"attributes": {"json_url": f"/{OVH_LEI}/2025-12-31/ovh.json"}}], 1

    def fetch_xbrl_json(self, filing):
        from tests.test_fr010_esef import XBRL_JSON

        self.json_fetches += 1
        return XBRL_JSON


def test_sweep_backfills_isins_then_enriches_in_the_same_run(tmp_path, monkeypatch) -> None:
    """End-to-end OVH scenario: universe row without ISIN + filed accounts on
    filings.xbrl.org → one sweep backfills the ISIN AND ingests the filing."""
    import duckdb as _duckdb

    from crible.ingest.service import run_esef_sweep

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))
    db = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    bootstrap_universe(db, _frame([{"symbol": "OVH.PA", "name": "OVH Groupe SA"}]))
    db.close()

    outcome = run_esef_sweep(
        limit=10, client=BackfillingIndexClient(), mapping={OVH_ISIN: OVH_LEI}
    )

    assert outcome["backfilled"] == 1
    assert outcome["enriched"] == ["OVH.PA"]
    assert list(tmp_path.glob("raw/provider=esef/symbol=OVH.PA/*.parquet"))

    db = _duckdb.connect(str(tmp_path / "crible.duckdb"))
    assert db.execute("SELECT isin FROM companies WHERE symbol = 'OVH.PA'").fetchone()[0] == OVH_ISIN
    db.close()


class ExplodingClient:
    """Any touch means the early-exit contract is broken."""

    def __getattr__(self, name):
        raise AssertionError(f"limit=0 must not touch the client (called {name})")


def test_esef_sweep_limit_zero_is_a_pure_no_op(tmp_path, monkeypatch) -> None:
    """The crawl-marathon runs `refresh --esef-limit 0`: no entities paging,
    no backfill, no index walk — zero requests to filings.xbrl.org."""
    from crible.ingest.service import run_esef_sweep

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))

    outcome = run_esef_sweep(limit=0, client=ExplodingClient(), mapping={"X": "Y"})

    assert outcome["enriched"] == []
    assert outcome["skipped"] == "limit 0"


def test_edgar_cycle_limit_zero_is_a_pure_no_op(tmp_path, monkeypatch) -> None:
    from crible.ingest.service import run_edgar_cycle

    monkeypatch.setenv("CRIBLE_DATA_DIR", str(tmp_path))

    outcome = run_edgar_cycle(limit=0, client=ExplodingClient())

    assert outcome["enriched"] == []
    assert outcome["skipped"] == "limit 0"
