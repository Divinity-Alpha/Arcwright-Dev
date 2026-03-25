"""Physics DSL Parser."""
from .lexer import Token
from typing import List

def parse(tokens: List[Token]) -> dict:
    result = {"name": "PHY_Untitled", "properties": {}, "constraints": [], "destructibles": []}
    current = None
    for tok in tokens:
        if tok.type == "HEADER": result["name"] = tok.name
        elif tok.type == "CONSTRAINT":
            current = {"name": tok.name, "properties": {}}; result["constraints"].append(current)
        elif tok.type == "DESTRUCTIBLE":
            current = {"name": tok.name, "properties": {}, "on_break": []}; result["destructibles"].append(current)
        elif tok.type == "PROPERTY":
            if current and tok.key == "on_break": current.setdefault("on_break",[]).append(tok.value)
            elif current and "properties" in current: current["properties"][tok.key] = tok.value
            else: result["properties"][tok.key] = tok.value
    return result
