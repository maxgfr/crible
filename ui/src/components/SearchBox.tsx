// Universe search — symbol/name substring over all ~161k listings (crawled or
// not), debounced, keyboard-free minimal dropdown. Picking a hit deep-links
// the company drawer. Works identically in api and static (demo) mode.

import { useEffect, useRef, useState } from "react";
import { search, type SearchHit } from "../data";

interface Props {
  onPick: (symbol: string) => void;
}

const DEBOUNCE_MS = 150;

export function SearchBox({ onPick }: Props) {
  const [value, setValue] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const needle = value.trim();
    if (!needle) {
      setHits([]);
      return;
    }
    timer.current = setTimeout(() => {
      search(needle)
        .then(setHits)
        .catch(() => setHits([]));
    }, DEBOUNCE_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [value]);

  return (
    <div className="searchbox">
      <input
        aria-label="Search the universe"
        placeholder="Find a company…"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onBlur={() => setTimeout(() => setHits([]), 150)}
      />
      {hits.length > 0 && (
        <ul role="listbox" className="searchbox-results">
          {hits.map((hit) => (
            <li
              key={hit.symbol}
              role="option"
              aria-selected={false}
              onMouseDown={() => {
                onPick(hit.symbol);
                setValue("");
                setHits([]);
              }}
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
