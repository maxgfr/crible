// Zero-result explainability: split a query into its top-level AND clauses
// so the empty state can count survivors per clause. The serializer mirrors
// the parser exactly — never a second grammar.

import { type AstNode, parse } from "./parser";

function literal(value: number | string): string {
  return typeof value === "number" ? String(value) : `'${String(value).replace(/'/g, "\\'")}'`;
}

export function toDsl(node: AstNode): string {
  switch (node.type) {
    case "comparison":
      return `${node.field} ${node.op} ${literal(node.value)}`;
    case "in":
      return `${node.field} IN (${node.values.map(literal).join(", ")})`;
    case "not":
      return `NOT (${toDsl(node.operand)})`;
    case "bool":
      return node.operands
        .map((operand) => (operand.type === "bool" ? `(${toDsl(operand)})` : toDsl(operand)))
        .join(` ${node.op} `);
  }
}

/** Top-level AND clauses of a query, or [] when the shape (single clause,
 *  OR at the top, parse error) makes a per-clause funnel meaningless. */
export function topLevelClauses(query: string): string[] {
  try {
    const ast = parse(query);
    if (ast.type === "bool" && ast.op === "AND") return ast.operands.map(toDsl);
  } catch {
    // an unparsable query already shows its own error elsewhere
  }
  return [];
}
