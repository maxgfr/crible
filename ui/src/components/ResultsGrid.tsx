// FR-007 — the results grid: TanStack Table, sortable columns, dense
// monospaced numerals, score coloring, row click opens the company drawer.

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";

type Row = Record<string, unknown>;

interface Props {
  rows: Row[];
  columns: string[];
  onSelect: (symbol: string) => void;
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
    if (column.endsWith("_growth")) return { text, className: value > 0 ? "num-good" : value < 0 ? "num-bad" : "" };
    return { text, className: "" };
  }
  return { text: String(value), className: "" };
}

export function ResultsGrid({ rows, columns, onSelect }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const helper = createColumnHelper<Row>();
  const tableColumns = useMemo(
    () =>
      columns.map((name) =>
        helper.accessor((row) => row[name], {
          id: name,
          header: name,
          cell: (info) => {
            const { text, className } = formatCell(name, info.getValue());
            return <span className={className}>{text}</span>;
          },
        }),
      ),
    [columns.join("|")],
  );

  const table = useReactTable({
    data: rows,
    columns: tableColumns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (!rows.length) {
    return (
      <div className="grid-wrap">
        <p className="meta">No matching rows — loosen a clause, or check coverage in the status bar.</p>
      </div>
    );
  }

  return (
    <div className="grid-wrap">
      <table className="results">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} onClick={header.column.getToggleSortingHandler()}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {{ asc: " ↑", desc: " ↓" }[header.column.getIsSorted() as string] ?? ""}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} onClick={() => onSelect(String(row.original.symbol))}>
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
