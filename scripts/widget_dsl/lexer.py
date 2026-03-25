"""
Widget DSL v2 Lexer — tokenizes Widget DSL text into structured tokens.

Reads each line, calculates indent level (2 spaces = 1 level),
identifies line type, and extracts properties.
"""

import re
from dataclasses import dataclass, field
from typing import List

WIDGET_TYPES = {
    "CANVAS", "VBOX", "HBOX", "OVERLAY", "SIZEBOX", "GRID",
    "TEXT", "IMAGE", "PROGRESS_BAR", "BUTTON", "SPACER",
    "BORDER", "INPUT", "CHECKBOX", "SLIDER", "SCROLLBOX",
}

# Token type constants
T_WIDGET_HEADER = "WIDGET_HEADER"
T_THEME = "THEME"
T_PALETTE = "PALETTE"
T_PALETTE_ENTRY = "PALETTE_ENTRY"
T_WIDGET_DECL = "WIDGET_DECL"
T_PROPERTY = "PROPERTY"
T_ANIM = "ANIM"
T_COMMENT = "COMMENT"
T_COMPONENTS = "COMPONENTS"
T_COMPONENT_ENTRY = "COMPONENT_ENTRY"
T_BLANK = "BLANK"


@dataclass
class Token:
    type: str
    indent: int = 0
    widget_type: str = ""
    name: str = ""
    key: str = ""
    value: str = ""
    raw: str = ""
    line_num: int = 0
    properties: dict = field(default_factory=dict)


def _indent_level(line: str) -> int:
    """Count leading spaces; 2 spaces = 1 indent level."""
    spaces = len(line) - len(line.lstrip(" "))
    return spaces // 2


def _parse_inline_props(text: str) -> dict:
    """Parse inline key=value pairs and bare flags."""
    props = {}
    if not text.strip():
        return props
    # key="quoted value" or key=bare_value
    for m in re.finditer(r'(\w+)\s*=\s*(?:"([^"]*?)"|(\S+))', text):
        props[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    # bare flags
    for w in ("bold", "italic", "hidden", "wrap", "auto_size", "clipping"):
        if re.search(rf'\b{w}\b', text) and w not in props:
            props[w] = "true"
    return props


def tokenize(dsl_text: str) -> List[Token]:
    """Tokenize Widget DSL text into a list of Token objects."""
    tokens: List[Token] = []
    lines = dsl_text.split("\n")
    in_palette = False
    in_components = False

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        stripped = line.strip()
        indent = _indent_level(line)
        ln = i + 1

        if not stripped:
            in_palette = False
            in_components = False
            tokens.append(Token(type=T_BLANK, line_num=ln, raw=raw_line))
            continue

        if stripped.startswith("--"):
            tokens.append(Token(type=T_COMMENT, value=stripped[2:].strip(), line_num=ln, raw=raw_line))
            continue

        # WIDGET: WBP_Name
        m = re.match(r'^WIDGET:\s*(\S+)', stripped)
        if m:
            in_palette = in_components = False
            tokens.append(Token(type=T_WIDGET_HEADER, name=m.group(1), line_num=ln, raw=raw_line))
            continue

        # THEME: ThemeName
        m = re.match(r'^THEME:\s*(\S+)', stripped)
        if m:
            tokens.append(Token(type=T_THEME, value=m.group(1), line_num=ln, raw=raw_line))
            continue

        # PALETTE:
        if stripped == "PALETTE:":
            in_palette = True
            in_components = False
            tokens.append(Token(type=T_PALETTE, line_num=ln, raw=raw_line))
            continue

        # Palette entry: $name = value
        if in_palette and stripped.startswith("$"):
            m = re.match(r'\$(\w+)\s*=\s*(.+)', stripped)
            if m:
                tokens.append(Token(type=T_PALETTE_ENTRY, key=m.group(1), value=m.group(2).strip(),
                                    line_num=ln, raw=raw_line))
                continue

        # COMPONENTS:
        if stripped == "COMPONENTS:":
            in_components = True
            in_palette = False
            tokens.append(Token(type=T_COMPONENTS, line_num=ln, raw=raw_line))
            continue

        # Component entry: Name: TYPE prop=val ...
        if in_components and indent >= 1:
            m = re.match(r'(\w+)\s*:\s*(\w+)\s*(.*)', stripped)
            if m:
                tokens.append(Token(type=T_COMPONENT_ENTRY, indent=indent,
                                    widget_type=m.group(2), name=m.group(1),
                                    properties=_parse_inline_props(m.group(3)),
                                    line_num=ln, raw=raw_line))
                continue

        # @anim:Trigger = Type|params
        m_anim = re.match(r'@anim:(\w+)\s*=\s*(.+)', stripped)
        if m_anim:
            tokens.append(Token(type=T_ANIM, key=m_anim.group(1), value=m_anim.group(2).strip(),
                                indent=indent, line_num=ln, raw=raw_line))
            continue

        # @property: value
        m_prop = re.match(r'@(\w+)\s*:\s*(.+)', stripped)
        if m_prop:
            tokens.append(Token(type=T_PROPERTY, key=m_prop.group(1), value=m_prop.group(2).strip(),
                                indent=indent, line_num=ln, raw=raw_line))
            continue

        # Widget declaration: TYPE Name [inline props]
        m = re.match(r'^(\w+)\s+(\w+)\s*(.*)', stripped)
        if m and m.group(1) in WIDGET_TYPES:
            in_palette = in_components = False
            tokens.append(Token(type=T_WIDGET_DECL, indent=indent,
                                widget_type=m.group(1), name=m.group(2),
                                properties=_parse_inline_props(m.group(3)),
                                line_num=ln, raw=raw_line))
            continue

        # Bare widget type: "CANVAS" alone
        if stripped in WIDGET_TYPES:
            tokens.append(Token(type=T_WIDGET_DECL, indent=indent,
                                widget_type=stripped, name=stripped,
                                line_num=ln, raw=raw_line))
            continue

        # Indented key=value or key: value fallback
        if indent > 0:
            m = re.match(r'(\w+)\s*[=:]\s*(.+)', stripped)
            if m:
                tokens.append(Token(type=T_PROPERTY, key=m.group(1), value=m.group(2).strip(),
                                    indent=indent, line_num=ln, raw=raw_line))
                continue

        # Unknown
        tokens.append(Token(type=T_COMMENT, value=f"[unknown] {stripped}", line_num=ln, raw=raw_line))

    return tokens
