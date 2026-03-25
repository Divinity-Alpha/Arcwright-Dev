"""AI Perception DSL Validator."""
def validate(tree):
    e, w = [], []
    valid_senses = {"Sight","Hearing","Damage","Touch","Team","Prediction"}
    for s in tree.get("senses", []):
        if s["type"] not in valid_senses: w.append(f"Unknown sense type: {s['type']}")
    if not tree.get("senses"): w.append("No senses defined")
    return {"errors": e, "warnings": w}
