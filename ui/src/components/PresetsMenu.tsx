// FR-009 — presets menu: selecting a preset loads its FULL DSL into the query
// bar (visible, editable — never hidden logic).

import { useEffect, useState } from "react";
import { presets as fetchPresets, type Preset } from "../api";

interface Props {
  onPick: (dsl: string) => void;
}

export function PresetsMenu({ onPick }: Props) {
  const [items, setItems] = useState<Preset[]>([]);

  useEffect(() => {
    fetchPresets().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <select
      aria-label="Preset screens"
      defaultValue=""
      onChange={(event) => {
        const preset = items.find((p) => p.id === event.target.value);
        if (preset) onPick(preset.dsl);
        event.target.value = "";
      }}
    >
      <option value="" disabled>
        Presets…
      </option>
      {items.map((preset) => (
        <option key={preset.id} value={preset.id} title={preset.dsl}>
          {preset.name} — {preset.description}
        </option>
      ))}
    </select>
  );
}
