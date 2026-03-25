"""
BlueprintLLM -- Temple Escape Custom 3D Models
================================================
Creates 7 custom models in Blender, exports as FBX, imports to UE,
and replaces placeholder meshes on temple Blueprints.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXPORTS = r"C:\Arcwright\exports"


def blender_model(c, name, build_fn, material_preset, material_params, bake_res=512):
    """Create a model in Blender: build geometry, material, UV, bake, export."""
    c.clear_scene(keep_camera=True, keep_lights=True)

    # Build geometry
    build_fn(c)

    # Join all mesh objects into one named after the model
    objs = c.get_objects("MESH")
    mesh_names = [o["name"] for o in objs.get("objects", [])]
    if len(mesh_names) > 1:
        c.join_objects(mesh_names[0], mesh_names)

    # Rename the joined object
    joined = mesh_names[0]
    if joined != name:
        c.set_transform(joined)  # just ensure it's active
        # Rename via delete_object + won't work. Just use it as-is.

    # Apply procedural material
    mat_name = f"MAT_{name}"
    c._send("blender_create_procedural_material", {
        "preset": material_preset,
        "name": mat_name,
        **material_params,
    })
    c.assign_material(joined, mat_name)

    # UV unwrap
    c.smart_uv_project(joined)

    # Bake
    tex_path = os.path.join(EXPORTS, f"T_{name}.png")
    c.bake_material_to_texture(joined, mat_name, tex_path, bake_res, "DIFFUSE")
    tex_size = os.path.getsize(tex_path) // 1024 if os.path.exists(tex_path) else 0

    # Export FBX
    fbx_path = os.path.join(EXPORTS, f"{name}.fbx")
    c.export_fbx(fbx_path, selected_only=False)
    fbx_size = os.path.getsize(fbx_path) // 1024 if os.path.exists(fbx_path) else 0

    print(f"    Texture: {tex_size} KB, FBX: {fbx_size} KB")
    return fbx_path, tex_path


def ue_import_and_apply(ue, fbx_path, tex_path, mesh_name, mat_name,
                         bp_name, comp_name, roughness=0.5, metallic=0.0):
    """Import mesh+texture into UE, create material, update BP component."""
    # Import mesh
    ue.import_static_mesh(fbx_path, mesh_name)
    time.sleep(0.3)

    # Import texture
    tex_name = f"T_{mesh_name}"
    ue.import_texture(tex_path, tex_name)
    time.sleep(0.3)

    # Create textured material
    ue.create_textured_material(
        mat_name,
        f"/Game/Arcwright/Textures/{tex_name}",
        roughness=roughness, metallic=metallic, tiling=1.0)
    time.sleep(0.5)

    # Update BP mesh component
    ue.send_command("set_component_property", {
        "blueprint": bp_name,
        "component_name": comp_name,
        "property_name": "static_mesh",
        "value": f"/Game/Arcwright/Meshes/{mesh_name}.{mesh_name}",
    })

    # Apply material
    ue.apply_material(bp_name, comp_name,
                      f"/Game/Arcwright/Materials/{mat_name}")
    time.sleep(0.3)


def respawn_actors(ue, bp_class_prefix):
    """Delete and re-query actors of a BP class. Returns actor list for re-spawn."""
    actors = ue.send_command("get_actors", {}).get("data", {}).get("actors", [])
    targets = [a for a in actors if bp_class_prefix in a.get("class", "")]
    for a in targets:
        ue.send_command("delete_actor", {"label": a["label"]})
    return targets


def respawn_from_list(ue, actor_list, bp_class_path):
    """Re-spawn actors from a saved list."""
    for a in actor_list:
        ue.send_command("spawn_actor_at", {
            "class": bp_class_path,
            "label": a["label"],
            "location": a["location"],
            "rotation": a.get("rotation", {"pitch": 0, "yaw": 0, "roll": 0}),
            "scale": a.get("scale", {"x": 1, "y": 1, "z": 1}),
        })


# =========================================================================
# Model definitions
# =========================================================================

def build_key(c):
    """Temple key: shaft + bow + teeth."""
    c.create_mesh("cylinder", name="Shaft", radius=0.1, depth=0.8)
    c.create_mesh("torus", name="Bow")
    c.set_transform("Bow", location=[0, 0, 0.5], scale=[0.2, 0.2, 0.2])
    c.create_mesh("cube", name="T1", scale=[0.05, 0.02, 0.08])
    c.set_transform("T1", location=[0.1, 0, -0.3])
    c.create_mesh("cube", name="T2", scale=[0.05, 0.02, 0.06])
    c.set_transform("T2", location=[0.1, 0, -0.2])
    c.create_mesh("cube", name="T3", scale=[0.05, 0.02, 0.1])
    c.set_transform("T3", location=[0.1, 0, -0.1])


def build_torch(c):
    """Torch: handle + flame cup."""
    c.create_mesh("cylinder", name="Handle", radius=0.04, depth=0.6)
    c.create_mesh("cone", name="Cup", radius=0.08, depth=0.15)
    c.set_transform("Cup", location=[0, 0, 0.35])


def build_pressure_plate(c):
    """Pressure plate: base slab + top plate."""
    c.create_mesh("cube", name="Base", scale=[1.0, 1.0, 0.1])
    c.create_mesh("cube", name="Top", scale=[0.9, 0.9, 0.05])
    c.set_transform("Top", location=[0, 0, 0.1])


def build_portal(c):
    """Exit portal: ring torus standing upright."""
    c.create_mesh("torus", name="Ring")
    c.set_transform("Ring", scale=[1.5, 1.5, 1.5], rotation=[90, 0, 0])


def build_lever(c):
    """Lever: base block + arm + grip."""
    c.create_mesh("cube", name="LBase", scale=[0.2, 0.2, 0.3])
    c.create_mesh("cylinder", name="Arm", radius=0.03, depth=0.5)
    c.set_transform("Arm", location=[0, 0, 0.4], rotation=[0, 30, 0])
    c.create_mesh("sphere", name="Grip", radius=0.05)
    c.set_transform("Grip", location=[0.12, 0, 0.62])


def build_enemy(c):
    """Temple enemy: body + head + horns."""
    c.create_mesh("cylinder", name="Body", radius=0.3, depth=1.6)
    c.create_mesh("sphere", name="Head", radius=0.25)
    c.set_transform("Head", location=[0, 0, 1.0])
    c.create_mesh("cone", name="Horn1", radius=0.05, depth=0.15)
    c.set_transform("Horn1", location=[-0.15, 0, 1.25])
    c.create_mesh("cone", name="Horn2", radius=0.05, depth=0.15)
    c.set_transform("Horn2", location=[0.15, 0, 1.25])


def build_health(c):
    """Health potion: bottle body + neck + cork."""
    c.create_mesh("cylinder", name="Bottle", radius=0.12, depth=0.3)
    c.create_mesh("cylinder", name="Neck", radius=0.05, depth=0.1)
    c.set_transform("Neck", location=[0, 0, 0.2])
    c.create_mesh("sphere", name="Cork", radius=0.06)
    c.set_transform("Cork", location=[0, 0, 0.28])


MODELS = [
    {
        "name": "SM_TempleKey",
        "build": build_key,
        "preset": "metal",
        "params": {"color1": [0.83, 0.69, 0.22, 1.0], "color2": [0.65, 0.50, 0.10, 1.0], "scale": 8.0, "roughness": 0.3},
        "bp": "BP_TempleKey",
        "comp": "KeyMesh",
        "mat": "MAT_KeyGold",
        "roughness": 0.3,
        "metallic": 0.9,
    },
    {
        "name": "SM_Torch",
        "build": build_torch,
        "preset": "wood",
        "params": {"color1": [0.35, 0.22, 0.10, 1.0], "color2": [0.20, 0.12, 0.05, 1.0], "scale": 6.0, "roughness": 0.8},
        "bp": "BP_Torch",
        "comp": "TorchMesh",
        "mat": "MAT_TorchWood",
        "roughness": 0.8,
        "metallic": 0.0,
    },
    {
        "name": "SM_PressurePlate",
        "build": build_pressure_plate,
        "preset": "stone",
        "params": {"color1": [0.35, 0.40, 0.42, 1.0], "color2": [0.25, 0.30, 0.32, 1.0], "scale": 6.0, "roughness": 0.7, "crack_amount": 0.1},
        "bp": "BP_PressurePlate",
        "comp": "PlateMesh",
        "mat": "MAT_PlateStone",
        "roughness": 0.7,
        "metallic": 0.0,
    },
    {
        "name": "SM_Portal",
        "build": build_portal,
        "preset": "energy",
        "params": {"color1": [0.1, 1.0, 0.3, 1.0], "color2": [0.0, 0.5, 0.1, 1.0], "scale": 4.0},
        "bp": "BP_ExitPortal",
        "comp": "PortalMesh",
        "mat": "MAT_PortalEnergy",
        "roughness": 0.2,
        "metallic": 0.0,
    },
    {
        "name": "SM_Lever",
        "build": build_lever,
        "preset": "metal",
        "params": {"color1": [0.3, 0.4, 0.7, 1.0], "color2": [0.15, 0.2, 0.5, 1.0], "scale": 10.0, "roughness": 0.4},
        "bp": "BP_TempleLever",
        "comp": "LeverMesh",
        "mat": "MAT_LeverMetal",
        "roughness": 0.4,
        "metallic": 0.8,
    },
    {
        "name": "SM_TempleEnemy",
        "build": build_enemy,
        "preset": "metal",
        "params": {"color1": [0.6, 0.1, 0.1, 1.0], "color2": [0.35, 0.05, 0.05, 1.0], "scale": 6.0, "roughness": 0.5},
        "bp": "BP_TempleEnemy",
        "comp": "EnemyMesh",
        "mat": "MAT_EnemyDarkRed",
        "roughness": 0.5,
        "metallic": 0.7,
    },
    {
        "name": "SM_HealthPotion",
        "build": build_health,
        "preset": "ice",
        "params": {"color1": [0.2, 0.9, 0.3, 1.0], "color2": [0.1, 0.6, 0.15, 1.0], "scale": 5.0, "roughness": 0.1},
        "bp": "BP_HealthPickup",
        "comp": "HealthMesh",
        "mat": "MAT_HealthPotion",
        "roughness": 0.1,
        "metallic": 0.0,
    },
]


def main():
    from scripts.blender_mcp.blender_client import BlenderClient
    from scripts.mcp_client.blueprint_client import ArcwrightClient

    bc = BlenderClient()
    bc.connect()
    print("Blender connected")

    ue = ArcwrightClient()
    ue.health_check()
    print("UE connected\n")

    for i, m in enumerate(MODELS):
        num = i + 1
        print(f"[{num}/7] {m['name']} -> {m['bp']}.{m['comp']}")

        # Blender: build, material, bake, export
        fbx_path, tex_path = blender_model(
            bc, m["name"], m["build"],
            m["preset"], m["params"])

        # UE: import, create material, update BP
        ue_import_and_apply(
            ue, fbx_path, tex_path, m["name"], m["mat"],
            m["bp"], m["comp"],
            roughness=m.get("roughness", 0.5),
            metallic=m.get("metallic", 0.0))

        # Re-spawn actors of this type
        old_actors = respawn_actors(ue, m["bp"])
        if old_actors:
            bp_path = f"/Game/Arcwright/Generated/{m['bp']}.{m['bp']}"
            respawn_from_list(ue, old_actors, bp_path)
            print(f"    Re-spawned {len(old_actors)} actors")
        else:
            print(f"    No actors to re-spawn")

        print(f"    DONE\n")

    ue.send_command("save_all", {})
    print("All saved!")

    # Final screenshot
    time.sleep(2)
    r = ue.send_command("take_screenshot", {
        "output_path": "C:/Arcwright/exports/temple_custom_models.png"})
    print(f"Screenshot: {r.get('data', {}).get('file_path', '?')}")

    bc.close()
    ue.close()


if __name__ == "__main__":
    main()
