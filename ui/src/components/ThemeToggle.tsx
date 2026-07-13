// T-016 — the header theme control cycles auto → explicit flip → auto:
// from auto one click forces the opposite of the current theme (a visible
// change), the next click hands control back to the OS. The Providers view
// keeps the explicit three-way choice.

import type { Theme, ThemePref } from "../theme";
import { toggled } from "../theme";

interface Props {
  pref: ThemePref;
  theme: Theme;
  onCycle: () => void;
}

function SunIcon() {
  return (
    <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4.5" />
      <g strokeLinecap="round">
        <line x1="12" y1="2" x2="12" y2="4.5" />
        <line x1="12" y1="19.5" x2="12" y2="22" />
        <line x1="2" y1="12" x2="4.5" y2="12" />
        <line x1="19.5" y1="12" x2="22" y2="12" />
        <line x1="4.9" y1="4.9" x2="6.7" y2="6.7" />
        <line x1="17.3" y1="17.3" x2="19.1" y2="19.1" />
        <line x1="4.9" y1="19.1" x2="6.7" y2="17.3" />
        <line x1="17.3" y1="6.7" x2="19.1" y2="4.9" />
      </g>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4 6.6 6.6 0 0 0 20 14.5Z" strokeLinejoin="round" />
    </svg>
  );
}

function AutoIcon() {
  // a half-filled circle: whatever the system says
  return (
    <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 3a9 9 0 0 1 0 18Z" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function ThemeToggle({ pref, theme, onCycle }: Props) {
  const label =
    pref === "auto"
      ? `Switch to the ${toggled(theme)} theme`
      : "Follow the system theme (auto)";
  return (
    <button className="theme-toggle" aria-label={label} title={label} onClick={onCycle}>
      {pref !== "auto" ? <AutoIcon /> : theme === "dark" ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
