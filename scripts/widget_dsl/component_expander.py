"""
Widget DSL v2 Component Expander — inflates component IDs into full widget subtrees.

Loads component JSON files, expands COMPONENTS: block entries,
applies anchor/offset/option overrides, and merges under the root.
"""

import json
import os
import copy
from typing import Dict, List, Optional

_COMPONENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "widget_components")


def _load_component(component_id: str) -> Optional[dict]:
    """Load a component JSON by ID."""
    path = os.path.join(_COMPONENTS_DIR, f"{component_id}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _count_nodes(node: dict) -> int:
    """Count total nodes in a tree."""
    count = 1
    for c in node.get("children", []):
        count += _count_nodes(c)
    return count


def _convert_tree(comp_tree: dict) -> dict:
    """Convert a component JSON tree node to the parser's node format."""
    node = {
        "type": comp_tree.get("type", "CANVAS"),
        "name": comp_tree.get("name", "Unknown"),
        "properties": dict(comp_tree.get("properties", {})),
        "children": [],
        "animations": list(comp_tree.get("animations", [])),
        "bindings": [],
    }

    # Extract BIND: from properties
    for k, v in list(node["properties"].items()):
        if isinstance(v, str) and v.startswith("BIND:"):
            node["bindings"].append({"property": k, "expression": v[5:]})

    # Process children recursively
    for child in comp_tree.get("children", []):
        node["children"].append(_convert_tree(child))

    return node


def _apply_overrides(node: dict, overrides: dict):
    """Apply property overrides from DSL to the expanded component."""
    for k, v in overrides.items():
        if k.startswith("@"):
            k = k[1:]  # strip @ prefix
        node["properties"][k] = v


def expand_component(component_id: str, overrides: dict = None) -> Optional[dict]:
    """Expand a single component ID into a full widget subtree node.

    Args:
        component_id: e.g. "health_bar", "score_panel"
        overrides: property overrides from DSL (anchor, offset, options, etc.)

    Returns:
        A widget tree node dict, or None if component not found.
    """
    comp = _load_component(component_id)
    if not comp:
        return None

    tree = _convert_tree(comp["tree"])

    # Apply default anchor/offset as properties on the root node of the component
    tree["properties"]["anchor"] = comp.get("default_anchor", "TopLeft")
    off = comp.get("default_offset", [0, 0])
    tree["properties"]["offset_x"] = str(off[0])
    tree["properties"]["offset_y"] = str(off[1])
    sz = comp.get("default_size", [0, 0])
    if sz[0]:
        tree["properties"]["size_x"] = str(sz[0])
    if sz[1]:
        tree["properties"]["size_y"] = str(sz[1])

    # Apply user overrides
    if overrides:
        _apply_overrides(tree, overrides)

    return tree


def expand_components_block(entries: List[dict]) -> List[dict]:
    """Expand a list of COMPONENT_ENTRY tokens into widget subtree nodes.

    Args:
        entries: List of dicts with keys: name (component_id), properties (overrides)

    Returns:
        List of expanded widget tree nodes.
    """
    expanded = []
    for entry in entries:
        comp_id = entry.get("widget_type", entry.get("name", "")).lower()
        # Also accept the component_id directly from the name field
        if not _load_component(comp_id):
            comp_id = entry.get("name", "").lower()

        overrides = entry.get("properties", {})
        node = expand_component(comp_id, overrides)
        if node:
            expanded.append(node)
    return expanded


def get_component_variables(component_id: str) -> List[dict]:
    """Get the variable manifest for a component."""
    comp = _load_component(component_id)
    if not comp:
        return []
    return comp.get("variables", [])


def list_components() -> Dict[str, List[str]]:
    """List all available components by category."""
    index_path = os.path.join(_COMPONENTS_DIR, "component_index.json")
    if os.path.isfile(index_path):
        with open(index_path, "r") as f:
            return json.load(f)
    return {}
