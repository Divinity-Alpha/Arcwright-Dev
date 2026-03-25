"""Command generator for worldpartition_dsl."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_worldpartition_config", {"name": tree["name"]})]
    for elem in tree.get("regions", []):
        cmds.append(_cmd("add_worldpartition_element", {"config": tree["name"], "element_type": elem["type"], "element_name": elem["name"], **elem.get("properties",{})}))
    return cmds
