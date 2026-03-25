"""
Widget DSL v2 Validator — validates the parsed tree before execution.

Checks widget types, properties, anchors, theme refs, bindings.
Returns list of errors and warnings.
"""

from typing import List, Dict
from .lexer import WIDGET_TYPES


# Valid anchor presets
VALID_ANCHORS = {
    "TopLeft", "TopCenter", "TopRight",
    "CenterLeft", "Center", "CenterRight",
    "BottomLeft", "BottomCenter", "BottomRight",
    "FillX", "FillY", "Fill",
    "TopFill", "BottomFill", "LeftFill", "RightFill",
}

# Valid properties per widget type (common + type-specific)
_COMMON_PROPS = {
    "anchor", "offset_x", "offset_y", "size_x", "size_y",
    "padding", "padding_left", "padding_right", "padding_top", "padding_bottom",
    "margin", "opacity", "visible", "hidden", "tooltip", "clipping",
    "color", "background", "render_transform",
}

_TYPE_PROPS = {
    "TEXT": {"text", "font", "font_size", "bold", "italic", "wrap", "justification",
             "auto_size", "shadow", "outline", "letter_spacing", "line_height"},
    "IMAGE": {"texture", "tint", "size_x", "size_y", "match_size"},
    "PROGRESS_BAR": {"percent", "fill_color", "bar_color", "fill_type", "bar_style"},
    "BUTTON": {"text", "font_size", "on_click", "style", "normal_color", "hovered_color", "pressed_color"},
    "INPUT": {"hint", "font_size", "max_length", "is_password"},
    "CHECKBOX": {"checked", "label", "check_color"},
    "SLIDER": {"value", "min", "max", "step", "bar_color", "handle_color"},
    "SPACER": {"size_x", "size_y"},
    "CANVAS": {"size_x", "size_y"},
    "VBOX": {"spacing"},
    "HBOX": {"spacing"},
    "OVERLAY": set(),
    "SIZEBOX": {"width_override", "height_override", "min_width", "min_height",
                "max_width", "max_height"},
    "GRID": {"columns", "row_spacing", "col_spacing"},
    "BORDER": {"border_color", "border_width", "corner_radius", "background"},
    "SCROLLBOX": {"orientation", "bar_visibility"},
}

# Leaf widgets that can't have children
_LEAF = {"TEXT", "IMAGE", "PROGRESS_BAR", "SPACER", "INPUT", "CHECKBOX", "SLIDER"}


def _validate_node(node: dict, errors: list, warnings: list, palette: dict, depth: int = 0):
    """Recursively validate a widget node."""
    wtype = node.get("type", "")
    wname = node.get("name", "?")

    # Check widget type
    if wtype not in WIDGET_TYPES:
        errors.append(f"Unknown widget type '{wtype}' on '{wname}'")

    # Check properties
    valid_props = _COMMON_PROPS | _TYPE_PROPS.get(wtype, set())
    for prop_key in node.get("properties", {}):
        if prop_key not in valid_props:
            warnings.append(f"Unknown property '{prop_key}' on {wtype} '{wname}'")

    # Check anchor values
    anchor = node["properties"].get("anchor", "")
    if anchor and anchor not in VALID_ANCHORS:
        errors.append(f"Invalid anchor '{anchor}' on '{wname}'. Valid: {', '.join(sorted(VALID_ANCHORS))}")

    # Check $ references in values
    for k, v in node.get("properties", {}).items():
        if isinstance(v, str) and v.startswith("$"):
            ref_name = v.lstrip("$").split(":")[0]
            if ref_name not in palette:
                warnings.append(f"Unresolved theme reference '${ref_name}' in {wname}.{k}")

    # Check leaf widgets have no children
    if wtype in _LEAF and node.get("children"):
        errors.append(f"Leaf widget {wtype} '{wname}' cannot have children (has {len(node['children'])})")

    # Check bindings syntax
    for binding in node.get("bindings", []):
        expr = binding.get("expression", "")
        if not expr:
            errors.append(f"Empty BIND: expression on '{wname}.{binding.get('property', '?')}'")

    # Recurse
    for child in node.get("children", []):
        _validate_node(child, errors, warnings, palette, depth + 1)


def validate(tree: dict) -> Dict[str, List[str]]:
    """Validate the parsed widget tree.

    Returns: {"errors": [...], "warnings": [...]}
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not tree.get("widget_name"):
        errors.append("Missing WIDGET: header (no widget name)")

    palette_keys = set(tree.get("palette", {}).keys())
    # Also include theme lookup keys if resolved
    lookup = tree.get("_lookup", {})
    all_refs = palette_keys | set(lookup.keys())

    _validate_node(tree["root"], errors, warnings, all_refs)

    return {"errors": errors, "warnings": warnings}
