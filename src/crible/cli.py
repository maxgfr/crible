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


def _print_version(value: bool) -> None:
    if value:
        from crible import __version__

        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _configure(
    data_dir: Path = typer.Option(
        None,
        "--data-dir",
        help="Data directory for this invocation (default: $CRIBLE_DATA_DIR or ./data)",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Print the crible version and exit",
        callback=_print_version,
        is_eager=True,
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
    return query or ""  # no query = no filter: screen the full snapshot


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
    symbols: str = typer.Option(
        "", "--symbols",
        help="Comma-separated symbols to crawl NOW with --once (e.g. OVH.PA,MC.PA)"
        " — targeted, bypasses the queue's priority order",
    ),
    fetch_gleif: bool = typer.Option(
        False, "--fetch-gleif", help="Download the GLEIF ISIN→LEI file (unlocks audited EU)"
    ),
) -> None:
    """Run the universe bootstrap and/or the rate-budgeted crawler."""
    from crible import config
    from crible.ingest.service import run_bootstrap, run_loop, run_once

    if fetch_gleif:
        from crible.providers.gleif import fetch_gleif as _fetch_gleif

        path = _fetch_gleif(config.data_dir())
        typer.echo(f"gleif: ISIN→LEI file ready at {path} — audited EU enrichment enabled")
    if bootstrap:
        report = run_bootstrap()
        typer.echo(f"universe: {report.loaded} rows loaded ({report.by_region})")
    if symbols and not once:
        _fail("--symbols requires --once (a targeted single crawl)")
    if once:
        targeted = [s.strip() for s in symbols.split(",") if s.strip()] or None
        outcome = run_once(limit=limit, symbols=targeted)
        typer.echo(f"crawled: {len(outcome.fetched)} ok, {len(outcome.failed)} failed")
    if loop:
        run_loop()
    if not (bootstrap or once or loop or fetch_gleif):
        _fail("nothing to do — pass --bootstrap, --once, --loop or --fetch-gleif")


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
        ...,
        help="'huggingface'/'defeatbeta' (US dumps), 'tradingview' (worldwide"
        " daily snapshot + cap census) or a path to a Stooq bulk zip",
    ),
    max_age_days: float = typer.Option(
        0, "--max-age-days", help="Skip when the last import is younger than this (0 = always run)"
    ),
) -> None:
    """Import a price DUMP (no API): the windowed OHLCV series into
    data/prices/ plus the per-symbol distillate (last close, as-of date,
    trailing 6-month return) into data/prices-latest.parquet (ADR-0007)."""
    import time

    from crible import config
    from crible.ingest.price_import import (
        import_huggingface,
        import_stooq,
        latest_import_age_days,
    )
    from crible.ingest.state import update_heartbeat

    data = config.data_dir()
    named_dumps = ("huggingface", "defeatbeta", "tradingview")
    if max_age_days > 0:
        # named dumps gate on their OWN rows; a Stooq path keeps the global gate
        named = source if source in named_dumps else None
        age = latest_import_age_days(data, named)
        if age is not None and age < max_age_days:
            typer.echo(f"import is {age:.1f} days old (< {max_age_days:g}) — nothing to do")
            return
    if source == "huggingface":
        report = import_huggingface(data)
    elif source == "defeatbeta":
        from crible.ingest.defeatbeta import import_defeatbeta

        report = import_defeatbeta(data)
    elif source == "tradingview":
        from crible.ingest.tradingview import import_tradingview

        report = import_tradingview(data)
    else:
        path = Path(source)
        if not path.exists():
            _fail(f"no such archive: {path} — download it manually from stooq.com/db/h/")
        report = import_stooq(data, path)
    imports = _heartbeat_section("imports")
    entry = {"symbols": report.imported, "imported_at": time.time()}
    if hasattr(report, "countries_ok"):
        entry["countries_ok"] = report.countries_ok
        entry["countries_failed"] = list(report.countries_failed)
    imports[report.source] = entry
    update_heartbeat(imports=imports)
    typer.echo(
        f"imported {report.imported} symbols from {report.source}"
        f" ({report.skipped_unknown} outside the universe) — run `crible compute` to refresh ratios"
    )


@app.command("import-fundamentals")
def import_fundamentals(
    source: str = typer.Argument(
        ..., help="'defeatbeta' — Yahoo-derived statements for symbols NO other source serves"
    ),
    limit: int = typer.Option(
        0, "--limit", help="Cap the number of gap symbols imported this run (0 = all)"
    ),
) -> None:
    """Import LAST-RESORT fundamentals: only universe symbols without audited
    raw (EDGAR/ESEF/…) and without crawled yfinance statements are filled;
    audited data always reconciles on top (assumed-risk tier, see
    docs/DATA-SOURCES.md)."""
    from crible import config
    from crible.ingest.defeatbeta import import_defeatbeta_fundamentals

    if source != "defeatbeta":
        _fail("only 'defeatbeta' is supported")
    report = import_defeatbeta_fundamentals(config.data_dir(), limit=limit or None)
    typer.echo(
        f"imported statements for {report.imported} gap symbols from {report.source}"
        " — run `crible compute` to refresh ratios"
    )


@app.command("check-coverage")
def check_coverage(
    min_fundamentals: float = typer.Option(
        40.0, "--min-fundamentals", help="Minimum % of top-10k companies with fundamentals"
    ),
    min_priced: float = typer.Option(
        70.0, "--min-priced", help="Minimum % of top-10k companies with a price"
    ),
) -> None:
    """Gate on the top-10k coverage block (status.json): exit 1 below a
    threshold, exit 2 when the block is missing entirely — both alarming
    once the census pipeline is live. Never blocks a publish: the CI beacon
    runs AFTER the release assets ship."""
    from crible import config

    path = config.data_dir() / "status.json"
    block = None
    if path.exists():
        try:
            block = json.loads(path.read_text()).get("coverage_top10k")
        except json.JSONDecodeError:
            block = None
    if not block:
        typer.secho("no coverage_top10k block in status.json", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=2)
    typer.echo(json.dumps(block, indent=2))
    failures = []
    if block.get("fundamentals_covered_pct", 0.0) < min_fundamentals:
        failures.append(
            f"fundamentals {block.get('fundamentals_covered_pct')}% < {min_fundamentals:g}%"
        )
    if block.get("priced_pct", 0.0) < min_priced:
        failures.append(f"priced {block.get('priced_pct')}% < {min_priced:g}%")
    if failures:
        for failure in failures:
            typer.secho(f"top-10k coverage below threshold: {failure}", err=True,
                        fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.echo("top-10k coverage above thresholds")


def _heartbeat_section(key: str) -> dict:
    """Current value of one status.json key (update_heartbeat merges shallow)."""
    from crible import config

    path = config.data_dir() / "status.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text()).get(key, {})
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


@app.command("solve-captcha")
def solve_captcha_cmd(
    image: str = typer.Argument(..., help="Path to a captcha image (png/jpg/gif), or '-' for stdin"),
    raw: bool = typer.Option(False, "--raw", help="Print the model output verbatim (no normalising)"),
) -> None:
    """OCR a captcha image and print the code (needs the optional 'captcha' extra)."""
    from crible.ingest.captcha import CaptchaError, solve_captcha

    if image == "-":
        data = sys.stdin.buffer.read()
    else:
        path = Path(image)
        if not path.exists():
            _fail(f"no such image: {path}")
        data = path.read_bytes()
    try:
        typer.echo(solve_captcha(data, normalize=not raw))
    except CaptchaError as exc:
        _fail(str(exc))


@app.command("stooq-download")
def stooq_download_cmd(
    dataset: str = typer.Argument(
        ..., help="Stooq bulk code, e.g. d_world_txt, d_us_txt, d_hu_txt (d_/h_/5_ = daily/hourly/5-min)"
    ),
    out: Path = typer.Option(None, "--out", help="Output zip path (default: ./<dataset>.zip)"),
    attempts: int = typer.Option(6, "--attempts", help="Max captcha attempts before giving up"),
    do_import: bool = typer.Option(
        False, "--import", help="After download, import it (series + distillate, see `import-prices`)"
    ),
) -> None:
    """Download a CAPTCHA-gated Stooq bulk archive automatically (proof-of-work + OCR captcha).

    Clears Stooq's anti-bot layers headlessly so the worldwide price dumps can be
    fetched in CI."""
    from crible.ingest.stooq_fetch import StooqError, download_stooq

    target = out or Path(f"{dataset}.zip")
    try:
        path = download_stooq(dataset, target, attempts=attempts)
    except StooqError as exc:
        _fail(str(exc))
    size_mb = path.stat().st_size / 1e6
    typer.echo(f"downloaded {dataset} -> {path} ({size_mb:.1f} MB)")
    if do_import:
        from crible import config
        from crible.ingest.price_import import import_stooq

        report = import_stooq(config.data_dir(), path)
        typer.echo(
            f"imported {report.imported} symbols from stooq"
            f" ({report.skipped_unknown} outside the universe) — run `crible compute` to refresh ratios"
        )


@app.command("refresh")
def refresh(
    deadline: float = typer.Option(9000.0, "--deadline", help="Crawl-loop budget in seconds"),
    max_minutes: float = typer.Option(
        0.0, "--max-minutes",
        help="WHOLE-RUN wall-clock guard: enrichment stages stop early so"
        " compute+publish always run (0 = unbounded, the self-hosted default)",
    ),
    esef_limit: int = typer.Option(25, "--esef-limit", help="Max ESEF enrichments this run"),
    edgar_limit: int = typer.Option(25, "--edgar-limit", help="Max EDGAR enrichments this run"),
    edgar_bulk: bool = typer.Option(
        False, "--edgar-bulk",
        help="Download companyfacts.zip (~1.4 GB) and ingest ALL resolved US issuers (ADR-0005)",
    ),
    fetch_gleif: bool = typer.Option(
        True, "--fetch-gleif/--no-fetch-gleif",
        help="Self-heal the GLEIF ISIN→LEI mirror so audited EU (ESEF) is enabled",
    ),
    fetch_fx: bool = typer.Option(
        True, "--fetch-fx/--no-fetch-fx",
        help="Mirror the ECB daily rates so the snapshot gets *_eur columns",
    ),
    fsds_quarters: int = typer.Option(
        0, "--fsds-quarters",
        help="Backfill deep US history from the N most recent SEC FSDS quarters (0=off)",
    ),
    edinet_days: int = typer.Option(
        0, "--edinet-days",
        help="Audited Japan: scan the last N EDINET filing days (0=off;"
        " free-key opt-in, self-skips without CRIBLE_EDINET_KEY)",
    ),
    ch_accounts_url: str = typer.Option(
        "", "--ch-accounts-url",
        help="Companies House Accounts Data Product ZIP URL (empty=off;"
        " also needs the operator's data/uk-company-numbers.csv)",
    ),
    cvm_limit: int = typer.Option(
        0, "--cvm-limit",
        help="Audited Brazil: max CVM listings enriched this run (0=off; keyless, ODbL)",
    ),
    twse_limit: int = typer.Option(
        0, "--twse-limit",
        help="Audited Taiwan: max TWSE listings enriched this run (0=off; keyless, OGDL)",
    ),
    dart_limit: int = typer.Option(
        0, "--dart-limit",
        help="Audited Korea: max OpenDART listings enriched this run (0=off;"
        " free-key opt-in, self-skips without CRIBLE_DART_KEY)",
    ),
) -> None:
    """One bounded keyless refresh pass (the nightly dataset run)."""
    from crible.ingest.service import run_refresh

    result = run_refresh(
        deadline_seconds=deadline, esef_limit=esef_limit, edgar_limit=edgar_limit,
        edgar_bulk=edgar_bulk, fsds_quarters=fsds_quarters,
        fetch_gleif=fetch_gleif, fetch_fx=fetch_fx,
        max_seconds=max_minutes * 60 if max_minutes > 0 else None,
        edinet_days=edinet_days, companies_house_url=ch_accounts_url,
        cvm_limit=cvm_limit, twse_limit=twse_limit, dart_limit=dart_limit,
    )
    typer.echo(json.dumps(result, indent=2, default=str))


@app.command("mcp")
def mcp_cmd() -> None:
    """Serve the read-only MCP tool surface over stdio (for agents).

    Same data contract as everything else: --data-dir / CRIBLE_DATA_DIR
    points at the dataset `crible bootstrap` pulled.
    """
    from crible.mcp_server import serve

    serve()


@app.command("export-site")
def export_site_cmd(
    out: Path = typer.Option(..., "--out", help="Directory to write the static site artifacts to"),
    min_symbols: int = typer.Option(50, "--min-symbols", help="Refuse to publish below this snapshot coverage"),
) -> None:
    """Export the static artifacts the hosted screener runs on."""
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
    from crible import config
    from crible.compute.snapshot import build_snapshot_incremental, publish_snapshot

    data = config.data_dir()
    # incremental: rebuild only symbols whose raw changed since the last build,
    # reuse the base cache for the rest, and skip the republish when nothing
    # changed (F7) — same path the service loop and nightly refresh use
    snapshot = build_snapshot_incremental(data)
    if snapshot is None:
        typer.echo("snapshot unchanged — no raw changes since the last build")
        return
    if snapshot.empty:
        _fail("no raw data yet — run `crible ingest --bootstrap` then `crible ingest --once` first")
    path = publish_snapshot(snapshot, data)
    typer.echo(f"published {len(snapshot)} rows × {len(snapshot.columns)} columns to {path}")


if __name__ == "__main__":
    app()
