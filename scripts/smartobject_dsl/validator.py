"""Validator for smartobject_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("slots"): w.append("No slots defined")
    return {"errors": e, "warnings": w}
