// FR-009 — presets menu: selecting a preset loads its FULL DSL into the query
// bar (visible, editable — never hidden logic); the edited text can be saved
// as a new named preset (stored locally, FR-009 AC-2).

import { useEffect, useState } from "react";
import { presets as fetchPresets, type Preset } from "../api";
import { loadCustomPresets, saveCustomPreset } from "../presets-store";

interface Props {
  onPick: (dsl: string) => void;
  currentQuery: string;
}

export function PresetsMenu({ onPick, currentQuery }: Props) {
  const [shipped, setShipped] = useState<Preset[]>([]);
  const [custom, setCustom] = useState<Preset[]>([]);

  useEffect(() => {
    fetchPresets().then(setShipped).catch(() => setShipped([]));
    setCustom(loadCustomPresets());
  }, []);

  const all = [...shipped, ...custom];

  return (
    <>
      <select
        aria-label="Preset screens"
        defaultValue=""
        onChange={(event) => {
          const preset = all.find((p) => p.id === event.target.value);
          if (preset) onPick(preset.dsl);
          event.target.value = "";
        }}
      >
        <option value="" disabled>
          Presets…
        </option>
        {all.map((preset) => (
          <option key={preset.id} value={preset.id} title={preset.dsl}>
            {preset.name} — {preset.description}
          </option>
        ))}
      </select>
      <button
        aria-label="Save current query as preset"
        title="Save the current query as a named preset"
        onClick={() => {
          const name = window.prompt("Preset name?", "");
          if (name && currentQuery.trim()) {
            setCustom(saveCustomPreset(name, currentQuery));
          }
        }}
      >
        Save preset
      </button>
    </>
  );
}
