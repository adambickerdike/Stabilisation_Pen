"""Minimal S-expression reader/writer for KiCad files.

Quoted strings are returned as Q (a str subclass) so they are written back
quoted; bare atoms are plain str.  Numbers stay as their original text.
"""
from __future__ import annotations


class Q(str):
    """A quoted string atom."""


def parse(text: str):
    i, n = 0, len(text)
    stack = [[]]
    while i < n:
        c = text[i]
        if c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            node = stack.pop()
            stack[-1].append(node)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1] if text[j + 1] in '"\\' else "\\" + text[j + 1])
                    j += 2
                    continue
                if text[j] == '"':
                    break
                buf.append(text[j])
                j += 1
            stack[-1].append(Q("".join(buf)))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in '()"':
                j += 1
            stack[-1].append(text[i:j])
            i = j
    assert len(stack) == 1, "unbalanced parentheses"
    return stack[0]


def _atom(a) -> str:
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return str(a)


def dumps(node, indent: int = 0) -> str:
    if not isinstance(node, list):
        return _atom(node)
    if not node:
        return "()"
    simple = all(not isinstance(x, list) for x in node)
    if simple and len(node) <= 8:
        return "(" + " ".join(_atom(x) for x in node) + ")"
    pad = "  " * (indent + 1)
    parts = [_atom(node[0]) if not isinstance(node[0], list) else dumps(node[0], indent + 1)]
    line = "(" + parts[0]
    out = [line]
    for x in node[1:]:
        if isinstance(x, list):
            out.append("\n" + pad + dumps(x, indent + 1))
        else:
            out.append(" " + _atom(x))
    return "".join(out) + ")"


def find(node, key):
    """First child list whose head is key."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
