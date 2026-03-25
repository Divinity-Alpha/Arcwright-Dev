"""
Arcwright -- Texture Library
===============================
Central registry of all available textures and materials.
Maps friendly names to UE asset paths for instant reuse.

Usage:
    from scripts.texture_library import get_texture, get_material, list_textures

    # Get a texture path by friendly name
    path = get_texture("stone_floor")  # -> "/Game/Arcwright/Textures/T_StoneFloor"

    # Get a pre-made material path
    path = get_material("stone_floor")  # -> "/Game/Arcwright/Materials/MAT_StoneFloor"

    # List all textures in a category
    for name, path in list_textures("stone"):
        print(f"{name}: {path}")
"""


# =========================================================================
# Texture Registry -- friendly name -> UE asset path
# =========================================================================
# Categories: stone, concrete, marble, metal, wood, energy, lava, ice, model
#
# Sources:
#   /Game/Arcwright/Textures/  -- procedural bakes from Blender (permanent)
#   /Game/Arcwright/Meshes/    -- model textures baked with custom 3D models
#   /Engine/                       -- engine built-in (very limited in UE 5.7)

TEXTURE_LIBRARY = {
    # --- Stone ---
    "stone_wall":       "/Game/Arcwright/Textures/T_StoneWall",
    "stone_floor":      "/Game/Arcwright/Textures/T_StoneFloor",

    # --- Concrete ---
    "concrete":         "/Game/Arcwright/Textures/T_Concrete",

    # --- Marble ---
    "marble_floor":     "/Game/Arcwright/Textures/T_MarbleFloor",

    # --- Metal ---
    "gold_metal":       "/Game/Arcwright/Textures/T_GoldMetal",

    # --- Energy / FX ---
    "energy_green":     "/Game/Arcwright/Textures/T_EnergyGreen",
    "energy_blue":      "/Game/Arcwright/Textures/T_EnergyBlue",

    # --- Lava / Hazard ---
    "lava":             "/Game/Arcwright/Textures/T_LavaHazard",

    # --- Model Textures (baked with custom 3D models) ---
    "model_key":        "/Game/Arcwright/Textures/T_SM_TempleKey",
    "model_torch":      "/Game/Arcwright/Textures/T_SM_Torch",
    "model_plate":      "/Game/Arcwright/Textures/T_SM_PressurePlate",
    "model_portal":     "/Game/Arcwright/Textures/T_SM_Portal",
    "model_lever":      "/Game/Arcwright/Textures/T_SM_Lever",
    "model_enemy":      "/Game/Arcwright/Textures/T_SM_TempleEnemy",
    "model_health":     "/Game/Arcwright/Textures/T_SM_HealthPotion",

    # --- Engine Built-in ---
    "moss":             "/Engine/Content/StarterContent/Textures/T_ground_Moss_D",
}


# =========================================================================
# Material Registry -- friendly name -> UE material asset path
# =========================================================================
# Pre-built materials ready to apply with apply_material().
# Textured materials use create_textured_material (TextureSample -> BaseColor).
# Simple materials use create_simple_material (constant color).

MATERIAL_LIBRARY = {
    # --- Textured surface materials ---
    "stone_wall":       "/Game/Arcwright/Materials/MAT_StoneWall",
    "stone_floor":      "/Game/Arcwright/Materials/MAT_StoneFloor",
    "concrete":         "/Game/Arcwright/Materials/MAT_Concrete",
    "marble_floor":     "/Game/Arcwright/Materials/MAT_MarbleFloor",
    "gold_metal":       "/Game/Arcwright/Materials/MAT_GoldMetal",
    "energy_green":     "/Game/Arcwright/Materials/MAT_EnergyGreen",
    "energy_blue":      "/Game/Arcwright/Materials/MAT_EnergyBlue",
    "lava":             "/Game/Arcwright/Materials/MAT_LavaHazard",

    # --- Model materials (textured) ---
    "key_gold":         "/Game/Arcwright/Materials/MAT_KeyGold",
    "torch_wood":       "/Game/Arcwright/Materials/MAT_TorchWood",
    "plate_stone":      "/Game/Arcwright/Materials/MAT_PlateStone",
    "portal_energy":    "/Game/Arcwright/Materials/MAT_PortalEnergy",
    "lever_metal":      "/Game/Arcwright/Materials/MAT_LeverMetal",
    "enemy_darkred":    "/Game/Arcwright/Materials/MAT_EnemyDarkRed",
    "health_potion":    "/Game/Arcwright/Materials/MAT_HealthPotion",

    # --- Simple color materials ---
    "gold":             "/Game/Arcwright/Materials/MAT_Gold",
    "green":            "/Game/Arcwright/Materials/MAT_Green",
    "red":              "/Game/Arcwright/Materials/MAT_Red",
    "enemy_red":        "/Game/Arcwright/Materials/MAT_EnemyRed",
}


# =========================================================================
# Material Presets -- for creating new materials from the library
# =========================================================================
# Each preset defines what's needed to recreate the material if it doesn't exist.

MATERIAL_PRESETS = {
    "stone_wall": {
        "type": "textured",
        "texture": "stone_wall",
        "roughness": 0.9,
        "metallic": 0.0,
        "tiling": 2.0,
    },
    "stone_floor": {
        "type": "textured",
        "texture": "stone_floor",
        "roughness": 0.85,
        "metallic": 0.0,
        "tiling": 2.0,
    },
    "concrete": {
        "type": "textured",
        "texture": "concrete",
        "roughness": 0.75,
        "metallic": 0.0,
        "tiling": 2.0,
    },
    "marble_floor": {
        "type": "textured",
        "texture": "marble_floor",
        "roughness": 0.15,
        "metallic": 0.0,
        "tiling": 1.5,
    },
    "gold_metal": {
        "type": "textured",
        "texture": "gold_metal",
        "roughness": 0.3,
        "metallic": 0.9,
        "tiling": 1.0,
    },
    "energy_green": {
        "type": "textured",
        "texture": "energy_green",
        "roughness": 0.2,
        "metallic": 0.0,
        "tiling": 1.0,
    },
    "energy_blue": {
        "type": "textured",
        "texture": "energy_blue",
        "roughness": 0.2,
        "metallic": 0.0,
        "tiling": 1.0,
    },
    "lava": {
        "type": "textured",
        "texture": "lava",
        "roughness": 0.6,
        "metallic": 0.0,
        "tiling": 1.0,
    },
    "gold": {
        "type": "simple",
        "color": {"r": 0.83, "g": 0.69, "b": 0.22},
    },
    "green": {
        "type": "simple",
        "color": {"r": 0.1, "g": 0.8, "b": 0.2},
    },
    "red": {
        "type": "simple",
        "color": {"r": 0.8, "g": 0.1, "b": 0.1},
    },
}


# =========================================================================
# Blender Bake Recipes -- for regenerating textures if needed
# =========================================================================
# Only needed if textures must be re-baked. Normally textures are permanent.

BAKE_RECIPES = {
    "stone_wall": {
        "preset": "stone",
        "color1": [0.28, 0.24, 0.20, 1.0],
        "color2": [0.18, 0.15, 0.13, 1.0],
        "scale": 4.0,
        "roughness": 0.9,
        "resolution": 1024,
    },
    "stone_floor": {
        "preset": "stone",
        "color1": [0.20, 0.18, 0.16, 1.0],
        "color2": [0.12, 0.10, 0.09, 1.0],
        "scale": 6.0,
        "roughness": 0.85,
        "resolution": 1024,
    },
    "concrete": {
        "preset": "stone",
        "color1": [0.52, 0.50, 0.48, 1.0],
        "color2": [0.48, 0.46, 0.44, 1.0],
        "scale": 5.0,
        "roughness": 0.75,
        "crack_amount": 0.05,
        "resolution": 1024,
    },
    "marble_floor": {
        "preset": "marble",
        "color1": [0.85, 0.82, 0.75, 1.0],
        "color2": [0.5, 0.45, 0.4, 1.0],
        "scale": 3.0,
        "roughness": 0.15,
        "resolution": 1024,
    },
    "gold_metal": {
        "preset": "metal",
        "color1": [0.83, 0.69, 0.22, 1.0],
        "color2": [0.65, 0.50, 0.10, 1.0],
        "scale": 8.0,
        "roughness": 0.3,
        "resolution": 512,
    },
    "energy_green": {
        "preset": "energy",
        "color1": [0.1, 1.0, 0.3, 1.0],
        "color2": [0.0, 0.5, 0.1, 1.0],
        "scale": 4.0,
        "resolution": 512,
    },
    "energy_blue": {
        "preset": "energy",
        "color1": [0.2, 0.5, 1.0, 1.0],
        "color2": [0.05, 0.2, 0.8, 1.0],
        "scale": 3.0,
        "resolution": 512,
    },
    "lava": {
        "preset": "lava",
        "color1": [1.0, 0.4, 0.05, 1.0],
        "color2": [0.8, 0.1, 0.0, 1.0],
        "scale": 3.0,
        "resolution": 512,
    },
}


# =========================================================================
# API Functions
# =========================================================================

def get_texture(name):
    """Get UE asset path for a texture by friendly name. Returns None if not found."""
    return TEXTURE_LIBRARY.get(name)


def get_material(name):
    """Get UE asset path for a material by friendly name. Returns None if not found."""
    return MATERIAL_LIBRARY.get(name)


def get_preset(name):
    """Get material preset for creating a new material. Returns None if not found."""
    return MATERIAL_PRESETS.get(name)


def get_bake_recipe(name):
    """Get Blender bake recipe for regenerating a texture. Returns None if not found."""
    return BAKE_RECIPES.get(name)


def resolve_texture(name_or_path):
    """Resolve a friendly name OR full asset path to a UE asset path.
    If it starts with '/' it's treated as a full path and returned as-is.
    Otherwise, looked up in the texture library.
    """
    if name_or_path.startswith("/"):
        return name_or_path
    return TEXTURE_LIBRARY.get(name_or_path)


def resolve_material(name_or_path):
    """Resolve a friendly name OR full asset path to a UE material path."""
    if name_or_path.startswith("/"):
        return name_or_path
    return MATERIAL_LIBRARY.get(name_or_path)


def list_textures(category=None):
    """List textures, optionally filtered by category prefix.
    Returns list of (name, path) tuples.
    """
    if category is None:
        return list(TEXTURE_LIBRARY.items())
    return [(k, v) for k, v in TEXTURE_LIBRARY.items() if k.startswith(category)]


def list_materials(category=None):
    """List materials, optionally filtered by category prefix."""
    if category is None:
        return list(MATERIAL_LIBRARY.items())
    return [(k, v) for k, v in MATERIAL_LIBRARY.items() if k.startswith(category)]


def ensure_material(client, name):
    """Ensure a material exists in UE. Creates it from preset if needed.
    Args:
        client: ArcwrightClient instance
        name: friendly name from MATERIAL_PRESETS
    Returns:
        UE asset path of the material, or None if creation failed.
    """
    import time

    mat_path = get_material(name)
    preset = get_preset(name)
    if not preset:
        return mat_path  # No preset, return whatever we have

    mat_name = mat_path.rsplit("/", 1)[-1] if mat_path else f"MAT_{name.replace('_', '').title()}"

    if preset["type"] == "textured":
        tex_path = get_texture(preset["texture"])
        if not tex_path:
            return None
        client.create_textured_material(
            mat_name, tex_path,
            roughness=preset.get("roughness", 0.5),
            metallic=preset.get("metallic", 0.0),
            tiling=preset.get("tiling", 1.0),
        )
    elif preset["type"] == "simple":
        color = preset["color"]
        client.send_command("create_simple_material", {
            "name": mat_name,
            "color": color,
        })

    time.sleep(0.5)  # Let shader compile
    return mat_path


# =========================================================================
# CLI: print library contents
# =========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Arcwright Texture Library")
    print("=" * 60)

    print(f"\nTextures ({len(TEXTURE_LIBRARY)}):")
    for name, path in sorted(TEXTURE_LIBRARY.items()):
        print(f"  {name:20s} -> {path}")

    print(f"\nMaterials ({len(MATERIAL_LIBRARY)}):")
    for name, path in sorted(MATERIAL_LIBRARY.items()):
        print(f"  {name:20s} -> {path}")

    print(f"\nPresets ({len(MATERIAL_PRESETS)}):")
    for name, preset in sorted(MATERIAL_PRESETS.items()):
        print(f"  {name:20s} -> {preset['type']}")

    print(f"\nBake Recipes ({len(BAKE_RECIPES)}):")
    for name, recipe in sorted(BAKE_RECIPES.items()):
        print(f"  {name:20s} -> {recipe['preset']} @ {recipe['resolution']}px")
