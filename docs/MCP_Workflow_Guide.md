# Arcwright — Claude Desktop MCP Workflow Guide

> **Version:** 1.0
> **Last Updated:** 2026-03-05
> **Requires:** UE 5.7 Editor with Arcwright plugin, Claude Desktop with MCP config

This guide explains how to use Claude Desktop to build Unreal Engine games through natural conversation.

---

## Setup (One-Time)

### 1. Configure Claude Desktop

Add this to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "blueprint-llm": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

### 2. Launch UE Editor

```powershell
# Build the plugin (first time or after changes)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" ArcwrightTestEditor Win64 Development "C:\Junk\ArcwrightTest\ArcwrightTest.uproject"

# Launch with -skipcompile on the 5070 Ti (adapter 0)
& "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" "C:\Junk\ArcwrightTest\ArcwrightTest.uproject" -skipcompile -graphicsadapter=0 -nosplash -unattended -nopause

# Kill CrashReportClient in background loop
powershell -Command "while ($true) { Get-Process -Name 'CrashReportClient*' -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 10 }" &
```

Wait for the editor to fully load. The command server starts automatically on port 13377.

### 3. Verify Connection

In Claude Desktop, say:

> "Check if the UE Editor connection is working."

Claude should call `health_check` and report the server version and UE engine version.

---

## What You Can Do

### Create Blueprints

> "Create a Blueprint called BP_RotatingCube that continuously rotates at 45 degrees per second on the Yaw axis."

Claude generates DSL, sends it through the pipeline, and the Blueprint appears in the UE content browser. It compiles automatically.

### Add Visual Components

> "Add a cube mesh to BP_RotatingCube and make it blue."

Claude calls `add_component` to add a StaticMesh, then `create_material_instance` and `apply_material` to color it.

### Place Actors in the Level

> "Spawn 3 copies of BP_RotatingCube in a row, spaced 500 units apart, starting at position 0,0,100."

Claude calls `spawn_actor_at` three times with calculated positions.

### Edit Existing Blueprints

> "Add a Delay node of 2 seconds to BP_RotatingCube between BeginPlay and the rotation."

Claude uses `add_node`, `remove_connection`, and `add_connection` to surgically modify the Blueprint graph.

### Inspect Blueprints

> "What nodes and connections does BP_RotatingCube have?"

Claude calls `get_blueprint_info` and describes the structure.

### Manage the Level

> "Move the first rotating cube to position 100, 200, 300."
> "Delete the second rotating cube."
> "What actors are in the level right now?"

Claude uses `move_actor`, `delete_actor`, and `get_actors`.

### Save the Project

> "Save everything."

Claude calls `save_all` to persist all changes to disk.

### Duplicate and Modify

> "Make a copy of BP_RotatingCube called BP_FastCube and make it rotate twice as fast."

Claude uses `duplicate_blueprint` then `set_node_param` to change the rotation speed.

---

## Example Conversations

### Build a Simple Game

> **You:** "I want to make a simple game. Create a pickup that the player can collect. When they walk through it, it should print 'Collected!' and disappear. Make it a gold sphere."
>
> **Claude:** Creates BP_Pickup with overlap → print → destroy logic, adds BoxCollision with overlap events, adds sphere mesh, creates gold material, applies it. Reports: "BP_Pickup created with 3 nodes, collision, gold sphere mesh. Ready to place in the level."
>
> **You:** "Place 5 of them in a line starting at 0,0,100, each 300 units apart."
>
> **Claude:** Spawns 5 instances at (0,0,100), (0,300,100), (0,600,100), (0,900,100), (0,1200,100).
>
> **You:** "Now add a red danger zone between pickups 2 and 3 that prints 'Danger!' every second while the player is inside."
>
> **Claude:** Creates BP_DangerZone with overlap → timer → custom event pattern, adds large red cube collision/mesh, spawns at (0,450,100).
>
> **You:** "Save the project."
>
> **Claude:** Calls save_all.

### Iterate on a Blueprint

> **You:** "What's in BP_Pickup right now?"
>
> **Claude:** Calls get_blueprint_info, reports nodes, connections, variables.
>
> **You:** "Add a 0.5 second delay between the print and the destroy."
>
> **Claude:** Adds Delay node, rewires connections.
>
> **You:** "Actually, also add a sound effect before the print. Use PlaySoundAtLocation."
>
> **Claude:** Adds node, rewires exec chain.

---

## Available Tools (27)

### Blueprint Creation & Editing
| Tool | What It Does |
|---|---|
| `create_blueprint_from_dsl` | DSL text → compiled Blueprint |
| `import_blueprint_ir` | Import .blueprint.json IR file |
| `get_blueprint_info` | Query nodes, connections, variables |
| `duplicate_blueprint` | Copy a Blueprint to a new name |
| `add_node` | Add a single node to a Blueprint |
| `remove_node` | Remove a node and its connections |
| `add_connection` | Wire two pins together |
| `remove_connection` | Disconnect two pins |
| `set_node_param` | Set a pin's default value |
| `set_variable_default` | Set a variable's default value |

### Components & Visuals
| Tool | What It Does |
|---|---|
| `add_component` | Add collision, mesh, light, etc. |
| `get_components` | List a Blueprint's components |
| `remove_component` | Remove a component |
| `set_component_property` | Change component settings |
| `create_material_instance` | Create a colored/textured material |
| `apply_material` | Apply material to a mesh component |

### Level Management
| Tool | What It Does |
|---|---|
| `spawn_actor` | Place an actor in the level |
| `get_actors` | List all level actors |
| `move_actor` | Change an actor's position/rotation/scale |
| `delete_actor` | Remove an actor from the level |
| `get_level_info` | Level metadata and actor census |

### Project Management
| Tool | What It Does |
|---|---|
| `save_all` | Save all modified assets and level |
| `save_level` | Save just the current level |
| `health_check` | Verify UE Editor connection |
| `get_output_log` | Read recent UE output log |
| `play_in_editor` | Start Play In Editor session* |
| `stop_play` | Stop Play In Editor session* |

*PIE has a known limitation — the request queues but may not execute automatically in UE 5.7. User may need to click Play manually.

---

## Tips for Best Results

### Be Specific About Structure
Instead of "make something that shoots," say "create a Blueprint with an InputAction for Fire that spawns a BP_Projectile at the actor's location."

### Name Things Clearly
Use BP_ prefix for Blueprints, descriptive component names (PickupCollision, HazardMesh), and meaningful variable names (Health, Score, IsActive).

### Build Incrementally
Create the Blueprint first, verify it compiled, then add components, then materials, then place in the level. If something breaks, you know which step failed.

### Check Your Work
Ask "what does BP_MyActor look like?" to inspect before placing. Ask "what actors are in the level?" to verify placement.

### Save Often
Say "save everything" after major changes. UE Editor crashes lose unsaved work.

---

## Known Limitations

1. **No mesh creation.** The pipeline assigns existing meshes (cubes, spheres, etc.) but cannot create custom 3D models. Use UE's built-in shapes or import models manually.

2. **No custom materials with textures.** Material instances can set colors and scalar parameters but cannot reference texture assets. For textured materials, create them manually in UE.

3. **Cast To Character requires a Character pawn.** The default UE test project uses DefaultPawn. CastToCharacter will always fail. Wire overlap events directly or set up a Character Blueprint.

4. **PIE automation is limited.** Play In Editor cannot be reliably started programmatically in UE 5.7. Click Play manually when testing.

5. **Component changes need actor re-spawn.** After adding components to a Blueprint, existing instances in the level don't update. Delete and re-spawn them.

6. **DSL covers event graphs only.** Construction scripts, animation graphs, and behavior trees are not yet supported.

---

## Troubleshooting

### "Cannot connect to UE Editor"
- Is UE Editor running?
- Did you launch with `-skipcompile`?
- Check if port 13377 is open: `python scripts/mcp_client/verify.py`

### "Blueprint failed to compile"
- Check the DSL syntax (use the compliance checker: `python scripts/compliance_checker.py --text "..."`)
- Look for unmapped node types in the error message
- Ensure all variables used in GetVar/SetVar are declared

### "Overlap events don't fire"
- Does the Blueprint have a collision component with `generate_overlap_events: true`?
- Is the player pawn a Character (not DefaultPawn)?

### "Material doesn't show"
- Did you re-spawn the actor after applying the material?
- Is the material path correct? (should be `/Game/MI_Name` for created instances)

### "Actor not visible"
- Does the Blueprint have a StaticMesh component?
- Is the mesh path correct? (`/Engine/BasicShapes/Sphere.Sphere`)
- Check the actor's position — it might be underground or far away

---

*Built with Arcwright v3.4 — 99.4% DSL syntax accuracy, 21 TCP commands, 27 MCP tools.*
