// FR-009 AC-2 — edited queries can be saved as new named presets.
// Custom presets live in localStorage (self-hosted, single operator) —
// same try/catch contract as theme.ts: storage may be missing or full.

import type { Preset } from "./data/types";

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

function persist(presets: Preset[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(presets));
  } catch {
    /* quota or SecurityError — the list still updates for this session */
  }
}

// FNV-1a over the UTF-16 code units: short, stable across sessions
function nameHash(name: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < name.length; i += 1) {
    hash ^= name.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(36);
}

// ASCII names keep their readable slug (ids already stored stay valid); a
// name with any non-ASCII character also carries a hash of the full name,
// so "価値株" and "成長株" never collapse onto the same "custom-" id
export function customPresetId(name: string): string {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const ascii = [...name].every((ch) => ch.charCodeAt(0) <= 0x7f);
  if (ascii) return `custom-${slug}`;
  return `custom-${slug ? `${slug}-` : ""}${nameHash(name)}`;
}

export function saveCustomPreset(name: string, dsl: string): Preset[] {
  const preset: Preset = {
    id: customPresetId(name),
    name,
    description: "custom preset",
    dsl,
  };
  const others = loadCustomPresets().filter((p) => p.id !== preset.id);
  const next = [...others, preset];
  persist(next);
  return next;
}

export function deleteCustomPreset(id: string): Preset[] {
  const next = loadCustomPresets().filter((p) => p.id !== id);
  persist(next);
  return next;
}
