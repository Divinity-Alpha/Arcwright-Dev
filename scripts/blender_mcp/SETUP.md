# Arcwright — Blender MCP Setup Guide

> **Version:** 1.0
> **Port:** 13378 (Blender) alongside 13377 (UE5)

## Architecture

```
Claude Desktop
    ├── Arcwright UE MCP (port 13377) → Unreal Engine 5
    └── Blender MCP (port 13378) → Blender
```

Both run simultaneously. Claude sees all tools from both servers and can orchestrate between them.

## Installation

### 1. Install the Blender Addon

1. Open Blender
2. Edit → Preferences → Add-ons → Install from Disk
3. Select `blender_addon/blueprintllm_blender_server.py`
4. Enable "Arcwright Blender Server"
5. The server auto-starts on port 13378

Or manually: open the sidebar (N key) → Arcwright tab → Start Server

### 2. Configure Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "blueprint-llm": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    },
    "blender": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\blender_mcp\\blender_mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop.

### 3. Verify

```bash
# Test Blender connection
python blender_mcp_server.py --test

# Test from Python
from blender_client import BlenderClient
with BlenderClient() as c:
    print(c.health_check())
```

## Available Tools (22)

### Mesh Creation
| Tool | Description |
|---|---|
| `blender_create_mesh` | Create primitives: cube, sphere, cylinder, cone, plane, torus, monkey |
| `blender_create_custom_mesh` | Create mesh from raw vertices and faces |

### Object Operations
| Tool | Description |
|---|---|
| `blender_get_objects` | List all scene objects with transforms |
| `blender_delete_object` | Delete by name |
| `blender_duplicate_object` | Copy an object |
| `blender_set_transform` | Set location, rotation, scale |

### Modifiers
| Tool | Description |
|---|---|
| `blender_add_modifier` | Add: SUBSURF, MIRROR, BEVEL, ARRAY, BOOLEAN, SOLIDIFY, DECIMATE |
| `blender_remove_modifier` | Remove modifier by name |

### Materials
| Tool | Description |
|---|---|
| `blender_create_material` | Create Principled BSDF with color, metallic, roughness |
| `blender_assign_material` | Apply material to object |

### Edit Mode
| Tool | Description |
|---|---|
| `blender_extrude` | Extrude faces |
| `blender_bevel` | Bevel edges |
| `blender_subdivide` | Subdivide mesh |

### Export
| Tool | Description |
|---|---|
| `blender_export_fbx` | Export as FBX (for UE5 import) |
| `blender_export_obj` | Export as OBJ |
| `blender_export_gltf` | Export as glTF/GLB |

### Scene
| Tool | Description |
|---|---|
| `blender_get_scene_info` | Scene metadata |
| `blender_clear_scene` | Remove all objects |
| `blender_save_file` | Save .blend file |

### UV
| Tool | Description |
|---|---|
| `blender_smart_uv_project` | Auto UV unwrap |

## Cross-Tool Workflow Example

```
User: "Create a low-poly health crystal for my game"

Claude:
1. blender_clear_scene()
2. blender_create_mesh(type="cone", name="Crystal_Base", scale="0.5,0.5,1.2")
3. blender_create_material(name="CrystalGreen", color="0.1,0.9,0.3,1.0", roughness=0.2)
4. blender_assign_material("Crystal_Base", "CrystalGreen")
5. blender_add_modifier("Crystal_Base", "SUBSURF", properties={"levels": 1})
6. blender_smart_uv_project("Crystal_Base")
7. blender_export_fbx("C:/BlueprintLLM/exports/health_crystal.fbx")
8. [UE] import_static_mesh("C:/BlueprintLLM/exports/health_crystal.fbx", "SM_HealthCrystal")
9. [UE] create_blueprint_from_dsl(pickup_dsl)
10. [UE] add_component with mesh=SM_HealthCrystal
11. [UE] spawn_actor_at(...)
```

Steps 1-7 use Blender MCP. Steps 8-11 use UE MCP. Claude orchestrates both.

## File Structure

```
C:\BlueprintLLM\scripts\blender_mcp\
├── blender_addon/
│   └── blueprintllm_blender_server.py  # Blender addon (TCP server)
├── blender_client.py                    # Python TCP client
├── blender_mcp_server.py               # MCP stdio server for Claude Desktop
└── SETUP.md                             # This file
```
