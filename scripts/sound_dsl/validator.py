"""Validator for sound_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("elements"): w.append("No elements defined")
    return {"errors": e, "warnings": w}
