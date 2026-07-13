// T-016 — theme: an explicit choice wins; "auto" (the default) follows the
// OS preference LIVE. The boot script in index.html applies the same
// resolution pre-paint (no FOUC): stored dark/light wins, else OS.

export type Theme = "dark" | "light";
export type ThemePref = Theme | "auto";

const STORAGE_KEY = "crible-theme";

export function resolvePref(stored: string | null): ThemePref {
  if (stored === "dark" || stored === "light") return stored;
  return "auto"; // nothing stored, "auto", or garbage — follow the OS
}

export function effectiveTheme(pref: ThemePref, prefersLight: boolean): Theme {
  if (pref === "auto") return prefersLight ? "light" : "dark";
  return pref;
}

export function toggled(theme: Theme): Theme {
  return theme === "dark" ? "light" : "dark";
}

/** The header cycle: auto → explicit flip (always a visible change) → auto. */
export function cycled(pref: ThemePref, effective: Theme): ThemePref {
  return pref === "auto" ? toggled(effective) : "auto";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function prefersLight(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: light)").matches
  );
}

export function loadThemePref(): ThemePref {
  let stored: string | null = null;
  try {
    stored = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    /* storage unavailable (private mode) — auto */
  }
  return resolvePref(stored);
}

export function saveThemePref(pref: ThemePref): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, pref);
  } catch {
    /* non-persistent is fine */
  }
}

/** In auto mode the theme must track live OS changes; returns the cleanup. */
export function watchSystemTheme(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const media = window.matchMedia("(prefers-color-scheme: light)");
  const handler = () => onChange();
  media.addEventListener?.("change", handler);
  return () => media.removeEventListener?.("change", handler);
}
