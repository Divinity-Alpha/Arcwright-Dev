"""GAS DSL Validator."""
from typing import List, Dict

def validate(tree: dict) -> Dict[str, List[str]]:
    errors, warnings = [], []

    # Collect all attribute names
    attr_names = set()
    for aset in tree.get("attribute_sets", []):
        for attr in aset.get("attributes", []):
            attr_names.add(attr["name"])

    if not attr_names:
        warnings.append("No attribute set defined")

    # Check abilities
    for ability in tree.get("abilities", []):
        props = ability.get("properties", {})
        # Check cost attribute exists
        cost_attr = props.get("cost_attribute", "")
        if cost_attr and cost_attr not in attr_names:
            errors.append(f"Ability '{ability['name']}' cost_attribute '{cost_attr}' not in attribute set")
        # Check tag format
        tags = props.get("tags", "")
        for tag in tags.split(","):
            tag = tag.strip()
            if tag and not all(c.isalnum() or c in "._" for c in tag):
                warnings.append(f"Ability '{ability['name']}' tag '{tag}' has invalid characters")
        # Check effects
        for effect in ability.get("effects", []):
            for mod in effect.get("modifiers", []):
                mp = mod.get("properties", {})
                mod_attr = mp.get("attribute", "")
                if mod_attr and mod_attr not in attr_names:
                    errors.append(f"Effect '{effect['name']}' modifier targets '{mod_attr}' not in attribute set")
                scale_attr = mp.get("scale_attribute", "")
                if scale_attr and scale_attr not in attr_names:
                    errors.append(f"Effect '{effect['name']}' scale_attribute '{scale_attr}' not in attribute set")

    return {"errors": errors, "warnings": warnings}
