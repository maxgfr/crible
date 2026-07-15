// Query history — the last screens ran, recalled with ArrowUp in the query
// bar (terminal idiom). Local to the operator, like custom presets.

const KEY = "crible.query-history";
const MAX = 20;

export function loadQueryHistory(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? (JSON.parse(raw) as string[]) : [];
    return Array.isArray(parsed) ? parsed.filter((q) => typeof q === "string") : [];
  } catch {
    return [];
  }
}

export function pushQueryHistory(query: string): void {
  const trimmed = query.trim();
  if (!trimmed) return;
  try {
    const next = [trimmed, ...loadQueryHistory().filter((q) => q !== trimmed)].slice(0, MAX);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // storage full/blocked — history is a convenience, never an error
  }
}
