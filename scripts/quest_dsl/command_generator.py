"""Quest DSL Command Generator."""
import json
from typing import List

def _cmd(c, p): return {"command": c, "params": p}

def generate(tree: dict) -> List[dict]:
    commands = []
    qid = tree["id"]
    props = tree.get("properties", {})

    # Create quest
    commands.append(_cmd("create_quest", {
        "name": qid,
        "title": props.get("title", ""),
        "description": props.get("description", ""),
        "giver": props.get("giver", ""),
        "category": props.get("category", "Main"),
        "level_requirement": int(props.get("level_requirement", "0")),
        "reward_xp": int(props.get("reward_xp", "0")),
        "reward_gold": int(props.get("reward_gold", "0")),
        "reward_items": props.get("reward_items", ""),
    }))

    # Add stages + objectives
    for si, stage in enumerate(tree.get("stages", [])):
        sp = stage.get("properties", {})
        commands.append(_cmd("add_quest_stage", {
            "quest": qid,
            "stage_id": stage["id"],
            "stage_index": si,
            "description": sp.get("description", ""),
            "type": sp.get("type", "Custom"),
        }))
        for obj in stage.get("objectives", []):
            op = obj.get("properties", {})
            commands.append(_cmd("add_quest_objective", {
                "quest": qid,
                "stage_id": stage["id"],
                "objective_id": obj["id"],
                "text": op.get("text", ""),
                "target": op.get("target", ""),
                "count": int(op.get("count", "1")),
                "optional": op.get("optional", "false") == "true",
            }))

    return commands
