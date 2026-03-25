"""Tags DSL Validator."""
def validate(tree):
    e, w = [], []
    all_tags = set()
    for h in tree.get("hierarchies", []):
        for t in h.get("tags", []):
            if t in all_tags: e.append(f"Duplicate tag: {t}")
            all_tags.add(t)
    if not all_tags: w.append("No tags defined")
    return {"errors": e, "warnings": w}
