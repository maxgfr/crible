// T-019/T-020 — the merged Status page: crawl observatory (coverage,
// freshness histogram, budget gauge, provider health) plus the Providers
// section (keyless inventory, plugin seam, theme preference).

import { fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppearanceSection } from "../components/AppearanceSection";
import { StatusView } from "../components/StatusView";

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

const STATUS_PAYLOAD = {
  universe: 160995,
  by_region: { europe: 21000, north_america: 32000 },
  snapshot: true,
  ingest: {
    universe: 160995,
    crawled: 3863,
    coverage_pct: 2.4,
    freshness: { "<7d": 3000, "<30d": 800, stale: 63, never: 157132 },
    requests_last_hour: 120,
    budget_per_hour: 360,
    last_cycle: { fetched: 48, failed: 2 },
    providers: { yfinance: "healthy" },
    esef_resolved: 410,
    esef_unmatched: 12,
  },
};

// StatusView hosts the Providers section, so its fetch mock must dispatch
// by URL: /api/status and /api/providers answer different shapes
function mockApi(overrides: Record<string, unknown> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const path = String(url).split("?")[0];
      if (path in overrides) return jsonResponse(overrides[path]);
      if (path === "/api/status") return jsonResponse(STATUS_PAYLOAD);
      if (path === "/api/providers") return jsonResponse([]);
      return jsonResponse({}, 404);
    }),
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("StatusView (T-019)", () => {
  it("renders coverage, freshness histogram, budget gauge and provider health", async () => {
    mockApi();
    render(<StatusView pref="dark" onPref={() => {}} />);
    await waitFor(() => expect(rtl.getByText(/2\.4\s?%/)).toBeInTheDocument());
    expect(rtl.getByText(/<7d/)).toBeInTheDocument();
    expect(rtl.getByText(/120/)).toBeInTheDocument();
    expect(rtl.getByText(/360/)).toBeInTheDocument();
    expect(rtl.getAllByText("yfinance").length).toBeGreaterThan(0);
    expect(rtl.getByText(/healthy/)).toBeInTheDocument();
  });

  it("teaches when there is no heartbeat yet", async () => {
    mockApi({ "/api/status": { universe: 0, snapshot: false } });
    render(<StatusView pref="dark" onPref={() => {}} />);
    await waitFor(() => expect(rtl.getByText(/no crawl heartbeat/i)).toBeInTheDocument());
    expect(rtl.getByText(/docker compose up/)).toBeInTheDocument();
  });

  it("is one merged page: observatory and theme prefs coexist — NO provider table", async () => {
    mockApi();
    render(<StatusView pref="dark" onPref={() => {}} />);
    await waitFor(() => expect(rtl.getByText(/2\.4\s?%/)).toBeInTheDocument());
    expect(rtl.getByRole("heading", { name: /appearance/i })).toBeInTheDocument();
    // users never see the provider inventory (operator concern, DATA-SOURCES.md)
    expect(rtl.queryByRole("heading", { name: /providers/i })).not.toBeInTheDocument();
    expect(rtl.queryByText(/\.env/)).not.toBeInTheDocument();
    expect(rtl.getByRole("radio", { name: /auto/i })).toBeInTheDocument();
  });

  it("keeps the Appearance section even when the crawl has no heartbeat", async () => {
    mockApi({ "/api/status": { universe: 0, snapshot: false } });
    render(<StatusView pref="dark" onPref={() => {}} />);
    await waitFor(() => expect(rtl.getByText(/no crawl heartbeat/i)).toBeInTheDocument());
    expect(rtl.getByRole("heading", { name: /appearance/i })).toBeInTheDocument();
    expect(rtl.getByRole("radio", { name: /auto/i })).toBeInTheDocument();
  });
});

describe("AppearanceSection (T-020)", () => {
  it("exposes the theme preference, auto included", async () => {
    const onPref = vi.fn();
    render(<AppearanceSection pref="dark" onPref={onPref} />);
    fireEvent.click(rtl.getByRole("radio", { name: /paper terminal/i }));
    expect(onPref).toHaveBeenCalledWith("light");
    fireEvent.click(rtl.getByRole("radio", { name: /auto/i }));
    expect(onPref).toHaveBeenCalledWith("auto");
  });
});
