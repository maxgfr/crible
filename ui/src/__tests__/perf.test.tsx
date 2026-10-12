// UI performance contracts: typing in the query bar never re-renders the
// results grid (query state lives in App — the grid is memoised and every
// prop it receives is referentially stable across keystrokes).

import { fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as format from "../format";
import App from "../App";

// formatCell runs once per rendered grid cell — the grid's render counter
vi.mock("../format", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../format")>();
  return { ...actual, formatCell: vi.fn(actual.formatCell) };
});

const ROWS = [
  { symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials", piotroski_f: 8 },
  { symbol: "SAP.DE", name: "SAP", country: "DE", sector: "Tech", piotroski_f: 7 },
];

beforeEach(() => {
  vi.restoreAllMocks();
  window.location.hash = "#/";
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const path = String(url).split("?")[0];
      if (path === "/api/screen") {
        return { ok: true, status: 200, json: async () => ({ rows: ROWS, total: 2, page: 1, tookMs: 1 }) };
      }
      if (path === "/api/status") {
        return { ok: true, status: 200, json: async () => ({ universe: 8, snapshot: true }) };
      }
      return { ok: true, status: 200, json: async () => [] };
    }),
  );
});

describe("results grid rendering", () => {
  it("typing in the query bar does not re-render the grid", async () => {
    render(<App />);
    await waitFor(() => expect(rtl.getAllByText("AIR.PA").length).toBeGreaterThan(0));
    const cells = vi.mocked(format.formatCell);
    await waitFor(() => expect(cells).toHaveBeenCalled());
    cells.mockClear();

    const input = rtl.getByLabelText("DSL query");
    for (const text of ["p", "pi", "pio", "piot"]) {
      fireEvent.change(input, { target: { value: text } });
    }
    expect(cells).not.toHaveBeenCalled();
  });
});
