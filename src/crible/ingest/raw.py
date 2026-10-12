"""FR-002 / ADR-0003 — the immutable, versioned raw Parquet layer.

Every fetch is written as its own file (write-temp-then-rename, atomic on
POSIX), never overwritten: the raw layer is the durable source of truth any
snapshot can be recomputed from.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# statement types that carry fundamentals (prices-* are bars, meta-* markers)
STATEMENT_TYPES = ("income", "balance", "cashflow")


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
    compare_meta: tuple[str, ...] = (),
) -> Path:
    """Persist one fetched statement frame as a new immutable raw file.

    ``skip_identical`` is for the re-fetch-everything providers (EDGAR bulk,
    FSDS, ESEF): when the newest committed version already holds byte-equal
    data, return it untouched instead of re-stamping. That keeps
    the inventory's newest stamp stable for unchanged issuers, so incremental
    compute stays O(actually-changed) and the published tarball stops
    churning. A dtype round-trip mismatch simply falls through to a write —
    safe, never lossy.

    ``compare_meta`` names ``_``-prefixed columns the caller placed in the
    frame that must participate in the identity check (e.g. the ESEF
    ``_history_depth``): a change in such a column re-stamps once even when
    the data is unchanged.
    """
    safe_symbol = symbol.replace("/", "_")
    directory = Path(data_dir) / "raw" / f"provider={provider}" / f"symbol={safe_symbol}"
    directory.mkdir(parents=True, exist_ok=True)
    if skip_identical:
        existing = _newest_matching(directory, statement_type, freq)
        if existing is not None:

            def strip(df: pd.DataFrame) -> pd.DataFrame:
                dropped = [c for c in df.columns if c.startswith("_") and c not in compare_meta]
                return df.drop(columns=dropped)

            old = strip(pd.read_parquet(existing))
            if old.reset_index(drop=True).equals(strip(frame).reset_index(drop=True)):
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


@dataclass
class RawInventory:
    """ONE pass over the raw layer: (provider, symbol) → newest file per
    (statement_type, freq), with its fetched-at stamp. Every reader that used
    to glob the tree on its own (served/priced/gap symbols, the queue
    restore, the enrichment re-seed, the snapshot's 8 globs per symbol)
    asks this instead — the tree is walked once per stage, not once per
    question. Symbols are the directory names (``/`` stored as ``_``)."""

    # (provider, symbol) → (statement_type, freq) → (stamp seconds, path)
    entries: dict[tuple[str, str], dict[tuple[str, str], tuple[float, Path]]] = field(default_factory=dict)
    # symbol → its providers, built on first use: newest_stamp is asked once
    # per symbol per compute, and a scan of every entry each time was O(N²)
    # (45 s of a 49 s no-op compute at 27k symbols)
    _providers: dict[str, list[str]] | None = field(default=None, init=False, repr=False)

    @classmethod
    def scan(cls, data_dir: Path | str) -> RawInventory:
        inventory = cls()
        root = Path(data_dir) / "raw"
        if not root.is_dir():
            return inventory
        with os.scandir(root) as providers:
            for provider_entry in providers:
                if not provider_entry.is_dir() or not provider_entry.name.startswith("provider="):
                    continue
                provider = provider_entry.name.split("=", 1)[1]
                with os.scandir(provider_entry.path) as symbols:
                    for symbol_entry in symbols:
                        if symbol_entry.is_dir() and symbol_entry.name.startswith("symbol="):
                            inventory._scan_symbol(provider, symbol_entry)
        return inventory

    def _scan_symbol(self, provider: str, symbol_entry: os.DirEntry) -> None:
        newest: dict[tuple[str, str], tuple[float, Path]] = {}
        with os.scandir(symbol_entry.path) as files:
            for file in files:
                name = file.name
                if name.startswith(".") or not name.endswith(".parquet"):
                    continue  # the .tmp-* partial of a crashed write
                parts = name[: -len(".parquet")].split("-", 2)
                if len(parts) != 3:
                    continue
                statement_type, freq, stamp = parts
                try:
                    seconds = int(stamp) / 1000.0
                except ValueError:
                    continue
                key = (statement_type, freq)
                if key not in newest or seconds >= newest[key][0]:
                    newest[key] = (seconds, Path(file.path))
        if newest:
            self.entries[(provider, symbol_entry.name.split("=", 1)[1])] = newest
            self._providers = None

    def symbols(self, provider: str | None = None) -> set[str]:
        return {s for p, s in self.entries if provider is None or p == provider}

    def files(self, provider: str, symbol: str) -> dict[tuple[str, str], Path]:
        """The newest raw file per (statement_type, freq) for one listing."""
        found = self.entries.get((provider, symbol.replace("/", "_")), {})
        return {key: path for key, (_, path) in found.items()}

    def newest_stamp(
        self, symbol: str, types: tuple[str, ...] | None = None, provider: str | None = None
    ) -> float:
        """Newest fetched-at (seconds) for a symbol across providers (or one),
        optionally restricted to statement types; 0.0 when none."""
        safe = symbol.replace("/", "_")
        if self._providers is None:
            self._providers = {}
            for p, s in self.entries:
                self._providers.setdefault(s, []).append(p)
        best = 0.0
        for p in self._providers.get(safe, ()):
            if provider is not None and p != provider:
                continue
            for (statement_type, _), (seconds, _) in self.entries[(p, safe)].items():
                if types is None or statement_type in types:
                    best = max(best, seconds)
        return best

    def statement_symbols(self, exclude: tuple[str, ...] = ()) -> set[str]:
        """Symbols with fundamentals from any provider not in ``exclude``."""
        return {
            s
            for (p, s), found in self.entries.items()
            if p not in exclude and any(t in STATEMENT_TYPES for t, _ in found)
        }

    def priced_symbols(self) -> set[str]:
        """Symbols with raw price bars from any provider."""
        return {s for (_, s), found in self.entries.items() if any(t == "prices" for t, _ in found)}
