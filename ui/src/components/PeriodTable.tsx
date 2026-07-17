// The shared multi-period table machinery for the company drawer: every
// table repeats the date-column header (sticky while its table scrolls),
// and period columns that carry no statement fundamentals render muted.

import type { ReactNode } from "react";

export type Period = Record<string, unknown>;

export const STATEMENT_FIELDS = [
  "revenue", "gross_profit", "operating_income", "net_income",
  "total_assets", "total_equity", "total_debt", "operating_cashflow", "free_cash_flow",
];

/** flags[i] is true when periods[i] has no value for ANY of `fields` —
 *  structural for the oldest columns (source depth ~4-5 fiscal years;
 *  YoY/average metrics need the prior year). Zero is a real value. */
export function sparsePeriodFlags(
  periods: Period[],
  fields: readonly string[] = STATEMENT_FIELDS,
): boolean[] {
  return periods.map((p) => fields.every((field) => p[field] == null));
}

interface HeaderProps {
  periods: Period[];
  sparse?: boolean[];
  /** overrides the period text (latest-only tables: "latest — 2025-12-31") */
  labels?: string[];
}

export function PeriodHeader({ periods, sparse, labels }: HeaderProps) {
  return (
    <thead>
      <tr>
        <th>field</th>
        {periods.map((p, i) => (
          <th key={String(p.period)} className={sparse?.[i] ? "col-muted" : undefined}>
            {labels?.[i] ?? String(p.period)}
          </th>
        ))}
      </tr>
    </thead>
  );
}

export function PeriodTable({
  periods,
  sparse,
  labels,
  children,
}: HeaderProps & { children: ReactNode }) {
  return (
    <table>
      <PeriodHeader periods={periods} sparse={sparse} labels={labels} />
      <tbody>{children}</tbody>
    </table>
  );
}

interface RowProps {
  label: ReactNode;
  labelClass?: string;
  periods: Period[];
  sparse?: boolean[];
  cell: (period: Period, index: number) => ReactNode;
}

export function PeriodRow({ label, labelClass, periods, sparse, cell }: RowProps) {
  return (
    <tr>
      <td className={labelClass}>{label}</td>
      {periods.map((p, i) => (
        <td key={String(p.period)} className={sparse?.[i] ? "col-muted" : undefined}>
          {cell(p, i)}
        </td>
      ))}
    </tr>
  );
}
