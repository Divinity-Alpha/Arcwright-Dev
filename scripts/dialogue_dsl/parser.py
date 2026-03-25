"""Dialogue DSL Parser — builds dialogue tree from tokens."""
import json
from typing import List
from .lexer import Token

def parse(tokens: List[Token]) -> dict:
    result = {"name": "DLG_Untitled", "properties": {}, "nodes": []}
    current_node = None
    current_choice = None

    for tok in tokens:
        if tok.type == "HEADER":
            result["name"] = tok.name
        elif tok.type == "NODE":
            current_node = {"id": tok.name, "speaker": "", "text": "", "choices": [],
                           "conditions": [], "actions": [], "next": "", "flags": []}
            result["nodes"].append(current_node)
            current_choice = None
        elif tok.type == "CHOICE":
            if current_node is not None:
                current_choice = {"text": tok.value, "next": "", "condition": ""}
                current_node["choices"].append(current_choice)
        elif tok.type == "PROPERTY":
            target = current_choice if current_choice and tok.indent >= 2 else current_node
            if target is None:
                result["properties"][tok.key] = tok.value
                continue
            k, v = tok.key, tok.value
            if k == "speaker": target["speaker"] = v if isinstance(target, dict) and "speaker" in target else v
            elif k == "text": target["text"] = v
            elif k == "next":
                if current_choice and tok.indent >= 2: current_choice["next"] = v
                elif current_node: current_node["next"] = v
            elif k == "condition":
                if current_choice and tok.indent >= 2: current_choice["condition"] = v
                elif current_node: current_node["conditions"].append(v)
            elif k == "set_flag" and current_node: current_node["flags"].append(v)
            elif k == "action" and current_node: current_node["actions"].append(v)
            elif k in ("speaker_default", "portrait"):
                result["properties"][k] = v
    return result
