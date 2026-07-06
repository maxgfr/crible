"""FR-002 / ADR-0003 — the immutable, versioned raw Parquet layer.

Every fetch is written as its own file (write-temp-then-rename, atomic on
POSIX), never overwritten: the raw layer is the durable source of truth any
snapshot can be recomputed from.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_raw_statement(
    data_dir: Path | str,
    *,
    symbol: str,
    provider: str,
    statement_type: str,
    freq: str,
    frame: pd.DataFrame,
    fetched_at: float,
) -> Path:
    safe_symbol = symbol.replace("/", "_")
    directory = Path(data_dir) / "raw" / f"provider={provider}" / f"symbol={safe_symbol}"
    directory.mkdir(parents=True, exist_ok=True)
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
