// Best-effort live quote: the staleness gate (EOD close vs today UTC), the
// direct→mirror fallback chain, the per-symbol cache, and the chip — which
// renders nothing when data is fresh or every route fails.

import { render, screen as rtl, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LiveQuote } from "../components/LiveQuote";
import { clearLiveQuoteCache, fetchLiveQuote, isStale } from "../data/live-quote";

const YAHOO = {
  chart: {
    result: [
      {
        meta: {
          regularMarketPrice: 123.45,
          chartPreviousClose: 120.0,
          currency: "EUR",
          regularMarketTime: 1752912000,
        },
      },
    ],
  },
};

const ok = (payload: unknown) => ({ ok: true, json: async () => payload });

beforeEach(() => clearLiveQuoteCache());
afterEach(() => vi.unstubAllGlobals());

describe("isStale", () => {
  it("today's close is fresh; older or missing is stale", () => {
    const today = new Date("2026-07-19T10:00:00Z");
    expect(isStale("2026-07-19", today)).toBe(false);
    expect(isStale("2026-07-17", today)).toBe(true);
    expect(isStale(null, today)).toBe(true);
    expect(isStale(undefined, today)).toBe(true);
  });
});

describe("fetchLiveQuote", () => {
  it("falls back to the next route when the direct call is CORS-blocked", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("cors"))
      .mockResolvedValueOnce(ok(YAHOO));
    vi.stubGlobal("fetch", fetchMock);
    const quote = await fetchLiveQuote("AIR.PA", { proxies: true });
    expect(quote).toMatchObject({ price: 123.45, previousClose: 120, currency: "EUR" });
    expect(quote?.source).toBe("Yahoo Finance via corsproxy.io");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    // the mirror wraps the SAME Yahoo url
    expect(String(fetchMock.mock.calls[1][0])).toContain(
      encodeURIComponent("query1.finance.yahoo.com"),
    );
  });

  it("caches per symbol — a second call within the TTL never refetches", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(YAHOO));
    vi.stubGlobal("fetch", fetchMock);
    await fetchLiveQuote("AIR.PA", { direct: true });
    await fetchLiveQuote("AIR.PA", { direct: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("concurrent calls for one symbol share a single request", async () => {
    // the grid row and the drawer asking at once each went to Yahoo
    let answer: (value: unknown) => void = () => {};
    const fetchMock = vi.fn(() => new Promise((resolve) => (answer = resolve)));
    vi.stubGlobal("fetch", fetchMock);
    const first = fetchLiveQuote("AIR.PA", { direct: true });
    const second = fetchLiveQuote("AIR.PA", { direct: true });
    answer(ok(YAHOO));
    const [a, b] = await Promise.all([first, second]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(a?.price).toBe(123.45);
    expect(b).toEqual(a);
  });

  it("resolves null when every route fails", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("down"));
    vi.stubGlobal("fetch", fetchMock);
    expect(await fetchLiveQuote("AIR.PA", { proxies: true })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(3); // every route tried once
  });

  it("API mode sends the ticker nowhere by default", async () => {
    // a self-hosted screener told Yahoo which company its user opened, on a
    // browser request Yahoo's CORS policy may never even let through
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("cors"));
    vi.stubGlobal("fetch", fetchMock);
    expect(await fetchLiveQuote("AIR.PA")).toBeNull(); // the test build is API mode
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("VITE_LIVE_QUOTE=1 opts API mode into the direct Yahoo call only", async () => {
    vi.stubEnv("VITE_LIVE_QUOTE", "1");
    try {
      const fetchMock = vi.fn().mockRejectedValue(new TypeError("cors"));
      vi.stubGlobal("fetch", fetchMock);
      expect(await fetchLiveQuote("AIR.PA")).toBeNull();
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(String(fetchMock.mock.calls[0][0])).toMatch(/^https:\/\/query1\.finance\.yahoo\.com\//);
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("VITE_LIVE_QUOTE_PROXY=1 opts API mode into the proxies", async () => {
    vi.stubEnv("VITE_LIVE_QUOTE_PROXY", "1");
    try {
      const fetchMock = vi.fn().mockRejectedValue(new TypeError("cors"));
      vi.stubGlobal("fetch", fetchMock);
      await fetchLiveQuote("AIR.PA");
      expect(fetchMock).toHaveBeenCalledTimes(3);
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("a direct answer is labelled as coming straight from Yahoo", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok(YAHOO)));
    expect((await fetchLiveQuote("AIR.PA", { direct: true }))?.source).toBe("Yahoo Finance (direct)");
  });
});

describe("LiveQuote chip", () => {
  it("renders price, signed change and both vintages when the close is stale", async () => {
    vi.stubEnv("VITE_LIVE_QUOTE", "1");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok(YAHOO)));
    render(<LiveQuote symbol="AIR.PA" asof="2020-01-02" />);
    await waitFor(() => expect(rtl.getByRole("status")).toBeInTheDocument());
    const chip = rtl.getByRole("status");
    expect(chip).toHaveTextContent("live 123.45 EUR");
    expect(chip).toHaveTextContent("+2.9% vs last close");
    expect(chip).toHaveTextContent("dataset close 2020-01-02");
    expect(chip).toHaveTextContent(/unofficial/);
    expect(chip).toHaveTextContent("Yahoo Finance (direct)"); // the route is named
    vi.unstubAllEnvs();
  });

  it("renders nothing and fetches nothing in a default API build", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(YAHOO));
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<LiveQuote symbol="AIR.PA" asof="2020-01-02" />);
    await Promise.resolve();
    await Promise.resolve();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });

  it("fetches nothing when the published close is today's", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const today = new Date().toISOString().slice(0, 10);
    const { container } = render(<LiveQuote symbol="AIR.PA" asof={today} />);
    await Promise.resolve();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });
});
