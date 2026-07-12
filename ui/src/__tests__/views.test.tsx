// T-019/T-020 — Status (coverage, freshness histogram, budget gauge,
// provider health) and Providers & settings (inventory, .env pointer,
// EODHD upgrade path, theme preference).

import { fireEvent, render, screen as rtl, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProvidersView } from "../components/ProvidersView";
import { StatusView } from "../components/StatusView";

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("StatusView (T-019)", () => {
  it("renders coverage, freshness histogram, budget gauge and provider health", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
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
        }),
      ),
    );
    render(<StatusView />);
    await waitFor(() => expect(rtl.getByText(/2\.4\s?%/)).toBeInTheDocument());
    expect(rtl.getByText(/<7d/)).toBeInTheDocument();
    expect(rtl.getByText(/120/)).toBeInTheDocument();
    expect(rtl.getByText(/360/)).toBeInTheDocument();
    expect(rtl.getByText("yfinance")).toBeInTheDocument();
    expect(rtl.getByText(/healthy/)).toBeInTheDocument();
  });

  it("teaches when there is no heartbeat yet", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ universe: 0, snapshot: false })),
    );
    render(<StatusView />);
    await waitFor(() => expect(rtl.getByText(/no crawl heartbeat/i)).toBeInTheDocument());
    expect(rtl.getByText(/docker compose up/)).toBeInTheDocument();
  });
});

describe("ProvidersView (T-020)", () => {
  it("lists keyless built-ins and keyed plugins with their state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse([
          { id: "yfinance", kind: "keyless", key_env_var: null, enabled: true },
          { id: "simfin", kind: "free-key", key_env_var: "SIMFIN_KEY", enabled: false },
          { id: "eodhd", kind: "paid", key_env_var: "EODHD_KEY", enabled: true },
        ]),
      ),
    );
    render(<ProvidersView theme="dark" onTheme={() => {}} />);
    await waitFor(() => expect(rtl.getByText("yfinance")).toBeInTheDocument());
    expect(rtl.getByText("simfin")).toBeInTheDocument();
    expect(rtl.getByText("SIMFIN_KEY")).toBeInTheDocument();
    expect(rtl.getAllByText(/off — no key/i).length).toBeGreaterThan(0);
    expect(rtl.getByText("eodhd")).toBeInTheDocument();
    // built-ins always present even before fetch resolves
    expect(rtl.getByText(/esef/i)).toBeInTheDocument();
    expect(rtl.getByText(/\.env/)).toBeInTheDocument();
  });

  it("exposes the theme preference", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse([])));
    const onTheme = vi.fn();
    render(<ProvidersView theme="dark" onTheme={onTheme} />);
    fireEvent.click(rtl.getByRole("radio", { name: /paper terminal/i }));
    expect(onTheme).toHaveBeenCalledWith("light");
  });
});
