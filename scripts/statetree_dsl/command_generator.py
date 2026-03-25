"""Command generator for statetree_dsl."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_statetree_config", {"name": tree["name"]})]
    for elem in tree.get("states", []):
        cmds.append(_cmd("add_statetree_element", {"config": tree["name"], "element_type": elem["type"], "element_name": elem["name"], **elem.get("properties",{})}))
    return cmds
