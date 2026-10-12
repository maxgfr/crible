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

// signed year-over-year changes that are not *_growth columns: shown with
// their sign like growth; issuance up dilutes the holder (inverted)
const SIGNED_CHANGES: Record<string, "up-is-good" | "up-is-bad"> = {
  net_share_issuance: "up-is-bad",
};

// P&L flows, margins, returns and yields where a NEGATIVE value is a loss
// by definition — the minus sign is the non-color half of the verdict.
// Positive stays neutral (profitable is the baseline, not a win to paint);
// balance-sheet stocks, prices and ranks are never sign-colored.
const NEGATIVE_IS_BAD = new Set([
  "gross_profit", "operating_income", "ebitda", "net_income",
  "operating_cashflow", "free_cash_flow",
  "ttm_net_income", "ttm_operating_cashflow", "ttm_free_cash_flow",
  "gross_margin", "operating_margin", "ebitda_margin", "net_profit_margin",
  "fcf_margin",
  "return_on_equity", "return_on_assets", "roic", "gross_profitability",
  "earnings_yield", "free_cash_flow_yield", "ttm_fcf_yield",
  "shareholder_yield", "greenblatt_earnings_yield", "greenblatt_roc",
]);

export type VerdictKind = keyof typeof FLAGS;

/** THE threshold table — grid, drawer and synthesis all read this one
 *  function; a verdict must never exist anywhere else. null = mid-band or
 *  no published cutoff. Growth columns are sign semantics, not verdicts —
 *  they stay in formatCell. */
export function verdictKind(column: string, value: number): VerdictKind | null {
  switch (column) {
    case "piotroski_f":
      return value >= 7 ? "good" : value <= 3 ? "bad" : null;
    case "altman_z":
      return value > 2.99 ? "good" : value < 1.81 ? "bad" : null;
    // Altman (2002) Z″ zones: safe above 2.60, distress below 1.10
    case "altman_z_double_prime":
      return value > 2.6 ? "good" : value < 1.1 ? "bad" : null;
    case "beneish_m":
      return value > -1.78 ? "warn" : "good";
    // distress models read like Altman: safe (green) below 0, distress above
    case "zmijewski_score":
    case "ohlson_o":
      return value < 0 ? "good" : value > 0 ? "bad" : null;
    // Montier reads like Beneish: 5–6 raised flags warns, 0–1 is clean
    case "montier_c":
      return value >= 5 ? "warn" : value <= 1 ? "good" : null;
    // Dechow (2011): F ≥ 1 above-normal misstatement risk, ≥ 1.85 substantial
    case "dechow_f":
      return value > 1.85 ? "warn" : value < 1 ? "good" : null;
    // value toolkit — published thresholds only
    case "graham_margin_of_safety":
      return value > 0 ? "good" : value < 0 ? "bad" : null;
    case "ncav_to_market_cap":
      return value >= 1.5 ? "good" : null;
    case "fcf_conversion":
      return value < 1 ? "warn" : null;
    case "dividend_coverage":
      return value >= 2 ? "good" : value < 1 ? "bad" : null;
    case "rule_of_40":
      return value >= 0.4 ? "good" : null;
    // Lynch's GARP threshold — only a POSITIVE peg ≤ 1 passes
    case "peg_ratio":
      return value > 0 && value <= 1 ? "good" : null;
    default:
      return null;
  }
}

/** The columns verdictKind can decide — the synthesis families draw on it. */
export const VERDICT_COLUMNS = [
  "piotroski_f", "altman_z", "altman_z_double_prime", "beneish_m", "zmijewski_score", "ohlson_o",
  "montier_c", "dechow_f", "graham_margin_of_safety", "ncav_to_market_cap",
  "fcf_conversion", "dividend_coverage", "rule_of_40", "peg_ratio",
] as const;

/** ≥1e9 → "…B", ≥1e6 → "…M", integers verbatim, else 3 decimals; NaN and
 *  ±Infinity → "—". The unit is picked AFTER rounding, so 999,999,999.9
 *  reads "1.00B", never "1000.0M". */
export function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const millions = Number((value / 1e6).toFixed(1));
  if (Math.abs(value) >= 1e9 || Math.abs(millions) >= 1000) return `${(value / 1e9).toFixed(2)}B`;
  const plain = Number.isInteger(value) ? value : Number(value.toFixed(3));
  if (Math.abs(plain) >= 1e6) return `${millions.toFixed(1)}M`;
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

/** Fractions → "40.0%" — chart-readout display for the margin series. */
export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatCell(column: string, value: unknown): FormattedCell {
  // NaN/±Infinity read as missing — never a verdict on a non-number
  if (value === null || value === undefined || (typeof value === "number" && !Number.isFinite(value))) {
    return { text: "—", className: "", flag: "" };
  }
  if (typeof value === "number") {
    const text = formatNumber(value);
    const kind = verdictKind(column, value);
    if (kind) return verdict(text, kind);
    if (VERDICT_COLUMNS.includes(column as (typeof VERDICT_COLUMNS)[number])) {
      return { text, className: "", flag: "" }; // mid-band: neutral, no glyph
    }
    if (NEGATIVE_IS_BAD.has(column)) {
      return { text, className: value < 0 ? "num-bad" : "", flag: "" };
    }
    if (column.endsWith("_growth") || column.endsWith("_cagr_3y") || column in SIGNED_CHANGES) {
      const goodWhenUp = !INVERTED_GROWTH.has(column) && SIGNED_CHANGES[column] !== "up-is-bad";
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
