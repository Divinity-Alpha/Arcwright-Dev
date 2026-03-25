"""
Widget DSL v2 Binding Extractor — finds all BIND: references and builds a variable manifest.

Walks the tree, extracts variable names, infers types from property context.
Handles format strings: BIND:"{Current}/{Max}" extracts Current and Max.
Handles expressions: BIND:Health/MaxHealth extracts Health and MaxHealth.
"""

import re
from typing import List, Dict, Set


# Property name -> inferred variable type
_TYPE_HINTS = {
    "percent": "Float",
    "opacity": "Float",
    "visible": "Bool",
    "hidden": "Bool",
    "enabled": "Bool",
    "text": "String",
    "color": "String",
    "font_size": "Float",
}


def _infer_type(property_name: str, expression: str) -> str:
    """Infer variable type from the property it's bound to."""
    prop_lower = property_name.lower()
    if prop_lower in _TYPE_HINTS:
        return _TYPE_HINTS[prop_lower]
    # If expression contains / (division), likely Float
    if "/" in expression and not expression.startswith("{"):
        return "Float"
    return "String"


def _extract_var_names(expression: str) -> List[str]:
    """Extract variable names from a binding expression.

    Handles:
        "Health"                -> ["Health"]
        "Health/MaxHealth"      -> ["Health", "MaxHealth"]
        "{Current}/{Max}"       -> ["Current", "Max"]
        "{PlayerName} - Lv{Level}" -> ["PlayerName", "Level"]
    """
    names = []

    # Format string: {VarName} placeholders
    fmt_vars = re.findall(r'\{(\w+)\}', expression)
    if fmt_vars:
        return fmt_vars

    # Expression with operators: split on /+-*
    parts = re.split(r'[/+\-*]', expression)
    for part in parts:
        part = part.strip()
        if part and re.match(r'^[A-Za-z_]\w*$', part):
            names.append(part)

    # Simple variable name
    if not names and re.match(r'^[A-Za-z_]\w*$', expression.strip()):
        names.append(expression.strip())

    return names


def _walk_bindings(node: dict, variables: Dict[str, dict]):
    """Recursively collect bindings from a node and its children."""
    for binding in node.get("bindings", []):
        prop = binding.get("property", "")
        expr = binding.get("expression", "")
        var_names = _extract_var_names(expr)
        for name in var_names:
            if name not in variables:
                variables[name] = {
                    "name": name,
                    "type": _infer_type(prop, expr),
                    "used_by": [],
                }
            variables[name]["used_by"].append({
                "widget": node.get("name", "?"),
                "property": prop,
                "expression": expr,
            })

    for child in node.get("children", []):
        _walk_bindings(child, variables)


def extract(tree: dict) -> List[dict]:
    """Extract all BIND: variables from the widget tree.

    Returns a list of variable manifests:
        [{"name": "Health", "type": "Float", "used_by": [...]}, ...]
    """
    variables: Dict[str, dict] = {}
    _walk_bindings(tree["root"], variables)
    return list(variables.values())
