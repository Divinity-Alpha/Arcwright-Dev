"""Dialogue DSL Command Generator."""
import json
from typing import List

def _cmd(c, p): return {"command": c, "params": p}

def generate(tree: dict) -> List[dict]:
    commands = []
    dlg_name = tree["name"]

    # Create dialogue data table
    commands.append(_cmd("create_dialogue", {"name": dlg_name}))

    # Add each node as a row
    for node in tree.get("nodes", []):
        choices_json = json.dumps(node.get("choices", []))
        commands.append(_cmd("add_dialogue_node", {
            "dialogue": dlg_name,
            "node_id": node["id"],
            "speaker": node.get("speaker", tree.get("properties", {}).get("speaker_default", "")),
            "text": node.get("text", ""),
            "choices": choices_json,
            "conditions": ",".join(node.get("conditions", [])),
            "actions": ",".join(node.get("actions", [])),
            "next_node": node.get("next", ""),
            "flags": ",".join(node.get("flags", [])),
        }))

    return commands
