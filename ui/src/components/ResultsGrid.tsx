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

function formatCell(column: string, value: unknown): { text: string; className: string } {
  if (value === null || value === undefined) return { text: "—", className: "" };
  if (typeof value === "number") {
    const text = Math.abs(value) >= 1e9
      ? `${(value / 1e9).toFixed(2)}B`
      : Math.abs(value) >= 1e6
        ? `${(value / 1e6).toFixed(1)}M`
        : Number.isInteger(value)
          ? String(value)
          : value.toFixed(3);
    if (column === "piotroski_f") return { text, className: value >= 7 ? "num-good" : value <= 3 ? "num-bad" : "" };
    if (column === "altman_z") return { text, className: value > 2.99 ? "num-good" : value < 1.81 ? "num-bad" : "" };
    if (column === "beneish_m") return { text, className: value > -1.78 ? "num-warn" : "num-good" };
    // distress models read like Altman: safe (green) below 0, distress (red) above
    if (column === "zmijewski_score" || column === "ohlson_o")
      return { text, className: value < 0 ? "num-good" : value > 0 ? "num-bad" : "" };
    // Montier reads like Beneish: 5–6 raised flags warns, 0–1 is clean
    if (column === "montier_c") return { text, className: value >= 5 ? "num-warn" : value <= 1 ? "num-good" : "" };
    if (column.endsWith("_growth")) return { text, className: value > 0 ? "num-good" : value < 0 ? "num-bad" : "" };
    return { text, className: "" };
  }
  return { text: String(value), className: "" };
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
            const { text, className } = formatCell(name, value);
            return <span className={className}>{text}</span>;
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
