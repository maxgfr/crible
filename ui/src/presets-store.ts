// FR-009 AC-2 — edited queries can be saved as new named presets.
// Custom presets live in localStorage (self-hosted, single operator).

import type { Preset } from "./api";

const KEY = "crible.custom-presets";

export function loadCustomPresets(): Preset[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? (JSON.parse(raw) as Preset[]) : [];
    return Array.isArray(parsed) ? parsed.filter((p) => p && p.id && p.dsl) : [];
  } catch {
    return [];
  }
}

export function saveCustomPreset(name: string, dsl: string): Preset[] {
  const preset: Preset = {
    id: `custom-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`,
    name,
    description: "custom preset",
    dsl,
  };
  const others = loadCustomPresets().filter((p) => p.id !== preset.id);
  const next = [...others, preset];
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
