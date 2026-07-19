// Drawer tables — every multi-period table repeats the date-column header,
// latest-only tables name their period explicitly, structurally-empty period
// columns render muted with one explanatory footnote, and money rows carry
// the listing currency.

import { render, screen as rtl, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const FULL_2025 = {
  period: "2025-12-31", revenue: 84e9, gross_profit: 16e9, operating_income: 2.1e9,
  net_income: 385e6, total_assets: 55e9, total_equity: 11.6e9, total_debt: 5.2e9,
  operating_cashflow: 3.9e9, free_cash_flow: 2.4e9,
  market_cap: 11.2e9, piotroski_f: 5, composite_rank: 81.4, quality_rank: null,
  value_rank: 73.1, momentum_rank: 89.6, return_6m: 0.184,
  graham_number: 14.7, magic_formula_rank: 62.4, ncav: -20.7e9,
  ttm_revenue: 85e9, provider: "esef", computed_at: 1700000000,
};

vi.mock("../data", () => ({
  company: async () => ({
    profile: { name: "Carrefour SA", country: "FR", sector: "Consumer Staples", currency: "EUR" },
    periods: [
      FULL_2025,
      { ...FULL_2025, period: "2024-12-31", ttm_revenue: null },
      // the oldest period carries NO statement fundamentals — structural
      { period: "2023-12-31", piotroski_f: 1 },
    ],
  }),
}));
vi.mock("../components/PriceChart", () => ({
  PriceChart: () => <div data-testid="price-chart" />,
}));
vi.mock("../components/LiveQuote", () => ({ LiveQuote: () => null }));

async function renderDrawer() {
  const { CompanyDrawer } = await import("../components/CompanyDrawer");
  const view = render(<CompanyDrawer symbol="CA.PA" onClose={() => {}} />);
  await waitFor(() => expect(rtl.getByText("Statements")).toBeInTheDocument());
  return view;
}

describe("drawer tables — repeated date headers", () => {
  it("repeats the period header on every multi-period table", async () => {
    await renderDrawer();
    // Statements, Cash quality, Key ratios, Growth (YoY), Scores
    expect(rtl.getAllByRole("columnheader", { name: "2024-12-31" })).toHaveLength(5);
    expect(rtl.getAllByRole("columnheader", { name: "2025-12-31" })).toHaveLength(5);
  });

  it("names the period on latest-only tables", async () => {
    await renderDrawer();
    // Momentum, TTM, Rank, Value — single-column tables anchored to the latest period
    expect(rtl.getAllByRole("columnheader", { name: "latest — 2025-12-31" })).toHaveLength(4);
  });
});

describe("drawer tables — structurally empty columns", () => {
  it("mutes the sparse column across every multi-period table", async () => {
    const { container } = await renderDrawer();
    expect(container.querySelectorAll("th.col-muted")).toHaveLength(5);
    // header muting never touches the populated columns
    for (const th of rtl.getAllByRole("columnheader", { name: "2024-12-31" })) {
      expect(th.className).not.toContain("col-muted");
    }
    // every multi-period table's body mutes the same column, not just Statements
    for (const anchor of ["drawer-statements", "drawer-cash", "drawer-growth", "drawer-scores"]) {
      const table = container.querySelector(`#${anchor} + table`);
      const firstRow = table?.querySelector("tbody tr");
      const cells = firstRow ? Array.from(firstRow.querySelectorAll("td")) : [];
      expect(cells.length).toBeGreaterThan(0);
      expect(cells.at(-1)?.className).toContain("col-muted");
      expect(cells.at(-2)?.className).not.toContain("col-muted");
    }
  });

  it("explains the muted columns once, under Statements", async () => {
    await renderDrawer();
    expect(rtl.getByText(/oldest \(rightmost\)/)).toBeInTheDocument();
  });
});

describe("drawer layout — charts after the numbers", () => {
  it("keeps the price chart and Trends below the last number table", async () => {
    await renderDrawer();
    const follows = (a: Element, b: Element) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    const scores = rtl.getByText("Scores — full breakdown");
    const chart = rtl.getByTestId("price-chart");
    const trends = rtl.getByText("Trends");
    const provenance = rtl.getByText("Provenance");
    // document order: …scores < price chart < Trends < Provenance
    expect(follows(scores, chart)).toBe(true);
    expect(follows(chart, trends)).toBe(true);
    expect(follows(trends, provenance)).toBe(true);
  });
});

describe("drawer tables — currency on money rows", () => {
  it("suffixes the price-denominated row labels with the listing currency", async () => {
    await renderDrawer();
    expect(rtl.getByText("Market cap (EUR)")).toBeInTheDocument();
    expect(rtl.getByText("Graham number (EUR)")).toBeInTheDocument();
    expect(rtl.getByText("NCAV (net-net) (EUR)")).toBeInTheDocument();
  });
});
