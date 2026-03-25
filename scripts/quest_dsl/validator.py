"""Quest DSL Validator."""
from typing import List, Dict

def validate(tree: dict) -> Dict[str, List[str]]:
    errors, warnings = [], []
    if not tree.get("id") or tree["id"] == "Q_Untitled":
        warnings.append("Missing QUEST: header")
    if not tree.get("properties", {}).get("title"):
        warnings.append("Missing @title")
    if not tree.get("stages"):
        errors.append("Quest has no stages")
    for stage in tree.get("stages", []):
        if not stage.get("objectives"):
            warnings.append(f"Stage '{stage['id']}' has no objectives")
        for obj in stage.get("objectives", []):
            if not obj.get("properties", {}).get("text"):
                warnings.append(f"Objective '{obj['id']}' has no @text")
    return {"errors": errors, "warnings": warnings}
