"""GAS DSL Parser."""
from typing import List
from .lexer import Token

def parse(tokens: List[Token]) -> dict:
    result = {"name": "GAS_Untitled", "properties": {}, "attribute_sets": [], "abilities": [], "effect_presets": []}
    current_set = None; current_attr = None; current_ability = None
    current_effect = None; current_modifier = None

    for tok in tokens:
        if tok.type == "SYSTEM":
            result["name"] = tok.name
        elif tok.type == "ATTR_SET":
            current_set = {"name": tok.name, "attributes": []}
            result["attribute_sets"].append(current_set)
            current_ability = None; current_effect = None
        elif tok.type == "ATTRIBUTE":
            current_attr = {"name": tok.name, "properties": {}}
            if current_set: current_set["attributes"].append(current_attr)
            current_effect = None; current_modifier = None
        elif tok.type == "ABILITY":
            current_ability = {"name": tok.name, "properties": {}, "effects": []}
            result["abilities"].append(current_ability)
            current_set = None; current_attr = None; current_effect = None
        elif tok.type == "EFFECT":
            current_effect = {"name": tok.name, "properties": {}, "modifiers": []}
            if current_ability: current_ability["effects"].append(current_effect)
            current_modifier = None
        elif tok.type == "EFFECT_PRESET":
            current_effect = {"name": tok.name, "properties": {}, "modifiers": []}
            result["effect_presets"].append(current_effect)
            current_ability = None; current_set = None; current_modifier = None
        elif tok.type == "PROPERTY":
            k, v = tok.key, tok.value
            # Modifier sub-properties (under @modifier line)
            if k == "modifier":
                current_modifier = {"name": v, "properties": {}}
                if current_effect: current_effect["modifiers"].append(current_modifier)
            elif current_modifier and k in ("attribute", "operation", "magnitude", "scale_attribute", "scale_factor"):
                current_modifier["properties"][k] = v
            elif current_effect and tok.indent >= 2:
                current_effect["properties"][k] = v
            elif current_attr and tok.indent >= 2:
                current_attr["properties"][k] = v
            elif current_ability:
                current_ability["properties"][k] = v
            elif current_set is None and current_ability is None:
                result["properties"][k] = v
    return result
