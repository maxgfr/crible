// T-016 — theme resolution & persistence: stored value wins, then OS
// preference, dark is the default; applyTheme stamps <html data-theme>.

import { describe, expect, it } from "vitest";
import { applyTheme, resolveTheme, toggled } from "../theme";

describe("resolveTheme", () => {
  it("uses the stored theme when valid", () => {
    expect(resolveTheme("light", false)).toBe("light");
    expect(resolveTheme("dark", true)).toBe("dark");
  });

  it("falls back to the OS preference when nothing stored", () => {
    expect(resolveTheme(null, true)).toBe("light");
    expect(resolveTheme(null, false)).toBe("dark");
  });

  it("ignores garbage stored values", () => {
    expect(resolveTheme("phosphore", false)).toBe("dark");
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
