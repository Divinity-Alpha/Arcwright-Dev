"""
Arcwright — Blender MCP Server
MCP stdio server for Claude Desktop. Wraps Blender TCP client.
Mirrors scripts/mcp_server/server.py for the UE plugin.

Usage:
    python blender_mcp_server.py          # Normal MCP mode (stdio)
    python blender_mcp_server.py --test   # Quick self-test

Claude Desktop config (%APPDATA%/Claude/claude_desktop_config.json):
{
    "mcpServers": {
        "blender": {
            "command": "python",
            "args": ["C:\\BlueprintLLM\\scripts\\blender_mcp\\blender_mcp_server.py"]
        }
    }
}
"""

import sys
import os
import json

# Add parent for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_client import BlenderClient, BlenderClientError

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)


mcp = FastMCP("blender_mcp")


def _client():
    """Create a connected Blender client."""
    c = BlenderClient()
    c.connect()
    return c


def _run(fn):
    """Execute a client operation with error handling."""
    try:
        c = _client()
        try:
            result = fn(c)
            return json.dumps(result, indent=2)
        finally:
            c.close()
    except BlenderClientError as e:
        return json.dumps({"error": str(e)})
    except ConnectionRefusedError:
        return json.dumps({"error": "Cannot connect to Blender. Is it running with the Arcwright addon enabled?"})


# ─── Health ──────────────────────────────────────────────────────────────────

@mcp.tool()
def blender_health_check() -> str:
    """Check if Blender is running and the command server is active."""
    return _run(lambda c: c.health_check())


# ─── Mesh Creation ───────────────────────────────────────────────────────────

@mcp.tool()
def blender_create_mesh(mesh_type: str = "cube", name: str = "", location: str = "0,0,0", scale: str = "1,1,1", size: float = 2.0, radius: float = 1.0, depth: float = 2.0) -> str:
    """Create a primitive mesh in Blender. Types: cube, sphere, cylinder, cone, plane, torus, monkey."""
    loc = [float(x) for x in location.split(",")]
    sc = [float(x) for x in scale.split(",")]
    return _run(lambda c: c.create_mesh(mesh_type, name=name, location=loc, scale=sc, size=size, radius=radius, depth=depth))


@mcp.tool()
def blender_create_custom_mesh(name: str, vertices: str, faces: str) -> str:
    """Create a mesh from vertices and faces. Vertices: '[[0,0,0],[1,0,0],[1,1,0]]'. Faces: '[[0,1,2]]'."""
    verts = json.loads(vertices)
    f = json.loads(faces)
    return _run(lambda c: c.create_custom_mesh(name, verts, f))


# ─── Object Operations ──────────────────────────────────────────────────────

@mcp.tool()
def blender_get_objects(obj_type: str = "") -> str:
    """List all objects in the Blender scene. Optional filter: MESH, LIGHT, CAMERA, EMPTY."""
    return _run(lambda c: c.get_objects(obj_type or None))


@mcp.tool()
def blender_delete_object(name: str) -> str:
    """Delete a Blender object by name."""
    return _run(lambda c: c.delete_object(name))


@mcp.tool()
def blender_duplicate_object(name: str, new_name: str = "") -> str:
    """Duplicate a Blender object. Optionally specify a new name."""
    return _run(lambda c: c.duplicate_object(name, new_name))


@mcp.tool()
def blender_set_transform(name: str, location: str = "", rotation: str = "", scale: str = "") -> str:
    """Set object location, rotation (degrees), and/or scale. Values as 'x,y,z'."""
    loc = [float(x) for x in location.split(",")] if location else None
    rot = [float(x) for x in rotation.split(",")] if rotation else None
    sc = [float(x) for x in scale.split(",")] if scale else None
    return _run(lambda c: c.set_transform(name, location=loc, rotation=rot, scale=sc))


# ─── Modifiers ───────────────────────────────────────────────────────────────

@mcp.tool()
def blender_add_modifier(name: str, modifier_type: str, modifier_name: str = "", properties: str = "{}") -> str:
    """Add a modifier to an object. Types: SUBSURF, MIRROR, BEVEL, ARRAY, BOOLEAN, SOLIDIFY, DECIMATE. Properties as JSON."""
    props = json.loads(properties)
    return _run(lambda c: c.add_modifier(name, modifier_type, modifier_name, props))


@mcp.tool()
def blender_remove_modifier(name: str, modifier_name: str) -> str:
    """Remove a modifier from an object."""
    return _run(lambda c: c.remove_modifier(name, modifier_name))


# ─── Materials ───────────────────────────────────────────────────────────────

@mcp.tool()
def blender_create_material(name: str, color: str = "0.8,0.8,0.8,1.0", metallic: float = 0.0, roughness: float = 0.5) -> str:
    """Create a Principled BSDF material with color (r,g,b,a), metallic, and roughness."""
    c_vals = [float(x) for x in color.split(",")]
    return _run(lambda c: c.create_material(name, c_vals, metallic, roughness))


@mcp.tool()
def blender_assign_material(object_name: str, material_name: str, slot: int = 0) -> str:
    """Assign an existing material to an object."""
    return _run(lambda c: c.assign_material(object_name, material_name, slot))


# ─── Edit Mode ───────────────────────────────────────────────────────────────

@mcp.tool()
def blender_extrude(name: str, value: float = 1.0) -> str:
    """Extrude all faces of a mesh object by a value along Z axis."""
    return _run(lambda c: c.extrude(name, value))


@mcp.tool()
def blender_bevel(name: str, width: float = 0.1, segments: int = 3) -> str:
    """Bevel all edges of a mesh object."""
    return _run(lambda c: c.bevel(name, width, segments))


@mcp.tool()
def blender_subdivide(name: str, cuts: int = 1) -> str:
    """Subdivide a mesh. More cuts = more geometry."""
    return _run(lambda c: c.subdivide(name, cuts))


# ─── Export ──────────────────────────────────────────────────────────────────

@mcp.tool()
def blender_export_fbx(filepath: str, selected_only: bool = False, apply_modifiers: bool = True) -> str:
    """Export objects as FBX file. Used to import into UE5."""
    return _run(lambda c: c.export_fbx(filepath, selected_only, apply_modifiers))


@mcp.tool()
def blender_export_obj(filepath: str) -> str:
    """Export objects as OBJ file."""
    return _run(lambda c: c.export_obj(filepath))


@mcp.tool()
def blender_export_gltf(filepath: str) -> str:
    """Export objects as glTF/GLB file."""
    return _run(lambda c: c.export_gltf(filepath))


# ─── Scene ───────────────────────────────────────────────────────────────────

@mcp.tool()
def blender_get_scene_info() -> str:
    """Get Blender scene information: objects, materials, render settings."""
    return _run(lambda c: c.get_scene_info())


@mcp.tool()
def blender_clear_scene(keep_camera: bool = True, keep_lights: bool = False) -> str:
    """Remove all objects from the scene. Optionally keep camera and lights."""
    return _run(lambda c: c.clear_scene(keep_camera, keep_lights))


@mcp.tool()
def blender_save_file(filepath: str = "") -> str:
    """Save the Blender file. If filepath provided, save as new file."""
    return _run(lambda c: c.save_file(filepath))


# ─── UV ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def blender_smart_uv_project(name: str, angle_limit: float = 66.0) -> str:
    """Auto UV unwrap a mesh object using Smart UV Project."""
    return _run(lambda c: c.smart_uv_project(name, angle_limit))


# ─── Procedural Textures ─────────────────────────────────────────────────────

@mcp.tool()
def blender_create_procedural_material(preset: str, name: str = "", color1: str = "", color2: str = "", scale: float = 0, roughness: float = 0) -> str:
    """Create a procedural material from a preset. Presets: stone, brick, wood, metal, marble, lava, ice, fabric, energy, terrain. Colors as 'r,g,b,a'."""
    params = {}
    if color1:
        params["color1"] = [float(x) for x in color1.split(",")]
    if color2:
        params["color2"] = [float(x) for x in color2.split(",")]
    if scale > 0:
        params["scale"] = scale
    if roughness > 0:
        params["roughness"] = roughness
    return _run(lambda c: c.create_procedural_material(preset, name=name, **params))


@mcp.tool()
def blender_bake_material_to_texture(object_name: str, material_name: str, output_path: str, resolution: int = 1024, bake_type: str = "DIFFUSE") -> str:
    """Bake a procedural material to an image texture file (PNG). Requires a UV-mapped object with the material assigned. bake_type: DIFFUSE, ROUGHNESS, NORMAL, EMIT."""
    return _run(lambda c: c.bake_material_to_texture(object_name, material_name, output_path, resolution, bake_type))


@mcp.tool()
def blender_list_procedural_presets() -> str:
    """List all available procedural material presets with descriptions."""
    return _run(lambda c: c.list_procedural_presets())


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("Blender MCP Server — Tool List:")
        tools = [name for name in dir() if name.startswith("blender_") and callable(eval(name))]
        for t in sorted(tools):
            print(f"  {t}")
        print(f"\nTotal: {len(tools)} tools")
        print("\nTesting connection...")
        try:
            c = BlenderClient()
            c.connect()
            result = c.health_check()
            print(f"  Connected: Blender {result.get('blender_version', '?')}")
            c.close()
        except Exception as e:
            print(f"  Not connected: {e}")
    else:
        mcp.run(transport="stdio")
