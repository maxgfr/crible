// The shared formatting/verdict module (grid + drawer): number scaling,
// the score grammar, the value-toolkit thresholds, and the rule that
// un-thresholded ratios stay neutral — no coloring by taste.

import { describe, expect, it } from "vitest";
import { formatCell, formatNumber } from "../format";

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

  it("signs and colors growth without a glyph", () => {
    expect(formatCell("revenue_growth", 0.12)).toEqual({
      text: "+0.120",
      className: "num-good",
      flag: "",
    });
    expect(formatCell("revenue_growth", -0.05).className).toBe("num-bad");
  });
});
