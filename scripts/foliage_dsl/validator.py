"""Validator for foliage_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("types"): w.append("No types defined")
    return {"errors": e, "warnings": w}
