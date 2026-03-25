# Arcwright Quickstart Guide

> **The Bridge Between AI and Unreal Engine.**
>
> Arcwright gives any AI assistant — Claude, Cursor, Windsurf, ChatGPT, or custom agents — the power to create Blueprints, build levels, and modify assets inside the running UE5 Editor through 154 TCP commands and 186 MCP tools.

---

## Prerequisites

- Unreal Engine 5.7 installed
- A UE5 project (C++ or Blueprint — both work)
- Windows 10/11

---

## Install the Arcwright Plugin

These steps are the same regardless of which AI client you use.

### Step 1: Copy the plugin

```
xcopy /E /I /Y C:\Arcwright\ue_plugin\BlueprintLLM "<YourProject>\Plugins\BlueprintLLM"
```

Replace `<YourProject>` with your UE project root (e.g. `C:\MyGame`).

### Step 2: Build the editor target

```
"C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" ^
    <YourProject>Editor Win64 Development "<YourProject>\<YourProject>.uproject"
```

### Step 3: Launch UE Editor

**Always use `-skipcompile`** — the editor's built-in compiler doesn't work with Arcwright.

```
"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" ^
    "<YourProject>\<YourProject>.uproject" -skipcompile -nosplash -unattended -nopause
```

### Step 4: Verify the command server

Wait for the editor to fully load (30-60 seconds), then:

```
python scripts/verify_connection.py
```

You should see:

```
============================================================
Arcwright Connection Verification
============================================================
[1/5] TCP connection to localhost:13377 ... OK
[2/5] health_check ........................ OK — Arcwright v1.0.0, UE 5.7
[3/5] get_level_info ...................... OK — Level: ArenaLevel, 48 actors
[4/5] find_actors ......................... OK — Found 48 actors
[5/5] get_capabilities .................... OK — 156 commands, 186 MCP tools

ALL CHECKS PASSED — Arcwright is ready!
```

---

## Section A: Claude Desktop (Recommended)

Claude Desktop has native MCP support — no coding required.

### 1. Open your Claude Desktop config

The config file is at:
```
%APPDATA%\Claude\claude_desktop_config.json
```

On most systems: `C:\Users\<you>\AppData\Roaming\Claude\claude_desktop_config.json`

### 2. Add the Arcwright MCP server

If the file doesn't exist, create it. If it exists, add the `arcwright` entry to the `mcpServers` object:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

> **Note:** Use double backslashes (`\\`) in the JSON paths. Adjust paths if your Arcwright installation is elsewhere.

### 3. Restart Claude Desktop

Close Claude Desktop completely and reopen it. The MCP server connects on startup.

### 4. Verify the connection

Open a new conversation in Claude Desktop and ask:

> "What Arcwright tools do you have?"

Claude should list categories of tools (Blueprints, Level, Materials, etc.) and confirm it has access to ~188 tools.

### 5. Try it!

> "Create a health pickup Blueprint called BP_HealthPickup that heals 25 HP on overlap, then spawn it at the origin."

Claude will:
1. Call `create_blueprint` to make BP_HealthPickup
2. Add overlap event logic with `add_nodes_batch`
3. Wire the nodes with `add_connections_batch`
4. Call `spawn_actor_at` to place it in your level
5. Report what it created

---

## Section B: Cursor / Windsurf

Both Cursor and Windsurf support MCP servers. The configuration is similar to Claude Desktop.

### Cursor

Cursor supports MCP via a `.cursor/mcp.json` file in your project root or global settings.

**Project-level config** (recommended — create `.cursor/mcp.json` in your UE project root):

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

**Global config** (applies to all projects — `%USERPROFILE%\.cursor\mcp.json`):

Same format as above.

After adding the config:
1. Restart Cursor (or reload the window)
2. Open the MCP panel (look for the plug icon or check Settings → MCP)
3. Verify "arcwright" appears as a connected server
4. In Composer or Chat, ask: *"Use the arcwright tools to create a health pickup Blueprint"*

### Windsurf

Windsurf reads MCP configuration from `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

After adding the config:
1. Restart Windsurf
2. Check the Cascade panel for connected MCP servers
3. Verify "arcwright" appears
4. Ask Cascade: *"Use arcwright to create a health pickup Blueprint and spawn it at 0,0,100"*

### Config files reference

| Client | Config Location | Format |
|---|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | `{"mcpServers": {"arcwright": {...}}}` |
| Cursor (project) | `<project>/.cursor/mcp.json` | `{"mcpServers": {"arcwright": {...}}}` |
| Cursor (global) | `%USERPROFILE%\.cursor\mcp.json` | `{"mcpServers": {"arcwright": {...}}}` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `{"mcpServers": {"arcwright": {...}}}` |

All use the same `mcpServers` object format.

---

## Section C: ChatGPT / Other AIs (TCP Direct)

Any AI that can run Python code (ChatGPT with Code Interpreter, custom agents, scripts) can use Arcwright via the TCP client library.

### 1. Install the client

The client is a single Python file with zero external dependencies:

```bash
# Copy the client into your project
cp C:\Arcwright\scripts\mcp_client\blueprint_client.py ./

# Or add the scripts directory to your Python path
```

### 2. Give the AI a system prompt

Copy the contents of `scripts/mcp_server/arcwright_system_prompt.txt` into your AI's system prompt. This gives it:
- All 156 commands grouped by category
- The 10 most important commands with full examples
- Connection instructions and JSON protocol
- Common workflows and error handling

### 3. Example: Using the TCP client in Python

```python
from blueprint_client import ArcwrightClient

# Connect to the running UE Editor
client = ArcwrightClient(host="localhost", port=13377)

# Check connection
result = client.health_check()
print(result)  # {"status": "ok", "data": {"server": "Arcwright", "version": "1.0.0"}}

# Create a Blueprint
client.create_blueprint("BP_HealthPickup", parent_class="Actor",
    variables=[{"name": "HealAmount", "type": "Float", "default": "25.0"}])

# Add nodes
client.add_nodes_batch("BP_HealthPickup", [
    {"node_type": "Event_ActorBeginOverlap", "node_id": "overlap"},
    {"node_type": "PrintString", "node_id": "print1",
     "params": {"InString": "Healed!"}},
    {"node_type": "DestroyActor", "node_id": "destroy"},
])

# Wire them together
client.add_connections_batch("BP_HealthPickup", [
    {"source_node": "overlap", "source_pin": "Then",
     "target_node": "print1", "target_pin": "execute"},
    {"source_node": "print1", "source_pin": "Then",
     "target_node": "destroy", "target_pin": "execute"},
])

# Validate
result = client.validate_blueprint("BP_HealthPickup")
print(f"Valid: {result['data']['valid']}, Issues: {result['data']['total_issues']}")

# Spawn it in the level
client.spawn_actor_at("BP_HealthPickup", label="HealthPickup_1",
    location={"x": 0, "y": 0, "z": 100})

# Save
client.save_all()
client.close()
```

### 4. Example conversation with ChatGPT

**You:** I have Arcwright running in UE5. Create a coin pickup that gives 10 points and destroys itself.

**ChatGPT:** I'll use the Arcwright TCP client to build this:

```python
from blueprint_client import ArcwrightClient

with ArcwrightClient() as client:
    # Create the Blueprint with a Points variable
    client.create_blueprint("BP_Coin", parent_class="Actor",
        variables=[{"name": "PointValue", "type": "Int", "default": "10"}])

    # Add a sphere mesh and collision
    client.add_component("BP_Coin", "SphereCollision", "PickupCollision",
        properties={"radius": 64, "generate_overlap_events": True})
    client.add_component("BP_Coin", "StaticMesh", "CoinMesh",
        properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere"})

    # Build the overlap → print → destroy logic
    client.add_nodes_batch("BP_Coin", [
        {"node_type": "Event_ActorBeginOverlap", "node_id": "overlap"},
        {"node_type": "PrintString", "node_id": "msg",
         "params": {"InString": "+10 Points!"}},
        {"node_type": "DestroyActor", "node_id": "destroy"},
    ])

    client.add_connections_batch("BP_Coin", [
        {"source_node": "overlap", "source_pin": "Then",
         "target_node": "msg", "target_pin": "execute"},
        {"source_node": "msg", "source_pin": "Then",
         "target_node": "destroy", "target_pin": "execute"},
    ])

    # Verify it's correct
    validation = client.validate_blueprint("BP_Coin")
    print(f"Blueprint valid: {validation['data']['valid']}")

    # Spawn 5 coins in a circle
    client.spawn_actor_circle(
        actor_class="/Game/Arcwright/Generated/BP_Coin.BP_Coin",
        count=5, radius=500,
        center={"x": 0, "y": 0, "z": 100},
        label_prefix="Coin")

    client.save_all()
```

### 5. JSON Protocol Reference

Arcwright uses newline-delimited JSON over TCP on `localhost:13377`:

```
→ {"command": "health_check", "params": {}}\n
← {"status": "ok", "data": {"server": "Arcwright", "version": "1.0.0"}}\n

→ {"command": "spawn_actor_at", "params": {"class": "BP_Coin", "label": "Coin_1", "location": {"x": 0, "y": 0, "z": 100}}}\n
← {"status": "ok", "data": {"actor_label": "Coin_1", "class": "BP_Coin"}}\n

→ {"command": "find_actors", "params": {"class_filter": "BP_Coin"}}\n
← {"status": "ok", "data": {"actors": [...], "count": 5}}\n
```

Every request is a single JSON line ending with `\n`. Every response is a single JSON line ending with `\n`. The `status` field is always `"ok"` or `"error"`.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `verify_connection.py` says "Connection refused" | UE Editor isn't running, or the Arcwright plugin isn't loaded. Check the editor's Output Log for "Arcwright Command Server started on port 13377". |
| Claude Desktop doesn't show Arcwright tools | Restart Claude Desktop after editing the config. Check the config JSON is valid (no trailing commas). |
| Cursor/Windsurf doesn't connect | Check the MCP config path is correct for your OS. Restart the IDE. |
| "Blueprint not found" errors | Use the full name (e.g. `"BP_HealthPickup"`) without path. Arcwright searches `/Game/Arcwright/Generated/` automatically. |
| Commands work but Blueprint is empty in editor | Click on the Blueprint in the Content Browser to refresh. Some changes require closing and reopening the Blueprint Editor tab. |
| `spawn_actor_at` spawns invisible actors | You need a mesh component. Add one with `add_component(bp, "StaticMesh", "Mesh", properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere"})`. |

---

## What's Next?

- Browse the [Command Reference](command_reference.md) for all 153 commands
- Try the [Cookbook: Enemy System](cookbook-enemy-system.md) for a guided build
- Try the [Cookbook: Level Building](cookbook-level-building.md) for scene population
- Check [Troubleshooting](troubleshooting.md) if you hit issues
