"""AI Perception DSL Parser."""
from .lexer import Token
from typing import List

def parse(tokens: List[Token]) -> dict:
    result = {"name": "APC_Untitled", "properties": {}, "senses": [], "team": {}}
    current = None
    for tok in tokens:
        if tok.type == "HEADER": result["name"] = tok.name
        elif tok.type == "SENSE":
            current = {"type": tok.name, "properties": {}}; result["senses"].append(current)
        elif tok.type == "TEAM": current = result["team"]
        elif tok.type == "PROPERTY":
            if current is not None:
                if isinstance(current, dict) and "properties" in current: current["properties"][tok.key] = tok.value
                elif isinstance(current, dict): current[tok.key] = tok.value
            else: result["properties"][tok.key] = tok.value
    return result
