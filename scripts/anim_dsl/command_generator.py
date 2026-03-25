"""Animation DSL Command Generator — converts parsed tree to TCP commands."""

from typing import List


def _cmd(command: str, params: dict) -> dict:
    return {"command": command, "params": params}


def generate(tree: dict) -> List[dict]:
    commands = []
    bp_name = tree["name"]

    # 1. Create AnimBlueprint (DSL handler reads skeleton_path)
    commands.append(_cmd("create_anim_blueprint_dsl", {
        "name": bp_name,
        "skeleton_path": tree.get("skeleton", ""),
        "mesh_path": tree.get("mesh", ""),
    }))

    # 2. State machines
    for sm in tree.get("state_machines", []):
        commands.append(_cmd("add_state_machine", {
            "anim_bp": bp_name,
            "machine_name": sm["name"],
        }))

        # States (DSL handler reads anim_bp, machine_name, state_name, is_entry)
        for i, state in enumerate(sm.get("states", [])):
            is_entry = state.get("properties", {}).get("entry") == "true" or i == 0
            commands.append(_cmd("add_anim_state_2", {
                "anim_bp": bp_name,
                "machine_name": sm["name"],
                "state_name": state["name"],
                "animation_path": state.get("properties", {}).get("animation", ""),
                "is_entry": is_entry,
            }))

        # Transitions (DSL handler reads anim_bp, from_state, to_state)
        for trans in sm.get("transitions", []):
            commands.append(_cmd("add_anim_transition_2", {
                "anim_bp": bp_name,
                "machine_name": sm["name"],
                "from_state": trans["from"],
                "to_state": trans["to"],
                "condition": trans.get("properties", {}).get("condition", ""),
                "blend_duration": float(trans.get("properties", {}).get("blend_duration", "0.2")),
            }))

    # 3. Blend spaces (Phase 6 handler reads: name, skeleton, dimensions)
    for bs in tree.get("blend_spaces", []):
        props = bs.get("properties", {})
        bs_type = props.get("type", "1D")
        dimensions = 1 if bs_type == "1D" else 2
        commands.append(_cmd("create_blend_space", {
            "name": bs["name"],
            "skeleton": tree.get("skeleton", ""),
            "dimensions": dimensions,
            "axis_x_name": props.get("axis_x", "Speed"),
            "axis_x_min": float(props.get("axis_x_min", "0")),
            "axis_x_max": float(props.get("axis_x_max", "600")),
            "samples": bs.get("samples", []),
        }))

    # 4. Montages (DSL handler reads name, skeleton_path, animation_path, slot_name)
    for mon in tree.get("montages", []):
        props = mon.get("properties", {})
        commands.append(_cmd("add_anim_montage_2", {
            "name": mon["name"],
            "skeleton_path": tree.get("skeleton", ""),
            "animation_path": props.get("animation", ""),
            "slot_name": props.get("slot", "DefaultSlot"),
        }))

    # 5. Layers
    for layer in tree.get("layers", []):
        props = layer.get("properties", {})
        commands.append(_cmd("add_anim_layer", {
            "anim_bp": bp_name,
            "layer_name": layer["name"],
            "bone_mask_root": props.get("bone_mask", "spine_01"),
            "slot_name": props.get("slot", "DefaultSlot"),
            "blend_mode": props.get("blend_mode", "Override"),
        }))

    # 6. Aim offsets
    for ao in tree.get("aim_offsets", []):
        props = ao.get("properties", {})
        commands.append(_cmd("create_aim_offset", {
            "name": ao["name"],
            "skeleton_path": tree.get("skeleton", ""),
            "axis_x_name": props.get("axis_x", "Yaw"),
            "axis_x_min": float(props.get("axis_x_min", "-90")),
            "axis_x_max": float(props.get("axis_x_max", "90")),
            "axis_y_name": props.get("axis_y", "Pitch"),
            "axis_y_min": float(props.get("axis_y_min", "-90")),
            "axis_y_max": float(props.get("axis_y_max", "90")),
            "samples": ao.get("samples", []),
        }))

    # 7. Compile
    commands.append(_cmd("compile_anim_blueprint", {"anim_bp": bp_name}))

    return commands
