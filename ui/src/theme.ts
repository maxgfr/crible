// T-016 — theme: stored value wins, then OS preference; dark is the default.
// The boot script in index.html applies the same resolution pre-paint (no FOUC).

export type Theme = "dark" | "light";

const STORAGE_KEY = "crible-theme";

export function resolveTheme(stored: string | null, prefersLight: boolean): Theme {
  if (stored === "dark" || stored === "light") return stored;
  return prefersLight ? "light" : "dark";
}

export function toggled(theme: Theme): Theme {
  return theme === "dark" ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function loadTheme(): Theme {
  let stored: string | null = null;
  try {
    stored = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    /* storage unavailable (private mode) — fall through to OS preference */
  }
  const prefersLight =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: light)").matches;
  return resolveTheme(stored, prefersLight);
}

export function saveTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* non-persistent is fine */
  }
}
