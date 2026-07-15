// Trend mini-charts over the fiscal periods. Receives detail.periods AS
// STORED (newest-first) and reverses ONCE here — the single flip point, so
// oldest always reads left. Hand-rolled SVG on tokens; ONE scale per chart,
// never dual-axis; series colors are the validated --color-series-* tokens
// (gain/loss/warn are status colors, reserved for verdicts). Hover is a
// full-height hit rect per period carrying a native <title> — deliberate
// v1: every value also lives in the tables around the charts.

import { formatNumber } from "../format";
import { barRects, baselineY, chartDomain, linePath } from "./charts";

interface Series {
  label: string;
  column: string;
  /** series-1 | series-2 | series-3 — maps to --color-series-* via CSS */
  tone: string;
}

function num(row: Record<string, unknown>, column: string): number | null {
  const v = row[column];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function TrendChart({
  title,
  periods,
  series,
  kind,
}: {
  title: string;
  /** oldest → newest (already reversed by TrendCharts) */
  periods: Record<string, unknown>[];
  series: Series[];
  kind: "bars" | "lines";
}) {
  const table = series.map((s) => periods.map((p) => num(p, s.column)));
  const domain = chartDomain(table);
  const plottable = table.some((vals) => vals.filter((v) => v !== null).length >= 2);
  if (!domain || !plottable) return null;

  const labels = periods.map((p) => String(p.period ?? ""));
  const slot = 100 / periods.length;
  const zero = baselineY(domain);
  return (
    <figure className="trend-chart">
      <figcaption>
        <span>{title}</span>
        {series.length > 1 && (
          <span className="chart-legend">
            {series.map((s) => (
              <span key={s.column} className={s.tone}>
                <i /> {s.label}
              </span>
            ))}
          </span>
        )}
      </figcaption>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        <line className="chart-baseline" x1="0" x2="100" y1={zero} y2={zero} />
        {kind === "bars"
          ? barRects(table[0], domain).map(
              (bar, i) =>
                bar && (
                  <rect
                    key={i}
                    className="trend-bar"
                    x={bar.x}
                    y={bar.y}
                    width={bar.width}
                    height={bar.height}
                  />
                ),
            )
          : series.map((s, index) => {
              const d = linePath(table[index], domain);
              return d ? <path key={s.column} className={`trend-line ${s.tone}`} d={d} /> : null;
            })}
        {periods.map((_, i) => (
          <rect
            key={`hit-${i}`}
            className="chart-hit"
            x={i * slot}
            y="0"
            width={slot}
            height="100"
            fill="transparent"
          >
            <title>
              {`${labels[i]} · ${series
                .map((s, index) => {
                  const value = table[index][i];
                  return `${s.label} ${value === null ? "—" : formatNumber(value)}`;
                })
                .join(" · ")}`}
            </title>
          </rect>
        ))}
      </svg>
      <div className="trend-meta">
        <span>{labels[0]}</span>
        <span>{labels[labels.length - 1]}</span>
      </div>
    </figure>
  );
}

export function TrendCharts({ periods }: { periods: Record<string, unknown>[] }) {
  const ordered = [...periods].reverse(); // stored newest-first → oldest left
  return (
    <div className="trend-charts">
      <TrendChart
        title="Revenue"
        periods={ordered}
        kind="bars"
        series={[{ label: "Revenue", column: "revenue", tone: "series-1" }]}
      />
      <TrendChart
        title="Net income & FCF"
        periods={ordered}
        kind="lines"
        series={[
          { label: "Net income", column: "net_income", tone: "series-1" },
          { label: "FCF", column: "free_cash_flow", tone: "series-2" },
        ]}
      />
      <TrendChart
        title="Margins"
        periods={ordered}
        kind="lines"
        series={[
          { label: "Gross", column: "gross_margin", tone: "series-1" },
          { label: "Operating", column: "operating_margin", tone: "series-2" },
          { label: "Net", column: "net_profit_margin", tone: "series-3" },
        ]}
      />
    </div>
  );
}

/** Piotroski F on its FIXED 0–9 domain — the quality trajectory at a glance. */
export function PiotroskiSparkline({ periods }: { periods: Record<string, unknown>[] }) {
  const ordered = [...periods].reverse();
  const values = ordered.map((p) => num(p, "piotroski_f"));
  const d = linePath(values, { min: 0, max: 9 });
  if (!d) return null;
  return (
    <span className="spark" title="Piotroski F across the reported periods (0–9)">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <path className="spark-line" d={d} />
      </svg>
    </span>
  );
}
