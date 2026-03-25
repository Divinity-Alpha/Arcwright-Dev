"""
Widget DSL v2 Command Generator — converts the resolved tree to Arcwright TCP commands.

Walks the tree depth-first, generating:
  create_widget_blueprint (once)
  add_widget_child (per widget)
  set_widget_property (per property)
  set_widget_anchor (per positioned widget)
  set_widget_binding (per binding)
  create_widget_animation (per animation)
"""

from typing import List, Dict, Any


# Map DSL widget types to UE widget class names
_TYPE_MAP = {
    "CANVAS": "CanvasPanel",
    "VBOX": "VerticalBox",
    "HBOX": "HorizontalBox",
    "OVERLAY": "Overlay",
    "SIZEBOX": "SizeBox",
    "GRID": "UniformGridPanel",
    "TEXT": "TextBlock",
    "IMAGE": "Image",
    "PROGRESS_BAR": "ProgressBar",
    "BUTTON": "Button",
    "SPACER": "Spacer",
    "BORDER": "Border",
    "INPUT": "EditableText",
    "CHECKBOX": "CheckBox",
    "SLIDER": "Slider",
    "SCROLLBOX": "ScrollBox",
}

# Properties handled by set_widget_property (vs. anchor/binding)
_ANCHOR_PROPS = {"anchor", "offset_x", "offset_y", "size_x", "size_y"}
_LAYOUT_PROPS = {"padding", "padding_left", "padding_right", "padding_top", "padding_bottom", "margin"}
_SKIP_PROPS = {"hidden"}  # handled by visible

# ── DSL name → Arcwright TCP property name mapping ────────────────
# The Arcwright TCP server uses specific property names (case-sensitive).
# DSL authors may use friendlier names. This maps common DSL conventions
# to the exact strings Arcwright expects.
_PROPERTY_NAME_MAP = {
    # Border properties
    "background":       "BrushColor",       # DSL 'background' → TCP 'BrushColor'
    "Background":       "BrushColor",
    "brush_color":      "BrushColor",
    "draw_type":        "Brush.DrawType",
    "DrawType":         "Brush.DrawType",
    # TextBlock properties
    "font_size":        "Font.Size",        # DSL 'font_size' → TCP 'Font.Size'
    "FontSize":         "Font.Size",
    "font_family":      "Font.Family",
    "font_typeface":    "Font.Typeface",
    "letter_spacing":   "Font.LetterSpacing",
    "color":            "ColorAndOpacity",   # DSL 'color' → TCP 'ColorAndOpacity'
    "auto_wrap":        "AutoWrapText",
    "wrap_text":        "AutoWrapText",
    "wrap":             "AutoWrapText",
    # Slot properties (VBox/HBox children)
    "fill_height":      "Slot.FillHeight",
    "fill_width":       "Slot.FillWidth",
    "slot_padding":     "Slot.Padding",
    "h_align":          "Slot.HAlign",
    "v_align":          "Slot.VAlign",
    # Anchor properties (CanvasPanel children — resolution independence)
    "anchor_min_x":     "Slot.Anchors.Min.X",
    "anchor_min_y":     "Slot.Anchors.Min.Y",
    "anchor_max_x":     "Slot.Anchors.Max.X",
    "anchor_max_y":     "Slot.Anchors.Max.Y",
    "offset_left":      "Slot.Offsets.Left",
    "offset_top":       "Slot.Offsets.Top",
    "offset_right":     "Slot.Offsets.Right",
    "offset_bottom":    "Slot.Offsets.Bottom",
    "slot_position_x":  "Slot.Position.X",
    "slot_position_y":  "Slot.Position.Y",
    "slot_size_x":      "Slot.Size.X",
    "slot_size_y":      "Slot.Size.Y",
    "auto_size":        "Slot.AutoSize",
}


def _cmd(command: str, params: dict) -> dict:
    return {"command": command, "params": params}


def _generate_node(node: dict, parent_name: str, widget_bp: str, commands: List[dict]):
    """Generate commands for a single node and recurse into children."""
    wtype = node["type"]
    wname = node["name"]
    ue_type = _TYPE_MAP.get(wtype, wtype)

    # add_widget_child — matches TCP API param names
    if parent_name:
        commands.append(_cmd("add_widget_child", {
            "widget_blueprint": widget_bp,
            "parent_widget": parent_name,
            "widget_type": ue_type,
            "widget_name": wname,
        }))

    # set_widget_property for each non-anchor property
    for prop_key, prop_val in node.get("properties", {}).items():
        if prop_key in _ANCHOR_PROPS:
            continue  # handled below
        if prop_key in _SKIP_PROPS:
            continue
        # Map DSL property names to Arcwright TCP property names
        tcp_prop = _PROPERTY_NAME_MAP.get(prop_key, prop_key)
        commands.append(_cmd("set_widget_property", {
            "widget_blueprint": widget_bp,
            "widget_name": wname,
            "property": tcp_prop,
            "value": prop_val,
        }))

    # set_widget_anchor for positioning
    anchor_props = {k: v for k, v in node.get("properties", {}).items() if k in _ANCHOR_PROPS}
    if anchor_props:
        params = {"widget_blueprint": widget_bp, "widget_name": wname}
        params.update(anchor_props)
        commands.append(_cmd("set_widget_anchor", params))

    # set_widget_binding for each binding
    for binding in node.get("bindings", []):
        expr = binding.get("expression", "")
        # Extract first variable name from expression
        import re as _re
        vars_found = _re.findall(r'[A-Za-z_]\w*', expr.replace("{", "").replace("}", ""))
        var_name = vars_found[0] if vars_found else expr
        # Infer type from property
        prop = binding.get("property", "")
        var_type = "Float" if prop in ("percent", "opacity") else "String"
        commands.append(_cmd("set_widget_binding", {
            "widget_blueprint": widget_bp,
            "widget_name": wname,
            "property": prop,
            "variable_name": var_name,
            "variable_type": var_type,
        }))

    # create_widget_animation for each animation
    for anim in node.get("animations", []):
        commands.append(_cmd("create_widget_animation", {
            "widget_blueprint": widget_bp,
            "widget_name": wname,
            "trigger": anim.get("trigger", ""),
            "anim_type": anim.get("type", anim.get("raw", "")),
            "params": anim.get("params", {}),
        }))

    # Recurse into children
    for child in node.get("children", []):
        _generate_node(child, wname, widget_bp, commands)


def generate(tree: dict, variables: list = None) -> List[dict]:
    """Generate the ordered list of TCP commands from a resolved widget tree.

    Args:
        tree: Output from theme_resolver.resolve()
        variables: Output from binding_extractor.extract() (optional)

    Returns:
        List of {"command": "...", "params": {...}} dicts ready for TCP send.
    """
    commands: List[dict] = []
    widget_bp = tree["widget_name"]
    root = tree["root"]

    # Step 1: create_widget_blueprint
    commands.append(_cmd("create_widget_blueprint", {"name": widget_bp}))

    # Step 2: Create the root CanvasPanel (WBP needs a panel root to add children to)
    root_type = _TYPE_MAP.get(root["type"], "CanvasPanel")
    commands.append(_cmd("add_widget_child", {
        "widget_blueprint": widget_bp,
        "widget_type": root_type,
        "widget_name": "RootPanel",
    }))

    # Step 3: Walk tree depth-first — all children go under RootPanel
    for child in root.get("children", []):
        _generate_node(child, "RootPanel", widget_bp, commands)

    # If root has properties, set them on "Root"
    for prop_key, prop_val in root.get("properties", {}).items():
        if prop_key not in _ANCHOR_PROPS and prop_key not in _SKIP_PROPS:
            tcp_prop = _PROPERTY_NAME_MAP.get(prop_key, prop_key)
            commands.append(_cmd("set_widget_property", {
                "widget_blueprint": widget_bp,
                "widget_name": "Root",
                "property": tcp_prop,
                "value": prop_val,
            }))

    return commands
