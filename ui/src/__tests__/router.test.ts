// T-016 — hash router: #/ (screener), #/status (absorbs the old
// #/providers), and the deep-linkable company drawer #/company/:symbol.
// The screener's state travels in the hash query string (#/?q=…&sort=…):
// every screen is a permalink.

import { describe, expect, it } from "vitest";
import { hashFor, parseHash } from "../router";

describe("parseHash", () => {
  it("defaults to the screener", () => {
    expect(parseHash("")).toEqual({ view: "screener", company: null, q: null, sort: null });
    expect(parseHash("#/")).toEqual({ view: "screener", company: null, q: null, sort: null });
    expect(parseHash("#garbage")).toEqual({ view: "screener", company: null, q: null, sort: null });
  });

  it("routes the status view — old #/providers permalinks land there too", () => {
    expect(parseHash("#/status")).toEqual({ view: "status", company: null, q: null, sort: null });
    expect(parseHash("#/providers")).toEqual({ view: "status", company: null, q: null, sort: null });
  });

  it("deep-links a company drawer over the screener", () => {
    expect(parseHash("#/company/AIR.PA")).toEqual({
      view: "screener", company: "AIR.PA", q: null, sort: null,
    });
  });

  it("decodes URI-encoded symbols", () => {
    expect(parseHash("#/company/BRK%2FB")).toEqual({
      view: "screener", company: "BRK/B", q: null, sort: null,
    });
  });

  it("restores the screen from the hash query string", () => {
    expect(parseHash("#/?q=piotroski_f%20%3E%3D%207&sort=-composite_rank")).toEqual({
      view: "screener", company: null, q: "piotroski_f >= 7", sort: "-composite_rank",
    });
    // a company link keeps the screen that found it
    expect(parseHash("#/company/AIR.PA?q=altman_z%20%3E%202.99")).toEqual({
      view: "screener", company: "AIR.PA", q: "altman_z > 2.99", sort: null,
    });
    // q="" is meaningful: blank query = the full snapshot
    expect(parseHash("#/?q=")).toEqual({ view: "screener", company: null, q: "", sort: null });
  });
});

describe("hashFor", () => {
  it("is the inverse of parseHash", () => {
    const roundtrip = (route: Parameters<typeof hashFor>[0]) =>
      expect(parseHash(hashFor(route))).toEqual(route);
    expect(hashFor({ view: "screener", company: null, q: null, sort: null })).toBe("#/");
    expect(hashFor({ view: "status", company: null, q: null, sort: null })).toBe("#/status");
    roundtrip({ view: "screener", company: "BRK/B", q: null, sort: null });
    roundtrip({ view: "screener", company: null, q: "piotroski_f >= 7 AND country IN ('FR','DE')", sort: "-roe" });
    roundtrip({ view: "screener", company: "AIR.PA", q: "altman_z > 2.99", sort: "altman_z" });
    roundtrip({ view: "screener", company: null, q: "", sort: null });
  });
});
