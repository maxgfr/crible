"""Cross-language DSL parity — Python compiler vs the TypeScript port.

`ui/src/dsl/golden.json` is the single source of truth both suites assert
against: every (query → SQL, params) vector and every error (message,
position, hint) must match EXACTLY in pytest and vitest, so the in-browser
static build can never drift from the server semantics.

The golden file is GENERATED from the inputs below by the Python
implementation — never edited by hand. After changing an input or the DSL:

    uv run --frozen python -m tests.test_dsl_parity

and `test_parity_golden_file_is_current` fails until it is regenerated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crible.dsl.compiler import compile_query, compile_sort
from crible.dsl.parser import DslError, parse

GOLDEN = Path(__file__).resolve().parent.parent / "ui" / "src" / "dsl" / "golden.json"

STRING_FIELDS = ["symbol", "name", "country", "country_name", "region", "sector", "industry", "exchange"]
STRING_FIELDS += ["currency", "period"]
NUMBER_FIELDS = [
    "revenue",
    "net_income",
    "total_assets",
    "free_cash_flow",
    "return_on_equity",
    "debt_to_equity_ratio",
    "price_to_earnings_ratio",
    "price_to_book_ratio",
    "earnings_yield",
    "piotroski_f",
    "altman_z",
    "beneish_m",
    "composite_rank",
    "quality_rank",
    "value_rank",
    "ncav_growth",
    "name_growth",
]
BOOLEAN_FIELDS = ["top10k", "primary_listing"]
TYPES = {
    **{f: "string" for f in STRING_FIELDS},
    **{f: "number" for f in NUMBER_FIELDS},
    **{f: "boolean" for f in BOOLEAN_FIELDS},
}

CASES = [
    "piotroski_f >= 7",
    "altman_z > 2.99",
    "beneish_m > -1.78",
    "price_to_earnings_ratio < 12 AND price_to_book_ratio < 1.5",
    "return_on_equity > 0.15 AND debt_to_equity_ratio < 1",
    "composite_rank >= 80",
    "country IN ('FR', 'DE') AND piotroski_f >= 7",
    "(country = 'JP' OR country = 'US') AND NOT price_to_earnings_ratio > 30",
    "NOT (sector = 'Financials' OR sector = 'Real Estate')",
    "name = 'O\\'Reilly'",
    "revenue > 1e9",
    "piotroski_f = 7 OR piotroski_f == 8",
    "country <> 'US' AND country != 'CA'",
    "sector IN ('Information Technology')",
    "country in ('FR') and piotroski_f >= 7",
    "country = 'FR' OR country = 'DE' AND piotroski_f >= 8",
    "revenue >= -2.5e-3",
    "top10k = true",
    "top10k = TRUE and primary_listing != False",
    'name = "Double \\"quoted\\""',
    "country = 'FR' and not sector = 'Energy' or region In ('europe')",
    "NOT NOT piotroski_f >= 7",
    "name = 'Société Générale' AND country = 'FR'",
    "name = '😀' AND piotroski_f > 1",
    "top10k = false",
    "(((piotroski_f > 1)))",
]

SORTS = [
    "-composite_rank",
    "country,-piotroski_f",
    "+name",
    "",
    "symbol , -altman_z",
    "-symbol",
    "piotroski_f",
]

ERRORS = [
    "piotroski > 7",
    "return_6m > 0.1",
    "zzz_qqq = 1",
    "roe >",
    "",
    "country = 'FR' ;",
    "country = 'FR' name",
    "country IN 'FR'",
    "IN > 3",
    "country IN (1,)",
    "(country = 'FR'",
    "country = ",
    # type mismatches — a 422, never a DuckDB ConversionException
    "sector = 5",
    'revenue = "abc"',
    "top10k = 'yes'",
    "country IN ('FR', 5)",
    # difflib tie-break: the LARGEST name wins an equal ratio
    "growth > 1",
    # positions count code points, after a non-BMP character too
    "name = '😀' AND zz > 1",
    "piotroski_f > ٣",
    "​piotroski_f > 1",
    " piotroski_f > 1",
    "\x85piotroski_f > 1",
    "\x85",
    " \t ",
    "name = '😀' AND 😀 > 1",
    # caps: nesting depth and length
    "NOT " * 40 + "piotroski_f > 1",
    "(" * 40 + "piotroski_f > 1" + ")" * 40,
    "piotroski_f > 1 AND " * 110 + "piotroski_f > 1",
]

SORT_ERRORS = ["-nope", "piotroski", "growth"]


def generate() -> dict:
    whitelist = set(TYPES)
    golden: dict = {"whitelist": list(TYPES), "types": TYPES, "cases": [], "sorts": [], "errors": []}
    for query in CASES:
        sql, params = compile_query(parse(query), whitelist, TYPES)
        golden["cases"].append({"query": query, "sql": sql, "params": params})
    for sort in SORTS:
        golden["sorts"].append({"sort": sort, "sql": compile_sort(sort, whitelist)})
    for query in ERRORS:
        with pytest.raises(DslError) as err:
            compile_query(parse(query), whitelist, TYPES)
        golden["errors"].append(
            {
                "query": query,
                "message": str(err.value),
                "position": err.value.position,
                "hint": err.value.hint,
            }
        )
    golden["sort_errors"] = []
    for sort in SORT_ERRORS:
        with pytest.raises(DslError) as err:
            compile_sort(sort, whitelist)
        golden["sort_errors"].append(
            {"sort": sort, "message": str(err.value), "position": err.value.position, "hint": err.value.hint}
        )
    return golden


def render(golden: dict) -> str:
    return json.dumps(golden, indent=2, ensure_ascii=False) + "\n"


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN.read_text())


def test_parity_golden_file_is_current() -> None:
    """The committed golden is exactly what the Python DSL produces today."""
    assert GOLDEN.read_text() == render(generate()), "run: uv run --frozen python -m tests.test_dsl_parity"


def test_parity_golden_file_is_meaningful(golden) -> None:
    assert len(golden["cases"]) >= 12
    assert len(golden["errors"]) >= 6
    assert len(golden["sorts"]) >= 3
    assert golden["sort_errors"]
    assert golden["whitelist"]


def test_parity_query_vectors_compile_identically(golden) -> None:
    whitelist = set(golden["whitelist"])
    for case in golden["cases"]:
        sql, params = compile_query(parse(case["query"]), whitelist, golden["types"])
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
            compile_query(parse(case["query"]), whitelist, golden["types"])
        assert str(err.value) == case["message"], case["query"]
        assert err.value.position == case["position"], case["query"]
        assert err.value.hint == case["hint"], case["query"]


if __name__ == "__main__":
    GOLDEN.write_text(render(generate()))
    print(f"wrote {GOLDEN}")
