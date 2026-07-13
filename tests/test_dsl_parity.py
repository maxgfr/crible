"""Cross-language DSL parity — Python compiler vs the TypeScript port.

`ui/src/dsl/golden.json` is the single source of truth both suites assert
against: every (query → SQL, params) vector and every error (message,
position, hint) must match EXACTLY in pytest and vitest, so the in-browser
static build can never drift from the server semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crible.dsl.compiler import compile_query, compile_sort
from crible.dsl.parser import DslError, parse

GOLDEN = Path(__file__).resolve().parent.parent / "ui" / "src" / "dsl" / "golden.json"


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN.read_text())


def test_parity_golden_file_is_meaningful(golden) -> None:
    assert len(golden["cases"]) >= 12
    assert len(golden["errors"]) >= 6
    assert len(golden["sorts"]) >= 3
    assert golden["whitelist"]


def test_parity_query_vectors_compile_identically(golden) -> None:
    whitelist = set(golden["whitelist"])
    for case in golden["cases"]:
        sql, params = compile_query(parse(case["query"]), whitelist)
        assert sql == case["sql"], case["query"]
        assert params == case["params"], case["query"]


def test_parity_sort_vectors_compile_identically(golden) -> None:
    whitelist = set(golden["whitelist"])
    for case in golden["sorts"]:
        assert compile_sort(case["sort"], whitelist) == case["sql"], case["sort"]


def test_parity_error_vectors_match_message_position_hint(golden) -> None:
    whitelist = set(golden["whitelist"])
    for case in golden["errors"]:
        with pytest.raises(DslError) as err:
            compile_query(parse(case["query"]), whitelist)
        assert str(err.value) == case["message"], case["query"]
        assert err.value.position == case["position"], case["query"]
        assert err.value.hint == case["hint"], case["query"]
