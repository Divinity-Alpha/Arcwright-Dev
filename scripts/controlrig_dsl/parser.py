"""Parser for controlrig_dsl."""
from .lexer import Token
from typing import List

def parse(tokens: List[Token]) -> dict:
    result = {"name": "Untitled", "properties": {}, "elements": []}
    current = None
    for tok in tokens:
        if tok.type == "HEADER": result["name"] = tok.name
        elif tok.type == "PROPERTY":
            if current and "properties" in current: current["properties"][tok.key] = tok.value
            else: result["properties"][tok.key] = tok.value
        elif tok.type not in ("HEADER", "PROPERTY"):
            current = {"type": tok.type, "name": tok.name, "properties": {}}
            result["elements"].append(current)
    return result
