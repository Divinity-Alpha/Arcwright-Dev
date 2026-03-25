"""Physics DSL Validator."""
def validate(tree):
    e, w = [], []
    valid = {"Hinge","Ball","Prismatic","Fixed","Spring","Cone"}
    for c in tree.get("constraints",[]):
        t = c["properties"].get("type","")
        if t and t not in valid: w.append(f"Unknown constraint type: {t}")
    for d in tree.get("destructibles",[]):
        if not d["properties"].get("health"): w.append(f"Destructible '{d['name']}' has no @health")
    return {"errors": e, "warnings": w}
