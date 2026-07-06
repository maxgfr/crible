"""FR-004 — the filter DSL: tokenizer + recursive-descent parser.

Grammar (case-insensitive keywords):

    expr       := or_expr
    or_expr    := and_expr (OR and_expr)*
    and_expr   := unary (AND unary)*
    unary      := NOT unary | '(' expr ')' | comparison
    comparison := FIELD op value | FIELD IN '(' value (',' value)* ')'
    op         := > | >= | < | <= | = | == | != | <>
    value      := NUMBER | 'quoted string' | "quoted string"

Every error is a DslError carrying the offending token and its position —
the parser is the only thing that ever reads user input; SQL never does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class DslError(ValueError):
    def __init__(self, message: str, position: int | None = None, hint: str | None = None) -> None:
        full = message if hint is None else f"{message} — {hint}"
        super().__init__(full)
        self.position = position
        self.hint = hint


@dataclass(frozen=True)
class Token:
    kind: str  # FIELD NUMBER STRING OP LPAREN RPAREN COMMA AND OR NOT IN
    value: str
    position: int


@dataclass(frozen=True)
class Comparison:
    field: str
    op: str
    value: float | str
    position: int


@dataclass(frozen=True)
class InList:
    field: str
    values: list[float | str]
    position: int


@dataclass(frozen=True)
class Not:
    operand: object


@dataclass(frozen=True)
class BoolOp:
    op: str  # AND | OR
    operands: list[object]


TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<op>>=|<=|!=|<>|==|>|<|=)
  | (?P<lparen>\()
  | (?P<rparen>\))
  | (?P<comma>,)
  | (?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
  | (?P<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
  | (?P<word>[A-Za-z_][A-Za-z0-9_.]*)
    """,
    re.VERBOSE,
)

KEYWORDS = {"and": "AND", "or": "OR", "not": "NOT", "in": "IN"}


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        match = TOKEN_RE.match(text, pos)
        if not match:
            raise DslError(f"unexpected character {text[pos]!r} at position {pos}", position=pos)
        pos = match.end()
        if match.lastgroup == "ws":
            continue
        value = match.group()
        kind = {
            "op": "OP", "lparen": "LPAREN", "rparen": "RPAREN", "comma": "COMMA",
            "number": "NUMBER", "string": "STRING", "word": "WORD",
        }[match.lastgroup]
        if kind == "WORD":
            kind = KEYWORDS.get(value.lower(), "FIELD")
        tokens.append(Token(kind, value, match.start()))
    return tokens


class _Parser:
    def __init__(self, tokens: list[Token], text: str) -> None:
        self.tokens = tokens
        self.text = text
        self.index = 0

    def peek(self) -> Token | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, kind: str | None = None) -> Token:
        token = self.peek()
        if token is None:
            raise DslError("unexpected end of query", position=len(self.text))
        if kind is not None and token.kind != kind:
            raise DslError(
                f"expected {kind} but found {token.value!r} at position {token.position}",
                position=token.position,
            )
        self.index += 1
        return token

    def parse_expr(self) -> object:
        operands = [self.parse_and()]
        while (t := self.peek()) and t.kind == "OR":
            self.take()
            operands.append(self.parse_and())
        return operands[0] if len(operands) == 1 else BoolOp("OR", operands)

    def parse_and(self) -> object:
        operands = [self.parse_unary()]
        while (t := self.peek()) and t.kind == "AND":
            self.take()
            operands.append(self.parse_unary())
        return operands[0] if len(operands) == 1 else BoolOp("AND", operands)

    def parse_unary(self) -> object:
        token = self.peek()
        if token is None:
            raise DslError("unexpected end of query", position=len(self.text))
        if token.kind == "NOT":
            self.take()
            return Not(self.parse_unary())
        if token.kind == "LPAREN":
            self.take()
            inner = self.parse_expr()
            self.take("RPAREN")
            return inner
        return self.parse_comparison()

    def parse_value(self) -> float | str:
        token = self.take()
        if token.kind == "NUMBER":
            return float(token.value)
        if token.kind == "STRING":
            raw = token.value[1:-1]
            return raw.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
        raise DslError(
            f"expected a number or quoted string but found {token.value!r} at position {token.position}",
            position=token.position,
        )

    def parse_comparison(self) -> object:
        field = self.take("FIELD")
        token = self.peek()
        if token is not None and token.kind == "IN":
            self.take()
            self.take("LPAREN")
            values = [self.parse_value()]
            while (t := self.peek()) and t.kind == "COMMA":
                self.take()
                values.append(self.parse_value())
            self.take("RPAREN")
            return InList(field.value, values, field.position)
        op = self.take("OP")
        value = self.parse_value()
        return Comparison(field.value, op.value, value, field.position)


def parse(text: str) -> object:
    if not text or not text.strip():
        raise DslError("empty query", position=0)
    tokens = tokenize(text)
    parser = _Parser(tokens, text)
    ast = parser.parse_expr()
    trailing = parser.peek()
    if trailing is not None:
        raise DslError(
            f"unexpected {trailing.value!r} at position {trailing.position}",
            position=trailing.position,
        )
    return ast
