"""Material DSL Lexer."""
import re
from dataclasses import dataclass, field
from typing import List

VALID_TYPES = {
    "TEXTURE_SAMPLE","TEXTURE_PARAM","SCALAR_PARAM","VECTOR_PARAM",
    "CONSTANT","CONSTANT3","CONSTANT4","MULTIPLY","ADD","SUBTRACT","DIVIDE",
    "LERP","CLAMP","POWER","ABS","ONE_MINUS","FRESNEL","PANNER","TEX_COORD",
    "TIME","NOISE","DESATURATION","MASK","APPEND","OUTPUT",
}

@dataclass
class Token:
    type: str; indent: int = 0; name: str = ""; key: str = ""; value: str = ""
    line_num: int = 0; properties: dict = field(default_factory=dict)

def tokenize(dsl: str) -> List[Token]:
    tokens = []
    for i, raw in enumerate(dsl.split("\n")):
        line = raw.rstrip(); stripped = line.strip(); ln = i + 1
        if not stripped: continue
        if stripped.startswith("--"): continue

        m = re.match(r'^MATERIAL:\s*(\S+)', stripped)
        if m: tokens.append(Token("HEADER", name=m.group(1), line_num=ln)); continue

        m = re.match(r'^OUTPUT:', stripped)
        if m: tokens.append(Token("OUTPUT", line_num=ln)); continue

        # Node declaration: TYPE: Name
        m = re.match(r'^(\w+):\s*(\S+)', stripped)
        if m and m.group(1) in VALID_TYPES:
            tokens.append(Token("NODE", name=m.group(2), key=m.group(1), line_num=ln)); continue

        # @property=value
        m = re.match(r'^\s*@(\w+)\s*=\s*(.+)', stripped)
        if m: tokens.append(Token("PROPERTY", key=m.group(1), value=m.group(2).strip(), line_num=ln)); continue

    return tokens
