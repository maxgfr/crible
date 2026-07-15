"""Static-site export — the artifacts the hosted screener runs on.

Copies the published universe/snapshot Parquet, exports the price-series
shards and emits the JSON surfaces (presets, providers, status, manifest)
into an output directory. Doubles as the "never publish an empty dataset"
gate: it refuses to write anything when the snapshot is missing or covers
fewer symbols than ``min_symbols``, so the nightly workflow keeps the
last-good data instead.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import asdict
from pathlib import Path

import duckdb

from crible.ingest.service import bootstrap_sample
from crible.presets import PRESETS
from crible.price_series import export_price_shards
from crible.providers.catalog import default_catalog, inventory
from crible.runtime import Runtime


class SiteExportError(RuntimeError):
    """The export was refused — publishing would break the hosted site."""


def export_site(data_dir: Path | str, out_dir: Path | str, min_symbols: int = 50) -> dict:
    data = Path(data_dir)
    out = Path(out_dir)
    runtime = Runtime(data_dir=data)
    snapshot = runtime.snapshot_path()
    universe = runtime.universe_path()

    # gate first, write nothing on refusal — the workflow keeps last-good
    if not snapshot.exists():
        raise SiteExportError("no snapshot to publish — run ingest + compute first")
    if not universe.exists():
        raise SiteExportError("no universe.parquet to publish — run ingest --bootstrap first")
    con = duckdb.connect()
    try:
        snapshot_rows, snapshot_symbols = con.execute(
            f"SELECT count(*), count(DISTINCT symbol) FROM read_parquet('{snapshot.as_posix()}')"
        ).fetchone()
        universe_rows = con.execute(
            f"SELECT count(*) FROM read_parquet('{universe.as_posix()}')"
        ).fetchone()[0]
        # coverage honesty: how the covered companies split by region (the
        # banner shows it; attach_universe embeds region in real snapshots —
        # a snapshot without the column, e.g. a minimal fixture, reports {})
        columns = {
            r[0]
            for r in con.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{snapshot.as_posix()}')"
            ).fetchall()
        }
        snapshot_by_region: dict[str, int] = {}
        if "region" in columns:
            snapshot_by_region = dict(
                con.execute(
                    f"SELECT coalesce(region, 'unknown'), count(DISTINCT symbol)"
                    f" FROM read_parquet('{snapshot.as_posix()}') GROUP BY 1 ORDER BY 1"
                ).fetchall()
            )
    finally:
        con.close()
    if snapshot_symbols < min_symbols:
        raise SiteExportError(
            f"snapshot covers {snapshot_symbols} symbols, below the required {min_symbols}"
            " — refusing to publish, keep the last-good data"
        )

    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(universe, out / "universe.parquet")
    shutil.copyfile(snapshot, out / "snapshot.parquet")
    # the OHLCV series shards (ADR-0007) — None when no series exist yet;
    # prices are an enrichment, never a gate
    prices = export_price_shards(data, out)

    status = runtime.status()
    status.pop("data_dir", None)  # no local paths in the published surface
    (out / "presets.json").write_text(json.dumps([asdict(p) for p in PRESETS.values()], indent=2))
    # empty env by construction: the site honestly reports the keyless state
    (out / "providers.json").write_text(json.dumps(inventory(default_catalog(), {}), indent=2))
    (out / "status.json").write_text(json.dumps(status, default=str))

    manifest = {
        "schema": 2,
        "generated_at": time.time(),
        "universe_rows": universe_rows,
        "snapshot_rows": snapshot_rows,
        "snapshot_symbols": snapshot_symbols,
        "snapshot_by_region": snapshot_by_region,
        "prices": prices,
        "sample": bootstrap_sample(),
        "commit": os.environ.get("GITHUB_SHA"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
