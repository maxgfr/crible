// FR-009 AC-2 — custom presets in localStorage: storage failures never
// throw into a click handler, and every name gets its own stable id (two
// all-non-ASCII names must not silently overwrite each other).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  customPresetId,
  deleteCustomPreset,
  loadCustomPresets,
  saveCustomPreset,
} from "../presets-store";

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe("customPresetId", () => {
  it("keeps the readable slug for ASCII names", () => {
    expect(customPresetId("Cash cows")).toBe("custom-cash-cows");
  });

  it("gives distinct, stable ids to different non-ASCII names", () => {
    const a = customPresetId("価値株");
    const b = customPresetId("成長株");
    expect(a).not.toBe(b);
    expect(a).toBe(customPresetId("価値株"));
    expect(a).toMatch(/^custom-[a-z0-9-]+$/);
    expect(customPresetId("Café ★")).not.toBe(customPresetId("Café ☆"));
  });

  it("two non-ASCII presets coexist in storage", () => {
    saveCustomPreset("価値株", "piotroski_f >= 7");
    saveCustomPreset("成長株", "revenue_growth > 0.2");
    expect(loadCustomPresets()).toHaveLength(2);
  });
});

describe("storage failures", () => {
  it("save and delete never throw when localStorage refuses the write", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("quota exceeded", "QuotaExceededError");
    });
    expect(() => saveCustomPreset("Cash cows", "fcf_margin >= 0.05")).not.toThrow();
    expect(saveCustomPreset("Cash cows", "fcf_margin >= 0.05")).toEqual([
      expect.objectContaining({ id: "custom-cash-cows" }),
    ]);
    expect(() => deleteCustomPreset("custom-cash-cows")).not.toThrow();
  });
});
