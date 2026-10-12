// T-016 — theme resolution & persistence: an explicit stored choice wins,
// "auto" (the default) follows the OS preference; applyTheme stamps
// <html data-theme>.

import { describe, expect, it, vi } from "vitest";
import indexHtml from "../../index.html?raw";
import { applyTheme, effectiveTheme, resolvePref } from "../theme";

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

// the pre-paint boot script in index.html must resolve exactly like
// effectiveTheme(loadThemePref(), prefersLight()) — App saves "auto" on
// mount, so "auto" is the common stored value, not an explicit choice
describe("index.html pre-paint script", () => {
  const script = /<script>([\s\S]*?)<\/script>/.exec(indexHtml)![1];

  function prePaint(stored: string | null, osLight: boolean): string | undefined {
    if (stored === null) localStorage.removeItem("crible-theme");
    else localStorage.setItem("crible-theme", stored);
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: osLight && q.includes("light") }));
    delete document.documentElement.dataset.theme;
    try {
      new Function(script)();
    } finally {
      vi.unstubAllGlobals();
    }
    return document.documentElement.dataset.theme;
  }

  it("stored auto follows the OS — no dark flash for light-OS users", () => {
    expect(prePaint("auto", true)).toBe("light");
    expect(prePaint("auto", false)).toBe("dark");
  });

  it("matches the runtime resolution for every stored value", () => {
    for (const stored of [null, "auto", "light", "dark", "garbage"]) {
      for (const osLight of [true, false]) {
        expect(prePaint(stored, osLight)).toBe(effectiveTheme(resolvePref(stored), osLight));
      }
    }
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
