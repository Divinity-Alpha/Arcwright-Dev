"""Tags DSL Command Generator."""
def _cmd(c,p): return {"command":c,"params":p}
def generate(tree):
    cmds = [_cmd("create_tag_hierarchy", {"name": tree["name"]})]
    for h in tree.get("hierarchies", []):
        for tag in h.get("tags", []):
            cmds.append(_cmd("add_gameplay_tag", {"tag": tag}))
    return cmds
