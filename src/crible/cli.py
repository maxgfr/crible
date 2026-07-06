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
def _configure_logging() -> None:
    import logging

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )


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
