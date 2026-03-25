"""Dialogue DSL Validator."""
from typing import List, Dict

def validate(tree: dict) -> Dict[str, List[str]]:
    errors, warnings = [], []
    node_ids = {n["id"] for n in tree.get("nodes", [])}

    if not tree.get("nodes"):
        errors.append("No dialogue nodes defined")
        return {"errors": errors, "warnings": warnings}

    for node in tree["nodes"]:
        # Check @next targets
        if node["next"] and node["next"] != "END" and node["next"] not in node_ids:
            errors.append(f"Node '{node['id']}' @next references unknown node '{node['next']}'")
        # Check choice targets
        for choice in node.get("choices", []):
            if choice["next"] and choice["next"] != "END" and choice["next"] not in node_ids:
                errors.append(f"Node '{node['id']}' choice '{choice['text'][:20]}' @next references unknown node '{choice['next']}'")
        # Warn on no text
        if not node.get("text"):
            warnings.append(f"Node '{node['id']}' has no @text")

    # Check for orphan nodes (unreachable)
    referenced = set()
    for node in tree["nodes"]:
        if node["next"]: referenced.add(node["next"])
        for c in node.get("choices", []):
            if c["next"]: referenced.add(c["next"])
    first_node = tree["nodes"][0]["id"] if tree["nodes"] else ""
    for node in tree["nodes"]:
        if node["id"] != first_node and node["id"] not in referenced:
            warnings.append(f"Node '{node['id']}' is unreachable (no node points to it)")

    return {"errors": errors, "warnings": warnings}
