"""Quest DSL Parser."""
from typing import List
from .lexer import Token

def parse(tokens: List[Token]) -> dict:
    result = {"id": "Q_Untitled", "properties": {}, "stages": [], "on_complete": [], "on_abandon": []}
    current_stage = None
    current_obj = None
    section = "quest"  # quest / on_complete / on_abandon

    for tok in tokens:
        if tok.type == "QUEST":
            result["id"] = tok.name; section = "quest"
        elif tok.type == "STAGE":
            current_stage = {"id": tok.name, "properties": {}, "objectives": []}
            result["stages"].append(current_stage)
            current_obj = None; section = "quest"
        elif tok.type == "OBJECTIVE":
            current_obj = {"id": tok.name, "properties": {}}
            if current_stage: current_stage["objectives"].append(current_obj)
        elif tok.type == "ON_COMPLETE":
            section = "on_complete"; current_stage = None; current_obj = None
        elif tok.type == "ON_ABANDON":
            section = "on_abandon"; current_stage = None; current_obj = None
        elif tok.type == "PROPERTY":
            if section == "on_complete":
                result["on_complete"].append({"key": tok.key, "value": tok.value})
            elif section == "on_abandon":
                result["on_abandon"].append({"key": tok.key, "value": tok.value})
            elif current_obj and tok.indent >= 2:
                current_obj["properties"][tok.key] = tok.value
            elif current_stage and tok.indent >= 1:
                current_stage["properties"][tok.key] = tok.value
            else:
                result["properties"][tok.key] = tok.value
    return result
