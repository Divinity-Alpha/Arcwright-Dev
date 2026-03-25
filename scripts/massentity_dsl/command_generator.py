"""Command generator for massentity_dsl."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_massentity_config", {"name": tree["name"]})]
    for elem in tree.get("archetypes", []):
        cmds.append(_cmd("add_massentity_element", {"config": tree["name"], "element_type": elem["type"], "element_name": elem["name"], **elem.get("properties",{})}))
    return cmds
