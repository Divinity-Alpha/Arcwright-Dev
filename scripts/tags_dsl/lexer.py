"""Tags DSL Lexer."""
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Token:
    type: str; indent: int = 0; name: str = ""; line_num: int = 0

def tokenize(dsl: str) -> List[Token]:
    tokens = []
    for i, raw in enumerate(dsl.split("\n")):
        s = raw.rstrip(); stripped = s.strip(); ln = i + 1
        if not stripped or stripped.startswith("--"): continue
        ind = (len(s) - len(s.lstrip(" "))) // 2
        m = re.match(r'^TAGS:\s*(\S+)', stripped)
        if m: tokens.append(Token("HEADER", name=m.group(1), line_num=ln)); continue
        m = re.match(r'^HIERARCHY:\s*(\S+)', stripped)
        if m: tokens.append(Token("HIERARCHY", name=m.group(1), line_num=ln)); continue
        if re.match(r'^[A-Za-z]\w*$', stripped):
            tokens.append(Token("TAG", indent=ind, name=stripped, line_num=ln)); continue
    return tokens
