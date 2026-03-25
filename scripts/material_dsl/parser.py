"""Material DSL Parser."""
from typing import List
from .lexer import Token

def parse(tokens: List[Token]) -> dict:
    result = {"name": "M_Untitled", "properties": {}, "nodes": [], "outputs": {}}
    current = None

    for tok in tokens:
        if tok.type == "HEADER":
            result["name"] = tok.name
        elif tok.type == "NODE":
            current = {"type": tok.key, "name": tok.name, "properties": {}}
            result["nodes"].append(current)
        elif tok.type == "OUTPUT":
            current = None  # outputs collect properties below
        elif tok.type == "PROPERTY":
            if current is not None:
                current["properties"][tok.key] = tok.value
            elif tok.key in ("domain","blend_mode","shading_model"):
                result["properties"][tok.key] = tok.value
            else:
                # OUTPUT section properties
                result["outputs"][tok.key] = tok.value
    return result
