def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_paper2d_config", {"name": tree["name"]})]
    for elem in tree.get("elements", []):
        cmds.append(_cmd("add_paper2d_element", {"config": tree["name"], "element_type": elem["type"], "element_name": elem["name"], **elem.get("properties",{})}))
    return cmds
