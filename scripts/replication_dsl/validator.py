"""Validator for replication_dsl."""
def validate(tree):
    e, w = [], []
    if not tree.get("properties"): w.append("No properties defined")
    return {"errors": e, "warnings": w}
