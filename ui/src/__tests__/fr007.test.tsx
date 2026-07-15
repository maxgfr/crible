// FR-007 — SPA behaviour: grid renders results, errors show inline while
// previous results stay visible, export targets the FULL result set.

import { render, screen as rtl, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { exportCsvUrl } from "../api";

const ROWS = [
  { symbol: "AIR.PA", name: "Airbus", country: "FR", sector: "Industrials", piotroski_f: 8, altman_z: 3.2, beneish_m: -2.5, return_on_equity: 0.18 },
  { symbol: "SAP.DE", name: "SAP", country: "DE", sector: "Tech", piotroski_f: 7, altman_z: 4.1, beneish_m: -2.9, return_on_equity: 0.22 },
];

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => handler(url, init)),
  );
}

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    json: async () => body,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("FR-007 results grid", () => {
  it("FR-007: renders matching rows with sortable columns after a screen", async () => {
    mockFetch((url) => {
      if (url === "/api/screen") return jsonResponse({ rows: ROWS, total: 2, page: 1, tookMs: 12 });
      if (url === "/api/presets") return jsonResponse([]);
      if (url === "/api/status") return jsonResponse({ universe: 8, snapshot: true });
      return jsonResponse({}, 404);
    });
    render(<App />);
    await waitFor(() => expect(rtl.getByText("AIR.PA")).toBeInTheDocument());
    expect(rtl.getByText("SAP.DE")).toBeInTheDocument();
    expect(rtl.getByText(/rows 1–2 of 2/)).toBeInTheDocument();
  });

  it("FR-007: a DSL error shows inline with hint and previous results stay visible", async () => {
    let calls = 0;
    mockFetch((url) => {
      if (url === "/api/screen") {
        calls += 1;
        if (calls === 1) return jsonResponse({ rows: ROWS, total: 2, page: 1, tookMs: 5 });
        return jsonResponse(
          { detail: { error: "unknown field 'piotroski'", position: 0, hint: "did you mean 'piotroski_f'?" } },
          422,
        );
      }
      if (url === "/api/presets") return jsonResponse([]);
      if (url === "/api/status") return jsonResponse({ universe: 8, snapshot: true });
      return jsonResponse({}, 404);
    });
    render(<App />);
    await waitFor(() => expect(rtl.getByText("AIR.PA")).toBeInTheDocument());

    fireEvent.change(rtl.getByLabelText("DSL query"), { target: { value: "piotroski > 7" } });
    fireEvent.click(rtl.getByText("Screen"));

    await waitFor(() => expect(rtl.getByRole("alert")).toBeInTheDocument());
    expect(rtl.getByRole("alert").textContent).toContain("piotroski_f");
    // previous results remain on screen (no blank state)
    expect(rtl.getByText("AIR.PA")).toBeInTheDocument();
  });
});

describe("FR-007 export", () => {
  it("FR-007: the export URL carries the executed query AND the visible columns", () => {
    expect(exportCsvUrl("piotroski_f >= 7", null)).toBe(
      "/api/screen.csv?query=piotroski_f+%3E%3D+7",
    );
    expect(exportCsvUrl("roe > 15", "-roe")).toContain("sort=-roe");
    const withColumns = exportCsvUrl("roe > 15", null, ["symbol", "roe", "piotroski_f"]);
    expect(withColumns).toContain("columns=symbol%2Croe%2Cpiotroski_f");
  });
});

describe("FR-009 custom presets", () => {
  it("FR-009: an edited query can be saved as a new named preset and reloaded", async () => {
    const { loadCustomPresets, saveCustomPreset } = await import("../presets-store");
    localStorage.clear();
    expect(loadCustomPresets()).toEqual([]);
    saveCustomPreset("My deep value", "price_to_book_ratio < 0.8 AND altman_z > 3");
    const saved = loadCustomPresets();
    expect(saved).toHaveLength(1);
    expect(saved[0].id).toBe("custom-my-deep-value");
    expect(saved[0].dsl).toBe("price_to_book_ratio < 0.8 AND altman_z > 3");
    // saving the same name overwrites instead of duplicating
    saveCustomPreset("My deep value", "altman_z > 4");
    expect(loadCustomPresets()).toHaveLength(1);
    expect(loadCustomPresets()[0].dsl).toBe("altman_z > 4");
  });
});
