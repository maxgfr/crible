// UX critique fixes — every screen is a permalink (#/?q=…&sort=…), sorting
// and paging run in the engine (never a client-side sort of one page), the
// grid and search are keyboard-first, presets group in a popover.

import { fireEvent, render, screen as rtl, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { PAGE_SIZE } from "../App";
import { SearchBox } from "../components/SearchBox";
import { PresetsMenu } from "../components/PresetsMenu";

const ROWS = [
  { symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials", piotroski_f: 8 },
  { symbol: "SAP.DE", name: "SAP", country: "DE", sector: "Tech", piotroski_f: 7 },
];

const screenCalls: { query: string; sort: string | null; page: number }[] = [];

function mockApi(total = 2) {
  screenCalls.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url) === "/api/screen") {
        const body = JSON.parse(String(init?.body ?? "{}"));
        screenCalls.push({ query: body.query, sort: body.sort ?? null, page: body.page });
        return { ok: true, status: 200, json: async () => ({ rows: ROWS, total, page: body.page, tookMs: 1 }) };
      }
      if (String(url) === "/api/presets") {
        return {
          ok: true, status: 200,
          json: async () => [
            { id: "piotroski-strong", name: "Piotroski strong", description: "d", dsl: "piotroski_f >= 7" },
            { id: "top-ranked", name: "Top ranked", description: "d", dsl: "composite_rank >= 80" },
          ],
        };
      }
      if (String(url) === "/api/status") {
        return { ok: true, status: 200, json: async () => ({ universe: 8, snapshot: true }) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }),
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  window.location.hash = "#/";
  localStorage.clear();
});

afterEach(() => {
  window.location.hash = "#/";
});

describe("screen permalinks", () => {
  it("restores query and sort from the URL on load", async () => {
    window.location.hash = "#/?q=altman_z%20%3E%202.99&sort=-altman_z";
    mockApi();
    render(<App />);
    await waitFor(() => expect(screenCalls.length).toBe(1));
    expect(screenCalls[0]).toEqual({ query: "altman_z > 2.99", sort: "-altman_z", page: 1 });
    expect((rtl.getByLabelText("DSL query") as HTMLInputElement).value).toBe("altman_z > 2.99");
  });

  it("writes the ran query into the hash so the screen is shareable", async () => {
    mockApi();
    render(<App />);
    await waitFor(() => expect(rtl.getAllByText("AIR.PA").length).toBeGreaterThan(0));
    await waitFor(() => expect(window.location.hash).toContain("q=piotroski_f"));
  });
});

describe("engine sort + pagination", () => {
  it("clicking a header re-screens with an engine sort, descending first", async () => {
    mockApi();
    render(<App />);
    await waitFor(() => expect(screenCalls.length).toBe(1));

    fireEvent.click(rtl.getByRole("button", { name: /^Piotroski F/ }));
    await waitFor(() => expect(screenCalls.length).toBe(2));
    expect(screenCalls[1]).toEqual({ query: "piotroski_f >= 7", sort: "-piotroski_f", page: 1 });
    await waitFor(() =>
      expect(document.querySelector('th[aria-sort="descending"]')).not.toBeNull());

    fireEvent.click(rtl.getByRole("button", { name: /^Piotroski F/ }));
    await waitFor(() => expect(screenCalls.length).toBe(3));
    expect(screenCalls[2].sort).toBe("piotroski_f"); // second click = ascending
  });

  it("pages through large result sets in the engine", async () => {
    mockApi(PAGE_SIZE * 2 + 1); // 3 pages
    render(<App />);
    await waitFor(() => expect(screenCalls.length).toBe(1));
    expect(rtl.getByText(/page 1 \/ 3/)).toBeInTheDocument();

    fireEvent.click(rtl.getByRole("button", { name: "Next page" }));
    await waitFor(() => expect(screenCalls.length).toBe(2));
    expect(screenCalls[1].page).toBe(2);
    expect(rtl.getByText(/page 2 \/ 3/)).toBeInTheDocument();
  });

  it("renders symbols as real links carrying the current screen", async () => {
    mockApi();
    render(<App />);
    await waitFor(() => expect(rtl.getAllByText("AIR.PA").length).toBeGreaterThan(0));
    const link = rtl.getByRole("link", { name: "AIR.PA" }) as HTMLAnchorElement;
    expect(link.getAttribute("href")).toContain("#/company/AIR.PA");
    expect(link.getAttribute("href")).toContain("q=piotroski_f");
  });
});

describe("search keyboard support", () => {
  it("ArrowDown + Enter picks the active option", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true, status: 200,
        json: async () => [
          { symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials" },
          { symbol: "AIRBNB", name: "Airbnb", country: "US", sector: "Consumer" },
        ],
      })),
    );
    const onPick = vi.fn();
    render(<SearchBox onPick={onPick} />);
    const input = rtl.getByLabelText("Search the universe");
    fireEvent.change(input, { target: { value: "air" } });
    await waitFor(() => expect(rtl.getByRole("listbox")).toBeInTheDocument());

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onPick).toHaveBeenCalledWith("AIRBNB");
    expect(input.getAttribute("aria-expanded")).toBe("false");
  });
});

describe("presets popover", () => {
  it("groups presets, previews their DSL, and picks one", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        String(url) === "/api/presets"
          ? {
              ok: true, status: 200,
              json: async () => [
                { id: "piotroski-strong", name: "Piotroski strong", description: "d", dsl: "piotroski_f >= 7" },
                { id: "top-ranked", name: "Top ranked", description: "d", dsl: "composite_rank >= 80" },
              ],
            }
          : { ok: false, status: 404, json: async () => ({}) },
      ),
    );
    const onPick = vi.fn();
    render(<PresetsMenu onPick={onPick} currentQuery="roe > 0.15" activeDsl="piotroski_f >= 7" />);

    const trigger = await rtl.findByRole("button", { name: /Preset: Piotroski strong/ });
    fireEvent.click(trigger);
    expect(rtl.getByRole("group", { name: "Scores" })).toBeInTheDocument();
    expect(rtl.getByRole("group", { name: "Ranks" })).toBeInTheDocument();
    expect(rtl.getByText("composite_rank >= 80")).toBeInTheDocument(); // DSL visible, never hidden

    fireEvent.click(rtl.getByText("Top ranked"));
    expect(onPick).toHaveBeenCalledWith("composite_rank >= 80");
  });

  it("saves and deletes a custom preset inline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, status: 200, json: async () => [] })),
    );
    render(<PresetsMenu onPick={() => {}} currentQuery="fcf_margin >= 0.05" activeDsl={null} />);
    fireEvent.click(await rtl.findByRole("button", { name: "Presets" }));

    fireEvent.change(rtl.getByLabelText("New preset name"), { target: { value: "Cash cows" } });
    fireEvent.submit(rtl.getByLabelText("New preset name").closest("form")!);
    const custom = rtl.getByRole("group", { name: "Custom" });
    expect(within(custom).getByText("Cash cows")).toBeInTheDocument();
    expect(within(custom).getByText("fcf_margin >= 0.05")).toBeInTheDocument();

    fireEvent.click(rtl.getByRole("button", { name: "Delete preset Cash cows" }));
    expect(rtl.queryByRole("group", { name: "Custom" })).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("crible.custom-presets") ?? "[]")).toEqual([]);
  });
});
