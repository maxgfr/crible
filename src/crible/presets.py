"""FR-009 — preset screens: plain, visible, editable DSL strings.

Every preset is an ordinary DSL query — no hidden logic anywhere. Thresholds
are published starting points (Piotroski ≥ 7; Altman safe zone Z > 2.99;
Beneish red flag M > -1.78), meant to be edited.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    description: str
    dsl: str


_PRESETS = [
    Preset(
        id="piotroski-strong",
        name="Piotroski strong",
        description="Financially strengthening companies (F-Score at least 7 of 9)",
        dsl="piotroski_f >= 7",
    ),
    Preset(
        id="altman-safe",
        name="Altman safe zone",
        description="Bankruptcy-safe zone under the classic Z-Score (Z > 2.99)",
        dsl="altman_z > 2.99",
    ),
    Preset(
        id="beneish-red-flags",
        name="Beneish red flags",
        description="Possible earnings manipulation (M-Score above the -1.78 threshold)",
        dsl="beneish_m > -1.78",
    ),
    Preset(
        id="classic-value",
        name="Classic value",
        description="Cheap on earnings and book value",
        dsl="price_to_earnings_ratio < 12 AND price_to_book_ratio < 1.5",
    ),
    Preset(
        id="quality",
        name="Quality",
        description="High return on equity with conservative leverage",
        dsl="return_on_equity > 0.15 AND debt_to_equity_ratio < 1",
    ),
]

PRESETS: dict[str, Preset] = {p.id: p for p in _PRESETS}
