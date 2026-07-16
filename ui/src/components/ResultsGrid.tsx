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
import { formatCell } from "../format";

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
            if (name === "name") {
              // compact identity column: truncate, full name on hover —
              // the numbers are what the grid is for
              return (
                <span className="cell-name" title={text}>
                  {text}
                </span>
              );
            }
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
