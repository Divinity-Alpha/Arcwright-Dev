"""
Widget DSL v2 Parser — builds a widget tree from lexer tokens.

Each node: {type, name, properties, children[], animations[], bindings[]}
Returns:   {widget_name, theme, palette, root_node}
"""

from typing import List, Optional, Dict, Any
from .lexer import (
    Token, T_WIDGET_HEADER, T_THEME, T_PALETTE, T_PALETTE_ENTRY,
    T_WIDGET_DECL, T_PROPERTY, T_ANIM, T_COMMENT, T_COMPONENTS,
    T_COMPONENT_ENTRY, T_BLANK, WIDGET_TYPES,
)

# Widget types that cannot have children
LEAF_WIDGETS = {"TEXT", "IMAGE", "PROGRESS_BAR", "SPACER", "INPUT", "CHECKBOX", "SLIDER"}


def _new_node(widget_type: str, name: str, properties: dict = None) -> dict:
    return {
        "type": widget_type,
        "name": name,
        "properties": dict(properties) if properties else {},
        "children": [],
        "animations": [],
        "bindings": [],
    }


def parse(tokens: List[Token]) -> dict:
    """Parse token list into a widget tree structure."""
    widget_name = "WBP_Untitled"
    theme = "Normal"
    palette: Dict[str, str] = {}
    root_node: Optional[dict] = None

    # Stack for tracking nesting: [(indent_level, node)]
    stack: list = []

    for tok in tokens:
        if tok.type in (T_BLANK, T_COMMENT, T_PALETTE, T_COMPONENTS):
            continue

        if tok.type == T_WIDGET_HEADER:
            widget_name = tok.name
            continue

        if tok.type == T_THEME:
            theme = tok.value
            continue

        if tok.type == T_PALETTE_ENTRY:
            palette[tok.key] = tok.value
            continue

        # COMPONENTS shorthand: each entry is a direct child of root
        if tok.type == T_COMPONENT_ENTRY:
            node = _new_node(tok.widget_type, tok.name, tok.properties)
            # Extract BIND: values from properties
            for k, v in list(tok.properties.items()):
                if isinstance(v, str) and v.startswith("BIND:"):
                    node["bindings"].append({"property": k, "expression": v[5:]})
            if root_node is not None:
                root_node["children"].append(node)
            continue

        if tok.type == T_WIDGET_DECL:
            node = _new_node(tok.widget_type, tok.name, tok.properties)

            # Extract BIND: from inline properties
            for k, v in list(tok.properties.items()):
                if isinstance(v, str) and v.startswith("BIND:"):
                    node["bindings"].append({"property": k, "expression": v[5:]})

            if root_node is None:
                # First widget = root
                root_node = node
                stack = [(tok.indent, node)]
            else:
                # Pop stack to find parent at lower indent
                while stack and stack[-1][0] >= tok.indent:
                    stack.pop()

                if stack:
                    parent = stack[-1][1]
                    parent["children"].append(node)
                else:
                    # Orphan at indent 0 — attach to root
                    root_node["children"].append(node)

                stack.append((tok.indent, node))
            continue

        if tok.type == T_PROPERTY:
            # Attach property to current widget (top of stack)
            if stack:
                current = stack[-1][1]
                val = tok.value
                if val.startswith("BIND:"):
                    current["bindings"].append({"property": tok.key, "expression": val[5:]})
                else:
                    current["properties"][tok.key] = val
            continue

        if tok.type == T_ANIM:
            if stack:
                current = stack[-1][1]
                current["animations"].append({"trigger": tok.key, "raw": tok.value})
            continue

    # If no root was created, make a default canvas
    if root_node is None:
        root_node = _new_node("CANVAS", "Root")

    return {
        "widget_name": widget_name,
        "theme": theme,
        "palette": palette,
        "root": root_node,
    }
