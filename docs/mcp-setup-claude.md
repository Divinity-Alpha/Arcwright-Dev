# MCP Setup for Claude Desktop

This guide configures Claude Desktop to connect to Arcwright via the Model Context Protocol (MCP). Once connected, Claude can create Blueprints, build levels, manage assets, and query the Unreal Editor directly through conversation.

---

## Prerequisites

1. **Unreal Engine 5.7+** with the Arcwright plugin installed and running.
2. **Python 3.11+** installed and available on PATH.
3. **Claude Desktop** installed (download from [claude.ai](https://claude.ai/download)).
4. The Arcwright MCP server script at `scripts/mcp_server/server.py`.

---

## Step 1: Locate the Config File

Claude Desktop's MCP configuration lives at:

```
%APPDATA%\Claude\claude_desktop_config.json
```

On a typical Windows install, this expands to:

```
C:\Users\<YourUsername>\AppData\Roaming\Claude\claude_desktop_config.json
```

If the file does not exist, create it.

---

## Step 2: Add the Arcwright MCP Server

Open `claude_desktop_config.json` and add or merge the following:

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

**Adjust the paths** to match your installation:
- `command` must point to your Python executable (virtual environment recommended).
- `args` must point to the Arcwright MCP server script.

### If you also use the Blender MCP server

```json
{
  "mcpServers": {
    "arcwright": {
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

---

## Step 3: Restart Claude Desktop

**Claude Desktop must be fully restarted after any config change.** Close it from the system tray (right-click the tray icon and choose Quit), then reopen it.

Simply closing the window is not enough -- the process continues in the background.

---

## Step 4: Verify the Connection

1. Open Claude Desktop.
2. Start a new conversation.
3. You should see Arcwright listed in the available tools (look for the tool icon in the chat input area).
4. Ask Claude: *"Use Arcwright to check the UE5 connection."*
5. Claude should call `health_check` and report the server status.

If successful, you will see output like:

```json
{
  "server": "Arcwright",
  "version": "1.0",
  "engine": "5.7.0"
}
```

---

## Step 5: First Commands via Claude

Try these prompts to verify the full pipeline works:

**Query the level:**
> "What actors are currently in my UE5 level?"

Claude will call `get_actors` and list all placed actors.

**Create a material:**
> "Create a red material called MAT_Danger in Unreal."

Claude will call `create_simple_material` with a red color value.

**Get level info:**
> "What level is currently loaded in Unreal?"

Claude will call `get_level_info` and report the map name and actor count.

---

## Environment Variables

The MCP server supports these optional environment variables:

| Variable | Default | Description |
|---|---|---|
| `BLUEPRINTLLM_HOST` | `localhost` | TCP host for the UE command server |
| `BLUEPRINTLLM_PORT` | `13377` | TCP port for the UE command server |
| `BLUEPRINTLLM_TIMEOUT` | `60` | TCP socket timeout in seconds |

To set these in the Claude Desktop config:

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

---

## Common Issues

### "Cannot connect to UE command server"

The MCP server starts but cannot reach the UE plugin TCP server.

**Fixes:**
- Ensure Unreal Editor is running with the Arcwright plugin loaded.
- Verify the plugin started the TCP server: look for `LogArcwright: Arcwright Command Server started on port 13377` in the UE output log.
- Check that nothing else is using port 13377.
- If the editor is running but the server did not start, check **Tools > Arcwright** in the UE menu bar and toggle the server.

### Claude does not show Arcwright tools

**Fixes:**
- Verify the config file path is correct (`%APPDATA%\Claude\claude_desktop_config.json`).
- Verify the JSON is valid (no trailing commas, correct escaping of backslashes).
- Fully restart Claude Desktop (quit from system tray, not just close the window).
- Check the Claude Desktop logs for MCP server errors.
- Verify Python runs the server without errors: `python scripts/mcp_server/server.py --test`

### "Tool execution failed" errors

**Fixes:**
- Check that the UE Editor did not crash. Relaunch if needed.
- If you see timeout errors, increase `BLUEPRINTLLM_TIMEOUT` to 120.
- Some commands (like `import_from_ir` with large files) take longer. Allow up to 60 seconds.

### Config changes not taking effect

**Fix:**
Claude Desktop caches the config at startup. You **must** fully restart it after every edit to `claude_desktop_config.json`. Use the system tray icon to Quit, then relaunch.

---

## Available Tools

Once connected, Claude Desktop has access to 107 MCP tools covering:

| Category | Examples |
|---|---|
| Core | `health_check`, `save_all`, `save_level`, `quit_editor` |
| Blueprint CRUD | `import_blueprint_ir`, `get_blueprint_info`, `compile_blueprint`, `delete_blueprint` |
| Node Editing | `add_node`, `remove_node`, `add_connection`, `set_node_param` |
| Level Actors | `spawn_actor`, `get_actors`, `move_actor`, `delete_actor` |
| Components | `add_component`, `get_components`, `remove_component` |
| Materials | `create_simple_material`, `apply_material`, `set_actor_material` |
| Widgets | `create_widget_blueprint`, `add_widget_child`, `set_widget_property` |
| Behavior Trees | `create_behavior_tree_from_dsl`, `setup_ai_for_pawn` |
| Data Tables | `create_data_table_from_dsl`, `get_data_table_info` |
| Sequencer | `create_sequence`, `add_sequence_track`, `add_keyframe` |
| Query | `find_blueprints`, `find_actors`, `find_assets` |
| Batch Operations | `batch_apply_material`, `batch_delete_actors`, `batch_set_property` |

See the [Command Reference](command-reference.md) for the complete list with parameters and examples.

---

## Architecture

```
Claude Desktop
    |
    | stdio JSON-RPC (MCP protocol)
    v
MCP Server (Python)  <-- scripts/mcp_server/server.py
    |
    | TCP (newline-delimited JSON)
    v
UE Command Server (C++)  <-- Arcwright plugin, port 13377
    |
    | Game thread dispatch
    v
Unreal Engine 5 Editor
```

The MCP server is a thin bridge. All Blueprint creation logic, asset management, and editor actions execute inside the UE plugin on the game thread. The MCP server translates MCP tool calls into TCP commands and returns the results.
