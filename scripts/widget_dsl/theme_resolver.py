"""
Widget DSL v2 Theme Resolver — loads theme JSON and resolves $ references.

Resolves $primary, $accent, $panel_bg, $heading etc. in all properties.
Handles $color:opacity syntax (e.g., $primary:0.5).
Falls back to Normal theme for missing values.
"""

import json
import os
import re
from typing import Dict, Any, Optional


_THEMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "widget_themes")


def _load_theme(name: str) -> dict:
    """Load a theme JSON file by name."""
    path = os.path.join(_THEMES_DIR, f"{name.lower()}.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_lookup(theme: dict, palette: dict) -> dict:
    """Build a flat $ -> value lookup from theme colors + palette overrides."""
    lookup = {}

    # Theme colors
    colors = theme.get("colors", {})
    for k, v in colors.items():
        lookup[k] = v

    # Theme fonts (as $heading, $body, $mono etc.)
    fonts = theme.get("fonts", {})
    for k, v in fonts.items():
        if isinstance(v, dict):
            lookup[k] = v  # keep as dict for font objects
        else:
            lookup[k] = v

    # User palette overrides (highest priority)
    for k, v in palette.items():
        lookup[k] = v

    return lookup


def _apply_opacity(color: str, opacity: str) -> str:
    """Apply opacity to a hex color. Returns rgba string or modified hex."""
    try:
        alpha = float(opacity)
    except ValueError:
        return color

    # Parse hex color
    color = color.strip().lstrip("#")
    if len(color) == 6:
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    return color


def _resolve_value(value: str, lookup: dict) -> str:
    """Resolve a single value that may contain $ references."""
    if not isinstance(value, str) or "$" not in value:
        return value

    # $name:opacity pattern
    m = re.match(r'^\$(\w+):([\d.]+)$', value)
    if m:
        name, opacity = m.group(1), m.group(2)
        base = lookup.get(name, value)
        if isinstance(base, str):
            return _apply_opacity(base, opacity)
        return value

    # Simple $name reference
    m = re.match(r'^\$(\w+)$', value)
    if m:
        name = m.group(1)
        resolved = lookup.get(name, value)
        return resolved if isinstance(resolved, str) else value

    # Inline references within a larger string: "... $name ..."
    def _repl(match):
        name = match.group(1)
        return str(lookup.get(name, match.group(0)))

    return re.sub(r'\$(\w+)', _repl, value)


def _resolve_node(node: dict, lookup: dict):
    """Recursively resolve all $ references in a widget node's properties."""
    for k, v in list(node["properties"].items()):
        if isinstance(v, str):
            node["properties"][k] = _resolve_value(v, lookup)

    for binding in node.get("bindings", []):
        if "expression" in binding and isinstance(binding["expression"], str):
            binding["expression"] = _resolve_value(binding["expression"], lookup)

    for child in node.get("children", []):
        _resolve_node(child, lookup)


def resolve(tree: dict) -> dict:
    """Resolve all theme/palette references in the parsed widget tree.

    Args:
        tree: Output from parser.parse() — {widget_name, theme, palette, root}

    Returns:
        The same tree with all $references replaced by concrete values.
    """
    theme_name = tree.get("theme", "Normal")
    user_palette = tree.get("palette", {})

    # Load theme, fall back to Normal
    theme_data = _load_theme(theme_name)
    if not theme_data and theme_name.lower() != "normal":
        theme_data = _load_theme("Normal")

    lookup = _build_lookup(theme_data, user_palette)

    # Store resolved theme metadata on tree
    tree["_theme_data"] = theme_data
    tree["_lookup"] = lookup

    # Resolve the root node recursively
    _resolve_node(tree["root"], lookup)

    return tree
