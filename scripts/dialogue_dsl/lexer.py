"""Dialogue DSL Lexer."""
import re
from dataclasses import dataclass, field
from typing import List

@dataclass
class Token:
    type: str; indent: int = 0; name: str = ""; key: str = ""; value: str = ""
    line_num: int = 0

def _indent(line): return (len(line) - len(line.lstrip(" "))) // 2

def tokenize(dsl: str) -> List[Token]:
    tokens = []
    for i, raw in enumerate(dsl.split("\n")):
        line = raw.rstrip(); stripped = line.strip(); ln = i + 1
        if not stripped or stripped.startswith("--"): continue

        m = re.match(r'^DIALOGUE:\s*(\S+)', stripped)
        if m: tokens.append(Token("HEADER", name=m.group(1), line_num=ln)); continue

        m = re.match(r'^NODE:\s*(\S+)', stripped)
        if m: tokens.append(Token("NODE", indent=_indent(line), name=m.group(1), line_num=ln)); continue

        m = re.match(r'^CHOICE:\s*"(.+)"', stripped)
        if m: tokens.append(Token("CHOICE", indent=_indent(line), value=m.group(1), line_num=ln)); continue

        m = re.match(r'^@(\w+)\s*=\s*(.+)', stripped)
        if m: tokens.append(Token("PROPERTY", indent=_indent(line), key=m.group(1), value=m.group(2).strip().strip('"'), line_num=ln)); continue

    return tokens
