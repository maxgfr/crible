// Universe search — the topbar box that makes all 161k listings reachable:
// type a few letters, pick a hit, the company drawer deep-links to it.

import { fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
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

  it("shows nothing for a blank or unmatched query", async () => {
    render(<SearchBox onPick={() => {}} />);
    fireEvent.change(rtl.getByLabelText("Search the universe"), { target: { value: "zz" } });
    await new Promise((r) => setTimeout(r, 250));
    expect(rtl.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
