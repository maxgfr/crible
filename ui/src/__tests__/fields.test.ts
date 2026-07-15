// dsl/fields — the auto fallback that turns a query's referenced fields
// into grid columns. Tokenizer-backed: keywords and literals never leak,
// malformed DSL yields [] (the compiler owns error reporting).

import { describe, expect, it } from "vitest";
import { fieldsInQuery } from "../dsl/fields";

describe("fieldsInQuery", () => {
  it("extracts referenced fields, deduped, in first-appearance order", () => {
    expect(fieldsInQuery("piotroski_f >= 7 AND altman_z > 2.99 AND piotroski_f < 9")).toEqual([
      "piotroski_f",
      "altman_z",
    ]);
  });

  it("excludes keywords and string/number literals", () => {
    expect(fieldsInQuery("country IN ('FR', 'DE') AND NOT sector = 'Energy'")).toEqual([
      "country",
      "sector",
    ]);
    expect(fieldsInQuery("magic_formula_rank >= 80 OR ncav_to_market_cap >= 1.5")).toEqual([
      "magic_formula_rank",
      "ncav_to_market_cap",
    ]);
  });

  it("returns [] for empty or malformed DSL", () => {
    expect(fieldsInQuery("")).toEqual([]);
    expect(fieldsInQuery("piotroski_f >= ###")).toEqual([]);
  });
});
