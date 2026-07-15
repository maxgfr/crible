// The fields a DSL query references — the auto fallback that surfaces a
// screen's inputs as grid columns (custom presets, hand-typed queries,
// permalinks). Reuses the golden-locked tokenizer, never the parser's
// grammar; malformed DSL yields [] — the compiler owns error reporting.

import { tokenize } from "./parser";

export function fieldsInQuery(dsl: string): string[] {
  try {
    const seen = new Set<string>();
    for (const token of tokenize(dsl)) {
      if (token.kind === "FIELD") seen.add(token.value);
    }
    return [...seen];
  } catch {
    return [];
  }
}
