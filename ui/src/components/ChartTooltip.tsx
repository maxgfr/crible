// Shared hover readout for the hand-rolled SVG charts (trend mini-charts,
// price chart). Pure presentation: callers own the hover state and pass
// pre-formatted values. aria-hidden because the same text lives on the
// charts' hit-target aria-labels. Values lead (strong ink), series labels
// follow (muted), keyed by a short stroke of the series color.

export interface TooltipRow {
  key: string;
  /** series-1 | series-2 | series-3 — maps to --series-color via CSS */
  tone?: string;
  label: string;
  value: string;
}

export function ChartTooltip({
  label,
  rows,
  leftPct,
  align,
  swatches,
}: {
  label: string;
  rows: TooltipRow[];
  /** anchor x as a percentage of the chart frame width */
  leftPct: number;
  /** edge clamp: start/end keep the box inside the chart at its borders */
  align: "start" | "center" | "end";
  /** color keys only make sense on multi-series charts (legend rule) */
  swatches: boolean;
}) {
  return (
    <div
      className={`chart-tooltip align-${align}`}
      style={{ left: `${leftPct}%` }}
      aria-hidden="true"
    >
      <strong>{label}</strong>
      {rows.map((row) => (
        <span key={row.key} className={row.tone}>
          {swatches && <i />}
          {row.label} <b>{row.value}</b>
        </span>
      ))}
    </div>
  );
}
