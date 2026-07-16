"""FR-001 — the screening universe, bootstrapped from FinanceDatabase.

FinanceDatabase ships ~161k equities as CSVs whose ``symbol`` column is the
Yahoo-suffixed ticker (e.g. ``ABN.AS``), directly usable by yfinance. This
module loads such a frame into the ``companies`` table with a crawl priority
of region tier (europe → us → world) THEN cap class (Mega → … → Nano) within
the tier: priority = region×8 + cap rank.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import duckdb
import pandas as pd

REQUIRED_COLUMNS = {"symbol", "name", "country", "sector", "industry", "exchange", "currency"}

# EU-27 + EEA + UK + CH — full country names as used by FinanceDatabase.
EUROPE_COUNTRIES = {
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Czechia",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Iceland", "Ireland", "Italy", "Latvia", "Liechtenstein", "Lithuania",
    "Luxembourg", "Malta", "Monaco", "Netherlands", "Norway", "Poland", "Portugal",
    "Romania", "Slovakia", "Slovenia", "Spain", "Sweden", "Switzerland",
    "United Kingdom",
}

REGION_PRIORITY = {"europe": 0, "us": 1, "world": 2}

# Within a region, larger caps crawl first: the budgeted Yahoo crawl feeds
# prices and quarterly statements, and Mega/Large are the names people
# actually screen — the long tail trickles in behind them. Region always
# dominates (priority = region×8 + rank; max rank 6 < 8).
CAP_RANK = {
    "Mega Cap": 0, "Large Cap": 1, "Mid Cap": 2,
    "Small Cap": 3, "Micro Cap": 4, "Nano Cap": 5,
}
UNKNOWN_CAP_RANK = 6

# FinanceDatabase country names → ISO-3166 alpha-2. The DSL filters on these
# codes (country IN ('FR','DE')); unmapped names fall back to the full name so
# filtering stays possible either way (country_name always keeps the original).
COUNTRY_TO_ISO = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY",
    "Czech Republic": "CZ", "Czechia": "CZ", "Denmark": "DK", "Estonia": "EE", "Finland": "FI",
    "France": "FR", "Germany": "DE", "Greece": "GR", "Hungary": "HU", "Iceland": "IS",
    "Ireland": "IE", "Italy": "IT", "Latvia": "LV", "Liechtenstein": "LI", "Lithuania": "LT",
    "Luxembourg": "LU", "Malta": "MT", "Monaco": "MC", "Netherlands": "NL", "Norway": "NO",
    "Poland": "PL", "Portugal": "PT", "Romania": "RO", "Slovakia": "SK", "Slovenia": "SI",
    "Spain": "ES", "Sweden": "SE", "Switzerland": "CH", "United Kingdom": "GB",
    "United States": "US", "Canada": "CA", "Japan": "JP", "China": "CN", "Hong Kong": "HK",
    "Taiwan": "TW", "South Korea": "KR", "India": "IN", "Australia": "AU", "New Zealand": "NZ",
    "Brazil": "BR", "Mexico": "MX", "Argentina": "AR", "Chile": "CL", "South Africa": "ZA",
    "Israel": "IL", "Turkey": "TR", "Saudi Arabia": "SA", "United Arab Emirates": "AE",
    "Singapore": "SG", "Malaysia": "MY", "Indonesia": "ID", "Thailand": "TH",
    "Philippines": "PH", "Vietnam": "VN", "Russia": "RU", "Ukraine": "UA",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    symbol           VARCHAR PRIMARY KEY,
    name             VARCHAR,
    isin             VARCHAR,
    country          VARCHAR,
    country_name     VARCHAR,
    region           VARCHAR NOT NULL,
    crawl_priority   TINYINT NOT NULL,
    sector           VARCHAR,
    industry         VARCHAR,
    exchange         VARCHAR,
    currency         VARCHAR,
    market_cap_class VARCHAR,
    delisted         BOOLEAN DEFAULT FALSE,
    updated_at       TIMESTAMP DEFAULT now()
)
"""


class UniverseSourceError(RuntimeError):
    """The universe source (FinanceDatabase) failed or produced an unusable frame."""


@dataclass(frozen=True)
class BootstrapReport:
    loaded: int
    dropped: int
    by_region: dict[str, int]


def region_for(country: str | None) -> str:
    if country in EUROPE_COUNTRIES:
        return "europe"
    if country == "United States":
        return "us"
    return "world"


def bootstrap_universe(con: duckdb.DuckDBPyConnection, frame: pd.DataFrame) -> BootstrapReport:
    """Idempotently upsert a FinanceDatabase-shaped frame into ``companies``.

    Validates before touching the table: on bad input the existing universe is
    left exactly as it was (FR-001 failure path).
    """
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise UniverseSourceError(
            f"FinanceDatabase frame is missing required columns: {sorted(missing)}"
        )

    rows = frame.copy()
    before = len(rows)
    rows = rows[rows["symbol"].notna() & (rows["symbol"].astype(str).str.strip() != "")]
    dropped = before - len(rows)

    rows["region"] = rows["country"].map(region_for)
    rows["country_name"] = rows["country"]
    rows["country"] = rows["country_name"].map(lambda n: COUNTRY_TO_ISO.get(n, n))
    if "isin" not in rows.columns:
        rows["isin"] = None
    if "delisted" not in rows.columns:
        rows["delisted"] = False
    market_cap = rows["market_cap"] if "market_cap" in rows.columns else None
    rows["market_cap_class"] = market_cap if market_cap is not None else None
    rows["crawl_priority"] = (
        rows["region"].map(REGION_PRIORITY) * 8
        + rows["market_cap_class"].map(CAP_RANK).fillna(UNKNOWN_CAP_RANK).astype("int64")
    )

    staged = rows[
        [
            "symbol", "name", "isin", "country", "country_name", "region", "crawl_priority",
            "sector", "industry", "exchange", "currency", "market_cap_class", "delisted",
        ]
    ]

    con.execute(SCHEMA)
    con.register("staged_universe", staged)
    con.execute("BEGIN")
    try:
        con.execute(
            """
            INSERT INTO companies (
                symbol, name, isin, country, country_name, region, crawl_priority,
                sector, industry, exchange, currency, market_cap_class, delisted, updated_at
            )
            SELECT symbol, name, isin, country, country_name, region, crawl_priority,
                   sector, industry, exchange, currency, market_cap_class,
                   coalesce(delisted, FALSE), now()
            FROM staged_universe
            ON CONFLICT (symbol) DO UPDATE SET
                name = excluded.name,
                -- upstream NULL means 'unknown', not 'no ISIN': a locally
                -- backfilled ISIN (name→LEI→ISIN, FR-010) must survive the
                -- nightly re-bootstrap; a real upstream value still wins
                isin = coalesce(excluded.isin, companies.isin),
                country = excluded.country,
                country_name = excluded.country_name,
                region = excluded.region,
                crawl_priority = excluded.crawl_priority,
                sector = excluded.sector,
                industry = excluded.industry,
                exchange = excluded.exchange,
                currency = excluded.currency,
                market_cap_class = excluded.market_cap_class,
                delisted = excluded.delisted,
                updated_at = now()
            """
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.unregister("staged_universe")

    by_region = dict(
        con.execute("SELECT region, count(*) FROM companies GROUP BY region").fetchall()
    )
    return BootstrapReport(loaded=len(staged), dropped=dropped, by_region=by_region)


def export_universe_parquet(con: duckdb.DuckDBPyConnection, data_dir) -> None:
    """Publish the universe as Parquet (atomic) so readers never open the
    ingest-owned DuckDB file (ADR-0003: single writer per layer)."""
    from pathlib import Path

    directory = Path(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / ".tmp-universe.parquet"
    final = directory / "universe.parquet"
    con.execute(f"COPY companies TO '{tmp.as_posix()}' (FORMAT parquet)")
    tmp.rename(final)


def restore_universe_from_parquet(con: duckdb.DuckDBPyConnection, path) -> int:
    """Restore ``companies`` from a previously exported universe.parquet — the
    last-good fallback when FinanceDatabase is unreachable.

    The parquet is a straight COPY of the table, so rows are inserted as-is;
    routing through ``bootstrap_universe`` would re-map the already-ISO country
    codes through ``region_for`` and mis-tag every row as world.
    """
    from pathlib import Path

    file = Path(path)
    if not file.exists():
        raise UniverseSourceError(f"no last-good universe parquet at {file}")
    con.execute(SCHEMA)
    con.execute(
        f"INSERT OR REPLACE INTO companies SELECT * FROM read_parquet('{file.as_posix()}')"
    )
    return con.execute("SELECT count(*) FROM companies").fetchone()[0]


def fetch_financedatabase() -> pd.DataFrame:
    """Download the full FinanceDatabase equity universe (network)."""
    try:
        import financedatabase as fd

        equities = fd.Equities()
        frame = equities.select().reset_index()
    except Exception as exc:  # noqa: BLE001 — any failure means the source is unusable
        raise UniverseSourceError(f"FinanceDatabase download failed: {exc}") from exc
    frame = frame.rename(columns={"symbol": "symbol"})
    return frame


def refresh_universe(
    con: duckdb.DuckDBPyConnection,
    fetch: Callable[[], pd.DataFrame] = fetch_financedatabase,
) -> BootstrapReport:
    """Fetch + bootstrap; a fetch failure never touches the existing table."""
    try:
        frame = fetch()
    except UniverseSourceError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise UniverseSourceError(f"FinanceDatabase source unreachable: {exc}") from exc
    return bootstrap_universe(con, frame)
