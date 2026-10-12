// FR-004 — 1:1 TypeScript port of src/crible/dsl/parser.py for the static
// (DuckDB-WASM) static build. Same grammar, same token kinds, same error messages,
// positions and hints — parity is locked by golden.json, asserted by BOTH
// tests/test_dsl_parity.py and ui/src/__tests__/dsl.test.ts. Any change here
// must land in the Python parser (and regenerate the golden file) too.

export class DslError extends Error {
  position: number | null;
  hint: string | null;

  constructor(message: string, position: number | null = null, hint: string | null = null) {
    super(hint === null ? message : `${message} — ${hint}`);
    this.name = "DslError";
    this.position = position;
    this.hint = hint;
  }
}

// Python's str.isprintable() is false for these categories (space aside)
const NON_PRINTABLE = /^[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}\p{Zs}]$/u;

/** Python `repr()` for strings — error messages embed offending tokens with
 * `{token!r}`, so the port must format them exactly the same way, escapes of
 * non-printable characters (`\xa0`, `\u200b`) included. */
export function pyRepr(text: string): string {
  const quote = text.includes("'") && !text.includes('"') ? '"' : "'";
  let out = quote;
  for (const ch of text) {
    if (ch === "\\" || ch === quote) out += `\\${ch}`;
    else if (ch === "\n") out += "\\n";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\t") out += "\\t";
    else if (ch !== " " && NON_PRINTABLE.test(ch)) {
      const code = ch.codePointAt(0) ?? 0;
      const hex = code.toString(16);
      out +=
        code < 0x100 ? `\\x${hex.padStart(2, "0")}` : code < 0x10000 ? `\\u${hex.padStart(4, "0")}` : `\\U${hex.padStart(8, "0")}`;
    } else out += ch;
  }
  return out + quote;
}

export type TokenKind =
  | "FIELD" | "NUMBER" | "STRING" | "OP"
  | "LPAREN" | "RPAREN" | "COMMA"
  | "AND" | "OR" | "NOT" | "IN";

export interface Token {
  kind: TokenKind;
  value: string;
  position: number;
}

export interface Comparison {
  type: "comparison";
  field: string;
  op: string;
  value: number | string;
  position: number;
}

export interface InList {
  type: "in";
  field: string;
  values: (number | string)[];
  position: number;
}

export interface NotNode {
  type: "not";
  operand: AstNode;
}

export interface BoolOp {
  type: "bool";
  op: "AND" | "OR";
  operands: AstNode[];
}

export type AstNode = Comparison | InList | NotNode | BoolOp;

// groups: 1 ws · 2 op · 3 lparen · 4 rparen · 5 comma · 6 number · 7 string · 8 word
// Whitespace and digits are spelled out ASCII classes: Python's re.ASCII
// \s/\d, not JS's Unicode \s (NBSP, BOM…) — parity on hostile input.
const TOKEN_RE =
  /([ \t\n\r\f\v]+)|(>=|<=|!=|<>|==|>|<|=)|(\()|(\))|(,)|(-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)|('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")|([A-Za-z_][A-Za-z0-9_.]*)/y;

const KEYWORDS: Record<string, TokenKind> = { and: "AND", or: "OR", not: "NOT", in: "IN" };

export const MAX_QUERY_LENGTH = 2000;
export const MAX_DEPTH = 32;

/** Python positions count code points; JS strings index UTF-16 units. */
function codePoints(text: string, end: number): number {
  let count = 0;
  for (let i = 0; i < end; i++) {
    const code = text.charCodeAt(i);
    if (code >= 0xd800 && code <= 0xdbff && i + 1 < end) i++;
    count++;
  }
  return count;
}

export function tokenize(text: string): Token[] {
  const tokens: Token[] = [];
  let pos = 0;
  while (pos < text.length) {
    TOKEN_RE.lastIndex = pos;
    const match = TOKEN_RE.exec(text);
    if (!match) {
      const at = codePoints(text, pos);
      const ch = String.fromCodePoint(text.codePointAt(pos) ?? 0);
      throw new DslError(`unexpected character ${pyRepr(ch)} at position ${at}`, at);
    }
    const start = codePoints(text, pos);
    pos = TOKEN_RE.lastIndex;
    if (match[1] !== undefined) continue;
    const value = match[0];
    let kind: TokenKind;
    if (match[2] !== undefined) kind = "OP";
    else if (match[3] !== undefined) kind = "LPAREN";
    else if (match[4] !== undefined) kind = "RPAREN";
    else if (match[5] !== undefined) kind = "COMMA";
    else if (match[6] !== undefined) kind = "NUMBER";
    else if (match[7] !== undefined) kind = "STRING";
    else kind = KEYWORDS[value.toLowerCase()] ?? "FIELD";
    tokens.push({ kind, value, position: start });
  }
  return tokens;
}

class Parser {
  private index = 0;
  private depth = 0;
  private end: number;

  constructor(
    private tokens: Token[],
    text: string,
  ) {
    this.end = codePoints(text, text.length);
  }

  peek(): Token | null {
    return this.index < this.tokens.length ? this.tokens[this.index] : null;
  }

  take(kind?: TokenKind): Token {
    const token = this.peek();
    if (token === null) {
      throw new DslError("unexpected end of query", this.end);
    }
    if (kind !== undefined && token.kind !== kind) {
      throw new DslError(
        `expected ${kind} but found ${pyRepr(token.value)} at position ${token.position}`,
        token.position,
      );
    }
    this.index += 1;
    return token;
  }

  parseExpr(): AstNode {
    const operands = [this.parseAnd()];
    let t: Token | null;
    while ((t = this.peek()) && t.kind === "OR") {
      this.take();
      operands.push(this.parseAnd());
    }
    return operands.length === 1 ? operands[0] : { type: "bool", op: "OR", operands };
  }

  parseAnd(): AstNode {
    const operands = [this.parseUnary()];
    let t: Token | null;
    while ((t = this.peek()) && t.kind === "AND") {
      this.take();
      operands.push(this.parseUnary());
    }
    return operands.length === 1 ? operands[0] : { type: "bool", op: "AND", operands };
  }

  parseUnary(): AstNode {
    const token = this.peek();
    if (token === null) {
      throw new DslError("unexpected end of query", this.end);
    }
    if (token.kind === "NOT" || token.kind === "LPAREN") {
      this.take();
      this.depth += 1;
      if (this.depth > MAX_DEPTH) {
        throw new DslError(
          `query nests too deeply at position ${token.position}`,
          token.position,
          `at most ${MAX_DEPTH} levels of NOT / parentheses`,
        );
      }
      let node: AstNode;
      if (token.kind === "NOT") {
        node = { type: "not", operand: this.parseUnary() };
      } else {
        node = this.parseExpr();
        this.take("RPAREN");
      }
      this.depth -= 1;
      return node;
    }
    return this.parseComparison();
  }

  parseValue(): number | string {
    const token = this.take();
    if (token.kind === "NUMBER") return Number(token.value);
    if (token.kind === "FIELD" && ["true", "false"].includes(token.value.toLowerCase())) {
      // boolean columns (top10k, primary_listing) compare against 1/0
      return token.value.toLowerCase() === "true" ? 1 : 0;
    }
    if (token.kind === "STRING") {
      const raw = token.value.slice(1, -1);
      // same replacement SEQUENCE as the Python parser
      return raw.replaceAll("\\'", "'").replaceAll('\\"', '"').replaceAll("\\\\", "\\");
    }
    throw new DslError(
      `expected a number or quoted string but found ${pyRepr(token.value)} at position ${token.position}`,
      token.position,
    );
  }

  parseComparison(): AstNode {
    const field = this.take("FIELD");
    const token = this.peek();
    if (token !== null && token.kind === "IN") {
      this.take();
      this.take("LPAREN");
      const values = [this.parseValue()];
      let t: Token | null;
      while ((t = this.peek()) && t.kind === "COMMA") {
        this.take();
        values.push(this.parseValue());
      }
      this.take("RPAREN");
      return { type: "in", field: field.value, values, position: field.position };
    }
    const op = this.take("OP");
    const value = this.parseValue();
    return { type: "comparison", field: field.value, op: op.value, value, position: field.position };
  }
}

export function parse(text: string): AstNode {
  // Python's str.strip(" \t\n\r\f\v"): the same ASCII whitespace as the tokenizer
  if (!text || !text.replace(/^[ \t\n\r\f\v]+/, "")) throw new DslError("empty query", 0);
  const length = codePoints(text, text.length);
  if (length > MAX_QUERY_LENGTH) {
    throw new DslError(
      `query too long (${length} characters) at position ${MAX_QUERY_LENGTH}`,
      MAX_QUERY_LENGTH,
      `at most ${MAX_QUERY_LENGTH} characters`,
    );
  }
  const tokens = tokenize(text);
  const parser = new Parser(tokens, text);
  const ast = parser.parseExpr();
  const trailing = parser.peek();
  if (trailing !== null) {
    throw new DslError(
      `unexpected ${pyRepr(trailing.value)} at position ${trailing.position}`,
      trailing.position,
    );
  }
  return ast;
}
