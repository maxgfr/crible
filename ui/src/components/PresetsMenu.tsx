// FR-009 — presets menu: a grouped popover (Scores / Ranks / Value / … /
// Custom) where every entry shows its FULL DSL (visible, editable — never
// hidden logic). Picking one loads the DSL into the query bar; the active
// preset is named on the trigger. The current query saves inline as a named
// custom preset (stored locally, FR-009 AC-2); custom presets can be deleted.

import { useEffect, useMemo, useRef, useState } from "react";
import { presets as fetchPresets, type Preset } from "../data";
import { fieldGroup } from "../data/field-catalog";
import {
  customPresetId,
  deleteCustomPreset,
  loadCustomPresets,
  saveCustomPreset,
} from "../presets-store";

interface Props {
  /** the whole preset: the DSL to run + the columns it wants visible */
  onPick: (preset: Preset) => void;
  currentQuery: string;
  /** the DSL of the last-run screen — names the active preset on the trigger */
  activeDsl?: string | null;
}

const GROUP_ORDER = ["Scores", "Ranks", "Value", "Screens", "Custom"];

function groupOf(preset: Preset): string {
  if (preset.id.startsWith("custom-")) return "Custom";
  const firstField = preset.dsl.match(/^[A-Za-z_][A-Za-z0-9_]*/)?.[0];
  const group = firstField ? fieldGroup(firstField) : "Screens";
  return GROUP_ORDER.includes(group) ? group : "Screens";
}

export function PresetsMenu({ onPick, currentQuery, activeDsl }: Props) {
  const [shipped, setShipped] = useState<Preset[]>([]);
  const [custom, setCustom] = useState<Preset[]>([]);
  const [open, setOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchPresets().then(setShipped).catch(() => setShipped([]));
    setCustom(loadCustomPresets());
  }, []);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  const all = useMemo(() => [...shipped, ...custom], [shipped, custom]);
  const active = all.find((p) => activeDsl != null && p.dsl === activeDsl) ?? null;
  const groups = useMemo(() => {
    const byGroup = new Map<string, Preset[]>();
    for (const preset of all) {
      const group = groupOf(preset);
      byGroup.set(group, [...(byGroup.get(group) ?? []), preset]);
    }
    return GROUP_ORDER.filter((g) => byGroup.has(g)).map((g) => [g, byGroup.get(g)!] as const);
  }, [all]);
  const wouldReplace = custom.some((p) => p.id === customPresetId(saveName));

  return (
    <div
      className="picker presets"
      ref={rootRef}
      onKeyDown={(event) => {
        if (event.key === "Escape") setOpen(false);
      }}
    >
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-haspopup="true">
        {active ? `Preset: ${active.name}` : "Presets"}
      </button>
      {open && (
        <div className="picker-menu presets-menu">
          {groups.map(([group, items]) => (
            <div key={group} className="preset-group" role="group" aria-label={group}>
              <div className="preset-group-name">{group}</div>
              {items.map((preset) => (
                <div
                  key={preset.id}
                  className={preset.id === active?.id ? "preset-item active" : "preset-item"}
                >
                  <button
                    className="preset-pick"
                    title={preset.description}
                    onClick={() => {
                      onPick(preset);
                      setOpen(false);
                    }}
                  >
                    <span className="preset-name">{preset.name}</span>
                    <code className="preset-dsl">{preset.dsl}</code>
                  </button>
                  {preset.id.startsWith("custom-") && (
                    <button
                      className="preset-delete"
                      aria-label={`Delete preset ${preset.name}`}
                      title={`Delete preset ${preset.name}`}
                      onClick={() => setCustom(deleteCustomPreset(preset.id))}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          ))}
          <form
            className="preset-save"
            onSubmit={(event) => {
              event.preventDefault();
              if (saveName.trim() && currentQuery.trim()) {
                setCustom(saveCustomPreset(saveName.trim(), currentQuery));
                setSaveName("");
              }
            }}
          >
            <input
              aria-label="New preset name"
              placeholder="Save current query as…"
              value={saveName}
              onChange={(event) => setSaveName(event.target.value)}
            />
            <button type="submit" disabled={!saveName.trim() || !currentQuery.trim()}>
              {wouldReplace ? "Replace" : "Save"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
