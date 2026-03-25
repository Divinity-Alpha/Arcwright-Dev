"""GAS DSL Command Generator."""
import json
from typing import List

def _cmd(c, p): return {"command": c, "params": p}

def generate(tree: dict) -> List[dict]:
    commands = []
    system_name = tree["name"]

    # Create GAS system
    commands.append(_cmd("create_ability_system", {
        "name": system_name,
        "owner": tree.get("properties", {}).get("owner", ""),
    }))

    # Attribute sets
    for aset in tree.get("attribute_sets", []):
        for attr in aset.get("attributes", []):
            ap = attr.get("properties", {})
            commands.append(_cmd("add_attribute", {
                "system": system_name,
                "set_name": aset["name"],
                "attribute_name": attr["name"],
                "base": float(ap.get("base", "0")),
                "min": float(ap.get("min", "0")),
                "max": float(ap.get("max", "9999")),
            }))

    # Abilities
    for ability in tree.get("abilities", []):
        ap = ability.get("properties", {})
        commands.append(_cmd("add_ability", {
            "system": system_name,
            "ability_name": ability["name"],
            "display_name": ap.get("display_name", ability["name"]),
            "description": ap.get("description", ""),
            "cooldown": float(ap.get("cooldown", "0")),
            "cost_attribute": ap.get("cost_attribute", ""),
            "cost_amount": float(ap.get("cost_amount", "0")),
            "tags": ap.get("tags", ""),
            "blocked_by": ap.get("blocked_by", ""),
            "input": ap.get("input", ""),
        }))

        # Effects
        for effect in ability.get("effects", []):
            ep = effect.get("properties", {})
            modifiers_json = json.dumps([{
                "name": m["name"],
                "attribute": m["properties"].get("attribute", ""),
                "operation": m["properties"].get("operation", "Add"),
                "magnitude": float(m["properties"].get("magnitude", "0")),
                "scale_attribute": m["properties"].get("scale_attribute", ""),
                "scale_factor": float(m["properties"].get("scale_factor", "1")),
            } for m in effect.get("modifiers", [])])

            commands.append(_cmd("add_ability_effect", {
                "system": system_name,
                "ability_name": ability["name"],
                "effect_name": effect["name"],
                "type": ep.get("type", "Instant"),
                "duration": float(ep.get("duration", "0")),
                "period": float(ep.get("period", "0")),
                "target": ep.get("target", "Enemy"),
                "tags_granted": ep.get("tags_granted", ""),
                "modifiers": modifiers_json,
            }))

    return commands
