"""ENGINE_SCHEMA_VERSION guards the base cache: kept rows carry the columns
they were built with, so a column change that forgets the bump publishes
nothing new on an existing dataset (the recette's « unchanged » compute that
dropped five new indicators). The frozen column set below is paired with the
version: change one, change the other, then regenerate with
`uv run --frozen python -m tests.test_engine_schema`."""

from __future__ import annotations

import json
from pathlib import Path

from crible.compute.snapshot import ENGINE_SCHEMA_VERSION, build_symbol_snapshot

from tests.test_fr003_compute import IMPROVING, income_frame

FROZEN = Path(__file__).parent / "fixtures" / "engine-schema.json"


def published_columns() -> list[str]:
    frames = {(s, "annual"): income_frame(rows, ["2023", "2024", "2025"]) for s, rows in IMPROVING.items()}
    snapshot = build_symbol_snapshot("P.PA", frames, computed_at=1.0, price_quote=(10.0, "2025-12-31"))
    return sorted(snapshot.columns)


def test_a_column_change_bumps_the_engine_schema() -> None:
    frozen = json.loads(FROZEN.read_text())
    columns = published_columns()
    if columns != frozen["columns"]:
        added = sorted(set(columns) - set(frozen["columns"]))
        removed = sorted(set(frozen["columns"]) - set(columns))
        assert ENGINE_SCHEMA_VERSION != frozen["engine_schema_version"], (
            f"snapshot columns changed (+{added} -{removed}) without an ENGINE_SCHEMA_VERSION bump"
        )
    assert ENGINE_SCHEMA_VERSION == frozen["engine_schema_version"], (
        "regenerate tests/fixtures/engine-schema.json"
    )
    assert columns == frozen["columns"], "regenerate tests/fixtures/engine-schema.json"


if __name__ == "__main__":
    FROZEN.write_text(
        json.dumps({"engine_schema_version": ENGINE_SCHEMA_VERSION, "columns": published_columns()}, indent=2)
        + "\n"
    )
    print(f"wrote {FROZEN}")
