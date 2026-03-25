# Getting Started with Arcwright

> **The Bridge Between AI and Unreal Engine.**
>
> Arcwright gives any AI assistant -- Claude, GPT, Cursor, Windsurf, or custom agents -- the power to create Blueprints, build levels, and modify assets inside the running UE5 Editor through **274 TCP commands** and **289 MCP tools**.

**Price:** $49.99 one-time purchase on the FAB Marketplace. No subscription, no API keys, no remote validation.

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Unreal Engine** | 5.4 or newer (5.5, 5.6, 5.7 all supported) |
| **Platform** | Windows 10/11 |
| **Python** | 3.10+ (only needed if using the MCP bridge) |
| **AI Assistant** | Any -- Claude Desktop, Cursor, Windsurf, ChatGPT, custom agents, or raw TCP scripts |

---

## Step 1: Install from FAB Marketplace

1. Open the **Epic Games Launcher**.
2. Go to the **FAB Marketplace** tab.
3. Search for **Arcwright**.
4. Click **Install to Engine** and select your UE version.
5. Open your UE project. Go to **Edit > Plugins**, search for "Arcwright", and enable it.
6. Restart the editor when prompted.

That is it. The plugin activates automatically on the next editor launch.

---

## Step 2: Verify the Command Server

When the Arcwright plugin loads, it starts a TCP command server on `localhost:13377`. You should see this line in the UE **Output Log** (Window > Output Log):

```
LogArcwright: Arcwright Command Server started on port 13377
```

### Quick health check (Python)

Open any terminal and run:

```python
import socket, json

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 13377))
sock.sendall(json.dumps({"command": "health_check", "params": {}}).encode() + b"\n")

response = b""
while b"\n" not in response:
    response += sock.recv(4096)

print(json.loads(response))
sock.close()
```

Expected output:

```json
{"status": "ok", "data": {"server": "Arcwright", "version": "1.0", "engine": "5.5.0"}}
```

### Quick health check (netstat)

If you just want to confirm the port is open:

```
netstat -an | findstr 13377
```

You should see a `LISTENING` entry on `127.0.0.1:13377`.

---

## Step 3: Connect Your AI Assistant

Arcwright supports two connection methods. Choose the one that fits your workflow:

| Method | Best For | How It Works |
|---|---|---|
| **MCP (Model Context Protocol)** | Claude Desktop, Cursor, Windsurf | AI calls tools through a stdio JSON-RPC bridge |
| **TCP (Direct)** | Custom agents, Python scripts, ChatGPT | Send newline-delimited JSON to `localhost:13377` |

### Option A: Claude Desktop (MCP)

Add this to your Claude Desktop config file at `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "python",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

Restart Claude Desktop completely (quit from the system tray, then reopen). See [MCP Setup](03_mcp_setup.md) for full details on Claude Desktop, Cursor, and Windsurf.

### Option B: Direct TCP

Any language can connect to `localhost:13377` and send commands:

```
{"command": "health_check", "params": {}}\n
```

The server responds with one JSON line:

```
{"status": "ok", "data": {"server": "Arcwright", "version": "1.0"}}\n
```

No authentication, no API keys, no internet required. Everything runs locally.

---

## Step 4: Your First Workflow -- Create and Spawn a Blueprint

These commands can be sent by any AI assistant via MCP, or directly via TCP. This example creates a simple Blueprint, adds a component, and spawns it into the level.

### 4.1 Create a Blueprint

```json
{
  "command": "create_blueprint",
  "params": {
    "name": "BP_HealthPickup",
    "parent_class": "Actor",
    "variables": [
      {"name": "HealAmount", "type": "Float", "default": "25.0"}
    ]
  }
}
```

### 4.2 Add a collision component

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_HealthPickup",
    "component_type": "SphereCollision",
    "component_name": "PickupCollision",
    "properties": {
      "radius": 100.0,
      "generate_overlap_events": true
    }
  }
}
```

### 4.3 Add a visible mesh

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_HealthPickup",
    "component_type": "StaticMesh",
    "component_name": "PickupMesh",
    "properties": {
      "mesh": "/Engine/BasicShapes/Sphere.Sphere"
    }
  }
}
```

### 4.4 Compile the Blueprint

```json
{"command": "compile_blueprint", "params": {"name": "BP_HealthPickup"}}
```

### 4.5 Spawn it into the level

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_HealthPickup.BP_HealthPickup_C",
    "label": "HealthPickup_1",
    "x": 0, "y": 0, "z": 100
  }
}
```

### 4.6 Save

```json
{"command": "save_all", "params": {}}
```

### 4.7 Verify

```json
{"command": "find_actors", "params": {"class_filter": "HealthPickup"}}
```

You should see your actor listed in the response. Open the UE Editor viewport and you will see the sphere in the level.

---

## What is Next

| Guide | Description |
|---|---|
| [Command Reference](02_command_reference.md) | All 274 TCP commands with examples |
| [MCP Setup](03_mcp_setup.md) | Configure Claude Desktop, Cursor, Windsurf |
| [HTML to Widget Translator](04_html_translator.md) | Design UIs in HTML, translate to UE widgets |
| [Best Practices](05_best_practices.md) | Key rules for reliable Blueprint and widget creation |
| [FAQ](06_faq.md) | Common questions and answers |
| [Widget Cookbook](07_widget_cookbook.md) | Build HUDs, menus, health bars, and inventory screens |
| [Changelog](08_changelog.md) | Version history and release notes |

---

## TCP Protocol Quick Reference

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
- Host: `localhost`
- Port: `13377`
- Encoding: UTF-8
- One JSON object per line, terminated by `\n`
- Commands execute on the UE game thread and are serialized (not concurrent)
