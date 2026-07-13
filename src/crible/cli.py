"""FR-005 — the crible CLI. Same DSL, same semantics as the API and UI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from crible.dsl.parser import DslError
from crible.presets import PRESETS
from crible.runtime import Runtime, SnapshotMissingError

app = typer.Typer(name="crible", help="Self-hosted fundamental stock screener.", no_args_is_help=True)


@app.callback()
def _configure(
    data_dir: Path = typer.Option(
        None,
        "--data-dir",
        help="Data directory for this invocation (default: $CRIBLE_DATA_DIR or ./data)",
    ),
) -> None:
    import logging
    import os

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    if data_dir is not None:
        os.environ["CRIBLE_DATA_DIR"] = str(data_dir)


def _fail(message: str) -> None:
    typer.secho(f"error: {message}", err=True, fg=typer.colors.RED)
    raise typer.Exit(code=1)


def _resolve_query(query: str | None, preset: str | None) -> str:
    if preset is not None:
        if preset not in PRESETS:
            _fail(f"unknown preset {preset!r} — available: {', '.join(sorted(PRESETS))}")
        return PRESETS[preset].dsl
    if not query:
        _fail("provide a DSL query or --preset — e.g. crible screen \"piotroski_f >= 7\"")
    return query


@app.command()
def screen(
    query: str = typer.Argument(None, help="Filter DSL, e.g. \"roe > 15 AND country IN ('FR','DE')\""),
    preset: str = typer.Option(None, "--preset", help="Run a named preset instead of a query"),
    fmt: str = typer.Option("table", "--format", help="table | csv"),
    sort: str = typer.Option(None, "--sort", help="e.g. -roe or country,-piotroski_f"),
    limit: int = typer.Option(50, "--limit"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    """Screen the snapshot with the filter DSL."""
    dsl = _resolve_query(query, preset)
    try:
        rows, total = Runtime.from_env().screen(dsl, sort=sort, limit=limit, offset=offset)
    except SnapshotMissingError as exc:
        _fail(str(exc))
    except DslError as exc:
        _fail(f"invalid query: {exc}")
    if fmt == "csv":
        rows.to_csv(sys.stdout, index=False)
    else:
        columns = [c for c in ("symbol", "name", "country", "sector", "piotroski_f", "altman_z", "beneish_m", "return_on_equity") if c in rows.columns]
        typer.echo(rows[columns].to_string(index=False) if columns else rows.to_string(index=False))
        typer.echo(f"({len(rows)} of {total} matching rows)")


@app.command()
def export(
    query: str = typer.Argument(None, help="Filter DSL"),
    preset: str = typer.Option(None, "--preset"),
    out: Path = typer.Option(..., "--out", help="CSV file to write the FULL result set to"),
    sort: str = typer.Option(None, "--sort"),
) -> None:
    """Write the FULL result set of a query to CSV (same rows as GET /screen.csv)."""
    dsl = _resolve_query(query, preset)
    try:
        rows, total = Runtime.from_env().screen(dsl, sort=sort, limit=10_000, offset=0)
    except SnapshotMissingError as exc:
        _fail(str(exc))
    except DslError as exc:
        _fail(f"invalid query: {exc}")
    rows.to_csv(out, index=False)
    typer.echo(f"wrote {len(rows)} of {total} rows to {out}")


@app.command()
def presets() -> None:
    """List preset screens — name, description and the full, editable DSL."""
    for preset in PRESETS.values():
        typer.echo(f"{preset.id}: {preset.description}\n    {preset.dsl}")


@app.command()
def fields(fmt: str = typer.Option("table", "--format", help="table | json")) -> None:
    """List every filterable snapshot column with its type (the DSL whitelist)."""
    listed = Runtime.from_env().fields()
    if not listed:
        _fail("no snapshot yet — run `crible bootstrap` (or ingest + compute) first")
    if fmt == "json":
        typer.echo(json.dumps(listed, indent=2))
    else:
        for field in listed:
            typer.echo(f"{field['name']}\t{field['type']}")


@app.command()
def status() -> None:
    """Universe coverage, freshness, rate budget and provider health."""
    typer.echo(json.dumps(Runtime.from_env().status(), indent=2, default=str))


@app.command()
def ingest(
    bootstrap: bool = typer.Option(False, "--bootstrap", help="Load the universe from FinanceDatabase"),
    once: bool = typer.Option(False, "--once", help="Run a single crawl cycle"),
    loop: bool = typer.Option(False, "--loop", help="Run the continuous crawl loop"),
    limit: int = typer.Option(50, "--limit", help="Symbols per cycle for --once"),
) -> None:
    """Run the universe bootstrap and/or the rate-budgeted crawler."""
    from crible.ingest.service import run_bootstrap, run_loop, run_once

    if bootstrap:
        report = run_bootstrap()
        typer.echo(f"universe: {report.loaded} rows loaded ({report.by_region})")
    if once:
        outcome = run_once(limit=limit)
        typer.echo(f"crawled: {len(outcome.fetched)} ok, {len(outcome.failed)} failed")
    if loop:
        run_loop()
    if not (bootstrap or once or loop):
        _fail("nothing to do — pass --bootstrap, --once or --loop")


@app.command()
def bootstrap(
    repo: str = typer.Option(None, "--repo", help="GitHub repo publishing the dataset (owner/name)"),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing data/ layer"),
) -> None:
    """Initialize data/ from the published open dataset — screen with zero crawl."""
    from crible import config
    from crible.bootstrap import BootstrapError, bootstrap_data

    try:
        report = bootstrap_data(config.data_dir(), repo=repo, force=force)
    except BootstrapError as exc:
        _fail(str(exc))
    typer.echo(
        f"bootstrapped {report.files} files from the {report.source} into {config.data_dir()}"
    )
    typer.echo(
        'next: crible screen "piotroski_f >= 7" — or docker compose up to keep the data fresh'
    )


@app.command("import-prices")
def import_prices(
    source: str = typer.Argument(
        ..., help="'huggingface' (US, plain HTTPS) or a path to a Stooq bulk zip (manual download)"
    ),
    max_age_days: float = typer.Option(
        0, "--max-age-days", help="Skip when the last import is younger than this (0 = always run)"
    ),
) -> None:
    """Distil a price DUMP (no API) into data/prices-latest.parquet.

    Only derived values are stored/published — last close, as-of date and
    trailing 6-month return per symbol — never the licensed series."""
    from crible import config
    from crible.ingest.price_import import (
        import_huggingface,
        import_stooq,
        latest_import_age_days,
    )

    data = config.data_dir()
    if max_age_days > 0:
        age = latest_import_age_days(data)
        if age is not None and age < max_age_days:
            typer.echo(f"import is {age:.1f} days old (< {max_age_days:g}) — nothing to do")
            return
    if source == "huggingface":
        report = import_huggingface(data)
    else:
        path = Path(source)
        if not path.exists():
            _fail(f"no such archive: {path} — download it manually from stooq.com/db/h/")
        report = import_stooq(data, path)
    typer.echo(
        f"imported {report.imported} symbols from {report.source}"
        f" ({report.skipped_unknown} outside the universe) — run `crible compute` to refresh ratios"
    )


@app.command("demo-refresh")
def demo_refresh(
    deadline: float = typer.Option(9000.0, "--deadline", help="Wall-clock budget in seconds"),
    esef_limit: int = typer.Option(25, "--esef-limit", help="Max ESEF enrichments this run"),
    edgar_limit: int = typer.Option(25, "--edgar-limit", help="Max EDGAR enrichments this run"),
    edgar_bulk: bool = typer.Option(
        False, "--edgar-bulk",
        help="Download companyfacts.zip (~1.4 GB) and ingest ALL resolved US issuers (ADR-0005)",
    ),
) -> None:
    """One bounded keyless refresh pass (the nightly demo-data run)."""
    from crible.ingest.service import run_refresh

    result = run_refresh(
        deadline_seconds=deadline, esef_limit=esef_limit, edgar_limit=edgar_limit,
        edgar_bulk=edgar_bulk,
    )
    typer.echo(json.dumps(result, indent=2, default=str))


@app.command("export-site")
def export_site_cmd(
    out: Path = typer.Option(..., "--out", help="Directory to write the static demo artifacts to"),
    min_symbols: int = typer.Option(50, "--min-symbols", help="Refuse to publish below this snapshot coverage"),
) -> None:
    """Export the static artifacts the GitHub Pages demo runs on."""
    from crible import config
    from crible.site_export import SiteExportError, export_site

    try:
        manifest = export_site(config.data_dir(), out, min_symbols=min_symbols)
    except SiteExportError as exc:
        _fail(str(exc))
    typer.echo(
        f"exported {manifest['snapshot_symbols']} symbols"
        f" ({manifest['snapshot_rows']} snapshot rows, {manifest['universe_rows']} universe rows)"
        f" to {out}"
    )


@app.command()
def compute() -> None:
    """Build and atomically publish the wide snapshot from the raw layer."""
    from crible.compute.snapshot import build_snapshot, publish_snapshot
    from crible import config

    data = config.data_dir()
    snapshot = build_snapshot(data)
    if snapshot.empty:
        _fail("no raw data yet — run `crible ingest --bootstrap` then `crible ingest --once` first")
    path = publish_snapshot(snapshot, data)
    typer.echo(f"published {len(snapshot)} rows × {len(snapshot.columns)} columns to {path}")


if __name__ == "__main__":
    app()
