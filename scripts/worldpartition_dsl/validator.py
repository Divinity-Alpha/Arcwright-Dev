"""Validator for worldpartition_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("regions"): w.append("No regions defined")
    return {"errors": e, "warnings": w}
