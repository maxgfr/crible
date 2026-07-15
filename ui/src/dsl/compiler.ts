// FR-004 / NFR-011 — 1:1 TypeScript port of src/crible/dsl/compiler.py.
// AST → parametrized DuckDB SQL over a strict whitelist: identifiers must be
// whitelisted, every value becomes a `?` placeholder. Error messages, hints
// and the closest-match suggestion mirror the Python implementation — parity
// locked by golden.json in both pytest and vitest.

import { type AstNode, DslError, pyRepr } from "./parser";

export const OPERATORS: Record<string, string> = {
  ">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=", "==": "=", "!=": "<>", "<>": "<>",
};

// mirrors crible.compute.ranks.RANK_COLUMNS + the compiler's extras
const RANK_COLUMNS = ["quality_rank", "value_rank", "momentum_rank", "composite_rank", "magic_formula_rank"];
export const BUILD_TIME_COLUMNS = new Set([
  ...RANK_COLUMNS, "rank_peer_group", "rank_missing_pillars", "return_6m",
]);
const BUILD_TIME_REMEDY =
  "added at snapshot build time (FR-015) — recompute the snapshot" +
  " (`crible compute`) after upgrading";

/** difflib.SequenceMatcher's matching-blocks total (Ratcliff–Obershelp with
 * difflib's tie-breaking: lowest a-index, then lowest b-index). */
function matchedChars(a: string, b: string): number {
  function longest(aLo: number, aHi: number, bLo: number, bHi: number): [number, number, number] {
    let bestI = aLo;
    let bestJ = bLo;
    let bestSize = 0;
    let j2len = new Map<number, number>();
    for (let i = aLo; i < aHi; i++) {
      const next = new Map<number, number>();
      for (let j = bLo; j < bHi; j++) {
        if (a[i] === b[j]) {
          const k = (j2len.get(j - 1) ?? 0) + 1;
          next.set(j, k);
          if (k > bestSize) {
            bestI = i - k + 1;
            bestJ = j - k + 1;
            bestSize = k;
          }
        }
      }
      j2len = next;
    }
    return [bestI, bestJ, bestSize];
  }
  function walk(aLo: number, aHi: number, bLo: number, bHi: number): number {
    const [i, j, size] = longest(aLo, aHi, bLo, bHi);
    if (size === 0) return 0;
    return size + walk(aLo, i, bLo, j) + walk(i + size, aHi, j + size, bHi);
  }
  return walk(0, a.length, 0, b.length);
}

/** difflib.get_close_matches(word, sorted(candidates), n=1, cutoff=0.6) —
 * candidates are iterated in sorted order and the first best ratio wins. */
export function closestMatch(word: string, candidates: string[], cutoff = 0.6): string | null {
  let best: string | null = null;
  let bestScore = -1;
  for (const candidate of candidates) {
    const total = candidate.length + word.length;
    const score = total === 0 ? 1 : (2 * matchedChars(candidate, word)) / total;
    if (score >= cutoff && score > bestScore) {
      best = candidate;
      bestScore = score;
    }
  }
  return best;
}

function checkField(field: string, whitelist: Set<string>, position: number): string {
  if (whitelist.has(field)) return field;
  if (BUILD_TIME_COLUMNS.has(field)) {
    throw new DslError(`unknown field ${pyRepr(field)} at position ${position}`, position, BUILD_TIME_REMEDY);
  }
  const closest = closestMatch(field, [...whitelist].sort());
  const hint = closest !== null ? `did you mean ${pyRepr(closest)}?` : "no similar field exists";
  throw new DslError(`unknown field ${pyRepr(field)} at position ${position}`, position, hint);
}

export function compileQuery(
  ast: AstNode,
  whitelist: Set<string>,
): [string, (number | string)[]] {
  const params: (number | string)[] = [];

  const emit = (node: AstNode): string => {
    switch (node.type) {
      case "comparison": {
        const field = checkField(node.field, whitelist, node.position);
        params.push(node.value);
        return `"${field}" ${OPERATORS[node.op]} ?`;
      }
      case "in": {
        const field = checkField(node.field, whitelist, node.position);
        params.push(...node.values);
        const placeholders = node.values.map(() => "?").join(", ");
        return `"${field}" IN (${placeholders})`;
      }
      case "not":
        return `NOT (${emit(node.operand)})`;
      case "bool":
        return node.operands.map((operand) => `(${emit(operand)})`).join(` ${node.op} `);
    }
  };

  return [emit(ast), params];
}

export function compileSort(sort: string | null, whitelist: Set<string>): string {
  if (!sort) return "";
  const clauses: string[] = [];
  for (const part of sort.split(",")) {
    const raw = part.trim();
    if (!raw) continue;
    const direction = raw.startsWith("-") ? "DESC" : "ASC";
    const field = raw.replace(/^[+-]+/, "");
    checkField(field, whitelist, 0);
    clauses.push(`"${field}" ${direction}`);
  }
  return clauses.length ? ` ORDER BY ${clauses.join(", ")}` : "";
}
