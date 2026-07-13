// FR-007 / FR-004 — the DSL query bar: monospaced, run-on-Enter, inline error
// with position + hint; previous results stay visible while an error shows.

import type { RefObject } from "react";
import type { DslErrorDetail } from "../data";

interface Props {
  value: string;
  onChange: (next: string) => void;
  onRun: () => void;
  running: boolean;
  error: DslErrorDetail | null;
  inputRef?: RefObject<HTMLInputElement>;
}

export function QueryBar({ value, onChange, onRun, running, error, inputRef }: Props) {
  return (
    <div>
      <div className="querybar">
        <input
          ref={inputRef}
          aria-label="DSL query"
          placeholder="e.g. roe > 15 AND piotroski_f >= 7 AND country IN ('FR','DE')"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") onRun();
          }}
        />
        <button className="primary" onClick={onRun} disabled={running}>
          {running ? "Running…" : "Screen"}
        </button>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error.error}
          {error.position !== null && <span> (at position {error.position})</span>}
          {error.hint && <div>hint: {error.hint}</div>}
        </div>
      )}
    </div>
  );
}
