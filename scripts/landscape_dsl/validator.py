"""Validator for landscape_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("layers"): w.append("No layers defined")
    return {"errors": e, "warnings": w}
