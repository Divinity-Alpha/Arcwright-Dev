"""Validator for vehicle_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("components"): w.append("No components defined")
    return {"errors": e, "warnings": w}
