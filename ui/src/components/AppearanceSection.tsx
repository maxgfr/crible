// T-020 — appearance preferences, rendered as a section of the Status view.
// The provider inventory that used to live here is intentionally GONE from
// the UI: sources are an operator concern (docs/DATA-SOURCES.md is the
// ledger), not something a screener user should have to see.

import type { ThemePref } from "../theme";

interface Props {
  pref: ThemePref;
  onPref: (pref: ThemePref) => void;
}

export function AppearanceSection({ pref, onPref }: Props) {
  return (
    <>
      <h2>Appearance</h2>
      <div className="view-body">
        <fieldset className="theme-pref">
          <legend className="meta">theme</legend>
          <label>
            <input
              type="radio"
              name="theme"
              checked={pref === "auto"}
              onChange={() => onPref("auto")}
            />{" "}
            Auto (follow the system)
          </label>
          <label>
            <input
              type="radio"
              name="theme"
              checked={pref === "dark"}
              onChange={() => onPref("dark")}
            />{" "}
            Dark (phosphore)
          </label>
          <label>
            <input
              type="radio"
              name="theme"
              checked={pref === "light"}
              onChange={() => onPref("light")}
            />{" "}
            Light (paper terminal)
          </label>
        </fieldset>
      </div>
    </>
  );
}
