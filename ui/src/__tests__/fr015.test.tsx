// FR-015 AC-3 — the drawer explains every rank: each pillar links back to its
// component values, the peer group is named, omissions are visible.

import { render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CompanyDrawer } from "../components/CompanyDrawer";

const DETAIL = {
  profile: { symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials" },
  periods: [
    {
      period: "2025-12-31",
      provider: "yfinance",
      computed_at: 1760000000,
      piotroski_f: 8,
      altman_z: 3.2,
      beneish_m: -2.5,
      earnings_yield: 0.06,
      price_to_book_ratio: 1.8,
      return_6m: null,
      quality_rank: 91.5,
      value_rank: 74.0,
      momentum_rank: null,
      composite_rank: 82.75,
      rank_peer_group: "europe×Industrials",
      rank_missing_pillars: "momentum",
    },
  ],
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, status: 200, json: async () => DETAIL })),
  );
});

describe("FR-015 rank breakdown in the drawer", () => {
  it("shows composite + pillar ranks, their component values and the peer group", async () => {
    render(<CompanyDrawer symbol="AIR.PA" onClose={() => {}} />);
    await waitFor(() => expect(rtl.getByText(/Rank — how it is built/)).toBeInTheDocument());

    expect(rtl.getByText("Composite")).toBeInTheDocument();
    expect(rtl.getByText("82.750")).toBeInTheDocument();
    // pillars link back to their component values (AC-3)
    expect(rtl.getByText("Quality")).toBeInTheDocument();
    expect(rtl.getByText("· earnings_yield")).toBeInTheDocument();
    expect(rtl.getByText("· price_to_book_ratio")).toBeInTheDocument();
    expect(rtl.getByText("· return_6m")).toBeInTheDocument();
    // peer group is named — no unexplained numbers
    expect(rtl.getByText(/peer group: europe×Industrials/)).toBeInTheDocument();
    // the omitted pillar is stated, never silently imputed
    expect(rtl.getByText(/momentum pillar omitted/)).toBeInTheDocument();
  });
});
