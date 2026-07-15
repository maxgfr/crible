// Shared number formatting + indicator verdicts for the results grid and
// the company drawer. Coloring is never color-only (DESIGN.md): every
// verdict carries a glyph — ✓ pass, ✗ fail, ! warning — and growth carries
// its sign. Only indicators with a published threshold (docs/INDICATORS.md)
// get a verdict; everything else stays neutral.

export const FLAGS = { good: " ✓", bad: " ✗", warn: " !" } as const;

export interface FormattedCell {
  text: string;
  className: string;
  flag: string;
}

function verdict(text: string, kind: keyof typeof FLAGS | ""): FormattedCell {
  return { text, className: kind ? `num-${kind}` : "", flag: kind ? FLAGS[kind] : "" };
}

// growth columns where UP is the bad direction (debt piling on)
const INVERTED_GROWTH = new Set([
  "total_debt_growth",
  "debt_to_equity_ratio_growth",
  "net_debt_to_ebitda_ratio_growth",
]);

/** ≥1e9 → "…B", ≥1e6 → "…M", integers verbatim, else 3 decimals. */
export function formatNumber(value: number): string {
  if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

export function formatCell(column: string, value: unknown): FormattedCell {
  if (value === null || value === undefined) return { text: "—", className: "", flag: "" };
  if (typeof value === "number") {
    const text = formatNumber(value);
    if (column === "piotroski_f") return verdict(text, value >= 7 ? "good" : value <= 3 ? "bad" : "");
    if (column === "altman_z") return verdict(text, value > 2.99 ? "good" : value < 1.81 ? "bad" : "");
    if (column === "beneish_m") return verdict(text, value > -1.78 ? "warn" : "good");
    // distress models read like Altman: safe (green) below 0, distress (red) above
    if (column === "zmijewski_score" || column === "ohlson_o")
      return verdict(text, value < 0 ? "good" : value > 0 ? "bad" : "");
    // Montier reads like Beneish: 5–6 raised flags warns, 0–1 is clean
    if (column === "montier_c") return verdict(text, value >= 5 ? "warn" : value <= 1 ? "good" : "");
    // value toolkit — published thresholds only
    if (column === "graham_margin_of_safety")
      return verdict(text, value > 0 ? "good" : value < 0 ? "bad" : "");
    if (column === "ncav_to_market_cap") return verdict(text, value >= 1.5 ? "good" : "");
    if (column === "fcf_conversion") return verdict(text, value < 1 ? "warn" : "");
    if (column === "dividend_coverage")
      return verdict(text, value >= 2 ? "good" : value < 1 ? "bad" : "");
    if (column.endsWith("_growth")) {
      const goodWhenUp = !INVERTED_GROWTH.has(column);
      return {
        text: value > 0 ? `+${text}` : text,
        className:
          value === 0 ? "" : (value > 0) === goodWhenUp ? "num-good" : "num-bad",
        flag: "",
      };
    }
    return { text, className: "", flag: "" };
  }
  return { text: String(value), className: "", flag: "" };
}
