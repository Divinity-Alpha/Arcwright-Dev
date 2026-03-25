"""Material DSL Command Generator."""
from typing import List

def _cmd(c, p): return {"command": c, "params": p}

def generate(tree: dict) -> List[dict]:
    commands = []
    mat_name = tree["name"]

    # Create material
    commands.append(_cmd("create_material_graph", {"name": mat_name}))

    # Create nodes (track name → index)
    name_to_idx = {}
    for i, node in enumerate(tree.get("nodes", [])):
        params = {"material": mat_name, "type": node["type"], "name": node["name"]}
        # Pass type-specific params
        props = node.get("properties", {})
        if "default" in props:
            vals = props["default"].split(",")
            if len(vals) >= 3:
                params["r"] = float(vals[0]); params["g"] = float(vals[1]); params["b"] = float(vals[2])
            elif len(vals) == 1:
                params["default_value"] = float(vals[0])
        if "value" in props:
            params["value"] = float(props["value"])
        if "r" in props: params["r"] = float(props["r"])
        if "g" in props: params["g"] = float(props["g"])
        if "b" in props: params["b"] = float(props["b"])
        params["pos_x"] = -400 + (i % 4) * 200
        params["pos_y"] = (i // 4) * 200

        commands.append(_cmd("add_material_node", params))
        name_to_idx[node["name"]] = i

    # Connect nodes based on @A, @B, @Alpha references
    for node in tree.get("nodes", []):
        dst_idx = name_to_idx.get(node["name"], -1)
        props = node.get("properties", {})
        for input_name in ("A", "B", "Alpha"):
            if input_name in props:
                ref = props[input_name]
                src_name = ref.split(".")[0]
                src_idx = name_to_idx.get(src_name, -1)
                if src_idx >= 0 and dst_idx >= 0:
                    commands.append(_cmd("connect_material_nodes", {
                        "material": mat_name, "source_index": src_idx,
                        "dest_index": dst_idx, "input_name": input_name,
                    }))

    # Connect outputs
    for pin, ref in tree.get("outputs", {}).items():
        ref_name = ref.split(".")[0]
        node_idx = name_to_idx.get(ref_name, -1)
        if node_idx >= 0:
            commands.append(_cmd("set_material_output", {
                "material": mat_name, "node_index": node_idx, "output_pin": pin,
            }))

    # Compile
    commands.append(_cmd("compile_material_graph", {"material": mat_name}))

    return commands
