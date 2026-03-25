# 5-Minute Quickstart

In 5 minutes, you will build a playable game level entirely from conversation with Claude Desktop. No manual Blueprint editing. No drag-and-drop. Just describe what you want, and Arcwright makes it real inside Unreal Engine.

---

## What You'll Build

A first-person arena with dark indoor lighting, a stone floor, brick walls on all four sides, eight gold coins arranged in a circle, four health pickups in the corners, three patrol enemies, and a score system. You walk around, collect coins, grab health, and dodge enemies -- all built from five chat messages.

---

## Before You Start

Make sure these three things are ready:

- **UE5 project with Arcwright plugin installed** -- the plugin folder lives at `YourProject/Plugins/Arcwright/` and the editor is running with `-skipcompile -nosplash` flags.
- **Claude Desktop configured with the Arcwright MCP server** -- see [Setting Up Claude Desktop](setup_claude_desktop.md) if you haven't done this yet.
- **The Arcwright MCP server can reach your editor** -- Claude Desktop should show "arcwright" in its MCP connections list.

That is all you need. No Python knowledge. No C++ builds. No Blueprint graph editing.

---

## Minute 1: Set Up the Scene

Paste this into Claude Desktop:

```
Set up a playable FPS scene with dark indoor lighting, a large stone floor, and save everything.
```

**What happens behind the scenes:** Claude calls `setup_playable_scene`, a compound tool that chains together five commands in one shot -- `setup_scene_lighting` (directional light, sky light, fog with the `indoor_dark` preset), `spawn_actor_at` (a scaled Plane mesh for the floor), `create_simple_material` (stone color and roughness), `set_game_mode` (first-person controls), and `save_all`. Your viewport fills with a lit, walkable arena floor in about two seconds.

---

## Minute 2: Create Game Objects

Paste this:

```
Create these Blueprints:
1. A health pickup called BP_HealthPickup that prints "Healed!" on overlap and destroys itself
2. A gold coin called BP_GoldCoin that prints "+10 Points!" on overlap and destroys itself
```

**What happens:** Claude calls `create_blueprint` twice to create the two actor Blueprints. For each one, it then calls `add_nodes_batch` and `add_connections_batch` to wire up the logic graph: Event ActorBeginOverlap flows into PrintString, which flows into DestroyActor. Two complete Blueprints with working game logic, no graph editor involved.

---

## Minute 3: Populate the Level

Paste this:

```
Spawn 8 gold coins in a circle with radius 800 at the center of the level at height 50.
Spawn 4 health pickups in the corners at positions (1000,1000,50), (-1000,1000,50), (1000,-1000,50), (-1000,-1000,50).
```

**What happens:** Claude calls `spawn_actor_circle` to place eight BP_GoldCoin instances evenly around a circle of radius 800 at Z=50. Then it calls `spawn_actor_at` four times to place the health pickups in each corner. Twelve actors appear in your level, correctly positioned, all using the Blueprints you just created.

---

## Minute 4: Add Enemies and Walls

Paste this:

```
Create a simple patrol enemy Blueprint called BP_Enemy with parent class Pawn that has a
floating pawn movement component.
Then spawn 3 enemies in a line from (-500,0,50) to (500,0,50).
Also spawn 4 wall actors using StaticMeshActor with the Cube mesh scaled to (1,20,5) at
the edges of the arena: (2000,0,250), (-2000,0,250), (0,2000,250), (0,-2000,250).
Rotate the side walls 90 degrees on the yaw axis.
```

**What happens:** Claude calls `create_blueprint` with parent class Pawn, then `add_component` to attach a FloatingPawnMovement component to it. It calls `spawn_actor_line` to distribute three enemies evenly between the start and end points. For the walls, it calls `spawn_actor_at` four times with the Cube static mesh, applying the scale and rotation you specified. The two side walls get a 90-degree yaw rotation so they run along the other axis.

---

## Minute 5: Apply Materials and Polish

Paste this:

```
Create a brick material with color (0.6, 0.3, 0.15) and apply it to all 4 wall actors.
Create a gold material with color (1.0, 0.85, 0.0) and emissive 0.3.
Apply the gold material to all the gold coin actors.
What's in my level now? Give me a summary.
```

**What happens:** Claude calls `create_simple_material` twice -- once for brick, once for gold with emissive glow. It then calls `batch_apply_material` (or `set_actor_material` per actor) to apply the brick material to every wall and the gold material to every coin. Finally, it calls `get_level_info` and `find_actors` to inventory the scene and reports back a summary: actor counts by type, materials in use, and the current lighting setup.

---

## You're Done

Click **Play** in the UE Editor toolbar. You are standing in a dark, lit arena with brick walls, eight glowing gold coins arranged in a circle, four health pickups in the corners, and three enemies. Walk into a coin -- "+10 Points!" prints to screen and the coin vanishes. Grab a health pickup -- "Healed!" and it disappears.

Five messages. Five minutes. A playable level.

---

## What's Next

- Try the [Example Prompts Cookbook](cookbook.md) for 50 ready-to-paste prompts covering hazards, wave spawners, AI patrol routes, HUD widgets, and more.
- Read the [Command Reference](../command_reference.md) for the full list of 156 TCP commands and 188 MCP tools.
- Set up [Cursor / Windsurf](setup_cursor.md) or [any MCP-compatible client](setup_any_mcp_client.md) -- Arcwright works with all of them.

---

## Tips for Better Results

- **Be specific.** "A health pickup that heals 25 HP and plays a sound" produces better results than "make a health thing."
- **Claude remembers context.** After creating BP_Enemy, you can say "spawn 5 of those enemies near the north wall" and Claude knows which Blueprint you mean.
- **Save periodically.** Say "save everything" or "save all" between steps. Claude calls `save_all` to persist your work.
- **Fix mistakes in conversation.** Say "delete all enemies" or "move the coins up by 100 units" -- Claude can query the level with `find_actors` and modify or remove anything.
- **Ask about your level anytime.** "What's in my level?" triggers an audit -- Claude lists every actor, Blueprint, and material currently in the scene.
- **Compound tools handle the boring parts.** Instead of manually setting up lighting, floor, and game mode separately, one prompt like "set up a playable scene" triggers a compound tool that chains five commands together.
- **Iterate fast.** The entire loop -- describe, create, test, adjust -- takes seconds per step. If the walls are too tall, just say "scale the walls down to 3 on the Z axis."
