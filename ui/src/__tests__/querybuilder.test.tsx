// The query builder composes the DSL — full field list, typed operators,
// AND/OR groups — and every output it can produce must be a grammatical,
// compilable query (the FilterBar contract, generalized).

import { fireEvent, render, screen as rtl } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryBuilder } from "../components/QueryBuilder";
import {
  buildDsl,
  operatorsFor,
  quote,
  type Condition,
  type FieldTypes,
  type Group,
} from "../components/query-dsl";
import { compileQuery } from "../dsl/compiler";
import { parse } from "../dsl/parser";
import type { FieldInfo } from "../data";

const FIELDS: FieldInfo[] = [
  { name: "piotroski_f", type: "number" },
  { name: "price_to_earnings_ratio", type: "number" },
  { name: "composite_rank", type: "number" },
  { name: "region", type: "string" },
  { name: "sector", type: "string" },
  { name: "country", type: "string" },
];

const TYPES: FieldTypes = new Map(FIELDS.map((f) => [f.name, f.type]));
const WHITELIST = new Set(FIELDS.map((f) => f.name));

const cond = (field: string, op: Condition["op"], value: string): Condition => ({
  kind: "cond",
  field,
  op,
  value,
});
const group = (op: "AND" | "OR", items: Group["items"]): Group => ({ kind: "group", op, items });

// -------------------------------------------------------------- serializer

describe("query-dsl serializer", () => {
  it("composes a single comparison", () => {
    expect(buildDsl(group("AND", [cond("piotroski_f", ">=", "7")]), TYPES)).toBe(
      "piotroski_f >= 7",
    );
  });

  it("chains with AND and parenthesizes nested OR groups", () => {
    const model = group("AND", [
      cond("piotroski_f", ">=", "7"),
      group("OR", [cond("region", "=", "europe"), cond("region", "=", "us")]),
    ]);
    expect(buildDsl(model, TYPES)).toBe(
      "piotroski_f >= 7 AND (region = 'europe' OR region = 'us')",
    );
  });

  it("types IN lists per field: numbers bare, strings quoted", () => {
    expect(buildDsl(group("AND", [cond("country", "IN", "FR, DE")]), TYPES)).toBe(
      "country IN ('FR', 'DE')",
    );
    expect(buildDsl(group("AND", [cond("piotroski_f", "IN", "7, 8")]), TYPES)).toBe(
      "piotroski_f IN (7, 8)",
    );
  });

  it("skips incomplete conditions instead of erroring", () => {
    const model = group("AND", [
      cond("", ">=", "7"), // no field
      cond("piotroski_f", ">=", ""), // no value
      cond("piotroski_f", ">=", "abc"), // not a number
      cond("composite_rank", ">=", "80"),
      group("OR", [cond("", "=", "")]), // empty group vanishes entirely
    ]);
    expect(buildDsl(model, TYPES)).toBe("composite_rank >= 80");
  });

  it("keeps hostile string values inside ONE literal (anti-injection)", () => {
    const hostile = "eu' OR 1=1 --";
    expect(quote(hostile)).toBe("'eu\\' OR 1=1 --'");
    const dsl = buildDsl(group("AND", [cond("country", "=", hostile)]), TYPES);
    const [where, params] = compileQuery(parse(dsl), WHITELIST);
    expect(where).toBe('"country" = ?');
    expect(params).toEqual([hostile]); // one bound param — never SQL text
  });

  it("every composable output parses and compiles against the whitelist", () => {
    const models: Group[] = [
      group("AND", [cond("piotroski_f", ">=", "7")]),
      group("OR", [cond("region", "=", "europe"), cond("sector", "!=", "Financials")]),
      group("AND", [
        cond("price_to_earnings_ratio", "<=", "12.5"),
        cond("country", "IN", "FR, DE, IT"),
        group("OR", [cond("piotroski_f", "IN", "8, 9"), cond("composite_rank", ">", "80")]),
      ]),
    ];
    for (const model of models) {
      const dsl = buildDsl(model, TYPES);
      expect(dsl).not.toBe("");
      const [where, params] = compileQuery(parse(dsl), WHITELIST); // must not throw
      expect(where.length).toBeGreaterThan(0);
      expect(Array.isArray(params)).toBe(true);
    }
  });

  it("constrains operators by field type", () => {
    expect(operatorsFor("number")).toContain(">=");
    expect(operatorsFor("string")).toEqual(["=", "!=", "IN"]);
  });
});

// --------------------------------------------------------------- component

describe("QueryBuilder (component)", () => {
  it("builds and applies a single condition", () => {
    const onApply = vi.fn();
    render(<QueryBuilder fields={FIELDS} onApply={onApply} />);
    fireEvent.change(rtl.getByLabelText("Field"), { target: { value: "piotroski_f" } });
    fireEvent.change(rtl.getByLabelText("Value"), { target: { value: "7" } });
    fireEvent.click(rtl.getByRole("button", { name: /apply filters/i }));
    expect(onApply).toHaveBeenCalledWith("piotroski_f >= 7");
  });

  it("offers enum values for region and composes an AND chain", () => {
    const onApply = vi.fn();
    render(<QueryBuilder fields={FIELDS} onApply={onApply} />);
    fireEvent.change(rtl.getByLabelText("Field"), { target: { value: "piotroski_f" } });
    fireEvent.change(rtl.getByLabelText("Value"), { target: { value: "7" } });
    fireEvent.click(rtl.getByRole("button", { name: /add condition/i }));
    fireEvent.change(rtl.getAllByLabelText("Field")[1], { target: { value: "region" } });
    // region is enumerated — the value control is a select of known regions
    const valueControls = rtl.getAllByLabelText("Value");
    expect(valueControls[1].tagName).toBe("SELECT");
    fireEvent.change(valueControls[1], { target: { value: "europe" } });
    fireEvent.click(rtl.getByRole("button", { name: /apply filters/i }));
    expect(onApply).toHaveBeenCalledWith("piotroski_f >= 7 AND region = 'europe'");
  });

  it("composes a nested OR group with parentheses", () => {
    const onApply = vi.fn();
    render(<QueryBuilder fields={FIELDS} onApply={onApply} />);
    fireEvent.change(rtl.getByLabelText("Field"), { target: { value: "piotroski_f" } });
    fireEvent.change(rtl.getByLabelText("Value"), { target: { value: "7" } });
    fireEvent.click(rtl.getByRole("button", { name: /add group/i }));
    fireEvent.change(rtl.getAllByLabelText("Field")[1], { target: { value: "region" } });
    fireEvent.change(rtl.getAllByLabelText("Value")[1], { target: { value: "europe" } });
    fireEvent.click(rtl.getByRole("button", { name: /add condition to group/i }));
    fireEvent.change(rtl.getAllByLabelText("Field")[2], { target: { value: "region" } });
    fireEvent.change(rtl.getAllByLabelText("Value")[2], { target: { value: "us" } });
    fireEvent.click(rtl.getByRole("button", { name: /apply filters/i }));
    expect(onApply).toHaveBeenCalledWith(
      "piotroski_f >= 7 AND (region = 'europe' OR region = 'us')",
    );
  });

  it("restricts the operator menu to the field's type", () => {
    render(<QueryBuilder fields={FIELDS} onApply={() => {}} />);
    fireEvent.change(rtl.getByLabelText("Field"), { target: { value: "region" } });
    const ops = [...(rtl.getByLabelText("Operator") as HTMLSelectElement).options].map(
      (o) => o.value,
    );
    expect(ops).toEqual(["=", "!=", "IN"]);
  });

  it("disables Apply while nothing is composable", () => {
    const onApply = vi.fn();
    render(<QueryBuilder fields={FIELDS} onApply={onApply} />);
    const apply = rtl.getByRole("button", { name: /apply filters/i });
    expect(apply).toBeDisabled();
    fireEvent.click(apply);
    expect(onApply).not.toHaveBeenCalled();
  });
});
