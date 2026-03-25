"""Validator for massentity_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("archetypes"): w.append("No archetypes defined")
    return {"errors": e, "warnings": w}
