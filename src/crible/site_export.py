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
from crible.price_series import SHARD_PATTERN, ShardSizeError, export_price_shards
from crible.providers.catalog import default_catalog, inventory
from crible.runtime import Runtime


class SiteExportError(RuntimeError):
    """The export was refused — publishing would break the hosted site."""


def _literal(path: Path) -> str:
    return "'" + path.as_posix().replace("'", "''") + "'"


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
        # views over the two files (a view cannot bind a parameter: the paths
        # are quoted SQL literals, a `'` in the data dir stays data)
        con.execute(f"CREATE VIEW snap AS SELECT * FROM read_parquet({_literal(snapshot)})")
        con.execute(f"CREATE VIEW uni AS SELECT * FROM read_parquet({_literal(universe)})")
        snapshot_rows, snapshot_symbols = con.execute(
            "SELECT count(*), count(DISTINCT symbol) FROM snap"
        ).fetchone()
        universe_rows = con.execute("SELECT count(*) FROM uni").fetchone()[0]
        # coverage honesty: how the covered companies split by region (the
        # banner shows it; attach_universe embeds region in real snapshots —
        # a snapshot without the column, e.g. a minimal fixture, reports {})
        columns = {r[0] for r in con.execute("DESCRIBE snap").fetchall()}
        snapshot_by_region: dict[str, int] = {}
        if "region" in columns:
            snapshot_by_region = dict(
                con.execute(
                    "SELECT coalesce(region, 'unknown'), count(DISTINCT symbol) FROM snap GROUP BY 1 ORDER BY 1"
                ).fetchall()
            )
        # the top-10k banner numbers (guarded: an old universe.parquet or a
        # minimal fixture simply omits the block)
        top10k: dict[str, int] = {}
        universe_columns = {r[0] for r in con.execute("DESCRIBE uni").fetchall()}
        if "top10k" in universe_columns:
            members = con.execute(
                "SELECT count(DISTINCT company_group) FROM uni WHERE coalesce(top10k, FALSE)"
            ).fetchone()[0]
            if members:
                in_snapshot = 0
                if "top10k" in columns:
                    in_snapshot = con.execute(
                        "SELECT count(DISTINCT coalesce(company_group, symbol)) FROM snap"
                        " WHERE coalesce(top10k, FALSE)"
                    ).fetchone()[0]
                top10k = {"members": int(members), "in_snapshot": int(in_snapshot)}
    finally:
        con.close()
    if snapshot_symbols < min_symbols:
        raise SiteExportError(
            f"snapshot covers {snapshot_symbols} symbols, below the required {min_symbols}"
            " — refusing to publish, keep the last-good data"
        )

    # everything is written to a sibling staging directory first and only
    # moved over `out` once complete: a failure (a shard past the git wall,
    # a full disk) leaves the previous export intact
    out.mkdir(parents=True, exist_ok=True)
    staging = out.parent / f".tmp-{out.name}-{os.getpid()}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        manifest = _write_artifacts(data, staging, runtime, universe, snapshot)
        manifest.update(
            universe_rows=universe_rows,
            snapshot_rows=snapshot_rows,
            snapshot_symbols=snapshot_symbols,
            snapshot_by_region=snapshot_by_region,
            top10k=top10k,
        )
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2))
        _swap_in(staging, out)
    except ShardSizeError as exc:
        raise SiteExportError(str(exc)) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return manifest


def _swap_in(staging: Path, out: Path) -> None:
    """Move every staged file over ``out`` (per-file atomic rename), then drop
    the shards the new export no longer has. Foreign files in ``out`` stay."""
    fresh = {f.name for f in staging.iterdir()}
    for stale in out.glob(SHARD_PATTERN):
        if stale.name not in fresh:
            stale.unlink()
    # the manifest last: a reader that sees it sees every file it names
    for name in sorted(fresh, key=lambda n: n == "manifest.json"):
        os.replace(staging / name, out / name)


def _write_artifacts(data: Path, out: Path, runtime: Runtime, universe: Path, snapshot: Path) -> dict:
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

    return {
        "schema": 2,
        "generated_at": time.time(),
        "prices": prices,
        "sample": bootstrap_sample(),
        "commit": os.environ.get("GITHUB_SHA"),
    }
