# Getting Started with Arcwright

Arcwright is a UE5 plugin that gives any AI assistant the ability to create Blueprints, build levels, and modify assets inside a running Unreal Editor. It exposes 94 TCP commands and 107 MCP tools that AI assistants call to drive UE5 programmatically.

This guide walks through installation, first connection, and your first AI-driven workflow.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Unreal Engine | 5.7+ | Must be installed via Epic Games Launcher |
| Python | 3.11+ | Required for the MCP server bridge |
| AI Assistant | Any MCP-compatible | Claude Desktop, Cursor, Windsurf, Cline, or custom agents |

---

## Step 1: Install the Plugin

### From FAB (Unreal Marketplace)

1. Open the Epic Games Launcher.
2. Go to **FAB** (Unreal Marketplace).
3. Search for **Arcwright**.
4. Click **Install to Engine** and select UE 5.7.
5. Open your UE project. In the editor, go to **Edit > Plugins**, search for "Arcwright", and enable it.
6. Restart the editor when prompted.

### From Source (Development)

```bash
# Copy the plugin into your UE project's Plugins directory
xcopy /E /I /Y C:\BlueprintLLM\ue_plugin\BlueprintLLM "C:\YourProject\Plugins\BlueprintLLM"

# Build the editor target
"C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" ^
    YourProjectEditor Win64 Development "C:\YourProject\YourProject.uproject"

# Launch with -skipcompile (required after command-line build)
"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" ^
    "C:\YourProject\YourProject.uproject" -skipcompile
```

---

## Step 2: Verify the TCP Server

When the plugin loads, it automatically starts a TCP command server on `localhost:13377`. You can verify it is running with a simple Python script or `netstat`.

### Quick Verification (Python)

```python
import socket
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 13377))
sock.sendall(json.dumps({"command": "health_check", "params": {}}).encode("utf-8") + b"\n")

response = b""
while b"\n" not in response:
    response += sock.recv(4096)

result = json.loads(response.decode("utf-8"))
print(result)
# {"status": "ok", "data": {"server": "Arcwright", "version": "1.0", "engine": "5.7.0"}}

sock.close()
```

### Using the Python Client Library

If you have the Arcwright source, a higher-level client is available:

```python
from scripts.mcp_client.blueprint_client import ArcwrightClient

with ArcwrightClient() as client:
    info = client.health_check()
    print(info)
    # {'server': 'Arcwright', 'version': '1.0', 'engine': '5.7.0'}
```

If `health_check` returns successfully, the plugin is running and ready for commands.

---

## Step 3: Configure Your AI Assistant

Arcwright supports two connection methods:

| Method | Best For | Protocol |
|---|---|---|
| **MCP** | Claude Desktop, Cursor, Windsurf, Cline | stdio JSON-RPC via Python bridge |
| **TCP** | Custom agents, scripts, direct integration | Newline-delimited JSON over TCP 13377 |

### MCP Setup (Claude Desktop)

See [MCP Setup for Claude Desktop](mcp-setup-claude.md) for the full guide.

Quick version -- add this to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "python",
      "args": ["C:\\path\\to\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

Restart Claude Desktop after editing the config.

### MCP Setup (Cursor)

See [MCP Setup for Cursor](mcp-setup-cursor.md) for the full guide.

### Direct TCP

Any language can connect to `localhost:13377` and send newline-delimited JSON:

```
{"command": "health_check", "params": {}}\n
```

The server responds with one JSON line:

```
{"status": "ok", "data": {...}}\n
```

---

## Step 4: First Workflow -- Create and Spawn a Blueprint

This walkthrough creates a simple Blueprint, adds a component, applies a material, and spawns it into the level. The commands below can be sent by any AI assistant via MCP tools or TCP.

### 4.1 Create a Blueprint from IR

```json
{"command": "import_from_ir", "params": {"path": "C:/path/to/BP_Pickup.blueprint.json"}}
```

Response:
```json
{
  "status": "ok",
  "data": {
    "blueprint_name": "BP_Pickup",
    "nodes_created": 5,
    "connections_wired": 4,
    "compiled": true
  }
}
```

### 4.2 Add a Collision Component

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Pickup",
    "component_type": "SphereCollision",
    "component_name": "PickupCollision",
    "properties": {
      "radius": 100.0,
      "generate_overlap_events": true
    }
  }
}
```

### 4.3 Add a Static Mesh

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Pickup",
    "component_type": "StaticMesh",
    "component_name": "PickupMesh",
    "properties": {
      "mesh": "/Engine/BasicShapes/Sphere.Sphere"
    }
  }
}
```

### 4.4 Create and Apply a Material

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_PickupGold",
    "color": {"r": 1.0, "g": 0.84, "b": 0.0},
    "emissive": 0.5
  }
}
```

### 4.5 Spawn the Actor

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_Pickup.BP_Pickup",
    "location": {"x": 500, "y": 0, "z": 100},
    "label": "Pickup_1"
  }
}
```

### 4.6 Apply Material to the Placed Actor

Because SCS materials do not always persist through the spawn pipeline, apply materials to placed actors directly:

```json
{
  "command": "set_actor_material",
  "params": {
    "actor_label": "Pickup_1",
    "material_path": "/Game/Arcwright/Materials/MAT_PickupGold"
  }
}
```

### 4.7 Save

```json
{"command": "save_all", "params": {}}
```

---

## Step 5: Verify the Result

Query the level to confirm your actor was placed:

```json
{"command": "get_actors", "params": {"class_filter": "Pickup"}}
```

Response:
```json
{
  "status": "ok",
  "data": {
    "count": 1,
    "actors": [
      {
        "label": "Pickup_1",
        "class": "BP_Pickup_C",
        "location": {"x": 500.0, "y": 0.0, "z": 100.0}
      }
    ]
  }
}
```

Query the Blueprint structure:

```json
{"command": "get_blueprint_info", "params": {"name": "BP_Pickup"}}
```

---

## What Next

- [Command Reference](command-reference.md) -- Full documentation of all 94 TCP commands.
- [MCP Setup for Claude Desktop](mcp-setup-claude.md) -- Detailed MCP configuration.
- [Cookbook: Enemy AI System](cookbook-enemy-system.md) -- Build an enemy with patrol behavior.
- [Cookbook: Level Building](cookbook-level-building.md) -- Build a complete game level from scratch.
- [Troubleshooting](troubleshooting.md) -- Common errors and fixes.

---

## TCP Protocol Reference

All communication uses **newline-delimited JSON** over TCP port 13377.

**Request format:**
```json
{"command": "<command_name>", "params": {<parameters>}}\n
```

**Success response:**
```json
{"status": "ok", "data": {<result>}}\n
```

**Error response:**
```json
{"status": "error", "message": "<error description>"}\n
```

**Connection details:**
- Host: `localhost` (configurable via `BLUEPRINTLLM_HOST` env var)
- Port: `13377` (configurable via `BLUEPRINTLLM_PORT` env var)
- Encoding: UTF-8
- One JSON object per line, terminated by `\n`
- The server processes commands on the UE game thread -- commands are serialized, not concurrent.
