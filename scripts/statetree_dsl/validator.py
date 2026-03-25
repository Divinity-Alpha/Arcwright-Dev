"""Validator for statetree_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("states"): w.append("No states defined")
    return {"errors": e, "warnings": w}
