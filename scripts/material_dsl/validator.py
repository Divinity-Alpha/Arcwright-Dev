"""Material DSL Validator."""
from .lexer import VALID_TYPES

def validate(tree: dict) -> dict:
    errors, warnings = [], []
    if not tree.get("name") or tree["name"] == "M_Untitled":
        warnings.append("Missing MATERIAL: header")
    node_names = {n["name"] for n in tree.get("nodes", [])}
    for n in tree.get("nodes", []):
        if n["type"] not in VALID_TYPES:
            errors.append(f"Unknown node type: {n['type']}")
        # Check connections reference existing nodes
        for k, v in n.get("properties", {}).items():
            if k in ("A", "B", "Alpha") and "." in v:
                ref = v.split(".")[0]
                if ref not in node_names:
                    errors.append(f"Node '{n['name']}' references unknown node '{ref}' in @{k}")
    for pin, ref in tree.get("outputs", {}).items():
        ref_name = ref.split(".")[0] if "." in ref else ref
        if ref_name not in node_names:
            errors.append(f"OUTPUT @{pin} references unknown node '{ref_name}'")
    return {"errors": errors, "warnings": warnings}
