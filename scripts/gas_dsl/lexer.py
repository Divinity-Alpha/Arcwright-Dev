"""GAS DSL Lexer."""
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Token:
    type: str; indent: int = 0; name: str = ""; key: str = ""; value: str = ""; line_num: int = 0

def _indent(line): return (len(line) - len(line.lstrip(" "))) // 2

def tokenize(dsl: str) -> List[Token]:
    tokens = []
    for i, raw in enumerate(dsl.split("\n")):
        s = raw.rstrip(); stripped = s.strip(); ln = i + 1
        if not stripped or stripped.startswith("--"): continue

        m = re.match(r'^ABILITY_SYSTEM:\s*(\S+)', stripped)
        if m: tokens.append(Token("SYSTEM", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^ATTRIBUTE_SET:\s*(\S+)', stripped)
        if m: tokens.append(Token("ATTR_SET", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^ATTRIBUTE:\s*(\S+)', stripped)
        if m: tokens.append(Token("ATTRIBUTE", indent=_indent(s), name=m.group(1), line_num=ln)); continue
        m = re.match(r'^ABILITY:\s*(\S+)', stripped)
        if m: tokens.append(Token("ABILITY", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^EFFECT:\s*(\S+)', stripped)
        if m: tokens.append(Token("EFFECT", indent=_indent(s), name=m.group(1), line_num=ln)); continue
        m = re.match(r'^EFFECT_PRESET:\s*(\S+)', stripped)
        if m: tokens.append(Token("EFFECT_PRESET", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^\s*@(\w+)\s*=\s*(.+)', stripped)
        if m: tokens.append(Token("PROPERTY", indent=_indent(s), key=m.group(1), value=m.group(2).strip().strip('"'), line_num=ln)); continue
    return tokens
