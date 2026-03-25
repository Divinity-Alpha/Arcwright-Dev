import re
from dataclasses import dataclass
from typing import List
@dataclass
class Token:
    type: str; indent: int = 0; name: str = ""; key: str = ""; value: str = ""; line_num: int = 0
def tokenize(dsl: str) -> List[Token]:
    tokens = []
    for i, raw in enumerate(dsl.split(chr(10))):
        s = raw.rstrip(); stripped = s.strip(); ln = i + 1
        if not stripped or stripped.startswith("--"): continue
        ind = (len(s) - len(s.lstrip(" "))) // 2
        m = re.match(r"^PAPER2D:\s*(\S+)", stripped)
        if m: tokens.append(Token("HEADER", name=m.group(1), line_num=ln)); continue
        m = re.match(r"^SPRITE:\s*(\S+)", stripped)
        if m: tokens.append(Token("SPRITE", name=m.group(1), line_num=ln)); continue
        m = re.match(r"^FLIPBOOK:\s*(\S+)", stripped)
        if m: tokens.append(Token("FLIPBOOK", name=m.group(1), line_num=ln)); continue
        m = re.match(r"^TILEMAP:\s*(\S+)", stripped)
        if m: tokens.append(Token("TILEMAP", name=m.group(1), line_num=ln)); continue
        m = re.match(r"^FRAME:\s*(\S+)", stripped)
        if m: tokens.append(Token("FRAME", name=m.group(1), line_num=ln)); continue
        m = re.match(r"^LAYER:\s*(\S+)", stripped)
        if m: tokens.append(Token("LAYER", name=m.group(1), line_num=ln)); continue
        m = re.match(r"^\s*@(\w+)\s*=\s*(.+)", stripped)
        if m: tokens.append(Token("PROPERTY", indent=ind, key=m.group(1), value=m.group(2).strip(), line_num=ln)); continue
    return tokens
