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


def test_fr008_zero_key_mode_is_the_only_mode() -> None:
    # the keyless contract, strengthened (2026-07-13): the stack passes NO
    # provider key env vars at all — there is nothing to configure
    compose = (ROOT / "docker-compose.yml").read_text()
    assert "_KEY" not in compose


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
