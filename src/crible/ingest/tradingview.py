"""TradingView scanner — keyless whole-market daily snapshots, ~40 countries.

One POST per country returns the ENTIRE stock list with close, currency and
a NUMERIC market cap (`market_cap_basic`) — the census the top-10k ranking
needs, plus daily close freshness for listings no dump covers (EU/world).

Snapshot-only: NO history. Never a series source, never a momentum source —
the column-aware distillate merge (price_import) guarantees a TradingView
quote can refresh a close but never erase a dump's momentum features.

TradingView's ToS forbids scraping: this is an explicitly assumed,
documented redistribution risk — same tier as Yahoo/Stooq/defeatbeta
(docs/DATA-SOURCES.md). Degradable enrichment: a failed country is skipped
and reported, never fatal; last-good = the data-latest restore cycle.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from crible.ingest.price_import import ImportReport, _merge_and_publish, universe_symbols

log = logging.getLogger("crible.ingest.tradingview")

SCAN_URL = "https://scanner.tradingview.com/{country}/scan"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
PAGE_SIZE = 10_000
MAX_ROWS_PER_COUNTRY = 80_000
REQUEST_JITTER_S = (1.0, 3.0)

SCAN_COLUMNS = [
    "name", "description", "close", "currency", "market_cap_basic",
    "volume", "exchange", "type", "subtype", "isin",
]

CAPS_DIR = "caps"
CENSUS_FILE = "tradingview.parquet"

# country slugs probed 2026-07-16 (all answer 200 with type=stock counts;
# 'southafrica' is 'rsa'). Curated top-10k-first; extending is additive and
# zero-risk — a bad slug is a counted per-country failure, never fatal.
TV_COUNTRIES = (
    "america", "canada", "mexico", "brazil", "chile", "argentina",
    "uk", "germany", "france", "italy", "spain", "netherlands", "belgium",
    "portugal", "switzerland", "austria", "sweden", "norway", "denmark",
    "finland", "poland", "greece", "turkey", "israel", "rsa", "ksa", "uae",
    "japan", "korea", "taiwan", "hongkong", "china", "india", "singapore",
    "malaysia", "indonesia", "thailand", "philippines", "australia",
    "newzealand",
)

# slug → ISO-2 (the universe's country column) — used by the ISIN fallback
TV_COUNTRY_ISO = {
    "america": "US", "canada": "CA", "mexico": "MX", "brazil": "BR",
    "chile": "CL", "argentina": "AR", "uk": "GB", "germany": "DE",
    "france": "FR", "italy": "IT", "spain": "ES", "netherlands": "NL",
    "belgium": "BE", "portugal": "PT", "switzerland": "CH", "austria": "AT",
    "sweden": "SE", "norway": "NO", "denmark": "DK", "finland": "FI",
    "poland": "PL", "greece": "GR", "turkey": "TR", "israel": "IL",
    "rsa": "ZA", "ksa": "SA", "uae": "AE", "japan": "JP", "korea": "KR",
    "taiwan": "TW", "hongkong": "HK", "china": "CN", "india": "IN",
    "singapore": "SG", "malaysia": "MY", "indonesia": "ID", "thailand": "TH",
    "philippines": "PH", "australia": "AU", "newzealand": "NZ",
}

# (country slug, TV exchange code) → candidate Yahoo suffixes, from the
# exchange codes actually observed per country (probed 2026-07-16). Multiple
# candidates when TV does not distinguish venues (KRX covers KOSPI+KOSDAQ) —
# the first candidate present in the universe wins. Deliberately unmapped:
# retail/dark venues (GETTEX, LS, LSX, Tradegate, LSIN, EUROTLX, BX,
# NEWCONNECT, NGM…) — unmapped (country, exchange) pairs are counted and
# logged so the table grows from real data.
TV_EXCHANGE_SUFFIXES: dict[tuple[str, str], tuple[str, ...]] = {
    ("america", "NYSE"): ("",), ("america", "NASDAQ"): ("",),
    ("america", "AMEX"): ("",), ("america", "OTC"): ("",),
    ("canada", "TSX"): (".TO",), ("canada", "TSXV"): (".V",),
    ("canada", "CSE"): (".CN",), ("canada", "NEO"): (".NE",),
    ("mexico", "BMV"): (".MX",),
    ("brazil", "BMFBOVESPA"): (".SA",),
    ("chile", "BCS"): (".SN",), ("argentina", "BCBA"): (".BA",),
    ("uk", "LSE"): (".L",),
    ("germany", "XETR"): (".DE",), ("germany", "FWB"): (".F",),
    ("germany", "DUS"): (".DU",), ("germany", "MUN"): (".MU",),
    ("germany", "HAM"): (".HM",), ("germany", "HAN"): (".HA",),
    ("germany", "BER"): (".BE",), ("germany", "SWB"): (".SG",),
    ("france", "EURONEXT"): (".PA",), ("netherlands", "EURONEXT"): (".AS",),
    ("belgium", "EURONEXT"): (".BR",), ("portugal", "EURONEXT"): (".LS",),
    ("italy", "MIL"): (".MI",), ("spain", "BME"): (".MC",),
    ("switzerland", "SIX"): (".SW",), ("austria", "VIE"): (".VI",),
    ("sweden", "OMXSTO"): (".ST",), ("norway", "OSL"): (".OL",),
    ("denmark", "OMXCOP"): (".CO",), ("finland", "OMXHEX"): (".HE",),
    ("poland", "GPW"): (".WA",), ("greece", "ATHEX"): (".AT",),
    ("turkey", "BIST"): (".IS",), ("israel", "TASE"): (".TA",),
    ("rsa", "JSE"): (".JO",), ("ksa", "TADAWUL"): (".SR",),
    ("uae", "ADX"): (".AD",),
    ("japan", "TSE"): (".T",),
    ("korea", "KRX"): (".KS", ".KQ"),
    ("taiwan", "TWSE"): (".TW",), ("taiwan", "TPEX"): (".TWO",),
    ("hongkong", "HKEX"): (".HK",),
    ("china", "SSE"): (".SS",), ("china", "SZSE"): (".SZ",),
    ("india", "NSE"): (".NS",), ("india", "BSE"): (".BO",),
    ("singapore", "SGX"): (".SI",), ("malaysia", "MYX"): (".KL",),
    ("indonesia", "IDX"): (".JK",), ("thailand", "SET"): (".BK",),
    ("philippines", "PSE"): (".PS",),
    ("australia", "ASX"): (".AX",), ("newzealand", "NZX"): (".NZ",),
}

# markets whose universe tickers are zero-padded numeric codes (the Stooq
# precedent, STOOQ_TICKER_PAD): TV '700' → universe '0700.HK'
TV_TICKER_PAD = {("hongkong", "HKEX"): 4}


class TradingViewError(RuntimeError):
    """The scan failed for every requested country."""


@dataclass(frozen=True)
class TradingViewReport(ImportReport):
    countries_ok: int = 0
    countries_failed: tuple[str, ...] = field(default_factory=tuple)


def map_tv_symbol(country: str, exchange: str, ticker: str) -> tuple[str, ...]:
    """Candidate universe symbols for one TV listing — () when the venue is
    deliberately unmapped. TV ticker classes ('BRK.B', 'VOLV_B') normalize to
    Yahoo's dash form; numeric-code markets are zero-padded."""
    suffixes = TV_EXCHANGE_SUFFIXES.get((country, exchange))
    if suffixes is None or not ticker:
        return ()
    pad = TV_TICKER_PAD.get((country, exchange))
    if pad and ticker.isdigit():
        ticker = ticker.zfill(pad)
    ticker = ticker.replace(".", "-").replace("_", "-")
    return tuple(f"{ticker}{suffix}" for suffix in suffixes)


def _scan_body(offset: int) -> dict:
    return {
        "columns": SCAN_COLUMNS,
        "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
        "range": [offset, offset + PAGE_SIZE],
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
    }


def scan_country(country: str, http) -> list[dict]:
    """All stock rows for one country, ranged pagination, schema-validated."""
    rows: list[dict] = []
    offset = 0
    while offset < MAX_ROWS_PER_COUNTRY:
        response = http.post(SCAN_URL.format(country=country), json=_scan_body(offset))
        response.raise_for_status()
        payload = response.json()
        if "data" not in payload or "totalCount" not in payload:
            raise TradingViewError(f"{country}: unexpected scan payload shape")
        for entry in payload["data"]:
            symbol = entry.get("s", "")
            values = entry.get("d", [])
            if ":" not in symbol or len(values) != len(SCAN_COLUMNS):
                raise TradingViewError(f"{country}: unexpected scan row shape")
            exchange_code, ticker = symbol.split(":", 1)
            row = dict(zip(SCAN_COLUMNS, values, strict=True))
            row["tv_symbol"] = symbol
            row["tv_exchange"] = exchange_code
            row["tv_ticker"] = ticker
            row["country"] = country
            rows.append(row)
        offset += PAGE_SIZE
        if offset >= int(payload["totalCount"]):
            break
    return rows


def _default_fetch(country: str) -> list[dict]:
    import httpx

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60) as http:
        return scan_country(country, http)


def _price_asof() -> str:
    """No reliable bar-time field in the scan — the run's UTC date clamped to
    the previous weekday (a Saturday run must not out-date Friday's dumps;
    holidays remain a documented ≤1-day imprecision)."""
    asof = date.today()
    while asof.weekday() >= 5:
        asof -= timedelta(days=1)
    return asof.isoformat()


def _universe_isin_table(data_dir: Path | str) -> pd.DataFrame:
    path = Path(data_dir) / "universe.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["symbol", "isin", "country"])
    table = pd.read_parquet(path, columns=["symbol", "isin", "country"])
    return table[table["isin"].notna()]


def _match_universe(table: pd.DataFrame, known: set[str], isin_table: pd.DataFrame) -> pd.DataFrame:
    """Two-stage symbol match: exchange-suffix candidates first, then ISIN —
    only when the ISIN maps to exactly ONE universe symbol of the same
    country (bare-ISIN matching is ambiguous across venues)."""
    symbols: list[str | None] = []
    methods: list[str | None] = []
    by_isin: dict[tuple[str, str], list[str]] = {}
    for row in isin_table.itertuples():
        by_isin.setdefault((str(row.isin), str(row.country)), []).append(str(row.symbol))
    for row in table.itertuples():
        matched = None
        method = None
        for candidate in map_tv_symbol(str(row.country), str(row.tv_exchange), str(row.tv_ticker)):
            if candidate in known:
                matched, method = candidate, "ticker"
                break
        if matched is None and isinstance(row.isin, str) and row.isin:
            iso = TV_COUNTRY_ISO.get(str(row.country), "")
            candidates = by_isin.get((row.isin, iso), [])
            if len(candidates) == 1:
                matched, method = candidates[0], "isin"
        symbols.append(matched)
        methods.append(method)
    return table.assign(symbol=symbols, match_method=methods)


def _write_census(data_dir: Path | str, table: pd.DataFrame) -> Path:
    directory = Path(data_dir) / CAPS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / CENSUS_FILE
    tmp = directory / f".tmp-{CENSUS_FILE}"
    table.to_parquet(tmp, index=False)
    tmp.rename(final)
    return final


def import_tradingview(
    data_dir: Path | str,
    countries: tuple[str, ...] | None = None,
    fetch=None,
    jitter: tuple[float, float] | None = None,
) -> TradingViewReport:
    """One scan per country → the cap census (data/caps/tradingview.parquet,
    unmatched listings KEPT with symbol=NULL — the census must be able to
    reveal what the universe lacks) + quote-only distillate rows for matched
    symbols (the column-aware merge keeps dump momentum intact)."""
    countries = countries if countries is not None else TV_COUNTRIES
    fetch = fetch if fetch is not None else _default_fetch
    jitter = jitter if jitter is not None else REQUEST_JITTER_S

    collected: list[dict] = []
    failed: list[str] = []
    for index, country in enumerate(countries):
        if index and jitter != (0, 0):
            time.sleep(random.uniform(*jitter))
        try:
            collected.extend(fetch(country))
        except Exception as exc:  # noqa: BLE001 — a country is never fatal
            failed.append(country)
            log.warning("tradingview scan failed for %s: %s", country, exc)
    if not collected:
        raise TradingViewError(f"every country failed: {', '.join(failed) or 'none requested'}")

    table = pd.DataFrame(collected)
    table = table[table["type"] == "stock"]  # belt and braces vs schema drift
    known = universe_symbols(data_dir)
    table = _match_universe(table, known, _universe_isin_table(data_dir))

    now = time.time()
    asof = _price_asof()
    unmapped = table[table["symbol"].isna()].groupby(["country", "tv_exchange"]).size()
    if len(unmapped):
        log.info("tradingview unmatched listings by venue:\n%s", unmapped.to_string())

    census = table[[
        "symbol", "tv_symbol", "description", "isin", "market_cap_basic", "currency",
        "close", "volume", "country", "tv_exchange", "match_method",
    ]].rename(
        columns={"market_cap_basic": "market_cap", "tv_exchange": "exchange",
                 "description": "name"}
    )
    census = census.assign(asof=asof, source="tradingview", imported_at=now)
    _write_census(data_dir, census.reset_index(drop=True))

    quotes = table[table["symbol"].notna() & table["close"].notna()]
    quotes = quotes[pd.to_numeric(quotes["close"], errors="coerce") > 0]
    # several venues can map onto one universe symbol (BMV+BIVA → .MX):
    # keep the largest-cap row, deterministically
    quotes = (
        quotes.sort_values(["market_cap_basic", "tv_symbol"], na_position="first")
        .drop_duplicates("symbol", keep="last")
    )
    fresh = pd.DataFrame(
        {
            "symbol": quotes["symbol"],
            "close": pd.to_numeric(quotes["close"], errors="coerce"),
            "price_asof": asof,
            "source": "tradingview",
            "imported_at": now,
        }
    )
    if len(fresh):
        _merge_and_publish(data_dir, fresh.reset_index(drop=True))

    matched = int(table["symbol"].notna().sum())
    report = TradingViewReport(
        source="tradingview",
        imported=len(fresh),
        skipped_unknown=len(table) - matched,
        countries_ok=len(countries) - len(failed),
        countries_failed=tuple(failed),
    )
    log.info(
        "import-prices: %d tradingview quotes (%d listings censused, %d unmatched,"
        " %d/%d countries)",
        report.imported, len(census), report.skipped_unknown,
        report.countries_ok, len(countries),
    )
    return report
