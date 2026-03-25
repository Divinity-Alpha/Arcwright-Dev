"""
BlueprintLLM -- Temple Escape Texture Pipeline
==============================================
Creates procedural textures in Blender, bakes them to PNG,
imports into UE5, creates textured materials, and applies
them to the Temple Escape level geometry.

Usage:
    python scripts/texture_temple.py              # Full pipeline
    python scripts/texture_temple.py --bake-only   # Only Blender bake (no UE)
    python scripts/texture_temple.py --ue-only     # Only UE import + apply (textures already baked)
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXPORTS_DIR = r"C:\Arcwright\exports"

# ═══════════════════════════════════════════════════════════════════
# Texture Definitions -- what to create and where to apply
# ═══════════════════════════════════════════════════════════════════

TEXTURES = [
    {
        "name": "T_StoneWall",
        "preset": "stone",
        "params": {
            "color1": [0.28, 0.24, 0.20, 1.0],
            "color2": [0.18, 0.15, 0.13, 1.0],
            "scale": 4.0,
            "roughness": 0.9,
        },
        "resolution": 1024,
        "material": {"name": "MAT_StoneWall", "roughness": 0.9, "tiling": 2.0},
    },
    {
        "name": "T_StoneFloor",
        "preset": "stone",
        "params": {
            "color1": [0.20, 0.18, 0.16, 1.0],
            "color2": [0.12, 0.10, 0.09, 1.0],
            "scale": 6.0,
            "roughness": 0.85,
        },
        "resolution": 1024,
        "material": {"name": "MAT_StoneFloor", "roughness": 0.85, "tiling": 2.0},
    },
    {
        "name": "T_MarbleFloor",
        "preset": "marble",
        "params": {
            "color1": [0.85, 0.82, 0.75, 1.0],
            "color2": [0.5, 0.45, 0.4, 1.0],
            "scale": 3.0,
            "roughness": 0.15,
        },
        "resolution": 1024,
        "material": {"name": "MAT_MarbleFloor", "roughness": 0.15, "tiling": 1.5},
    },
    {
        "name": "T_GoldMetal",
        "preset": "metal",
        "params": {
            "color1": [0.83, 0.69, 0.22, 1.0],
            "color2": [0.65, 0.50, 0.10, 1.0],
            "scale": 8.0,
            "roughness": 0.3,
        },
        "resolution": 512,
        "material": {"name": "MAT_GoldMetal", "roughness": 0.3, "metallic": 0.9, "tiling": 1.0},
    },
    {
        "name": "T_LavaHazard",
        "preset": "lava",
        "params": {
            "color1": [1.0, 0.4, 0.05, 1.0],
            "color2": [0.8, 0.1, 0.0, 1.0],
            "scale": 3.0,
        },
        "resolution": 512,
        "material": {"name": "MAT_LavaHazard", "roughness": 0.6, "tiling": 1.0},
    },
    {
        "name": "T_EnergyGreen",
        "preset": "energy",
        "params": {
            "color1": [0.1, 1.0, 0.3, 1.0],
            "color2": [0.0, 0.5, 0.1, 1.0],
            "scale": 4.0,
        },
        "resolution": 512,
        "material": {"name": "MAT_EnergyGreen", "roughness": 0.2, "tiling": 1.0},
    },
    {
        "name": "T_EnergyBlue",
        "preset": "energy",
        "params": {
            "color1": [0.2, 0.5, 1.0, 1.0],
            "color2": [0.05, 0.2, 0.8, 1.0],
            "scale": 3.0,
        },
        "resolution": 512,
        "material": {"name": "MAT_EnergyBlue", "roughness": 0.2, "tiling": 1.0},
    },
]

# Material -> actor label prefix mapping
# After creating materials, apply them to existing temple geometry
MATERIAL_ASSIGNMENTS = {
    # Walls get stone wall texture
    "MAT_StoneWall": {"bp": "BP_WallBlock", "component": "BlockMesh"},
    # Floors get stone floor texture
    "MAT_StoneFloor": {"bp": "BP_FloorBlock", "component": "BlockMesh"},
}


# ═══════════════════════════════════════════════════════════════════
# Step 1: Blender -- Create procedural materials and bake to PNG
# ═══════════════════════════════════════════════════════════════════

def bake_textures_in_blender():
    """Connect to Blender, create procedural materials, bake to PNG files."""
    from scripts.blender_mcp.blender_client import BlenderClient, BlenderClientError

    os.makedirs(EXPORTS_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print("STEP 1: Baking procedural textures in Blender")
    print("=" * 60)

    try:
        client = BlenderClient()
        client.connect()
        print("  Connected to Blender on port 13378")
    except (ConnectionRefusedError, BlenderClientError) as e:
        print(f"  ERROR: Cannot connect to Blender: {e}")
        print("  Make sure Blender is running with the BlueprintLLM addon enabled.")
        return False

    try:
        # Health check
        health = client.health_check()
        print(f"  Blender {health.get('blender_version', '?')} ready")

        # Clear scene for baking
        client.clear_scene(keep_camera=True, keep_lights=True)

        # Create a bake target plane (UV-mapped)
        client.create_mesh("plane", name="BakeTarget", scale=[2, 2, 2])
        client.smart_uv_project("BakeTarget")

        baked = []
        for i, tex in enumerate(TEXTURES):
            print(f"\n  [{i+1}/{len(TEXTURES)}] {tex['name']} (preset: {tex['preset']})")

            # Create procedural material
            mat_result = client.create_procedural_material(
                tex["preset"],
                name=tex["name"],
                **{k: v for k, v in tex["params"].items()
                   if k in ("color1", "color2", "scale", "roughness")}
            )
            print(f"    Created material: {mat_result.get('name', tex['name'])}")

            # Assign to bake target
            client.assign_material("BakeTarget", tex["name"])

            # Bake to PNG
            output_path = os.path.join(EXPORTS_DIR, f"{tex['name']}.png")
            bake_result = client.bake_material_to_texture(
                "BakeTarget", tex["name"], output_path,
                resolution=tex.get("resolution", 1024),
                bake_type="DIFFUSE"
            )

            if os.path.exists(output_path):
                size_kb = os.path.getsize(output_path) / 1024
                print(f"    Baked: {output_path} ({size_kb:.0f} KB)")
                baked.append(tex["name"])
            else:
                print(f"    WARNING: Bake may have failed -- file not found: {output_path}")
                # Check for error in result
                if isinstance(bake_result, dict) and "error" in bake_result:
                    print(f"    Error: {bake_result['error']}")

        print(f"\n  Baked {len(baked)}/{len(TEXTURES)} textures to {EXPORTS_DIR}")
        return len(baked) == len(TEXTURES)

    except BlenderClientError as e:
        print(f"  ERROR: Blender operation failed: {e}")
        return False
    finally:
        client.close()


# ═══════════════════════════════════════════════════════════════════
# Step 2: UE5 -- Import textures, create materials, apply to geometry
# ═══════════════════════════════════════════════════════════════════

def import_and_apply_in_ue():
    """Import baked textures into UE, create textured materials, apply."""
    from scripts.mcp_client.blueprint_client import ArcwrightClient

    print("\n" + "=" * 60)
    print("STEP 2: Importing textures and creating materials in UE5")
    print("=" * 60)

    try:
        client = ArcwrightClient()
        health = client.health_check()
        print(f"  Connected to UE5 -- {health.get('server', '?')} v{health.get('version', '?')}")
    except Exception as e:
        print(f"  ERROR: Cannot connect to UE: {e}")
        return False

    try:
        # Step 2a: Import textures
        print("\n  --- Importing textures into UE ---")
        imported = []
        for tex in TEXTURES:
            png_path = os.path.join(EXPORTS_DIR, f"{tex['name']}.png")
            if not os.path.exists(png_path):
                print(f"  SKIP: {tex['name']} -- PNG not found at {png_path}")
                continue

            result = client.import_texture(png_path, tex["name"])
            if result.get("status") == "error":
                print(f"  WARNING: {tex['name']}: {result.get('message', 'unknown error')}")
                # May already exist -- that's OK
            else:
                print(f"  Imported: {tex['name']} -> /Game/Arcwright/Textures/{tex['name']}")
            imported.append(tex["name"])

        print(f"  {len(imported)}/{len(TEXTURES)} textures imported")

        # Step 2b: Create textured materials
        print("\n  --- Creating textured materials ---")
        created_mats = []
        for tex in TEXTURES:
            mat_info = tex["material"]
            mat_name = mat_info["name"]
            tex_path = f"/Game/Arcwright/Textures/{tex['name']}"

            result = client.create_textured_material(
                mat_name,
                tex_path,
                roughness=mat_info.get("roughness", 0.5),
                metallic=mat_info.get("metallic", 0.0),
                tiling=mat_info.get("tiling", 1.0),
            )
            if isinstance(result, dict) and result.get("status") == "error":
                print(f"  WARNING: {mat_name}: {result.get('message', 'unknown error')}")
            else:
                print(f"  Created: {mat_name} (texture: {tex['name']}, roughness: {mat_info.get('roughness', 0.5)})")
                created_mats.append(mat_name)

        print(f"  {len(created_mats)}/{len(TEXTURES)} materials created")

        # Step 2c: Apply materials to temple geometry
        print("\n  --- Applying materials to temple geometry ---")
        applied = 0
        for mat_name, target in MATERIAL_ASSIGNMENTS.items():
            bp = target["bp"]
            comp = target["component"]
            mat_path = f"/Game/Arcwright/Materials/{mat_name}"

            result = client.apply_material(bp, comp, mat_path)
            if isinstance(result, dict) and "error" in str(result.get("status", "")):
                print(f"  WARNING: {bp}.{comp} <- {mat_name}: {result.get('message', 'unknown')}")
            else:
                print(f"  Applied: {bp}.{comp} <- {mat_name}")
                applied += 1

        print(f"  {applied}/{len(MATERIAL_ASSIGNMENTS)} materials applied to BPs")

        # Step 2d: Save
        print("\n  --- Saving ---")
        client.send_command("save_all", {})
        print("  Saved all assets")

        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    bake_only = "--bake-only" in sys.argv
    ue_only = "--ue-only" in sys.argv

    print("=" * 60)
    print("Temple Escape Texture Pipeline")
    print("=" * 60)

    success = True

    if not ue_only:
        success = bake_textures_in_blender()
        if not success and not bake_only:
            print("\nBlender bake had issues. Continuing to UE anyway...")

    if not bake_only:
        success = import_and_apply_in_ue()

    print("\n" + "=" * 60)
    print("Pipeline complete!" if success else "Pipeline finished with warnings.")
    print("=" * 60)
