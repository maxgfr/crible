// UX critique fixes — every screen is a permalink (#/?q=…&sort=…), sorting
// and paging run in the engine (never a client-side sort of one page), the
// grid and search are keyboard-first, presets group in a popover, the query
// bar autocompletes fields and recalls history, scores are never color-only,
// and the status observatory stays live.

import { act, fireEvent, render, screen as rtl, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { PAGE_SIZE } from "../App";
import { SearchBox } from "../components/SearchBox";
import { PresetsMenu } from "../components/PresetsMenu";
import { StatusView } from "../components/StatusView";

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
      if (String(url) === "/api/fields") {
        return {
          ok: true, status: 200,
          json: async () => [
            { name: "piotroski_f", type: "number" },
            { name: "altman_z", type: "number" },
            { name: "return_on_equity", type: "number" },
          ],
        };
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

describe("query bar accelerators", () => {
  it("autocompletes field names — Tab inserts the suggestion", async () => {
    mockApi();
    render(<App />);
    await waitFor(() => expect(screenCalls.length).toBe(1));
    const input = rtl.getByLabelText("DSL query") as HTMLInputElement;

    fireEvent.change(input, { target: { value: "altm" } });
    await waitFor(() => expect(rtl.getByText("altman_z")).toBeInTheDocument());
    fireEvent.keyDown(input, { key: "Tab" });
    expect(input.value).toBe("altman_z ");
    expect(rtl.queryByText(/Altman Z ·/)).not.toBeInTheDocument(); // dropdown closed
  });

  it("ArrowUp recalls the last ran query when no suggestions are open", async () => {
    mockApi();
    render(<App />);
    await waitFor(() => expect(screenCalls.length).toBe(1)); // ran DEFAULT_QUERY
    const input = rtl.getByLabelText("DSL query") as HTMLInputElement;

    fireEvent.change(input, { target: { value: "" } });
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input.value).toBe("piotroski_f >= 7");
  });

  it("scores carry a non-color verdict glyph", async () => {
    mockApi();
    render(<App />);
    await waitFor(() => expect(rtl.getAllByText(/✓/).length).toBeGreaterThan(0)); // piotroski 8 ≥ 7
  });
});

describe("status observatory", () => {
  it("auto-refreshes every 30 s and shows when the view was refreshed", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        // the merged page also fetches /api/providers — only count status polls
        if (String(url) === "/api/providers") {
          return { ok: true, status: 200, json: async () => [] };
        }
        calls += 1;
        return {
          ok: true, status: 200,
          json: async () => ({
            universe: 8, snapshot: true,
            ingest: { coverage_pct: 1.2, crawled: 100, universe: 8, ts: 1_784_000_000 },
          }),
        };
      }),
    );
    vi.useFakeTimers();
    try {
      render(<StatusView pref="dark" onPref={() => {}} />);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0); // flush the initial load
      });
      expect(calls).toBe(1);
      expect(rtl.getByText(/auto-refreshes every 30 s/)).toBeInTheDocument();
      expect(rtl.getByText(/crawl heartbeat/)).toBeInTheDocument();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(30_000);
      });
      expect(calls).toBe(2);
    } finally {
      vi.useRealTimers();
    }
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
