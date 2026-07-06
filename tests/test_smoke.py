"""T-000 — project skeleton smoke tests."""

import crible


def test_package_importable() -> None:
    assert crible.__version__
