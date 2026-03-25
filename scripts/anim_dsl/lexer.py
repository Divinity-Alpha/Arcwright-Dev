"""Animation DSL Lexer — tokenizes Animation DSL text."""

import re
from dataclasses import dataclass, field
from typing import List

T_HEADER = "HEADER"
T_SKELETON = "SKELETON"
T_MESH = "MESH"
T_STATE_MACHINE = "STATE_MACHINE"
T_STATE = "STATE"
T_TRANSITION = "TRANSITION"
T_BLEND_SPACE = "BLEND_SPACE"
T_LAYER = "LAYER"
T_MONTAGE = "MONTAGE"
T_AIM_OFFSET = "AIM_OFFSET"
T_VARIABLES = "VARIABLES"
T_VAR_DECL = "VAR_DECL"
T_PROPERTY = "PROPERTY"
T_COMMENT = "COMMENT"
T_BLANK = "BLANK"
T_SAMPLE = "SAMPLE"


@dataclass
class Token:
    type: str
    indent: int = 0
    name: str = ""
    key: str = ""
    value: str = ""
    raw: str = ""
    line_num: int = 0
    properties: dict = field(default_factory=dict)


def _indent(line: str) -> int:
    return (len(line) - len(line.lstrip(" "))) // 2


def _parse_props(text: str) -> dict:
    props = {}
    for m in re.finditer(r'(\w+)\s*=\s*(?:"([^"]*?)"|(\S+))', text):
        props[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return props


def tokenize(dsl: str) -> List[Token]:
    tokens = []
    for i, raw in enumerate(dsl.split("\n")):
        line = raw.rstrip()
        stripped = line.strip()
        indent = _indent(line)
        ln = i + 1

        if not stripped:
            tokens.append(Token(T_BLANK, line_num=ln))
            continue
        if stripped.startswith("--"):
            tokens.append(Token(T_COMMENT, value=stripped[2:].strip(), line_num=ln))
            continue

        # Headers
        m = re.match(r'^ANIMBP:\s*(\S+)', stripped)
        if m: tokens.append(Token(T_HEADER, name=m.group(1), line_num=ln)); continue

        m = re.match(r'^SKELETON:\s*(.+)', stripped)
        if m: tokens.append(Token(T_SKELETON, value=m.group(1).strip(), line_num=ln)); continue

        m = re.match(r'^MESH:\s*(.+)', stripped)
        if m: tokens.append(Token(T_MESH, value=m.group(1).strip(), line_num=ln)); continue

        if stripped == "VARIABLES:":
            tokens.append(Token(T_VARIABLES, line_num=ln)); continue

        m = re.match(r'^STATE_MACHINE:\s*(\S+)', stripped)
        if m: tokens.append(Token(T_STATE_MACHINE, indent=indent, name=m.group(1), line_num=ln)); continue

        m = re.match(r'^STATE:\s*(\S+)\s*(.*)', stripped)
        if m:
            tokens.append(Token(T_STATE, indent=indent, name=m.group(1),
                                properties=_parse_props(m.group(2)), line_num=ln)); continue

        m = re.match(r'^TRANSITION:\s*(\S+)\s*->\s*(\S+)\s*(.*)', stripped, re.UNICODE)
        if not m:
            m = re.match(r'^TRANSITION:\s*(\S+)\s*→\s*(\S+)\s*(.*)', stripped, re.UNICODE)
        if m:
            tokens.append(Token(T_TRANSITION, indent=indent, name=f"{m.group(1)}->{m.group(2)}",
                                key=m.group(1), value=m.group(2),
                                properties=_parse_props(m.group(3)), line_num=ln)); continue

        m = re.match(r'^BLEND_SPACE:\s*(\S+)\s*(.*)', stripped)
        if m:
            tokens.append(Token(T_BLEND_SPACE, indent=indent, name=m.group(1),
                                properties=_parse_props(m.group(2)), line_num=ln)); continue

        m = re.match(r'^LAYER:\s*(\S+)\s*(.*)', stripped)
        if m:
            tokens.append(Token(T_LAYER, indent=indent, name=m.group(1),
                                properties=_parse_props(m.group(2)), line_num=ln)); continue

        m = re.match(r'^MONTAGE:\s*(\S+)\s*(.*)', stripped)
        if m:
            tokens.append(Token(T_MONTAGE, indent=indent, name=m.group(1),
                                properties=_parse_props(m.group(2)), line_num=ln)); continue

        m = re.match(r'^AIM_OFFSET:\s*(\S+)\s*(.*)', stripped)
        if m:
            tokens.append(Token(T_AIM_OFFSET, indent=indent, name=m.group(1),
                                properties=_parse_props(m.group(2)), line_num=ln)); continue

        m = re.match(r'^SAMPLE:\s*(.*)', stripped)
        if m:
            tokens.append(Token(T_SAMPLE, indent=indent, properties=_parse_props(m.group(1)),
                                line_num=ln)); continue

        # @property
        m = re.match(r'^@(\w+)\s*[=:]\s*(.+)', stripped)
        if m:
            tokens.append(Token(T_PROPERTY, indent=indent, key=m.group(1),
                                value=m.group(2).strip(), line_num=ln)); continue

        # Variable declaration: VarName: Type = Default
        m = re.match(r'^(\w+)\s*:\s*(\w+)\s*(?:=\s*(.+))?', stripped)
        if m and indent >= 1:
            tokens.append(Token(T_VAR_DECL, indent=indent, name=m.group(1),
                                key=m.group(2), value=m.group(3) or "", line_num=ln)); continue

        tokens.append(Token(T_COMMENT, value=f"[unknown] {stripped}", line_num=ln))

    return tokens
