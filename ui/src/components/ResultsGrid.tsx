// FR-007 — the results grid: TanStack Table, engine-sorted columns (the sort
// travels to DuckDB, never a client-side sort of one page), dense monospaced
// numerals, score coloring, symbol links + row click open the company drawer.

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo } from "react";
import { fieldLabel } from "../data/field-catalog";

type Row = Record<string, unknown>;

interface Props {
  rows: Row[];
  columns: string[];
  selected?: string | null;
  onSelect: (symbol: string) => void;
  /** engine sort: "-field" descending, "field" ascending, null unsorted */
  sort?: string | null;
  onSort?: (column: string) => void;
  /** permalink for a symbol's drawer (keeps the current screen in the URL) */
  hrefFor?: (symbol: string) => string;
}

// score coloring is never color-only (DESIGN.md): each verdict carries a
// glyph — ✓ pass, ✗ fail, ! warning — and growth carries its sign
const FLAGS = { good: " ✓", bad: " ✗", warn: " !" } as const;

function verdict(text: string, kind: keyof typeof FLAGS | ""): { text: string; className: string; flag: string } {
  return { text, className: kind ? `num-${kind}` : "", flag: kind ? FLAGS[kind] : "" };
}

function formatCell(column: string, value: unknown): { text: string; className: string; flag: string } {
  if (value === null || value === undefined) return { text: "—", className: "", flag: "" };
  if (typeof value === "number") {
    const text = Math.abs(value) >= 1e9
      ? `${(value / 1e9).toFixed(2)}B`
      : Math.abs(value) >= 1e6
        ? `${(value / 1e6).toFixed(1)}M`
        : Number.isInteger(value)
          ? String(value)
          : value.toFixed(3);
    if (column === "piotroski_f") return verdict(text, value >= 7 ? "good" : value <= 3 ? "bad" : "");
    if (column === "altman_z") return verdict(text, value > 2.99 ? "good" : value < 1.81 ? "bad" : "");
    if (column === "beneish_m") return verdict(text, value > -1.78 ? "warn" : "good");
    // distress models read like Altman: safe (green) below 0, distress (red) above
    if (column === "zmijewski_score" || column === "ohlson_o")
      return verdict(text, value < 0 ? "good" : value > 0 ? "bad" : "");
    // Montier reads like Beneish: 5–6 raised flags warns, 0–1 is clean
    if (column === "montier_c") return verdict(text, value >= 5 ? "warn" : value <= 1 ? "good" : "");
    if (column.endsWith("_growth"))
      return { text: value > 0 ? `+${text}` : text, className: value > 0 ? "num-good" : value < 0 ? "num-bad" : "", flag: "" };
    return { text, className: "", flag: "" };
  }
  return { text: String(value), className: "", flag: "" };
}

function ariaSort(sort: string | null | undefined, column: string): "ascending" | "descending" | undefined {
  if (sort === column) return "ascending";
  if (sort === `-${column}`) return "descending";
  return undefined;
}

export function ResultsGrid({ rows, columns, selected, onSelect, sort, onSort, hrefFor }: Props) {
  const helper = createColumnHelper<Row>();
  const linkFor = hrefFor ?? ((symbol: string) => `#/company/${encodeURIComponent(symbol)}`);
  const tableColumns = useMemo(
    () =>
      columns.map((name) =>
        helper.accessor((row) => row[name], {
          id: name,
          header: fieldLabel(name),
          cell: (info) => {
            const value = info.getValue();
            if (name === "symbol" && value !== null && value !== undefined) {
              const symbol = String(value);
              // a real link: keyboard-reachable, middle-clickable, honest URL
              return (
                <a className="symlink" href={linkFor(symbol)} onClick={(event) => event.stopPropagation()}>
                  {symbol}
                </a>
              );
            }
            const { text, className, flag } = formatCell(name, value);
            return (
              <span className={className}>
                {text}
                {flag && <span className="cell-flag">{flag}</span>}
              </span>
            );
          },
        }),
      ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [columns.join("|"), linkFor],
  );

  const table = useReactTable({
    data: rows,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!rows.length) {
    return (
      <div className="grid-wrap">
        <p className="meta">
          No matching rows — loosen a clause, or check coverage in the{" "}
          <a href="#/status">Status view</a>.
        </p>
      </div>
    );
  }

  return (
    <div className="grid-wrap">
      <table className="results">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const name = header.column.id;
                const direction = ariaSort(sort, name);
                return (
                  <th key={header.id} aria-sort={direction}>
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => onSort?.(name)}
                      title={`Sort by ${fieldLabel(name)} (${name})`}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {direction === "ascending" ? " ↑" : direction === "descending" ? " ↓" : ""}
                    </button>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={String(row.original.symbol) === selected ? "selected" : undefined}
              onClick={() => onSelect(String(row.original.symbol))}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
