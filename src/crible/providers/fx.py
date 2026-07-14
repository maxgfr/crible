"""FX normalization from ECB reference rates (keyless, via Frankfurter).

crible's ratios are currency-neutral, but absolute magnitudes (revenue, assets,
equity…) are in each company's reporting currency, so cross-currency size
screens ("revenue over €1B across FR/DE/US") are impossible on the raw columns.

We mirror the ECB daily reference rates (published via the open-source,
keyless Frankfurter API — redistributable) and add companion ``*_eur`` columns.
The rate file lives in the local mirror, so normalization works offline once
fetched, and a missing rate or unknown currency leaves the column NULL — never
imputed, the same rule as every other computed field. Values are normalized by
the listing currency (the universe's ``currency``), a documented approximation
where reporting and listing currency usually coincide.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("crible.providers.fx")

FRANKFURTER_URL = "https://api.frankfurter.app/latest?base=EUR"

# absolute-magnitude snapshot fields worth a cross-currency companion; ratios
# are currency-neutral and deliberately excluded
FX_FIELDS = ("revenue", "net_income", "total_assets", "stockholders_equity")


def to_eur(amount, currency, rates: dict[str, float]) -> float | None:
    """Convert ``amount`` (in ``currency``) to EUR using ECB rates (units per
    EUR). Returns None — never imputed — for a missing amount, a non-numeric
    value, or a currency with no published rate."""
    if amount is None:
        return None
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return None
    if amt != amt:  # NaN
        return None
    if currency == "EUR":
        return amt
    rate = rates.get(currency)
    if not rate:
        return None
    return amt / rate


def _mirror_file(data_dir: Path | str) -> Path:
    return Path(data_dir) / "mirror" / "fx" / "rates.json"


def fetch_rates(data_dir: Path | str, http=None, max_age_seconds: float = 24 * 3600) -> dict[str, float]:
    """Mirror the ECB daily reference rates and return {currency: units-per-EUR}
    (EUR itself omitted; treated as 1.0 in ``to_eur``)."""
    from crible.ingest.mirror import fetch_if_stale

    result = fetch_if_stale(
        data_dir, "fx", "rates.json", FRANKFURTER_URL,
        http=http, max_age_seconds=max_age_seconds,
    )
    payload = json.loads(result.path.read_text())
    return {k: float(v) for k, v in payload.get("rates", {}).items()}


def load_rates(data_dir: Path | str) -> dict[str, float] | None:
    """Read the mirrored ECB rates for the offline/compute path, or None."""
    path = _mirror_file(data_dir)
    if not path.exists():
        return None
    try:
        return {k: float(v) for k, v in json.loads(path.read_text()).get("rates", {}).items()}
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def attach_fx(
    snapshot: pd.DataFrame, data_dir: Path | str | None, rates: dict[str, float] | None = None
) -> pd.DataFrame:
    """Add ``<field>_eur`` companions for the absolute FX_FIELDS present in the
    snapshot, using the row's listing currency and the ECB rates. A no-op when
    rates are unavailable — the snapshot ships unchanged rather than imputing."""
    if rates is None:
        rates = load_rates(data_dir) if data_dir is not None else None
    if not rates or snapshot.empty or "currency" not in snapshot.columns:
        return snapshot
    # we mirror only the CURRENT spot rate, so *_eur is filled only for the
    # latest period per symbol (the row screens use). Applying today's rate to a
    # 2020 figure would be wrong, so older periods stay NULL — never imputed (F12).
    if "period" in snapshot.columns and "symbol" in snapshot.columns:
        latest = set(
            snapshot.assign(_p=snapshot["period"].astype(str))
            .sort_values("_p")
            .groupby("symbol", sort=False)
            .tail(1)
            .index
        )
    else:
        latest = set(snapshot.index)
    additions: dict[str, list] = {}
    for field in FX_FIELDS:
        if field in snapshot.columns:
            additions[f"{field}_eur"] = [
                to_eur(v, c, rates) if idx in latest else None
                for idx, v, c in zip(snapshot.index, snapshot[field], snapshot["currency"])
            ]
    if not additions:
        return snapshot
    return pd.concat([snapshot, pd.DataFrame(additions, index=snapshot.index)], axis=1)
