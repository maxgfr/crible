// The query builder's model → DSL text. PURE composition, no hidden logic
// (FR-009 spirit, inherited from the retired FilterBar): the output is a
// plain, editable query the user could have typed, handled by the same
// grammar in both the api and static engines. One-way by design — the DSL
// text stays the single screening language; the builder never parses it back.

import type { FieldInfo } from "../data";

export const NUMBER_OPS = [">", ">=", "<", "<=", "=", "!=", "IN"] as const;
export const STRING_OPS = ["=", "!=", "IN"] as const;
export type Op = (typeof NUMBER_OPS)[number];

export interface Condition {
  kind: "cond";
  field: string;
  op: Op;
  value: string;
}

export interface Group {
  kind: "group";
  op: "AND" | "OR";
  items: Array<Condition | Group>;
}

export type FieldTypes = Map<string, FieldInfo["type"]>;

/** Escape a value into one single-quoted DSL string literal. */
export function quote(value: string): string {
  return `'${value.replaceAll("\\", "\\\\").replaceAll("'", "\\'")}'`;
}

export function operatorsFor(type: FieldInfo["type"]): readonly Op[] {
  return type === "number" ? NUMBER_OPS : STRING_OPS;
}

export function emptyCondition(): Condition {
  return { kind: "cond", field: "", op: ">=", value: "" };
}

export function emptyGroup(op: "AND" | "OR" = "OR"): Group {
  return { kind: "group", op, items: [emptyCondition()] };
}

function literal(raw: string, type: FieldInfo["type"]): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  if (type === "number") {
    const num = Number(trimmed);
    return Number.isFinite(num) ? String(num) : null;
  }
  return quote(trimmed);
}

function conditionDsl(cond: Condition, types: FieldTypes): string | null {
  const type = types.get(cond.field);
  if (!type) return null; // unpicked or non-whitelisted field — skipped
  if (cond.op === "IN") {
    const items = cond.value
      .split(",")
      .map((item) => literal(item, type))
      .filter((item): item is string => item !== null);
    return items.length ? `${cond.field} IN (${items.join(", ")})` : null;
  }
  const value = literal(cond.value, type);
  return value === null ? null : `${cond.field} ${cond.op} ${value}`;
}

/**
 * Serialize a group to DSL text. Incomplete conditions (no field, empty or
 * non-numeric value on a number field) are skipped, never errored — the
 * builder composes what is complete. Returns "" when nothing is complete.
 */
export function buildDsl(group: Group, types: FieldTypes): string {
  const parts = group.items
    .map((item) =>
      item.kind === "cond" ? conditionDsl(item, types) : nestedDsl(item, types),
    )
    .filter((part): part is string => part !== null && part !== "");
  return parts.join(` ${group.op} `);
}

function nestedDsl(group: Group, types: FieldTypes): string | null {
  const inner = buildDsl(group, types);
  return inner ? `(${inner})` : null;
}
