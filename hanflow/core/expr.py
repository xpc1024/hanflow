"""A tiny, safe expression engine for DSL conditions and templates.

Supported grammar (deliberately small — no eval, no attribute access to
arbitrary objects, no function calls):

    expr   := or_expr
    or_expr:= and_expr ('or' and_expr)*
    and_expr:= cmp ('and' cmp)*
    cmp    := operand (('==' | '!=') operand | 'in' list)?
    operand:= NAME | NUMBER | STRING
    list   := '[' operand (',' operand)* ']'
    NAME   := dotted path resolving via ``lookup`` (dict traversal / index)

Templates use ``{{ path }}`` interpolation; conditions use the grammar above.
See detailed design §2.4.
"""

from __future__ import annotations

import re
from typing import Any

PLACEHOLDER = re.compile(r"\{\{\s*(.*?)\s*\}\}")

_NAME = r"[A-Za-z_][\w-]*(?:\.[A-Za-z_0-9][\w-]*)*"
_NUMBER = r"-?\d+(?:\.\d+)?"
_STRING = r"'[^']*'|\"[^\"]*\""
_TOKEN_RE = re.compile(rf"\s*(?:(in|and|or)\b|(==|!=)|(\[|\]|,)|({_NAME})|({_NUMBER})|({_STRING}))")


class ExprError(Exception):
    """Raised on a malformed expression or unknown variable."""


# --------------------------------------------------------------------------- #
# Interpolation
# --------------------------------------------------------------------------- #


def interpolate(template: str, context: dict[str, Any]) -> str:
    """Replace ``{{ path }}`` placeholders with looked-up values (str-coerced).

    Used for human-readable output templates (e.g. prompt strings). Conditions
    are evaluated separately by :func:`evaluate` against the live context
    (with dotted-path variable resolution), NOT by interpolating then
    re-parsing — that avoids ambiguity between a bare value and a variable.
    """
    if "{{" not in template:
        return template

    def _replace(m: re.Match[str]) -> str:
        path = m.group(1).strip()
        return str(lookup(path, context))

    return PLACEHOLDER.sub(_replace, template)


# --------------------------------------------------------------------------- #
# Condition evaluation
# --------------------------------------------------------------------------- #


def evaluate(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a boolean condition against ``context``."""
    tokens = _tokenize(condition)
    parser = _Parser(tokens, context)
    result = parser.parse_expression()
    if parser.peek() is not None:
        raise ExprError(f"unexpected trailing tokens in: {condition!r}")
    if not isinstance(result, bool):
        raise ExprError(f"condition did not evaluate to bool: {condition!r}")
    return result


# --------------------------------------------------------------------------- #
# Variable lookup (shared by interpolate + evaluate)
# --------------------------------------------------------------------------- #


def lookup(path: str, context: dict[str, Any]) -> Any:
    cur: Any = context
    for part in path.split("."):
        cur = _step(cur, part)
        if cur is None:
            raise ExprError(f"unknown variable or path: {path!r} (failed at {part!r})")
    return cur


def _step(container: Any, key: str) -> Any:
    if isinstance(container, dict):
        return container.get(key)
    if isinstance(container, (list, tuple)):
        try:
            return container[int(key)]
        except (ValueError, IndexError):
            return None
    return getattr(container, key, None)


# --------------------------------------------------------------------------- #
# Tokenizer
# --------------------------------------------------------------------------- #


def _tokenize(s: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            if s[pos:].isspace():
                break
            raise ExprError(f"cannot tokenize at: {s[pos:]!r}")
        pos = m.end()
        kw, op, bracket, name, num, string = m.groups()
        if kw:
            tokens.append(("KW", kw))
        elif op:
            tokens.append(("OP", op))
        elif bracket:
            tokens.append(("BRACKET", bracket))
        elif name:
            tokens.append(("NAME", name))
        elif num:
            tokens.append(("NUM", num))
        elif string:
            tokens.append(("STR", string[1:-1]))
    return tokens


# --------------------------------------------------------------------------- #
# Recursive-descent parser / evaluator
# --------------------------------------------------------------------------- #


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], context: dict[str, Any]) -> None:
        self.tokens = tokens
        self.i = 0
        self.context = context

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def advance(self) -> tuple[str, str]:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def parse_expression(self) -> Any:
        return self._parse_or()

    def _parse_or(self) -> Any:
        left = self._parse_and()
        while self.peek() == ("KW", "or"):
            self.advance()
            right = self._parse_and()
            left = bool(left) or bool(right)
        return left

    def _parse_and(self) -> Any:
        left = self._parse_cmp()
        while self.peek() == ("KW", "and"):
            self.advance()
            right = self._parse_cmp()
            left = bool(left) and bool(right)
        return left

    def _parse_cmp(self) -> Any:
        left = self._parse_operand()
        tok = self.peek()
        if tok is None:
            return left
        kind, value = tok
        if kind == "OP":
            self.advance()
            right = self._parse_operand()
            return _eq(left, value == "==", right)
        if tok == ("KW", "in"):
            self.advance()
            items = self._parse_list()
            return left in items
        return left

    def _parse_list(self) -> list[Any]:
        if self.peek() != ("BRACKET", "["):
            raise ExprError("expected '[' after 'in'")
        self.advance()
        items: list[Any] = []
        if self.peek() == ("BRACKET", "]"):
            self.advance()
            return items
        items.append(self._parse_operand(literal_fallback=True))
        while self.peek() == ("BRACKET", ","):
            self.advance()
            items.append(self._parse_operand(literal_fallback=True))
        if self.peek() != ("BRACKET", "]"):
            raise ExprError("expected ']' to close list")
        self.advance()
        return items

    def _parse_operand(self, literal_fallback: bool = False) -> Any:
        tok = self.peek()
        if tok is None:
            raise ExprError("unexpected end of expression")
        kind, value = tok
        self.advance()
        if kind == "NUM":
            return float(value) if "." in value else int(value)
        if kind == "STR":
            return value
        if kind == "NAME":
            try:
                return lookup(value, self.context)
            except ExprError:
                # Inside an ``in [...]`` list, a bare NAME that isn't a variable
                # is treated as a literal string (e.g. ``in [confidential, ...]``).
                if literal_fallback:
                    return value
                raise
        raise ExprError(f"unexpected token: {tok!r}")


def _eq(left: Any, equal: bool, right: Any) -> bool:
    result = left == right
    return result if equal else not result
