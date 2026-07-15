// T-016/T-018 — the one-window shell: wordmark, view-switcher pills,
// persisted theme toggle, `/` focuses the DSL bar, teaching first-run
// empty state (never a blank grid).

import { fireEvent, render, screen as rtl, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";

const ROWS = [
  { symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials", piotroski_f: 8 },
];

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

function mockApi(overrides: Record<string, unknown> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const path = String(url).split("?")[0];
      if (path in overrides) return jsonResponse(overrides[path]);
      if (path === "/api/screen") return jsonResponse({ rows: ROWS, total: 1, page: 1, tookMs: 3 });
      if (path === "/api/presets") return jsonResponse([]);
      if (path === "/api/status") return jsonResponse({ universe: 8, snapshot: true, ingest: {} });
      if (path === "/api/providers") return jsonResponse([]);
      return jsonResponse({}, 404);
    }),
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.location.hash = "";
  document.documentElement.dataset.theme = "dark";
});

describe("shell & navigation", () => {
  it("renders the wordmark and the two view pills", async () => {
    mockApi();
    render(<App />);
    expect(rtl.getByRole("heading", { name: /crible/i })).toBeInTheDocument();
    const nav = rtl.getByRole("navigation", { name: /views/i });
    expect(nav).toHaveTextContent("Screener");
    expect(nav).toHaveTextContent("Status");
    expect(nav).not.toHaveTextContent("Providers");
    await waitFor(() => expect(rtl.getByText("AIR.PA")).toBeInTheDocument());
  });

  it("switches views on hash change — #/providers lands on the merged Status page", async () => {
    mockApi({ "/api/providers": [] });
    render(<App />);
    window.location.hash = "#/providers";
    await waitFor(() => expect(rtl.getByRole("heading", { name: /status/i })).toBeInTheDocument());
    // the merged page carries the Providers section (old permalinks keep working)
    expect(rtl.getByRole("heading", { name: /providers/i })).toBeInTheDocument();
    window.location.hash = "#/status";
    await waitFor(() => expect(rtl.getByRole("heading", { name: /status/i })).toBeInTheDocument());
  });

  it("offers all three theme states and persists the choice", async () => {
    mockApi();
    render(<App />);
    const group = rtl.getByRole("group", { name: /theme/i });
    const buttons = within(group).getAllByRole("button");
    expect(buttons).toHaveLength(3);
    // auto is the default — exactly one segment is pressed
    expect(buttons.filter((b) => b.getAttribute("aria-pressed") === "true")).toHaveLength(1);
    expect(within(group).getByRole("button", { name: /auto/i })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(within(group).getByRole("button", { name: /light theme/i }));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("crible-theme")).toBe("light");

    fireEvent.click(within(group).getByRole("button", { name: /dark theme/i }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("crible-theme")).toBe("dark");

    // back to auto — the OS decides (no matchMedia in jsdom → dark)
    fireEvent.click(within(group).getByRole("button", { name: /auto/i }));
    expect(window.localStorage.getItem("crible-theme")).toBe("auto");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("focuses the DSL bar on `/`", async () => {
    mockApi();
    render(<App />);
    fireEvent.keyDown(window, { key: "/" });
    expect(rtl.getByLabelText("DSL query")).toHaveFocus();
  });

  it("opens the drawer from #/company/:symbol and closes it on Escape", async () => {
    mockApi({ "/api/company/AIR.PA": { profile: { name: "Airbus" }, periods: [] } });
    render(<App />);
    window.location.hash = "#/company/AIR.PA";
    await waitFor(() => expect(rtl.getByLabelText(/AIR\.PA details/)).toBeInTheDocument());
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(rtl.queryByLabelText(/AIR\.PA details/)).not.toBeInTheDocument());
  });
});

describe("teaching first-run empty state (T-018)", () => {
  it("shows crawl progress instead of a blank grid when there is no snapshot", async () => {
    mockApi({
      "/api/screen": { rows: [], total: 0, page: 1, tookMs: 1 },
      "/api/status": {
        universe: 160995,
        snapshot: false,
        ingest: { coverage_pct: 2.4, crawled: 3863, universe: 160995 },
      },
    });
    render(<App />);
    await waitFor(() => expect(rtl.getByText(/first crawl is running/i)).toBeInTheDocument());
    expect(rtl.getByText(/2\.4\s?%/)).toBeInTheDocument();
    expect(rtl.getByRole("link", { name: /status view/i })).toHaveAttribute("href", "#/status");
  });
});
