// FR-007 / FR-004 — the DSL query bar: monospaced, run-on-Enter, inline error
// with position + hint; previous results stay visible while an error shows.
// Field-name autocomplete over the live schema (type 2+ letters; ArrowUp/Down
// + Tab/Enter complete), and ArrowUp recalls the query history when no
// suggestions are open (terminal idiom).

import { useRef, useState } from "react";
import type { RefObject } from "react";
import type { DslErrorDetail, FieldInfo } from "../data";
import { fieldLabel } from "../data/field-catalog";
import { loadQueryHistory } from "../query-history";

interface Props {
  value: string;
  onChange: (next: string) => void;
  onRun: () => void;
  running: boolean;
  error: DslErrorDetail | null;
  inputRef?: RefObject<HTMLInputElement>;
  fields?: FieldInfo[];
}

const SUGGEST_ID = "querybar-suggestions";
const MAX_SUGGESTIONS = 8;
const DSL_KEYWORDS = new Set(["and", "or", "not", "in"]);

function trailingToken(text: string): string | null {
  const match = text.match(/([A-Za-z_][A-Za-z0-9_]*)$/);
  return match ? match[1] : null;
}

export function QueryBar({ value, onChange, onRun, running, error, inputRef, fields = [] }: Props) {
  const [suggestions, setSuggestions] = useState<FieldInfo[]>([]);
  const [active, setActive] = useState(-1);
  const histPos = useRef(-1);
  const draft = useRef("");

  const suggestFor = (text: string) => {
    const token = trailingToken(text);
    if (!token || token.length < 2 || DSL_KEYWORDS.has(token.toLowerCase())) {
      setSuggestions([]);
      setActive(-1);
      return;
    }
    const needle = token.toLowerCase();
    const starts = fields.filter((f) => f.name.startsWith(needle));
    const contains = fields.filter((f) => !f.name.startsWith(needle) && f.name.includes(needle));
    setSuggestions([...starts, ...contains].filter((f) => f.name !== needle).slice(0, MAX_SUGGESTIONS));
    setActive(-1);
  };

  const accept = (field: FieldInfo) => {
    onChange(`${value.replace(/([A-Za-z_][A-Za-z0-9_]*)$/, field.name)} `);
    setSuggestions([]);
    setActive(-1);
    inputRef?.current?.focus();
  };

  // history recall bypasses suggestFor: a recalled query is complete
  const recall = (next: string) => {
    onChange(next);
    setSuggestions([]);
    setActive(-1);
  };

  return (
    <div>
      <div className="querybar">
        <div className="qb-autocomplete">
          <input
            ref={inputRef}
            aria-label="DSL query"
            role="combobox"
            aria-expanded={suggestions.length > 0}
            aria-controls={SUGGEST_ID}
            aria-autocomplete="list"
            aria-activedescendant={active >= 0 ? `qb-suggestion-${active}` : undefined}
            placeholder="blank = every covered company · e.g. peg_ratio <= 1 AND country IN ('FR','DE')"
            value={value}
            onChange={(event) => {
              histPos.current = -1;
              onChange(event.target.value);
              suggestFor(event.target.value);
            }}
            onBlur={() => setTimeout(() => setSuggestions([]), 150)}
            onKeyDown={(event) => {
              if (suggestions.length > 0) {
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setActive((i) => Math.min(i + 1, suggestions.length - 1));
                  return;
                }
                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setActive((i) => Math.max(i - 1, -1));
                  return;
                }
                if (event.key === "Escape") {
                  setSuggestions([]);
                  setActive(-1);
                  return;
                }
                if (event.key === "Tab") {
                  event.preventDefault();
                  accept(suggestions[active >= 0 ? active : 0]);
                  return;
                }
                if (event.key === "Enter") {
                  if (active >= 0) {
                    event.preventDefault();
                    accept(suggestions[active]);
                  } else {
                    setSuggestions([]);
                    onRun();
                  }
                  return;
                }
                return;
              }
              if (event.key === "Enter") onRun();
              if (event.key === "ArrowUp") {
                const history = loadQueryHistory();
                if (!history.length || histPos.current >= history.length - 1) return;
                event.preventDefault();
                if (histPos.current === -1) draft.current = value;
                histPos.current += 1;
                recall(history[histPos.current]);
              }
              if (event.key === "ArrowDown" && histPos.current !== -1) {
                event.preventDefault();
                histPos.current -= 1;
                recall(histPos.current === -1 ? draft.current : loadQueryHistory()[histPos.current]);
              }
            }}
          />
          {suggestions.length > 0 && (
            <ul role="listbox" id={SUGGEST_ID} className="qb-suggestions">
              {suggestions.map((field, index) => (
                <li
                  key={field.name}
                  id={`qb-suggestion-${index}`}
                  role="option"
                  aria-selected={index === active}
                  className={index === active ? "active" : undefined}
                  onMouseEnter={() => setActive(index)}
                  onMouseDown={() => accept(field)}
                >
                  <code>{field.name}</code>
                  <span className="meta"> {fieldLabel(field.name)} · {field.type}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
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
