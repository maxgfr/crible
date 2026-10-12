// Universe search — the topbar box that makes all 161k listings reachable:
// type a few letters, pick a hit, the company drawer deep-links to it.

import { act, fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SearchBox } from "../components/SearchBox";

const HITS = [
  { symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials" },
  { symbol: "AIRBNB", name: "Airbnb", country: "US", sector: "Consumer" },
];

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () => (String(url).includes("q=air") ? HITS : []),
    })),
  );
});

describe("universe search", () => {
  it("shows hits for a query and picks a symbol", async () => {
    const onPick = vi.fn();
    render(<SearchBox onPick={onPick} />);

    fireEvent.change(rtl.getByLabelText("Search the universe"), { target: { value: "air" } });

    await waitFor(() => expect(rtl.getByRole("listbox")).toBeInTheDocument());
    expect(rtl.getByText(/Airbus/)).toBeInTheDocument();

    fireEvent.mouseDown(rtl.getByText(/AIR\.PA/));
    expect(onPick).toHaveBeenCalledWith("AIR.PA");
    // picking closes the dropdown and clears the box
    expect(rtl.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("ignores the response of an outdated query ('ap' landing after 'apple')", async () => {
    const pending = new Map<string, (hits: unknown[]) => void>();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const q = new URL(String(url), "http://x").searchParams.get("q") ?? "";
        const hits = await new Promise<unknown[]>((resolve) => pending.set(q, resolve));
        return { ok: true, status: 200, json: async () => hits };
      }),
    );
    render(<SearchBox onPick={() => {}} />);
    const input = rtl.getByLabelText("Search the universe");
    fireEvent.change(input, { target: { value: "ap" } });
    await waitFor(() => expect(pending.has("ap")).toBe(true));
    fireEvent.change(input, { target: { value: "apple" } });
    await waitFor(() => expect(pending.has("apple")).toBe(true));

    await act(async () => pending.get("apple")!([{ symbol: "AAPL", name: "Apple", country: "US", sector: "Tech" }]));
    await waitFor(() => expect(rtl.getByText(/Apple/)).toBeInTheDocument());
    await act(async () => pending.get("ap")!([{ symbol: "APD", name: "Air Products", country: "US", sector: "Materials" }]));
    expect(rtl.queryByText(/Air Products/)).not.toBeInTheDocument();
    expect(rtl.getByText(/Apple/)).toBeInTheDocument();
  });

  it("shows nothing for a blank or unmatched query", async () => {
    render(<SearchBox onPick={() => {}} />);
    fireEvent.change(rtl.getByLabelText("Search the universe"), { target: { value: "zz" } });
    await new Promise((r) => setTimeout(r, 250));
    expect(rtl.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
