"""
Arcwright — Blender Procedural Texture Commands
===================================================
Extension handlers for the Blender TCP server that create
procedural materials and bake them to image textures.

These create genuinely good-looking materials using Blender's
node-based shader system — no external images needed.

Add these handlers to BlenderCommandServer.handlers dict.
"""


def register_procedural_handlers(server):
    """Register all procedural texture handlers on a BlenderCommandServer instance."""
    server.handlers.update({
        "blender_create_procedural_material": server.handle_create_procedural_material,
        "blender_bake_material_to_texture": server.handle_bake_material_to_texture,
        "blender_list_procedural_presets": server.handle_list_procedural_presets,
    })


# ─── Procedural Material Presets ─────────────────────────────────────────────
# Each preset is a function that builds a complete node tree

PRESETS = {}


def preset(name, description):
    """Decorator to register a preset."""
    def decorator(fn):
        PRESETS[name] = {"fn": fn, "description": description}
        return fn
    return decorator


@preset("stone", "Rough stone surface with cracks and variation — walls, floors, ruins")
def build_stone(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color1 = params.get("color1", (0.25, 0.22, 0.2, 1.0))
    color2 = params.get("color2", (0.15, 0.13, 0.12, 1.0))
    scale = params.get("scale", 5.0)
    crack_amount = params.get("crack_amount", 0.5)
    roughness = params.get("roughness", 0.85)
    
    # Noise for base color variation
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.7
    noise.location = (-600, 300)
    
    # Voronoi for crack pattern
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = scale * 2
    voronoi.feature = "DISTANCE_TO_EDGE"
    voronoi.location = (-600, 0)
    
    # Color ramp for base color
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = color1
    ramp.color_ramp.elements[1].color = color2
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[1].position = 0.7
    ramp.location = (-300, 300)
    
    # Mix noise into color
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    
    # Crack darkening
    crack_ramp = nodes.new("ShaderNodeValToRGB")
    crack_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    crack_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    crack_ramp.color_ramp.elements[0].position = 0.0
    crack_ramp.color_ramp.elements[1].position = crack_amount
    crack_ramp.location = (-300, 0)
    
    links.new(voronoi.outputs["Distance"], crack_ramp.inputs["Fac"])
    
    # Multiply color by crack mask
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0  # Factor
    mix.location = (-100, 200)
    
    links.new(ramp.outputs["Color"], mix.inputs[6])  # Color1
    links.new(crack_ramp.outputs["Color"], mix.inputs[7])  # Color2
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])  # Result
    
    # Roughness variation from noise
    rough_noise = nodes.new("ShaderNodeTexNoise")
    rough_noise.inputs["Scale"].default_value = scale * 3
    rough_noise.inputs["Detail"].default_value = 4.0
    rough_noise.location = (-600, -200)
    
    rough_ramp = nodes.new("ShaderNodeMapRange")
    rough_ramp.inputs["From Min"].default_value = 0.0
    rough_ramp.inputs["From Max"].default_value = 1.0
    rough_ramp.inputs["To Min"].default_value = roughness - 0.1
    rough_ramp.inputs["To Max"].default_value = roughness + 0.1
    rough_ramp.location = (-300, -200)
    
    links.new(rough_noise.outputs["Fac"], rough_ramp.inputs["Value"])
    links.new(rough_ramp.outputs["Result"], bsdf.inputs["Roughness"])
    
    # Bump from voronoi for surface detail
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    bump.location = (-100, -100)
    
    links.new(voronoi.outputs["Distance"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    
    bsdf.inputs["Metallic"].default_value = 0.0


@preset("brick", "Brick wall pattern with mortar lines — buildings, walls, floors")
def build_brick(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    brick_color = params.get("color1", (0.35, 0.15, 0.08, 1.0))
    mortar_color = params.get("color2", (0.6, 0.55, 0.5, 1.0))
    scale = params.get("scale", 3.0)
    
    brick = nodes.new("ShaderNodeTexBrick")
    brick.inputs["Scale"].default_value = scale
    brick.inputs["Color1"].default_value = brick_color
    brick.inputs["Color2"].default_value = (brick_color[0]*0.8, brick_color[1]*0.8, brick_color[2]*0.8, 1.0)
    brick.inputs["Mortar"].default_value = mortar_color
    brick.inputs["Mortar Size"].default_value = 0.02
    brick.inputs["Mortar Smooth"].default_value = 0.1
    brick.location = (-400, 200)
    
    links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    
    # Roughness variation
    rough_map = nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value = 0.0
    rough_map.inputs["From Max"].default_value = 1.0
    rough_map.inputs["To Min"].default_value = 0.7
    rough_map.inputs["To Max"].default_value = 0.95
    rough_map.location = (-200, -100)
    
    links.new(brick.outputs["Fac"], rough_map.inputs["Value"])
    links.new(rough_map.outputs["Result"], bsdf.inputs["Roughness"])
    
    # Bump from brick pattern
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    bump.location = (-100, -200)
    
    links.new(brick.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


@preset("wood", "Wood grain pattern — floors, furniture, crates, doors")
def build_wood(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color1 = params.get("color1", (0.4, 0.22, 0.08, 1.0))
    color2 = params.get("color2", (0.25, 0.13, 0.05, 1.0))
    scale = params.get("scale", 3.0)
    
    # Wave texture for grain
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'RINGS'
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 8.0
    wave.inputs["Detail"].default_value = 3.0
    wave.inputs["Detail Scale"].default_value = 1.5
    wave.location = (-600, 200)
    
    # Noise to break up the regularity
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale * 5
    noise.inputs["Detail"].default_value = 5.0
    noise.location = (-600, 0)
    
    # Color ramp for wood tones
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = color1
    ramp.color_ramp.elements[1].color = color2
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.65
    ramp.location = (-300, 200)
    
    # Mix wave and noise
    mix_fac = nodes.new("ShaderNodeMix")
    mix_fac.data_type = 'FLOAT'
    mix_fac.inputs[0].default_value = 0.3
    mix_fac.location = (-450, 100)
    
    links.new(wave.outputs["Fac"], mix_fac.inputs[2])
    links.new(noise.outputs["Fac"], mix_fac.inputs[3])
    links.new(mix_fac.outputs[0], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    
    bsdf.inputs["Roughness"].default_value = params.get("roughness", 0.6)
    bsdf.inputs["Metallic"].default_value = 0.0
    
    # Subtle bump
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    bump.location = (-100, -100)
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


@preset("metal", "Brushed or worn metal — weapons, armor, machinery, sci-fi")
def build_metal(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color = params.get("color1", (0.6, 0.6, 0.65, 1.0))
    wear = params.get("wear", 0.3)
    
    # Base noise for color variation
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = params.get("scale", 20.0)
    noise.inputs["Detail"].default_value = 10.0
    noise.inputs["Roughness"].default_value = 0.5
    noise.location = (-500, 200)
    
    # Color ramp for subtle variation
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = color
    ramp.color_ramp.elements[1].color = (color[0]*0.7, color[1]*0.7, color[2]*0.7, 1.0)
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[1].position = 0.6
    ramp.location = (-250, 200)
    
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    
    bsdf.inputs["Metallic"].default_value = 0.95
    
    # Scratches/wear via voronoi
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = 50.0
    voronoi.feature = "DISTANCE_TO_EDGE"
    voronoi.location = (-500, -100)
    
    rough_ramp = nodes.new("ShaderNodeMapRange")
    rough_ramp.inputs["From Min"].default_value = 0.0
    rough_ramp.inputs["From Max"].default_value = 0.1
    rough_ramp.inputs["To Min"].default_value = 0.15
    rough_ramp.inputs["To Max"].default_value = 0.4 + wear
    rough_ramp.location = (-250, -100)
    
    links.new(voronoi.outputs["Distance"], rough_ramp.inputs["Value"])
    links.new(rough_ramp.outputs["Result"], bsdf.inputs["Roughness"])
    
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.1
    bump.location = (-100, -200)
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


@preset("marble", "Polished marble surface — temple floors, pillars, statues")
def build_marble(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color1 = params.get("color1", (0.9, 0.88, 0.85, 1.0))
    color2 = params.get("color2", (0.3, 0.28, 0.35, 1.0))
    scale = params.get("scale", 3.0)
    
    # Wave for marble veins
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'DIAGONAL'
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 10.0
    wave.inputs["Detail"].default_value = 5.0
    wave.inputs["Detail Scale"].default_value = 2.0
    wave.location = (-500, 200)
    
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = color1
    ramp.color_ramp.elements[1].color = color2
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[1].position = 0.6
    ramp.location = (-250, 200)
    
    links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    
    bsdf.inputs["Roughness"].default_value = params.get("roughness", 0.15)
    bsdf.inputs["Metallic"].default_value = 0.0
    
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    bump.location = (-100, -100)
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


@preset("lava", "Glowing lava/magma — volcanic, fire effects, energy")
def build_lava(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    hot_color = params.get("color1", (1.0, 0.3, 0.0, 1.0))
    cool_color = params.get("color2", (0.05, 0.02, 0.01, 1.0))
    scale = params.get("scale", 4.0)
    glow = params.get("glow", 5.0)
    
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = scale
    voronoi.location = (-500, 200)
    
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale * 2
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Distortion"].default_value = 2.0
    noise.location = (-500, 0)
    
    # Mix voronoi and noise
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'FLOAT'
    mix.inputs[0].default_value = 0.5
    mix.location = (-300, 100)
    links.new(voronoi.outputs["Distance"], mix.inputs[2])
    links.new(noise.outputs["Fac"], mix.inputs[3])
    
    # Color ramp for hot/cool
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = hot_color
    ramp.color_ramp.elements[1].color = cool_color
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[1].position = 0.6
    ramp.location = (-100, 200)
    
    links.new(mix.outputs[0], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    
    # Emission for glow
    emit_ramp = nodes.new("ShaderNodeValToRGB")
    emit_ramp.color_ramp.elements[0].color = (hot_color[0]*glow, hot_color[1]*glow, hot_color[2]*glow, 1.0)
    emit_ramp.color_ramp.elements[1].color = (0, 0, 0, 1.0)
    emit_ramp.color_ramp.elements[0].position = 0.0
    emit_ramp.color_ramp.elements[1].position = 0.4
    emit_ramp.location = (-100, 0)
    
    links.new(mix.outputs[0], emit_ramp.inputs["Fac"])
    links.new(emit_ramp.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.8


@preset("ice", "Frozen ice surface — arctic, frozen lake, ice cave")
def build_ice(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color1 = params.get("color1", (0.7, 0.85, 0.95, 1.0))
    color2 = params.get("color2", (0.3, 0.5, 0.7, 1.0))
    scale = params.get("scale", 5.0)
    
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = scale
    voronoi.feature = "F1"
    voronoi.location = (-500, 200)
    
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale * 3
    noise.inputs["Detail"].default_value = 8.0
    noise.location = (-500, 0)
    
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = color1
    ramp.color_ramp.elements[1].color = color2
    ramp.location = (-250, 200)
    
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'FLOAT'
    mix.inputs[0].default_value = 0.4
    mix.location = (-400, 100)
    links.new(voronoi.outputs["Distance"], mix.inputs[2])
    links.new(noise.outputs["Fac"], mix.inputs[3])
    links.new(mix.outputs[0], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    
    bsdf.inputs["Roughness"].default_value = params.get("roughness", 0.05)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["IOR"].default_value = 1.31  # Ice IOR
    bsdf.inputs["Transmission Weight"].default_value = 0.3  # Slight translucency


@preset("fabric", "Woven fabric texture — cloth, curtains, banners, clothing")
def build_fabric(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color = params.get("color1", (0.3, 0.1, 0.1, 1.0))
    scale = params.get("scale", 30.0)
    
    # Checker for weave pattern
    checker = nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = scale
    checker.inputs["Color1"].default_value = color
    checker.inputs["Color2"].default_value = (color[0]*0.85, color[1]*0.85, color[2]*0.85, 1.0)
    checker.location = (-400, 200)
    
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale * 5
    noise.inputs["Detail"].default_value = 3.0
    noise.location = (-400, 0)
    
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.inputs[0].default_value = 0.1
    mix.location = (-200, 100)
    links.new(checker.outputs["Color"], mix.inputs[6])
    links.new(noise.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    
    bsdf.inputs["Roughness"].default_value = params.get("roughness", 0.9)
    bsdf.inputs["Metallic"].default_value = 0.0
    
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.2
    bump.location = (-100, -100)
    links.new(checker.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


@preset("energy", "Glowing energy/magic effect — shields, portals, power-ups, sci-fi")
def build_energy(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color = params.get("color1", (0.0, 0.5, 1.0, 1.0))
    glow = params.get("glow", 10.0)
    scale = params.get("scale", 5.0)
    
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = scale
    voronoi.feature = "DISTANCE_TO_EDGE"
    voronoi.location = (-500, 200)
    
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale * 3
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Distortion"].default_value = 3.0
    noise.location = (-500, 0)
    
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = 'FLOAT'
    mix.inputs[0].default_value = 0.5
    mix.location = (-300, 100)
    links.new(voronoi.outputs["Distance"], mix.inputs[2])
    links.new(noise.outputs["Fac"], mix.inputs[3])
    
    # Base color dark
    bsdf.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1.0)
    
    # Emission is where the magic happens
    emit_ramp = nodes.new("ShaderNodeValToRGB")
    emit_ramp.color_ramp.elements[0].color = (color[0]*glow, color[1]*glow, color[2]*glow, 1.0)
    emit_ramp.color_ramp.elements[1].color = (0, 0, 0, 1.0)
    emit_ramp.color_ramp.elements[0].position = 0.0
    emit_ramp.color_ramp.elements[1].position = 0.5
    emit_ramp.location = (-100, 100)
    
    links.new(mix.outputs[0], emit_ramp.inputs["Fac"])
    links.new(emit_ramp.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.1
    bsdf.inputs["Alpha"].default_value = 0.7
    mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else None


@preset("terrain", "Natural ground — dirt, grass, sand, earth")
def build_terrain(mat, params):
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    
    color1 = params.get("color1", (0.2, 0.15, 0.08, 1.0))  # Dirt
    color2 = params.get("color2", (0.15, 0.25, 0.05, 1.0))  # Grass tint
    scale = params.get("scale", 8.0)
    
    noise1 = nodes.new("ShaderNodeTexNoise")
    noise1.inputs["Scale"].default_value = scale
    noise1.inputs["Detail"].default_value = 10.0
    noise1.inputs["Roughness"].default_value = 0.6
    noise1.location = (-600, 300)
    
    noise2 = nodes.new("ShaderNodeTexNoise")
    noise2.inputs["Scale"].default_value = scale * 4
    noise2.inputs["Detail"].default_value = 5.0
    noise2.location = (-600, 100)
    
    musgrave = nodes.new("ShaderNodeTexMusgrave") if hasattr(nodes, 'new') else None
    # Musgrave may not exist in all Blender versions — use noise as fallback
    
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = color1
    ramp.color_ramp.elements[1].color = color2
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.7
    ramp.location = (-300, 300)
    
    links.new(noise1.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    
    bsdf.inputs["Roughness"].default_value = params.get("roughness", 0.9)
    
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.location = (-100, -100)
    links.new(noise2.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])


# ─── Handler Implementations ─────────────────────────────────────────────────

def handle_create_procedural_material(self, params):
    """Create a procedural material from a preset.
    
    Params:
        preset: str — one of: stone, brick, wood, metal, marble, lava, ice, fabric, energy, terrain
        name: str — material name
        color1: [r,g,b,a] — primary color (meaning varies by preset)
        color2: [r,g,b,a] — secondary color
        scale: float — texture scale (higher = smaller pattern)
        roughness: float — surface roughness override
        Additional params vary by preset (crack_amount, wear, glow, etc.)
    """
    import bpy
    
    preset_name = params.get("preset", "stone")
    mat_name = params.get("name", f"M_Procedural_{preset_name}")
    
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    
    # Create material
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    
    # Clear default nodes except output and BSDF
    for node in list(mat.node_tree.nodes):
        if node.type not in ('OUTPUT_MATERIAL', 'BSDF_PRINCIPLED'):
            mat.node_tree.nodes.remove(node)
    
    # Parse color params
    for key in ("color1", "color2"):
        if key in params:
            c = params[key]
            if isinstance(c, dict):
                params[key] = (c.get("r", 0.5), c.get("g", 0.5), c.get("b", 0.5), c.get("a", 1.0))
            elif isinstance(c, list):
                params[key] = tuple(c) if len(c) == 4 else tuple(c) + (1.0,)
    
    # Build the node tree
    PRESETS[preset_name]["fn"](mat, params)
    
    return {
        "name": mat.name,
        "preset": preset_name,
        "node_count": len(mat.node_tree.nodes),
    }


def handle_bake_material_to_texture(self, params):
    """Bake a procedural material to an image texture for export.
    
    Params:
        object_name: str — object to bake from (must have UVs)
        material_name: str — material to bake
        output_path: str — save path for the image
        resolution: int — texture resolution (default 1024)
        bake_type: str — DIFFUSE, ROUGHNESS, NORMAL, EMIT (default DIFFUSE)
    """
    import bpy
    
    obj_name = params.get("object_name", "")
    mat_name = params.get("material_name", "")
    output_path = params.get("output_path", "")
    resolution = params.get("resolution", 1024)
    bake_type = params.get("bake_type", "DIFFUSE").upper()
    
    if not output_path:
        raise ValueError("output_path is required")
    
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        raise ValueError(f"Object '{obj_name}' not found")
    
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        raise ValueError(f"Material '{mat_name}' not found")
    
    # Ensure object has the material
    if mat.name not in [slot.material.name for slot in obj.material_slots if slot.material]:
        obj.data.materials.append(mat)
    
    # Create bake image
    img = bpy.data.images.new("BakeTarget", resolution, resolution)
    
    # Add image texture node to material for bake target
    img_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    img_node.image = img
    mat.node_tree.nodes.active = img_node
    
    # Set render engine to Cycles for baking
    original_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.cycles.device = 'CPU'
    
    # Select object
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Bake
    bake_settings = {
        "DIFFUSE": {"type": "DIFFUSE", "pass_filter": {'COLOR'}},
        "ROUGHNESS": {"type": "ROUGHNESS"},
        "NORMAL": {"type": "NORMAL"},
        "EMIT": {"type": "EMIT"},
    }
    
    settings = bake_settings.get(bake_type, {"type": "DIFFUSE"})
    
    if bake_type == "DIFFUSE":
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={'COLOR'})
    else:
        bpy.ops.object.bake(type=settings["type"])
    
    # Save image
    img.filepath_raw = output_path
    img.file_format = 'PNG'
    img.save()
    
    # Cleanup
    mat.node_tree.nodes.remove(img_node)
    bpy.context.scene.render.engine = original_engine
    
    return {
        "output_path": output_path,
        "resolution": resolution,
        "bake_type": bake_type,
    }


def handle_list_procedural_presets(self, params):
    """List all available procedural material presets."""
    return {
        "presets": {name: info["description"] for name, info in PRESETS.items()},
        "count": len(PRESETS),
    }


# Monkey-patch the handlers onto the server class
import types

def _patch_server(server_class):
    """Add procedural handlers to a BlenderCommandServer class."""
    server_class.handle_create_procedural_material = handle_create_procedural_material
    server_class.handle_bake_material_to_texture = handle_bake_material_to_texture
    server_class.handle_list_procedural_presets = handle_list_procedural_presets
