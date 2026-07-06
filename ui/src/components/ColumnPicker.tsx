// FR-007 — searchable column picker over the snapshot's ~200 columns.

import { useMemo, useState } from "react";

interface Props {
  available: string[];
  visible: string[];
  onChange: (next: string[]) => void;
}

export function ColumnPicker({ available, visible, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const shown = useMemo(
    () => available.filter((c) => c.toLowerCase().includes(filter.toLowerCase())),
    [available, filter],
  );

  return (
    <div className="picker">
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        Columns ({visible.length})
      </button>
      {open && (
        <div className="picker-menu">
          <input
            aria-label="Filter columns"
            placeholder="filter…"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            style={{ width: "100%", marginBottom: 6 }}
          />
          {shown.map((column) => (
            <label key={column}>
              <input
                type="checkbox"
                checked={visible.includes(column)}
                onChange={(event) =>
                  onChange(
                    event.target.checked
                      ? [...visible, column]
                      : visible.filter((c) => c !== column),
                  )
                }
              />{" "}
              {column}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
