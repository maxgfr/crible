// Price block — the covered date interval (first → last session) and the
// listing currency belong next to the price numbers.

import { render, screen as rtl, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../data", () => ({
  prices: async () => [
    { symbol: "CA.PA", date: "2025-06-20", close: 12.1 },
    { symbol: "CA.PA", date: "2025-06-23", close: 12.4 },
    { symbol: "CA.PA", date: "2026-07-15", close: 16.39 },
  ],
}));

async function renderChart(currency?: string) {
  const { PriceChart } = await import("../components/PriceChart");
  render(<PriceChart symbol="CA.PA" currency={currency} />);
  await waitFor(() => expect(rtl.getByRole("heading")).toBeInTheDocument());
}

describe("PriceChart", () => {
  it("shows the currency next to the session count", async () => {
    await renderChart("EUR");
    expect(rtl.getByRole("heading").textContent).toBe("Price — 3 sessions · EUR");
  });

  it("shows the covered interval, not only the as-of date", async () => {
    await renderChart("EUR");
    expect(rtl.getByText(/2025-06-20 → 2026-07-15/)).toBeInTheDocument();
  });

  it("degrades cleanly without a currency", async () => {
    await renderChart();
    expect(rtl.getByRole("heading").textContent).toBe("Price — 3 sessions");
  });
});
