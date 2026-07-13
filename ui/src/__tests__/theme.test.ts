// T-016 — theme resolution & persistence: an explicit stored choice wins,
// "auto" (the default) follows the OS preference; applyTheme stamps
// <html data-theme>.

import { describe, expect, it } from "vitest";
import { applyTheme, effectiveTheme, resolvePref, toggled } from "../theme";

describe("resolvePref", () => {
  it("keeps an explicit stored choice", () => {
    expect(resolvePref("light")).toBe("light");
    expect(resolvePref("dark")).toBe("dark");
  });

  it("defaults to auto when nothing (or garbage) is stored", () => {
    expect(resolvePref(null)).toBe("auto");
    expect(resolvePref("auto")).toBe("auto");
    expect(resolvePref("phosphore")).toBe("auto");
  });
});

describe("effectiveTheme", () => {
  it("follows the OS in auto mode", () => {
    expect(effectiveTheme("auto", true)).toBe("light");
    expect(effectiveTheme("auto", false)).toBe("dark");
  });

  it("ignores the OS when an explicit theme is chosen", () => {
    expect(effectiveTheme("dark", true)).toBe("dark");
    expect(effectiveTheme("light", false)).toBe("light");
  });
});

describe("toggled", () => {
  it("cycles dark ⇄ light", () => {
    expect(toggled("dark")).toBe("light");
    expect(toggled("light")).toBe("dark");
  });
});

describe("applyTheme", () => {
  it("stamps data-theme on the root element", () => {
    applyTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    applyTheme("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});
