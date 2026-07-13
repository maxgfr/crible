// The full query builder: any snapshot column (live schema via
// DataClient.fields()), operators constrained by field type, AND/OR groups —
// COMPOSING the DSL. It replaces the fixed FilterBar and keeps its contract:
// no hidden logic (FR-009 spirit), applying writes a plain, editable query
// into the query bar, one-way — the DSL stays the single screening language.

import { useMemo, useState } from "react";
import type { FieldInfo } from "../data";
import { ENUM_VALUES, GROUP_ORDER, fieldGroup, fieldLabel } from "../data/field-catalog";
import { parse } from "../dsl/parser";
import {
  buildDsl,
  emptyCondition,
  emptyGroup,
  operatorsFor,
  type Condition,
  type FieldTypes,
  type Group,
  type Op,
} from "./query-dsl";

interface Props {
  fields: FieldInfo[];
  onApply: (dsl: string) => void;
}

interface OptionGroup {
  group: string;
  fields: FieldInfo[];
}

function FieldSelect({
  value,
  groups,
  onChange,
}: {
  value: string;
  groups: OptionGroup[];
  onChange: (field: string) => void;
}) {
  return (
    <select aria-label="Field" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">field…</option>
      {groups.map((g) => (
        <optgroup key={g.group} label={g.group}>
          {g.fields.map((f) => (
            <option key={f.name} value={f.name}>
              {fieldLabel(f.name)}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}

function ConditionRow({
  cond,
  groups,
  types,
  onChange,
  onRemove,
}: {
  cond: Condition;
  groups: OptionGroup[];
  types: FieldTypes;
  onChange: (cond: Condition) => void;
  onRemove: () => void;
}) {
  const type = types.get(cond.field) ?? "number";
  const enumValues = cond.op !== "IN" ? ENUM_VALUES[cond.field] : undefined;

  const pickField = (field: string) => {
    const nextType = types.get(field) ?? "number";
    const ops = operatorsFor(nextType) as readonly string[];
    const op = ops.includes(cond.op) ? cond.op : nextType === "number" ? ">=" : "=";
    onChange({ ...cond, field, op: op as Op, value: "" });
  };

  return (
    <span className="qb-row">
      <FieldSelect value={cond.field} groups={groups} onChange={pickField} />
      <select
        aria-label="Operator"
        value={cond.op}
        onChange={(e) => onChange({ ...cond, op: e.target.value as Op })}
      >
        {operatorsFor(type).map((op) => (
          <option key={op} value={op}>
            {op}
          </option>
        ))}
      </select>
      {enumValues ? (
        <select
          aria-label="Value"
          value={cond.value}
          onChange={(e) => onChange({ ...cond, value: e.target.value })}
        >
          <option value="">value…</option>
          {enumValues.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      ) : (
        <input
          aria-label="Value"
          placeholder={cond.op === "IN" ? "v1, v2, …" : "value"}
          type={type === "number" && cond.op !== "IN" ? "number" : "text"}
          size={cond.op === "IN" ? 14 : 8}
          value={cond.value}
          onChange={(e) => onChange({ ...cond, value: e.target.value })}
        />
      )}
      <button aria-label="Remove condition" title="Remove condition" onClick={onRemove}>
        ×
      </button>
    </span>
  );
}

export function QueryBuilder({ fields, onApply }: Props) {
  const [root, setRoot] = useState<Group>({ kind: "group", op: "AND", items: [emptyCondition()] });

  const types: FieldTypes = useMemo(
    () => new Map(fields.map((f) => [f.name, f.type])),
    [fields],
  );

  const groups: OptionGroup[] = useMemo(() => {
    const byGroup = new Map<string, FieldInfo[]>();
    for (const field of fields) {
      const g = fieldGroup(field.name);
      byGroup.set(g, [...(byGroup.get(g) ?? []), field]);
    }
    const order = [
      ...GROUP_ORDER,
      ...[...byGroup.keys()].filter((g) => !GROUP_ORDER.includes(g)).sort(),
    ];
    return order
      .filter((g) => byGroup.has(g))
      .map((g) => ({
        group: g,
        fields: byGroup
          .get(g)!
          .slice()
          .sort((a, b) => fieldLabel(a.name).localeCompare(fieldLabel(b.name))),
      }));
  }, [fields]);

  // path is [rootIndex] or [rootIndex, subIndex]; next === null removes
  const updateItem = (path: number[], next: Condition | Group | null) => {
    setRoot((current) => {
      const items = [...current.items];
      if (path.length === 1) {
        if (next === null) items.splice(path[0], 1);
        else items[path[0]] = next;
      } else {
        const sub = items[path[0]] as Group;
        const subItems = [...sub.items];
        if (next === null) subItems.splice(path[1], 1);
        else subItems[path[1]] = next;
        if (subItems.length === 0) items.splice(path[0], 1); // emptied group goes away
        else items[path[0]] = { ...sub, items: subItems };
      }
      return { ...current, items };
    });
  };

  const dsl = buildDsl(root, types);

  const apply = () => {
    if (!dsl) return;
    try {
      parse(dsl); // belt-and-braces: composed text must be grammatical
    } catch {
      return; // a serializer bug must never run a broken query
    }
    onApply(dsl);
  };

  return (
    <div className="querybuilder">
      {root.items.map((item, i) =>
        item.kind === "cond" ? (
          <ConditionRow
            key={i}
            cond={item}
            groups={groups}
            types={types}
            onChange={(cond) => updateItem([i], cond)}
            onRemove={() => updateItem([i], null)}
          />
        ) : (
          <span className="qb-subgroup" key={i}>
            <button
              className="qb-op"
              aria-label="Toggle group operator"
              title="Toggle AND/OR inside this group"
              onClick={() => updateItem([i], { ...item, op: item.op === "AND" ? "OR" : "AND" })}
            >
              {item.op}
            </button>
            {item.items.map((sub, j) =>
              sub.kind === "cond" ? (
                <ConditionRow
                  key={j}
                  cond={sub}
                  groups={groups}
                  types={types}
                  onChange={(cond) => updateItem([i, j], cond)}
                  onRemove={() => updateItem([i, j], null)}
                />
              ) : null,
            )}
            <button
              aria-label="Add condition to group"
              onClick={() => updateItem([i], { ...item, items: [...item.items, emptyCondition()] })}
            >
              +
            </button>
          </span>
        ),
      )}
      <button
        className="qb-op"
        aria-label="Toggle root operator"
        title="Combine top-level conditions with AND/OR"
        onClick={() => setRoot((r) => ({ ...r, op: r.op === "AND" ? "OR" : "AND" }))}
      >
        {root.op}
      </button>
      <button
        aria-label="Add condition"
        onClick={() => setRoot((r) => ({ ...r, items: [...r.items, emptyCondition()] }))}
      >
        + condition
      </button>
      <button
        aria-label="Add group"
        onClick={() => setRoot((r) => ({ ...r, items: [...r.items, emptyGroup()] }))}
      >
        + group
      </button>
      {dsl && (
        <code className="qb-preview" title="The query this composes — editable in the bar above">
          {dsl}
        </code>
      )}
      <button className="qb-apply" disabled={!dsl} onClick={apply}>
        Apply filters
      </button>
    </div>
  );
}
