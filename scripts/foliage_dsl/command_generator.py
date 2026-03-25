"""Command generator for foliage_dsl."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_foliage_config", {"name": tree["name"]})]
    for elem in tree.get("types", []):
        cmds.append(_cmd("add_foliage_element", {"config": tree["name"], "element_type": elem["type"], "element_name": elem["name"], **elem.get("properties",{})}))
    return cmds
