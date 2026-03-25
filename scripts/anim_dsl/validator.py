"""Animation DSL Validator — checks syntax, references, and structure."""

from typing import List, Dict


def validate(tree: dict) -> Dict[str, List[str]]:
    errors = []
    warnings = []

    if not tree.get("name") or tree["name"] == "ABP_Untitled":
        warnings.append("Missing ANIMBP: header")
    if not tree.get("skeleton"):
        errors.append("Missing SKELETON: declaration")

    # Check state machines
    for sm in tree.get("state_machines", []):
        state_names = {s["name"] for s in sm.get("states", [])}
        if not state_names:
            warnings.append(f"State machine '{sm['name']}' has no states")

        # Check transitions reference existing states
        for trans in sm.get("transitions", []):
            if trans["from"] not in state_names:
                errors.append(f"Transition from '{trans['from']}' — state not found in '{sm['name']}'")
            if trans["to"] not in state_names:
                errors.append(f"Transition to '{trans['to']}' — state not found in '{sm['name']}'")

        # Check at least one state has entry property or is first
        has_entry = any(s.get("properties", {}).get("entry") == "true" for s in sm.get("states", []))
        if not has_entry and sm.get("states"):
            warnings.append(f"No entry state in '{sm['name']}' — first state will be used")

    # Check blend spaces have samples
    for bs in tree.get("blend_spaces", []):
        if not bs.get("samples"):
            warnings.append(f"Blend space '{bs['name']}' has no samples")

    # Check montages have animation
    for mon in tree.get("montages", []):
        if not mon.get("properties", {}).get("animation"):
            warnings.append(f"Montage '{mon['name']}' has no @animation")

    return {"errors": errors, "warnings": warnings}
