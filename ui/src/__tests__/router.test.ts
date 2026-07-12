// T-016 — hash router: #/ (screener), #/status, #/providers, and the
// deep-linkable company drawer #/company/:symbol (drawer over the screener).

import { describe, expect, it } from "vitest";
import { hashFor, parseHash } from "../router";

describe("parseHash", () => {
  it("defaults to the screener", () => {
    expect(parseHash("")).toEqual({ view: "screener", company: null });
    expect(parseHash("#/")).toEqual({ view: "screener", company: null });
    expect(parseHash("#garbage")).toEqual({ view: "screener", company: null });
  });

  it("routes the status and providers views", () => {
    expect(parseHash("#/status")).toEqual({ view: "status", company: null });
    expect(parseHash("#/providers")).toEqual({ view: "providers", company: null });
  });

  it("deep-links a company drawer over the screener", () => {
    expect(parseHash("#/company/AIR.PA")).toEqual({ view: "screener", company: "AIR.PA" });
  });

  it("decodes URI-encoded symbols", () => {
    expect(parseHash("#/company/BRK%2FB")).toEqual({ view: "screener", company: "BRK/B" });
  });
});

describe("hashFor", () => {
  it("is the inverse of parseHash", () => {
    expect(hashFor({ view: "screener", company: null })).toBe("#/");
    expect(hashFor({ view: "status", company: null })).toBe("#/status");
    expect(hashFor({ view: "providers", company: null })).toBe("#/providers");
    expect(parseHash(hashFor({ view: "screener", company: "BRK/B" })))
      .toEqual({ view: "screener", company: "BRK/B" });
  });
});
