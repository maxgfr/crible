"""Top-10k global companies — numeric cap census, dedup, slice, priority.

The universe only knows a 6-way cap CLASS; the numeric layer comes from the
TradingView census (data/caps/tradingview.parquet), with the published
snapshot's price×shares cap as second source and the previous last-good
universe.parquet as carryover (the CI database is disposable — membership
hysteresis and cap staleness survive through the parquet). Everything is
converted to EUR via the mirrored ECB rates; a missing rate leaves NULL,
never imputed.

Companies dedup by ISIN (universe ISIN, else the census's, else the listing
is its own group); one deterministic primary listing per group. Known v1
limitation: ADRs carry US ISINs and do not fold into their ordinary's group
— name-based folding is rejected (false merges), the hysteresis band absorbs
the duplicate slots.

Membership: entry at rank ≤ 10,000, stay while rank ≤ 11,000 (hysteresis),
plus a class floor — Mega/Large groups with NO numeric cap are members
whenever a ranking exists at all (the 10,000th global cap sits below the
Large-Cap threshold, so the guarantee errs to over-inclusion; the floor
count is reported, never hidden).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from crible.providers.fx import to_eur

CENSUS_MAX_AGE_DAYS = 30
TOP10K_SIZE = 10_000
TOP10K_EXIT_RANK = 11_000
# unranked floor members slot between the ranked tiers (ranked megas first)
FLOOR_TIERS = {"Mega Cap": 1, "Large Cap": 5}
# the pre-census regional formula shifts up by one full tier stride so every
# top-10k primary listing (tiers 0-7) outranks it; the -1 bootstrap-sample
# sentinel stays in front of everything (queue.seed_from_universe skips it)
BASE_PRIORITY_SHIFT = 8

CAP_UPDATE_COLUMNS = [
    "cap_eur", "cap_asof", "cap_source", "company_group",
    "primary_listing", "cap_rank_global", "top10k",
]


@dataclass(frozen=True)
class CapCensusReport:
    listings: int
    ranked_groups: int
    member_groups: int
    floor_groups: int


def load_census(data_dir: Path | str) -> pd.DataFrame | None:
    """Universe-matched census rows, one per symbol (largest cap wins when
    several venues map onto the same listing). None while no census exists —
    the whole layer is then a guaranteed no-op."""
    path = Path(data_dir) / "caps" / "tradingview.parquet"
    if not path.exists():
        return None
    table = pd.read_parquet(
        path, columns=["symbol", "isin", "market_cap", "currency", "volume", "country", "asof"]
    )
    table = table[table["symbol"].notna()]
    if not len(table):
        return None
    return (
        table.sort_values("market_cap", na_position="first")
        .drop_duplicates("symbol", keep="last")
        .rename(columns={"isin": "census_isin", "volume": "census_volume",
                         "country": "census_country", "asof": "cap_asof"})
        .reset_index(drop=True)
    )


def load_previous_caps(data_dir: Path | str) -> pd.DataFrame | None:
    """The cap layer of the last-good universe.parquet (None for a pre-census
    parquet) — the carryover channel across disposable CI databases."""
    path = Path(data_dir) / "universe.parquet"
    if not path.exists():
        return None
    table = pd.read_parquet(path)
    if "cap_eur" not in table.columns:
        return None
    kept = table[["symbol", "cap_eur", "cap_asof", "cap_source", "top10k"]]
    kept = kept[kept["cap_eur"].notna() | kept["top10k"].fillna(False).astype(bool)]
    return kept.reset_index(drop=True) if len(kept) else None


def snapshot_caps(data_dir: Path | str) -> pd.DataFrame | None:
    """Latest computed market_cap per symbol from the published snapshot
    (price × shares, listing currency) — the second cap source."""
    path = Path(data_dir) / "snapshot" / "snapshot.parquet"
    if not path.exists():
        return None
    try:
        table = pd.read_parquet(
            path, columns=["symbol", "period", "market_cap", "currency", "price_asof"]
        )
    except Exception:  # noqa: BLE001 — an old snapshot without the columns
        return None
    table = table[table["market_cap"].notna()]
    if not len(table):
        return None
    latest = (
        table.sort_values("period")
        .drop_duplicates("symbol", keep="last")
        .rename(columns={"market_cap": "snap_cap", "currency": "snap_currency",
                         "price_asof": "snap_asof"})
    )
    return latest[["symbol", "snap_cap", "snap_currency", "snap_asof"]].reset_index(drop=True)


def _census_is_fresh(asof, now: float) -> bool:
    try:
        stamp = datetime.fromisoformat(str(asof)).timestamp()
    except (TypeError, ValueError):
        return False
    return stamp >= now - CENSUS_MAX_AGE_DAYS * 86400


def build_cap_table(
    universe: pd.DataFrame,
    census: pd.DataFrame | None,
    snapcaps: pd.DataFrame | None,
    previous: pd.DataFrame | None,
    rates: dict[str, float],
    now: float,
) -> pd.DataFrame:
    """One row per (non-delisted) listing: cap_eur + provenance, precedence
    fresh census → snapshot → carryover → NULL (competes via the class floor,
    never silently vanishes)."""
    caps = universe[["symbol", "isin", "country", "market_cap_class"]].copy()
    caps = caps.merge(census, on="symbol", how="left") if census is not None else caps.assign(
        census_isin=None, market_cap=float("nan"), currency=None,
        census_volume=float("nan"), census_country=None, cap_asof=None,
    )
    if snapcaps is not None:
        caps = caps.merge(snapcaps, on="symbol", how="left")
    else:
        caps = caps.assign(snap_cap=float("nan"), snap_currency=None, snap_asof=None)
    if previous is not None:
        prev = previous.rename(
            columns={"cap_eur": "prev_cap_eur", "cap_asof": "prev_asof",
                     "cap_source": "prev_source", "top10k": "prev_top10k"}
        )
        caps = caps.merge(prev, on="symbol", how="left")
    else:
        caps = caps.assign(prev_cap_eur=float("nan"), prev_asof=None,
                           prev_source=None, prev_top10k=None)

    cap_eur, cap_asof, cap_source = [], [], []
    for row in caps.itertuples():
        census_eur = to_eur(row.market_cap, row.currency, rates)
        if census_eur is not None and _census_is_fresh(row.cap_asof, now):
            cap_eur.append(census_eur)
            cap_asof.append(str(row.cap_asof))
            cap_source.append("tradingview")
            continue
        snap_eur = to_eur(row.snap_cap, row.snap_currency, rates)
        if snap_eur is not None:
            cap_eur.append(snap_eur)
            cap_asof.append(str(row.snap_asof) if pd.notna(row.snap_asof) else None)
            cap_source.append("snapshot")
            continue
        if pd.notna(row.prev_cap_eur):
            cap_eur.append(float(row.prev_cap_eur))
            # the ORIGINAL asof travels — staleness stays visible
            cap_asof.append(str(row.prev_asof) if pd.notna(row.prev_asof) else None)
            cap_source.append("carryover")
            continue
        cap_eur.append(float("nan"))
        cap_asof.append(None)
        cap_source.append(None)
    caps["cap_eur"] = cap_eur
    caps["cap_asof"] = cap_asof
    caps["cap_source"] = cap_source

    # grouping key: universe ISIN, else the census's (46% of Mega/Large rows
    # lack a universe ISIN — calibrated 2026-07-16), else the listing itself
    group = caps["isin"].fillna(caps["census_isin"])
    caps["company_group"] = group.fillna("sym:" + caps["symbol"])
    return caps


def pick_primary(caps: pd.DataFrame) -> pd.DataFrame:
    """Exactly one primary listing per group. Deterministic tie-break:
    listing venue in the company's own country, then largest cap, then
    largest census volume, then symbol ASC."""
    from crible.ingest.tradingview import TV_COUNTRY_ISO

    venue_iso = caps["census_country"].map(lambda c: TV_COUNTRY_ISO.get(str(c), None))
    caps = caps.assign(_home=(venue_iso == caps["country"]).fillna(False).astype(int))
    ordered = caps.sort_values(
        ["company_group", "_home", "cap_eur", "census_volume", "symbol"],
        ascending=[True, False, False, False, True],
        na_position="last",
    )
    primary_symbols = ordered.drop_duplicates("company_group", keep="first")["symbol"]
    caps = caps.assign(primary_listing=caps["symbol"].isin(set(primary_symbols)))
    return caps.drop(columns=["_home"])


def assign_top10k(caps: pd.DataFrame, previous_members: set[str]) -> pd.DataFrame:
    """Group ranking + membership: entry ≤ 10,000, stay ≤ 11,000 for previous
    members, plus the Mega/Large class floor for cap-less groups (only once a
    ranking exists at all — pre-census nothing activates)."""
    group_cap = caps.groupby("company_group")["cap_eur"].max()
    ranked = group_cap.dropna().sort_values(ascending=False)
    rank_of_group = {group: index + 1 for index, group in enumerate(ranked.index)}

    caps = caps.assign(
        cap_rank_global=caps["company_group"].map(rank_of_group).astype("Int64")
    )
    if not rank_of_group:
        return caps.assign(top10k=False, _floor=False)

    previous_groups = set(caps.loc[caps["symbol"].isin(previous_members), "company_group"])
    floor_classes = caps["market_cap_class"].isin(FLOOR_TIERS)
    floor_groups = set(caps.loc[floor_classes, "company_group"]) - set(ranked.index)

    def _member(group: str) -> bool:
        rank = rank_of_group.get(group)
        if rank is not None:
            if rank <= TOP10K_SIZE:
                return True
            return group in previous_groups and rank <= TOP10K_EXIT_RANK
        return group in floor_groups

    member_groups = {g for g in caps["company_group"].unique() if _member(g)}
    caps = caps.assign(
        top10k=caps["company_group"].isin(member_groups),
        _floor=caps["company_group"].isin(floor_groups & member_groups),
    )
    return caps
