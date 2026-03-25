"""Validator for input_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("actions"): w.append("No actions defined")
    return {"errors": e, "warnings": w}
