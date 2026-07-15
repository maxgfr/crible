"""FR-002 / ADR-0003 — the immutable, versioned raw Parquet layer.

Every fetch is written as its own file (write-temp-then-rename, atomic on
POSIX), never overwritten: the raw layer is the durable source of truth any
snapshot can be recomputed from.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def iter_raw_files(directory: Path) -> list[Path]:
    """Committed raw parquet files in a symbol dir, chronological (zero-padded
    ms stamps sort lexically), skipping the ``.tmp-*`` partials a crashed write
    leaves behind — pathlib's ``glob('*.parquet')`` matches dotfiles, so those
    would otherwise be misparsed by prune and crash the snapshot reader (F11)."""
    return sorted(f for f in directory.glob("*.parquet") if not f.name.startswith("."))


def prune_raw(data_dir: Path | str) -> int:
    """Delete all but the newest raw file per (provider, symbol, statement, freq).

    Lossless for snapshots — ``latest_raw_frames`` only ever reads the newest
    version — and caps the size of a persisted raw layer (the published dataset)
    no matter how many refresh runs accumulate. Returns the number deleted.
    """
    deleted = 0
    for directory in (Path(data_dir) / "raw").glob("provider=*/symbol=*"):
        newest: dict[tuple[str, str], Path] = {}
        # zero-padded ms stamps make lexical order chronological
        for file in iter_raw_files(directory):
            statement_type, freq, _ = file.stem.split("-", 2)
            key = (statement_type, freq)
            if key in newest:
                newest[key].unlink()
                deleted += 1
            newest[key] = file
    return deleted


def _newest_matching(directory: Path, statement_type: str, freq: str) -> Path | None:
    prefix = f"{statement_type}-{freq}"
    candidates = [f for f in iter_raw_files(directory) if f.stem.rsplit("-", 1)[0] == prefix]
    return candidates[-1] if candidates else None


def write_raw_statement(
    data_dir: Path | str,
    *,
    symbol: str,
    provider: str,
    statement_type: str,
    freq: str,
    frame: pd.DataFrame,
    fetched_at: float,
    skip_identical: bool = False,
) -> Path:
    """Persist one fetched statement frame as a new immutable raw file.

    ``skip_identical`` is for the re-fetch-everything providers (EDGAR bulk,
    FSDS, ESEF): when the newest committed version already holds byte-equal
    data, return it untouched instead of re-stamping. That keeps
    ``_newest_raw_stamp`` stable for unchanged issuers, so incremental
    compute stays O(actually-changed) and the published tarball stops
    churning. A dtype round-trip mismatch simply falls through to a write —
    safe, never lossy.
    """
    safe_symbol = symbol.replace("/", "_")
    directory = Path(data_dir) / "raw" / f"provider={provider}" / f"symbol={safe_symbol}"
    directory.mkdir(parents=True, exist_ok=True)
    if skip_identical:
        existing = _newest_matching(directory, statement_type, freq)
        if existing is not None:
            old = pd.read_parquet(existing)
            old = old.drop(columns=[c for c in old.columns if c.startswith("_")])
            if old.reset_index(drop=True).equals(frame.reset_index(drop=True)):
                return existing
    stamp = f"{int(fetched_at * 1000):015d}"
    final = directory / f"{statement_type}-{freq}-{stamp}.parquet"
    tmp = directory / f".tmp-{statement_type}-{freq}-{stamp}.parquet"
    out = frame.copy()
    out["_symbol"] = symbol
    out["_provider"] = provider
    out["_statement_type"] = statement_type
    out["_freq"] = freq
    out["_fetched_at"] = fetched_at
    out.to_parquet(tmp, index=False)
    tmp.rename(final)
    return final
