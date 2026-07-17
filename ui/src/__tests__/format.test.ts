// The shared formatting/verdict module (grid + drawer): number scaling,
// the score grammar, the value-toolkit thresholds, and the rule that
// un-thresholded ratios stay neutral — no coloring by taste.

import { describe, expect, it } from "vitest";
import { VERDICT_COLUMNS, formatCell, formatNumber, verdictKind } from "../format";

describe("formatNumber", () => {
  it("scales billions/millions and keeps small numbers precise", () => {
    expect(formatNumber(2_500_000_000)).toBe("2.50B");
    expect(formatNumber(1_500_000)).toBe("1.5M");
    expect(formatNumber(-3_000_000_000)).toBe("-3.00B");
    expect(formatNumber(7)).toBe("7");
    expect(formatNumber(0.1234)).toBe("0.123");
  });
});

describe("formatCell — the verdict table", () => {
  const cls = (column: string, value: unknown) => formatCell(column, value).className;
  const flag = (column: string, value: unknown) => formatCell(column, value).flag;

  it("renders null as an em dash, neutral", () => {
    expect(formatCell("piotroski_f", null)).toEqual({ text: "—", className: "", flag: "" });
  });

  it("keeps the historic score grammar, glyphs included", () => {
    expect(cls("piotroski_f", 8)).toBe("num-good");
    expect(cls("piotroski_f", 2)).toBe("num-bad");
    expect(cls("altman_z", 3.2)).toBe("num-good");
    expect(cls("altman_z", 1.2)).toBe("num-bad");
    expect(cls("beneish_m", -1.5)).toBe("num-warn");
    expect(cls("beneish_m", -2.5)).toBe("num-good");
    expect(flag("piotroski_f", 8)).toContain("✓");
    expect(flag("piotroski_f", 2)).toContain("✗");
    expect(flag("beneish_m", -1.5)).toContain("!");
  });

  it("colors the value toolkit at its published thresholds only", () => {
    expect(cls("graham_margin_of_safety", 0.42)).toBe("num-good");
    expect(cls("graham_margin_of_safety", -0.2)).toBe("num-bad");
    expect(cls("ncav_to_market_cap", 1.6)).toBe("num-good");
    expect(cls("ncav_to_market_cap", 0.4)).toBe("");
    expect(cls("fcf_conversion", 0.8)).toBe("num-warn");
    expect(cls("fcf_conversion", 1.2)).toBe("");
    expect(cls("dividend_coverage", 2.5)).toBe("num-good");
    expect(cls("dividend_coverage", 0.5)).toBe("num-bad");
    expect(cls("dividend_coverage", 1.5)).toBe("");
  });

  it("leaves un-thresholded ratios neutral", () => {
    expect(cls("return_on_equity", 0.32)).toBe("");
    expect(cls("net_profit_margin", 0.01)).toBe("");
    expect(cls("debt_to_equity_ratio", 4)).toBe("");
  });

  it("verdictKind and formatCell always agree — one threshold table", () => {
    const samples = [-5, -1.78, -1, 0, 0.4, 0.5, 1, 1.5, 1.81, 1.85, 2, 2.99, 3, 5, 7, 8];
    for (const column of VERDICT_COLUMNS) {
      for (const value of samples) {
        const kind = verdictKind(column, value);
        const cell = formatCell(column, value);
        expect(cell.className).toBe(kind ? `num-${kind}` : "");
        expect(cell.flag !== "").toBe(kind !== null);
      }
    }
  });

  it("verdictKind boundaries match the published cutoffs", () => {
    expect(verdictKind("piotroski_f", 7)).toBe("good");
    expect(verdictKind("piotroski_f", 3)).toBe("bad");
    expect(verdictKind("piotroski_f", 5)).toBeNull();
    expect(verdictKind("altman_z", 2.99)).toBeNull(); // strictly above
    expect(verdictKind("altman_z", 1.81)).toBeNull(); // strictly below
    expect(verdictKind("dechow_f", 1.85)).toBeNull();
    expect(verdictKind("dechow_f", 1.86)).toBe("warn");
    expect(verdictKind("peg_ratio", 1)).toBe("good");
    expect(verdictKind("peg_ratio", -0.5)).toBeNull(); // negative PEG never passes
    expect(verdictKind("revenue_growth", 0.5)).toBeNull(); // growth ≠ verdict
    expect(verdictKind("unknown_column", 1)).toBeNull();
  });

  it("signs and colors growth without a glyph", () => {
    expect(formatCell("revenue_growth", 0.12)).toEqual({
      text: "+0.120",
      className: "num-good",
      flag: "",
    });
    expect(formatCell("revenue_growth", -0.05).className).toBe("num-bad");
  });

  it("signs and colors the 3y CAGR columns like growth", () => {
    expect(formatCell("revenue_cagr_3y", 0.12)).toEqual({
      text: "+0.120",
      className: "num-good",
      flag: "",
    });
    expect(formatCell("net_income_cagr_3y", -0.05).className).toBe("num-bad");
  });

  it("reads debt growth inverted: piling on debt is never green", () => {
    expect(formatCell("total_debt_growth", 0.15).className).toBe("num-bad");
    expect(formatCell("total_debt_growth", 0.15).text).toBe("+0.150");
    expect(formatCell("total_debt_growth", -0.1).className).toBe("num-good");
    expect(formatCell("debt_to_equity_ratio_growth", 0.2).className).toBe("num-bad");
    expect(formatCell("net_debt_to_ebitda_ratio_growth", -0.3).className).toBe("num-good");
  });
});

test("negative P&L, margin, return and yield figures read as losses", () => {
  expect(formatCell("net_income", -5e8).className).toBe("num-bad");
  expect(formatCell("net_income", 5e8).className).toBe("");
  expect(formatCell("fcf_margin", -0.12).className).toBe("num-bad");
  expect(formatCell("free_cash_flow", -1e6).className).toBe("num-bad");
  expect(formatCell("return_on_equity", -0.05).className).toBe("num-bad");
  expect(formatCell("earnings_yield", -0.02).className).toBe("num-bad");
  // ranks, prices and balance-sheet stocks are never sign-colored
  expect(formatCell("composite_rank", 65).className).toBe("");
  expect(formatCell("total_debt", 2e9).className).toBe("");
});
