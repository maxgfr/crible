// DSL parity — the TypeScript port must match the Python compiler EXACTLY on
// the shared golden vectors (ui/src/dsl/golden.json), including error
// messages, positions and hints, so the in-browser static build can never drift from
// the server semantics. The same file is asserted by tests/test_dsl_parity.py.

import { describe, expect, it } from "vitest";
import golden from "../dsl/golden.json";
import { compileQuery, compileSort } from "../dsl/compiler";
import { DslError, parse } from "../dsl/parser";

const whitelist = new Set<string>(golden.whitelist);

describe("DSL golden parity", () => {
  it("the golden file is meaningful", () => {
    expect(golden.cases.length).toBeGreaterThanOrEqual(12);
    expect(golden.errors.length).toBeGreaterThanOrEqual(6);
    expect(golden.sorts.length).toBeGreaterThanOrEqual(3);
  });

  it("compiles every query vector to identical SQL and params", () => {
    for (const c of golden.cases) {
      const [sql, params] = compileQuery(parse(c.query), whitelist);
      expect(sql, c.query).toBe(c.sql);
      expect(params, c.query).toEqual(c.params);
    }
  });

  it("compiles every sort vector identically", () => {
    for (const s of golden.sorts) {
      expect(compileSort(s.sort, whitelist), JSON.stringify(s.sort)).toBe(s.sql);
    }
  });

  it("raises identical errors — message, position, hint", () => {
    for (const e of golden.errors) {
      let caught: DslError | null = null;
      try {
        compileQuery(parse(e.query), whitelist);
      } catch (err) {
        caught = err as DslError;
      }
      expect(caught, e.query).toBeInstanceOf(DslError);
      expect(caught!.message, e.query).toBe(e.message);
      expect(caught!.position, e.query).toBe(e.position);
      expect(caught!.hint, e.query).toBe(e.hint);
    }
  });
});
