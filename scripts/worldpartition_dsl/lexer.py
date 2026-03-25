"""Lexer for worldpartition_dsl."""
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Token:
    type: str; indent: int = 0; name: str = ""; key: str = ""; value: str = ""; line_num: int = 0

def tokenize(dsl: str) -> List[Token]:
    tokens = []
    for i, raw in enumerate(dsl.split("\n")):
        s = raw.rstrip(); stripped = s.strip(); ln = i + 1
        if not stripped or stripped.startswith("--"): continue
        ind = (len(s) - len(s.lstrip(" "))) // 2
        m = re.match(r'^WORLD_PARTITION:\\s*(\\S+)', stripped)
        if m: tokens.append(Token("HEADER", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^REGION:\\s*(\\S+)', stripped)
        if m: tokens.append(Token("REGION", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^DATA_LAYER:\\s*(\\S+)', stripped)
        if m: tokens.append(Token("DATA_LAYER", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^HLOD:\\s*(\\S+)', stripped)
        if m: tokens.append(Token("HLOD", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^STREAMING_SOURCE:\\s*(\\S+)', stripped)
        if m: tokens.append(Token("STREAMING_SOURCE", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^\\s*@(\\w+)\\s*=\\s*(.+)', stripped)
        if m: tokens.append(Token("PROPERTY", indent=ind, key=m.group(1), value=m.group(2).strip(), line_num=ln)); continue
    return tokens
