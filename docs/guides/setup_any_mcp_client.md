# Connecting Any AI Client to Arcwright

Arcwright exposes the Unreal Engine 5 Editor to AI assistants through two protocols: **MCP** (Model Context Protocol) and **direct TCP**. Any AI client that speaks either protocol can create Blueprints, populate levels, manage assets, and control the editor programmatically.

- **156 TCP commands** available on the UE5 plugin's command server
- **188 MCP tools** available via the stdio MCP server (157 direct wrappers + 29 compound workflow tools + 2 node reference tools)

This guide covers both connection methods, with examples for every major AI client.

---

## Prerequisites

Before connecting any client, you need:

1. **Unreal Engine 5.7** with the Arcwright plugin installed and the project built.
2. **UE Editor running** with the Arcwright plugin loaded. The TCP command server starts automatically on port 13377 when the plugin loads.
3. **Python 3.11+** with the Arcwright virtual environment (only required for MCP connections).

Verify the command server is live:

```bash
cd C:\Arcwright
.\venv\Scripts\activate
python scripts/mcp_client/verify.py
```

You should see all 5 checks pass, confirming TCP connectivity and command execution.

---

## Two Ways to Connect

### 1. MCP Protocol (stdio) -- Recommended for AI Assistants

Best for AI assistants that natively support the Model Context Protocol: Claude Desktop, Cursor, Windsurf, Cline, and others. The MCP server translates between standard MCP JSON-RPC (over stdin/stdout) and Arcwright's TCP protocol. The AI assistant discovers all 188 tools automatically at connection time and can call them without any custom code.

**Architecture:**

```
AI Assistant  -->  MCP Protocol (stdio JSON-RPC)  -->  MCP Server (Python)  -->  TCP  -->  UE5 Plugin
```

### 2. Direct TCP -- For Custom Agents and Any Language

Best for custom agents, scripts, pipelines, or any programming language. Connect a TCP socket to `localhost:13377`, send JSON commands, and receive JSON responses. No Python dependency required -- any language with socket support works.

**Architecture:**

```
Your Code  -->  TCP socket (localhost:13377)  -->  UE5 Plugin
```

---

## Option 1: MCP Server Setup

The MCP server is a standard stdio server built with FastMCP. It is compatible with any MCP client that follows the protocol specification.

### Server Location

```
C:\Arcwright\scripts\mcp_server\server.py
```

### Configuration Pattern

Every MCP client needs to know how to launch the server process. The configuration is the same across all clients -- only the config file location differs:

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

On macOS or Linux, adjust the Python path accordingly (e.g., `C:/Arcwright/venv/bin/python`).

### Config File Locations by Client

| AI Client | Config File Location | Notes |
|---|---|---|
| **Claude Desktop** | `%APPDATA%\Claude\claude_desktop_config.json` | Restart Claude Desktop after editing |
| **Cursor (project)** | `<project>/.cursor/mcp.json` | Per-project config |
| **Cursor (global)** | `%USERPROFILE%\.cursor\mcp.json` | Applies to all projects |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | Global config |
| **Cline** | VS Code settings or `<project>/.cline/mcp.json` | Check Cline docs for current location |
| **Continue.dev** | `~/.continue/config.json` under `mcpServers` | Global config |
| **Custom MCP client** | Varies | Pass `command` and `args` to your MCP client library |

### Claude Desktop Example

Create or edit `%APPDATA%\Claude\claude_desktop_config.json`:

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

Restart Claude Desktop. The Arcwright tools will appear in Claude's tool list.

### Cursor Example

Create `<your-project>/.cursor/mcp.json`:

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

Cursor will detect the config and offer the Arcwright tools in its AI assistant.

### Environment Variables

The MCP server accepts optional environment variables for non-default configurations:

| Variable | Default | Description |
|---|---|---|
| `BLUEPRINTLLM_HOST` | `localhost` | UE command server hostname |
| `BLUEPRINTLLM_PORT` | `13377` | UE command server port |
| `BLUEPRINTLLM_TIMEOUT` | `60` | TCP timeout in seconds |

To use them, add an `env` block to your MCP config:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"],
      "env": {
        "BLUEPRINTLLM_PORT": "13377",
        "BLUEPRINTLLM_TIMEOUT": "120"
      }
    }
  }
}
```

### Self-Test

Run the MCP server in self-test mode to verify tool registration and UE connectivity:

```bash
cd C:\Arcwright
.\venv\Scripts\activate
python scripts/mcp_server/server.py --test
```

This prints the number of registered tools, lists every tool name, and runs a `health_check` against the UE command server. If the tool count shows 188 and the health check returns OK, the server is ready.

---

## Option 2: Direct TCP

### Protocol Specification

- **Transport:** TCP socket
- **Address:** `localhost:13377`
- **Framing:** Newline-delimited JSON. Each message is a single JSON object followed by a newline character (`\n`).
- **Encoding:** UTF-8

### Request Format

```json
{"command": "<command_name>", "params": { ... }}\n
```

- `command` (string, required): The command name (e.g., `"health_check"`, `"spawn_actor_at"`).
- `params` (object, optional): Command-specific parameters. Omit or pass `{}` for commands with no parameters.

### Response Format

```json
{"status": "ok", "data": { ... }}\n
```

On success, `status` is `"ok"` and `data` contains the command-specific result.

```json
{"status": "error", "message": "Blueprint not found: BP_Missing"}\n
```

On failure, `status` is `"error"` and `message` describes what went wrong.

### Example: Raw TCP in Python

This example uses only the standard library -- no dependencies beyond Python itself.

```python
import socket
import json


def connect(host="localhost", port=13377, timeout=30.0):
    """Open a TCP connection to the Arcwright command server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    return sock


def send_command(sock, command, params=None):
    """Send a command and return the parsed JSON response."""
    request = json.dumps({"command": command, "params": params or {}}) + "\n"
    sock.sendall(request.encode("utf-8"))

    # Read until we receive a complete newline-terminated response
    data = b""
    while b"\n" not in data:
        chunk = sock.recv(65536)
        if not chunk:
            raise ConnectionError("Server closed connection")
        data += chunk

    line = data.split(b"\n", 1)[0]
    return json.loads(line.decode("utf-8"))


# --- Usage ---

sock = connect()

# 1. Check connection
result = send_command(sock, "health_check")
print(result)
# {"status": "ok", "data": {"server": "Arcwright", "version": "1.0"}}

# 2. Query the current level
result = send_command(sock, "get_level_info")
print(f"Level: {result['data']['level_name']}, Actors: {result['data']['actor_count']}")

# 3. Create a Blueprint with a variable
result = send_command(sock, "create_blueprint", {
    "name": "BP_HealthPickup",
    "parent_class": "Actor",
    "variables": [
        {"name": "HealAmount", "type": "Float", "default": "25.0"}
    ]
})
print(f"Created: {result['data']['blueprint_path']}")

# 4. Spawn it into the level
result = send_command(sock, "spawn_actor_at", {
    "class": "BP_HealthPickup",
    "label": "HealthPickup_1",
    "location": {"x": 100, "y": 0, "z": 50}
})
print(f"Spawned: {result['data']['label']}")

# 5. Save
send_command(sock, "save_all")

sock.close()
```

### Example: Using the Python Client Library

The included client library at `scripts/mcp_client/blueprint_client.py` wraps the TCP protocol with typed methods, context manager support, error handling, and automatic buffering. It has zero external dependencies beyond the Python standard library.

```python
import sys
sys.path.insert(0, "C:/Arcwright/scripts/mcp_client")
from blueprint_client import ArcwrightClient

with ArcwrightClient(host="localhost", port=13377) as client:
    # Check connection
    info = client.health_check()
    print(info)

    # Create a Blueprint
    client.create_blueprint(
        "BP_Coin",
        parent_class="Actor",
        variables=[{"name": "PointValue", "type": "Int", "default": "10"}]
    )

    # Add a collision component
    client.add_component("BP_Coin", "SphereCollision", "PickupZone",
                         properties={"radius": 100, "generate_overlap_events": True})

    # Add a mesh component
    client.add_component("BP_Coin", "StaticMesh", "CoinMesh",
                         properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere"})

    # Import a complete Blueprint from IR (intermediate representation) JSON
    client.import_from_ir("C:/Arcwright/test_ir/BP_Coin.blueprint.json")

    # Spawn into the level
    client.spawn_actor_at("BP_Coin", label="Coin_1",
                          location={"x": 0, "y": 0, "z": 100})

    # Query what is in the level
    actors = client.get_actors()
    print(f"Actors in level: {actors['data']['count']}")

    # Find specific Blueprints
    result = client.send_command("find_blueprints", {"name_filter": "Coin"})
    print(result)

    # Save everything
    client.save_all()
```

### Example: Node.js (Direct TCP)

```javascript
const net = require('net');

const client = new net.Socket();
client.connect(13377, 'localhost', () => {
    console.log('Connected to Arcwright');

    // Send health_check
    const request = JSON.stringify({command: 'health_check', params: {}}) + '\n';
    client.write(request);
});

let buffer = '';
client.on('data', (data) => {
    buffer += data.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
        if (line.trim()) {
            const response = JSON.parse(line);
            console.log('Response:', response);
        }
    }
});

client.on('error', (err) => {
    console.error('Connection error:', err.message);
});
```

### Example: C# (.NET)

```csharp
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

using var client = new TcpClient("localhost", 13377);
using var stream = client.GetStream();
using var reader = new StreamReader(stream, Encoding.UTF8);
using var writer = new StreamWriter(stream, Encoding.UTF8) { AutoFlush = true };

// Send command
var request = JsonSerializer.Serialize(new {
    command = "health_check",
    @params = new { }
});
writer.WriteLine(request);

// Read response
string response = reader.ReadLine();
Console.WriteLine(response);
```

### Example: curl (Quick Test)

TCP is not HTTP, so `curl` does not work directly. For a quick command-line test, use Python:

```bash
python -c "
import socket, json
s = socket.socket(); s.connect(('localhost', 13377))
s.sendall(b'{\"command\":\"health_check\",\"params\":{}}\n')
print(s.recv(4096).decode())
s.close()
"
```

---

## Verifying Your Connection

Run the built-in 5-step verification:

```bash
cd C:\Arcwright
.\venv\Scripts\activate
python scripts/mcp_client/verify.py
```

The script tests:

1. **TCP connect** -- Can a socket reach `localhost:13377`?
2. **health_check** -- Does the server respond with its name and version?
3. **import_from_ir** -- Can a test Blueprint be created from an IR file?
4. **get_blueprint_info** -- Can the created Blueprint be queried?
5. **delete_blueprint** -- Can the test Blueprint be cleaned up?

All 5 passing confirms end-to-end connectivity and command execution.

---

## Command Categories

Arcwright's 156 TCP commands are organized into these categories. Each MCP tool wraps one or more TCP commands.

| Category | Example Commands | Description |
|---|---|---|
| **Server** | `health_check`, `get_capabilities`, `get_stats` | Connection status, available commands, usage stats |
| **Blueprint CRUD** | `create_blueprint`, `import_from_ir`, `delete_blueprint`, `compile_blueprint` | Create, import, delete, and compile Blueprint assets |
| **Blueprint Inspection** | `get_blueprint_info`, `get_blueprint_details`, `find_blueprints` | Query Blueprint structure, variables, nodes, components |
| **Blueprint Editing** | `add_node`, `remove_node`, `add_connection`, `remove_connection`, `set_node_param` | Modify individual nodes and connections in a Blueprint graph |
| **Blueprint Config** | `modify_blueprint`, `reparent_blueprint`, `rename_asset`, `set_class_defaults`, `set_variable_default` | Change variables, parent class, CDO defaults |
| **Components** | `add_component`, `get_components`, `remove_component`, `set_component_property` | Manage SCS components (collision, mesh, light, audio, camera, spring arm) |
| **Actors** | `spawn_actor_at`, `get_actors`, `delete_actor`, `set_actor_transform`, `copy_actor` | Place, query, move, and remove actors in the level |
| **Actor Properties** | `get_actor_properties`, `set_actor_tags`, `set_actor_visibility`, `set_actor_mobility`, `set_actor_enabled`, `set_actor_scale` | Read and write actor state |
| **Actor Hierarchy** | `attach_actor_to`, `detach_actor` | Parent-child actor relationships |
| **Spawn Patterns** | `spawn_actor_grid`, `spawn_actor_circle`, `spawn_actor_line` | Procedural actor placement in geometric patterns |
| **Batch Operations** | `batch_set_variable`, `batch_add_component`, `batch_apply_material`, `batch_set_property`, `batch_delete_actors`, `batch_replace_material`, `batch_scale_actors`, `batch_move_actors` | Bulk modifications across multiple actors or Blueprints |
| **Materials** | `create_simple_material`, `create_material_instance`, `create_textured_material`, `apply_material`, `set_actor_material`, `list_available_materials` | Create and apply materials and textures |
| **Widgets (UI)** | `create_widget_blueprint`, `add_widget_child`, `set_widget_property`, `get_widget_tree`, `remove_widget` | Build UMG Widget Blueprints for HUDs and menus |
| **Behavior Trees** | `create_behavior_tree`, `get_behavior_tree_info`, `setup_ai_for_pawn` | Create AI behavior trees and wire them to pawns |
| **Data Tables** | `create_data_table`, `get_data_table_info`, `add_data_table_row`, `edit_data_table_row`, `get_data_table_rows` | Create and manage data-driven game tables |
| **Animation** | `create_anim_blueprint`, `add_anim_state`, `add_anim_transition`, `create_anim_montage`, `create_blend_space`, `play_animation`, `get_skeleton_bones`, `get_available_animations` | Animation Blueprint state machines, montages, blend spaces |
| **Sequencer** | `create_sequence`, `add_sequence_track`, `add_keyframe`, `get_sequence_info`, `play_sequence` | Cinematic level sequences with keyframes |
| **Scene Setup** | `setup_scene_lighting`, `set_game_mode` | Lighting presets and GameMode configuration |
| **Splines** | `create_spline_actor`, `add_spline_point`, `get_spline_info` | Spline paths for movement, rails, rivers |
| **Post-Processing** | `add_post_process_volume`, `set_post_process_settings` | Bloom, exposure, color grading, depth of field, vignette |
| **Physics** | `add_physics_constraint`, `break_constraint`, `set_physics_enabled`, `set_movement_defaults` | Physics constraints, simulation, movement tuning |
| **Landscape & Foliage** | `get_landscape_info`, `set_landscape_material`, `create_foliage_type`, `paint_foliage`, `get_foliage_info` | Terrain queries and procedural vegetation |
| **Asset Import** | `import_static_mesh`, `import_texture`, `import_sound` | Import FBX/OBJ meshes, PNG/JPG textures, WAV/OGG audio |
| **Asset Discovery** | `find_assets`, `list_available_blueprints`, `list_available_materials`, `list_project_assets` | Search the asset registry by type, name, or path |
| **Level Management** | `save_all`, `save_level`, `get_level_info`, `create_sublevel`, `set_level_visibility`, `get_sublevel_list`, `move_actor_to_sublevel` | Save, query, and manage streaming levels |
| **World Settings** | `get_world_settings`, `set_world_settings` | Gravity, kill-Z, time dilation |
| **Niagara (VFX)** | `spawn_niagara_at_location`, `add_niagara_component`, `set_niagara_parameter`, `activate_niagara`, `get_niagara_parameters` | Particle system parameters and activation |
| **Input** | `create_input_action`, `add_input_mapping`, `set_player_input_mapping` | Enhanced Input actions, mappings, and contexts |
| **Collision** | `set_collision_preset`, `set_collision_shape` | Collision profiles and shape configuration |
| **Audio** | `set_audio_properties`, `play_sound_at_location` | Spatial audio configuration |
| **Navigation** | `create_nav_mesh_bounds` | AI pathfinding bounds |
| **Editor Control** | `play_in_editor`, `stop_play`, `get_output_log`, `quit_editor`, `take_screenshot` | PIE control, log reading, screenshots, shutdown |

For the full parameter reference of every command, see `docs/command_reference.md`.

---

## Compound Workflow Tools (MCP Only)

The MCP server includes 29 compound tools that combine multiple TCP commands into single high-level operations. These are only available through MCP, not direct TCP.

| Category | Tool | What It Does |
|---|---|---|
| Scene Setup | `setup_playable_scene` | Lighting + floor + material + game mode + save |
| Scene Setup | `setup_cinematic_scene` | Lighting + post-process + camera + sequence |
| Game Objects | `create_collectible` | Blueprint + overlap logic + spawn + material |
| Game Objects | `create_hazard_zone` | Blueprint + damage logic + spawn + red material |
| Game Objects | `create_game_manager` | Score/wave/timer manager Blueprint + spawn |
| Blueprint | `scaffold_actor_blueprint` | Create Blueprint + add components + set defaults |
| Blueprint | `scaffold_pawn_blueprint` | Pawn Blueprint + movement + collision + mesh |
| Level | `create_arena_layout` | Floor + walls + lighting for arena games |
| Level | `scatter_actors` | Random scatter with configurable density |
| Query | `audit_level` | Count actors by class, list Blueprints, materials |
| Query | `compare_blueprints` | Diff two Blueprints (variables, components, nodes) |
| AI | `create_ai_enemy` | Pawn + BT + AI controller + spawn |
| AI | `create_patrol_path` | Spline path + AI pawn following it |
| UI | `create_game_hud` | Widget Blueprint with health/score/ammo bars |
| UI | `create_menu_widget` | Menu widget with title + buttons |
| Assets | `import_and_apply_mesh` | Import FBX + create Blueprint + add mesh component |
| Assets | `create_material_library` | Batch-create materials from color definitions |
| Physics | `create_physics_playground` | Multiple constrained actors for testing |
| Physics | `create_environment_zone` | Post-process volume with preset (underwater, toxic, etc.) |

---

## Troubleshooting

### "Connection refused" on localhost:13377

The UE5 Editor is not running, or the Arcwright plugin did not load.

- Confirm the editor is open with the project that has the Arcwright plugin installed.
- Check the UE output log for `LogArcwright: Command server started on port 13377`.
- If building from source, ensure the plugin compiled without errors.

### Timeout when sending commands

- A firewall or security tool may be blocking localhost TCP connections. Ensure `localhost:13377` is allowed.
- Some commands (e.g., `import_from_ir` with large Blueprints) may take longer than the default timeout. Increase the timeout on your client connection.
- If the editor is busy (compiling shaders, loading a level), commands queue on the game thread. Wait for the editor to finish loading.

### "Unknown command" in response

- Check the exact command name spelling. Command names are case-sensitive and use `snake_case`.
- Use `get_capabilities` to retrieve the full list of supported commands from the running server.
- If you recently updated the plugin, rebuild and relaunch the editor.

### "Blueprint not found" or "Actor not found"

- Blueprint names are searched in `/Game/Arcwright/Generated/` by default. Use the exact asset name without path prefix (e.g., `"BP_Coin"`, not `"/Game/Arcwright/Generated/BP_Coin"`).
- Actor labels are case-sensitive. Use `get_actors` or `find_actors` to list current actors and their exact labels.
- After creating a Blueprint, you must `spawn_actor_at` to place it in the level. The Blueprint exists as an asset; spawning creates an instance.

### MCP server fails to start

- Ensure the Python virtual environment exists at `C:\Arcwright\venv\` and has the `mcp` package installed:
  ```bash
  C:\Arcwright\venv\Scripts\pip.exe list | findstr mcp
  ```
- If the `mcp` package is missing: `C:\Arcwright\venv\Scripts\pip.exe install mcp`
- Verify the path in your MCP client config uses double backslashes (`\\`) in JSON strings.

### MCP tools not appearing in AI assistant

- After editing the MCP config file, restart the AI assistant completely (not just the conversation).
- Run the self-test to confirm the server can start: `python scripts/mcp_server/server.py --test`
- Check the AI assistant's MCP logs for connection errors. Claude Desktop logs are at `%APPDATA%\Claude\logs\`.

### Commands succeed but nothing visible in editor

- The editor viewport may not be focused on the location where actors were spawned. Check the Outliner panel for new actors.
- If using `create_blueprint` without `spawn_actor_at`, the Blueprint exists only as an asset in the Content Browser -- it has no level presence until spawned.
- After `batch_apply_material` or `apply_material`, the viewport may need a focus change to refresh. Clicking in the viewport triggers a redraw.

---

## Next Steps

- **[Example Prompts Cookbook](cookbook.md)** -- 50 copy-paste prompts for common game development tasks.
- **[5-Minute Quickstart](quickstart.md)** -- Build a playable level from conversation in 5 minutes.
- **[Command Reference](../command_reference.md)** -- Full parameter documentation of every command.
- **Template Library:** 16 reusable game patterns available at `templates/`. Run with `python templates/template_runner.py <template_id>`.
- **Blender Integration:** Arcwright also has a Blender MCP server for cross-tool 3D pipelines. See `scripts/blender_mcp/SETUP.md`.
