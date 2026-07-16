"""FR-008 — Docker Compose deployment (static contract checks).

The living proof is the zero-key E2E (docker compose up without keys → first
screen returns rows); these tests pin the contract the E2E relies on.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fr008_compose_defines_ingest_and_api_with_shared_volume_and_healthchecks() -> None:
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "ingest:" in compose and "api:" in compose
    assert compose.count("crible-data:/data") == 2  # one shared volume, both services
    assert compose.count("healthcheck:") == 2
    assert 'command: ["crible", "ingest", "--loop"]' in compose


def test_fr008_keyless_by_default_any_key_is_an_optional_passthrough() -> None:
    # the keyless contract (2026-07-14, hardened 2026-07-17: keyless-only —
    # no keyed provider ships at all): the stack runs with NO keys — if a
    # key passthrough ever reappears it must DEFAULT TO EMPTY (disabled),
    # never be required and never hardcoded.
    import re

    compose = (ROOT / "docker-compose.yml").read_text()
    for line in compose.splitlines():
        if "_KEY" in line and not line.strip().startswith("#"):
            assert re.search(r"_KEY:\s*\$\{[A-Z_]+:-\}", line), f"key not empty-defaulted: {line!r}"


def test_fr008_no_secrets_baked_into_the_image() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "_KEY" not in dockerfile  # no provider keys anywhere (NFR-002)
    assert "ENV" in dockerfile and "CRIBLE_DATA_DIR=/data" in dockerfile


def test_fr008_ingest_loop_owns_bootstrap_crawl_compute() -> None:
    """The compose ingest service runs the loop that FR-008 promises:
    bootstrap if empty → crawl cycle → compute after every cycle."""
    from crible.ingest import service

    source = (ROOT / "src/crible/ingest/service.py").read_text()
    assert "run_bootstrap" in source and "run_compute" in source
    assert service.bootstrap_sample()  # non-empty default sample (~100 symbols)
    assert 90 <= len(service.bootstrap_sample()) <= 110
