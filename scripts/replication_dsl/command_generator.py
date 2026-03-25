"""Command generator for replication_dsl."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_replication_config", {"name": tree["name"]})]
    for elem in tree.get("properties", []):
        cmds.append(_cmd("add_replication_element", {"config": tree["name"], "element_type": elem["type"], "element_name": elem["name"], **elem.get("properties",{})}))
    return cmds
