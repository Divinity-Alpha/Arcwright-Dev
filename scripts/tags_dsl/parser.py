"""Tags DSL Parser — builds tag hierarchy."""
from .lexer import Token
from typing import List

def parse(tokens: List[Token]) -> dict:
    result = {"name": "GameplayTags", "hierarchies": []}
    current_hier = None
    # Stack: [(indent, path_prefix)]
    stack = []

    for tok in tokens:
        if tok.type == "HEADER": result["name"] = tok.name
        elif tok.type == "HIERARCHY":
            current_hier = {"root": tok.name, "tags": []}
            result["hierarchies"].append(current_hier)
            stack = [(0, tok.name)]
        elif tok.type == "TAG" and current_hier:
            # Pop stack to find parent at lower indent
            while stack and stack[-1][0] >= tok.indent:
                stack.pop()
            parent = stack[-1][1] if stack else current_hier["root"]
            full_tag = f"{parent}.{tok.name}"
            current_hier["tags"].append(full_tag)
            stack.append((tok.indent, full_tag))
    return result
