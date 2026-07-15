// Universe search — symbol/name substring over all ~161k listings (crawled or
// not), debounced, a real combobox: ArrowUp/Down + Enter work, the active
// option is announced. Picking a hit deep-links the company drawer. Works
// identically in api and static mode.

import { useEffect, useRef, useState } from "react";
import { search, type SearchHit } from "../data";

interface Props {
  onPick: (symbol: string) => void;
}

const DEBOUNCE_MS = 150;
const LISTBOX_ID = "universe-search-listbox";

export function SearchBox({ onPick }: Props) {
  const [value, setValue] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [active, setActive] = useState(-1);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const needle = value.trim();
    if (!needle) {
      setHits([]);
      setActive(-1);
      return;
    }
    timer.current = setTimeout(() => {
      search(needle)
        .then((found) => {
          setHits(found);
          setActive(-1);
        })
        .catch(() => setHits([]));
    }, DEBOUNCE_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [value]);

  const pick = (hit: SearchHit) => {
    onPick(hit.symbol);
    setValue("");
    setHits([]);
    setActive(-1);
  };

  return (
    <div className="searchbox">
      <input
        aria-label="Search the universe"
        role="combobox"
        aria-expanded={hits.length > 0}
        aria-controls={LISTBOX_ID}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `search-option-${active}` : undefined}
        placeholder="Find a company…"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (!hits.length) return;
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setActive((i) => Math.min(i + 1, hits.length - 1));
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((i) => Math.max(i - 1, -1));
          } else if (event.key === "Enter" && active >= 0) {
            event.preventDefault();
            pick(hits[active]);
          } else if (event.key === "Escape") {
            setHits([]);
            setActive(-1);
          }
        }}
        onBlur={() => setTimeout(() => setHits([]), 150)}
      />
      {hits.length > 0 && (
        <ul role="listbox" id={LISTBOX_ID} className="searchbox-results">
          {hits.map((hit, index) => (
            <li
              key={hit.symbol}
              id={`search-option-${index}`}
              role="option"
              aria-selected={index === active}
              className={index === active ? "active" : undefined}
              onMouseEnter={() => setActive(index)}
              onMouseDown={() => pick(hit)}
            >
              <strong>{hit.symbol}</strong> — {hit.name ?? "?"}
              <span className="meta"> · {hit.country ?? "?"}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
