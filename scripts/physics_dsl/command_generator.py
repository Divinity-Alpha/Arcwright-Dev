"""Physics DSL Command Generator."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_physics_setup", {"name": tree["name"], "actor": tree.get("properties",{}).get("actor","")})]
    for c in tree.get("constraints",[]):
        cmds.append(_cmd("add_physics_constraint_dsl", {"setup": tree["name"], "constraint_name": c["name"], **c.get("properties",{})}))
    for d in tree.get("destructibles",[]):
        cmds.append(_cmd("add_destructible", {"setup": tree["name"], "target": d["name"], "health": d["properties"].get("health","100"), "on_break": d.get("on_break",[])}))
    return cmds
