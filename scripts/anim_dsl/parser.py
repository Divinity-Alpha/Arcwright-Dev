"""Animation DSL Parser — builds structured representation from tokens."""

from typing import List, Dict
from .lexer import (Token, T_HEADER, T_SKELETON, T_MESH, T_STATE_MACHINE, T_STATE,
                    T_TRANSITION, T_BLEND_SPACE, T_LAYER, T_MONTAGE, T_AIM_OFFSET,
                    T_VARIABLES, T_VAR_DECL, T_PROPERTY, T_SAMPLE, T_BLANK, T_COMMENT)


def parse(tokens: List[Token]) -> dict:
    result = {
        "name": "ABP_Untitled",
        "skeleton": "",
        "mesh": "",
        "state_machines": [],
        "blend_spaces": [],
        "layers": [],
        "montages": [],
        "aim_offsets": [],
        "variables": [],
    }

    current_sm = None
    current_element = None  # last state/blend_space/montage/aim_offset for attaching properties

    for tok in tokens:
        if tok.type in (T_BLANK, T_COMMENT):
            continue

        if tok.type == T_HEADER:
            result["name"] = tok.name
        elif tok.type == T_SKELETON:
            result["skeleton"] = tok.value
        elif tok.type == T_MESH:
            result["mesh"] = tok.value

        elif tok.type == T_STATE_MACHINE:
            current_sm = {"name": tok.name, "states": [], "transitions": []}
            result["state_machines"].append(current_sm)
            current_element = current_sm

        elif tok.type == T_STATE:
            state = {"name": tok.name, "properties": dict(tok.properties), "samples": []}
            if current_sm:
                current_sm["states"].append(state)
            current_element = state

        elif tok.type == T_TRANSITION:
            trans = {"from": tok.key, "to": tok.value, "properties": dict(tok.properties)}
            if current_sm:
                current_sm["transitions"].append(trans)
            current_element = trans

        elif tok.type == T_BLEND_SPACE:
            bs = {"name": tok.name, "properties": dict(tok.properties), "samples": []}
            result["blend_spaces"].append(bs)
            current_element = bs

        elif tok.type == T_LAYER:
            layer = {"name": tok.name, "properties": dict(tok.properties)}
            result["layers"].append(layer)
            current_element = layer

        elif tok.type == T_MONTAGE:
            mon = {"name": tok.name, "properties": dict(tok.properties), "notifies": []}
            result["montages"].append(mon)
            current_element = mon

        elif tok.type == T_AIM_OFFSET:
            ao = {"name": tok.name, "properties": dict(tok.properties), "samples": []}
            result["aim_offsets"].append(ao)
            current_element = ao

        elif tok.type == T_SAMPLE:
            if current_element and "samples" in current_element:
                current_element["samples"].append(tok.properties)

        elif tok.type == T_VARIABLES:
            current_element = None  # variables block

        elif tok.type == T_VAR_DECL:
            result["variables"].append({
                "name": tok.name, "type": tok.key, "default": tok.value
            })

        elif tok.type == T_PROPERTY:
            if current_element and "properties" in current_element:
                current_element["properties"][tok.key] = tok.value

    return result
