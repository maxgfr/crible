// New scores & value toolkit — grid coloring grammar, field-catalog labels /
// groups / starter chips, and the drawer breakdowns that unfold each score.

import { render, screen as rtl, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ResultsGrid } from "../components/ResultsGrid";
import { GROUP_ORDER, STARTER_FILTERS, fieldGroup, fieldLabel, isHiddenField } from "../data/field-catalog";

// the drawer pulls its data through ../data; mock it (and PriceChart, which
// otherwise reaches for the price series) with a single self-contained company
vi.mock("../data", () => ({
  company: async () => ({
    profile: { name: "Acme", country: "FR", sector: "Tech" },
    periods: [
      {
        period: "2025", revenue: 1000,
        piotroski_f: 7, altman_z: 3.0, beneish_m: -2.5, composite_rank: 75,
        zmijewski_score: -2.4, ohlson_o: -3.1, montier_c: 2,
        montier_ni_cfo_diverging: 1, montier_dso_rising: 0, montier_dsi_rising: 1,
        montier_oca_to_rev_rising: 0, montier_depr_declining: 0, montier_asset_growth_high: 0,
        graham_number: 14.2, graham_margin_of_safety: 0.42, ncav: 100,
        ncav_to_market_cap: 0.1, magic_formula_rank: 80,
        greenblatt_earnings_yield: 0.13, greenblatt_roc: 0.21,
        ebitda_margin: 0.22, fcf_margin: 0.08, fcf_conversion: 0.4, dividend_coverage: 2.5,
        income_quality_ratio: 1.3, price_to_earnings_ratio: 11.4, return_on_equity: 0.18,
        current_ratio: 1.9, asset_turnover_ratio: 0.9, days_of_sales_outstanding: 41.2,
        revenue_growth: 0.07, total_debt_growth: 0.15,
        provider: "yfinance", computed_at: 1700000000,
      },
    ],
  }),
}));
vi.mock("../components/PriceChart", () => ({ PriceChart: () => null }));

describe("new scores — grid coloring", () => {
  it("applies the shared semantic grammar: distress bipolar, manipulation warns", () => {
    const rows = [
      { symbol: "SAFE", zmijewski_score: -2.5, ohlson_o: -3.5, montier_c: 1 },
      { symbol: "RISK", zmijewski_score: 1.2, ohlson_o: 0.8, montier_c: 5 },
    ];
    render(
      <ResultsGrid rows={rows} columns={["symbol", "zmijewski_score", "ohlson_o", "montier_c"]} onSelect={() => {}} />,
    );
    const cls = (text: string) => rtl.getByText(text).className;
    // distress models read like Altman: safe (green) below 0, distress (red) above
    expect(cls("-2.500")).toBe("num-good");
    expect(cls("1.200")).toBe("num-bad");
    expect(cls("-3.500")).toBe("num-good");
    expect(cls("0.800")).toBe("num-bad");
    // Montier reads like Beneish: 0–1 clean (green), 5–6 raised flags warn
    expect(cls("1")).toBe("num-good");
    expect(cls("5")).toBe("num-warn");
  });
});

describe("new scores — field catalog", () => {
  it("labels and groups the new fields for the query builder", () => {
    expect(fieldLabel("magic_formula_rank")).toBe("Magic Formula rank");
    expect(fieldLabel("ohlson_o")).toBe("Ohlson O");
    expect(fieldGroup("zmijewski_score")).toBe("Scores");
    expect(fieldGroup("montier_c")).toBe("Scores");
    expect(fieldGroup("graham_number")).toBe("Value");
    expect(fieldGroup("ncav_to_market_cap")).toBe("Value");
    // heuristic fallback covers an un-catalogued montier flag column
    expect(fieldGroup("montier_dso_rising")).toBe("Scores");
    // magic_formula_rank belongs to Value, NOT Ranks, despite the _rank suffix
    expect(fieldGroup("magic_formula_rank")).toBe("Value");
    expect(GROUP_ORDER).toContain("Value");
  });

  it("hides the always-NaN price-ratio growths and the ncav duplicate", () => {
    // price applies to the latest period only — these growths never resolve
    expect(isHiddenField("market_cap_growth")).toBe(true);
    expect(isHiddenField("price_to_earnings_ratio_growth")).toBe(true);
    expect(isHiddenField("weighted_dividend_yield_growth")).toBe(true);
    expect(isHiddenField("net_current_asset_value")).toBe(true); // ≡ ncav
    // real growth columns and the canonical ncav stay offered
    expect(isHiddenField("revenue_growth")).toBe(false);
    expect(isHiddenField("ncav")).toBe(false);
  });

  it("ships the new starter chips", () => {
    const fields = STARTER_FILTERS.map((f) => f.field);
    expect(fields).toEqual(
      expect.arrayContaining([
        "magic_formula_rank", "ncav_to_market_cap", "zmijewski_score", "montier_c", "graham_margin_of_safety",
      ]),
    );
  });
});

describe("new scores — drawer breakdown", () => {
  it("unfolds every new score and renders the value section", async () => {
    const { CompanyDrawer } = await import("../components/CompanyDrawer");
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Zmijewski")).toBeInTheDocument());
    expect(rtl.getByText("Ohlson O")).toBeInTheDocument();
    expect(rtl.getByText("Montier C")).toBeInTheDocument();
    // Montier unfolds into its six flags (same pattern as Piotroski/Beneish)
    expect(rtl.getByText("· ni_cfo_diverging")).toBeInTheDocument();
    // the value section and its Greenblatt/Graham rows
    expect(rtl.getByText("Value — Greenblatt & Graham")).toBeInTheDocument();
    expect(rtl.getByText("Magic Formula rank")).toBeInTheDocument();
    expect(rtl.getByText("Graham number")).toBeInTheDocument();
  });

  it("colors drawer values with the shared verdict grammar (never color-only)", async () => {
    const { CompanyDrawer } = await import("../components/CompanyDrawer");
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Zmijewski")).toBeInTheDocument());
    // headline scores carry class + glyph
    expect(rtl.getByText("-2.400").className).toBe("num-good");
    expect(rtl.getByText("-2.400").querySelector(".cell-flag")?.textContent).toContain("✓");
    // value toolkit thresholds reach the drawer too
    expect(rtl.getByText("0.420").className).toBe("num-good");
  });

  it("renders the Cash quality and Key ratios sections", async () => {
    const { CompanyDrawer } = await import("../components/CompanyDrawer");
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Cash quality")).toBeInTheDocument());
    expect(rtl.getByText("Key ratios")).toBeInTheDocument();
    // cash-quality rows are labeled via the catalog and colored where thresholded
    expect(rtl.getByText("FCF conversion")).toBeInTheDocument();
    const conversion = rtl.getByText("0.400");
    expect(conversion.className).toBe("num-warn");
    expect(conversion.querySelector(".cell-flag")?.textContent).toContain("!");
    expect(rtl.getByText("Dividend cover")).toBeInTheDocument();
    // key-ratio groups and a valuation row from the catalog
    expect(rtl.getByText("Valuation")).toBeInTheDocument();
    expect(rtl.getByText("Profitability")).toBeInTheDocument();
    expect(rtl.getByText("P/E")).toBeInTheDocument();
    expect(rtl.getByText("11.400")).toBeInTheDocument();
    // un-thresholded ratios stay neutral
    expect(rtl.getByText("0.180").className).toBe("");
  });

  it("renders the Efficiency group and the Growth (YoY) section", async () => {
    const { CompanyDrawer } = await import("../components/CompanyDrawer");
    render(<CompanyDrawer symbol="ACME" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText("Efficiency")).toBeInTheDocument());
    expect(rtl.getByText("Asset turnover")).toBeInTheDocument();
    expect(rtl.getByText("DSO (days)")).toBeInTheDocument();
    expect(rtl.getByText("Income quality (OCF/NI)")).toBeInTheDocument();
    // growth trajectory: signed + colored, debt growth reads inverted
    expect(rtl.getByText("Growth (YoY)")).toBeInTheDocument();
    expect(rtl.getByText("+0.070").className).toBe("num-good"); // revenue up
    expect(rtl.getByText("+0.150").className).toBe("num-bad"); // debt up
  });
});
