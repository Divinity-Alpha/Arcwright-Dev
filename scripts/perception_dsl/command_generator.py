"""AI Perception DSL Command Generator."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_ai_perception", {"name": tree["name"], "owner": tree.get("properties",{}).get("owner","")})]
    for s in tree.get("senses",[]):
        cmds.append(_cmd("add_perception_sense", {"perception": tree["name"], "sense_type": s["type"], **s.get("properties",{})}))
    return cmds
