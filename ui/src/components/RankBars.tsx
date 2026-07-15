// Percentile ranks as horizontal bars on a FIXED 0–100 domain — magnitudes
// per named category read as bars, never a radar. Reuses StatusView's Bars
// table idiom; the fill is the accent (a lone-series color), value labels
// live in text tokens. NULL ranks show "—" and an empty track — an absent
// rank is information, not zero.

import { formatNumber } from "../format";

const RANKS: [string, string][] = [
  ["Composite", "composite_rank"],
  ["Quality", "quality_rank"],
  ["Value", "value_rank"],
  ["Momentum", "momentum_rank"],
  ["Magic formula", "magic_formula_rank"],
];

export function RankBars({ row }: { row: Record<string, unknown> }) {
  return (
    <table className="bars rank-bars">
      <tbody>
        {RANKS.map(([label, column]) => {
          const raw = row[column];
          const value = typeof raw === "number" && Number.isFinite(raw) ? raw : null;
          return (
            <tr key={column}>
              <th scope="row">{label}</th>
              <td className="bars-track">
                <svg width="100%" height="10" preserveAspectRatio="none">
                  {value !== null && (
                    <rect className="rank-bar" x="0" y="1" height="8" width={`${Math.max(0.5, value)}%`}>
                      <title>{`${label} rank — ${Math.round(value)}th percentile`}</title>
                    </rect>
                  )}
                </svg>
              </td>
              <td className="bars-count">{value !== null ? formatNumber(value) : "—"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
