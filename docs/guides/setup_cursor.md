# Connecting Cursor IDE to Arcwright

Arcwright is a UE5 plugin that exposes 156 TCP commands and 188 MCP tools, letting any AI assistant create Blueprints, build levels, spawn actors, apply materials, and manage assets inside a running Unreal Editor. This guide walks you through connecting Cursor to Arcwright via MCP so that Cursor's AI can drive your UE5 project directly.

---

## Prerequisites

Before you begin, make sure the following are in place:

1. **Unreal Engine 5.4+** installed with the Arcwright plugin enabled in your project.
2. **UE Editor running** with your project open. Confirm the plugin is active by checking the Output Log for:
   ```
   LogArcwright: Arcwright Command Server listening on port 13377
   ```
3. **Python 3.11+** installed and accessible from your terminal.
4. **Cursor** installed (latest version with MCP support). Download from [cursor.com](https://cursor.com) if you haven't already.

---

## Step 1: Create the MCP Configuration

Cursor reads MCP server definitions from a JSON config file. You have two options for where to place it.

### Option A: Project-Level Config (Recommended)

Create the file `.cursor/mcp.json` in your UE project root (the directory containing your `.uproject` file):

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

This scopes Arcwright to this specific project. Anyone who clones the repo gets the same config.

### Option B: Global Config

If you want Arcwright available across all Cursor projects, create or edit the global config at:

```
%USERPROFILE%\.cursor\mcp.json
```

Use the same JSON format as Option A. The global config applies to every project you open in Cursor.

### Adjusting Paths

The paths above assume the default Arcwright installation at `C:\Arcwright`. If you installed elsewhere, update both `command` (the Python executable inside the Arcwright venv) and `args` (the MCP server script path) accordingly.

On macOS or Linux, the Python path changes to the platform equivalent:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "/path/to/Arcwright/venv/bin/python",
      "args": ["/path/to/Arcwright/scripts/mcp_server/server.py"]
    }
  }
}
```

---

## Step 2: Restart Cursor

After saving the config file, Cursor needs to reload to pick up the new MCP server:

- Open the Command Palette with **Ctrl+Shift+P** (or **Cmd+Shift+P** on macOS).
- Type **Reload Window** and select it.
- Alternatively, close and reopen Cursor entirely.

---

## Step 3: Verify the Connection

1. Open **File > Preferences > Cursor Settings** (or press **Ctrl+Shift+J**).
2. Navigate to the **MCP** section in the sidebar.
3. Look for **arcwright** in the server list. It should show a green status indicator. The tool count should display **188 tools**.
4. If the status is red or the server is missing, click the refresh icon next to it.

You can also verify from the AI chat. Open Cursor's chat panel (**Ctrl+L**) and type:

> Use the arcwright health_check tool to verify the UE5 connection.

A successful response looks like:

```json
{
  "server": "Arcwright",
  "version": "1.0",
  "engine": "5.7.0"
}
```

If `health_check` returns an error about connecting to UE, the MCP server itself is running correctly but cannot reach the Unreal Editor. Check that UE is open and the plugin is loaded (see Troubleshooting below).

---

## Step 4: Try It

Open Cursor's Composer or Chat and try these example prompts. Prefix with "Use Arcwright" or "Use the arcwright tools" so Cursor routes the request through MCP rather than its built-in code editing tools.

### Query the level

> Use Arcwright to check what's in my UE level.

Cursor calls `get_level_info` and returns the current map name, path, and actor count.

### Create a Blueprint

> Use Arcwright tools to create a health pickup Blueprint with a sphere collision and a static mesh component.

Cursor calls `create_blueprint`, `add_component` (for the collision and mesh), and `compile_blueprint`.

### Spawn actors in a pattern

> Spawn 5 health pickups in a circle at the center of the level using Arcwright.

Cursor calls `spawn_actor_circle` with the Blueprint class, count, radius, and center coordinates.

### Search and modify

> Use Arcwright to find all actors tagged "enemy" and set their Health variable to 200.

Cursor calls `find_actors` with a tag filter, then `batch_set_variable` on the results.

### Build a full scene

> Using Arcwright, set up outdoor lighting, create a 50x50 floor, and spawn a 4x4 grid of pillars.

Cursor chains `setup_scene_lighting`, `spawn_actor_at` (for the floor), and `spawn_actor_grid` (for the pillars).

---

## Architecture

Understanding the data flow helps with debugging:

```
Cursor AI (Composer / Chat)
    |
    |  stdio JSON-RPC (MCP protocol)
    v
Arcwright MCP Server (Python)     scripts/mcp_server/server.py
    |
    |  TCP, newline-delimited JSON, localhost:13377
    v
Arcwright Command Server (C++)    UE5 plugin, embedded in editor
    |
    |  Game thread dispatch (AsyncTask)
    v
Unreal Engine 5 Editor            Creates real assets, spawns actors
```

The MCP server is a thin Python process that translates MCP protocol calls into TCP commands. All heavy work happens inside the UE Editor process on the game thread.

---

## Environment Variables

The MCP server accepts optional environment variables for custom configurations. Set them in the `env` block of your `mcp.json`:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"],
      "env": {
        "BLUEPRINTLLM_HOST": "localhost",
        "BLUEPRINTLLM_PORT": "13377",
        "BLUEPRINTLLM_TIMEOUT": "120"
      }
    }
  }
}
```

| Variable | Default | Description |
|---|---|---|
| `BLUEPRINTLLM_HOST` | `localhost` | Hostname of the UE command server |
| `BLUEPRINTLLM_PORT` | `13377` | TCP port of the UE command server |
| `BLUEPRINTLLM_TIMEOUT` | `60` | Socket timeout in seconds for TCP operations |

Most users will not need to change these. The defaults work for a standard local setup.

---

## Also Works: Windsurf

Windsurf uses the same MCP protocol with a different config file location.

Create or edit `~/.codeium/windsurf/mcp_config.json`:

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

Restart Windsurf after saving the file. Open the Cascade panel and verify that `arcwright` appears as a connected server with 188 tools.

The same example prompts from Step 4 work in Windsurf's AI chat.

---

## Troubleshooting

### "arcwright" does not appear in the MCP panel

- **Validate your JSON.** A trailing comma or missing bracket will silently prevent the server from loading. Paste your config into a JSON validator if unsure.
- **Check the file location.** For project-level config, the file must be at `<project_root>/.cursor/mcp.json`. For global config, it must be at `%USERPROFILE%\.cursor\mcp.json`.
- **Restart Cursor completely.** A window reload is usually sufficient, but a full restart resolves edge cases.

### Server shows as connected but tool calls fail

- **UE Editor is not running.** The MCP server starts successfully (it is a standalone Python process) but cannot reach the Arcwright plugin. Launch UE with your project and verify the Output Log shows the command server listening on port 13377.
- **Verify manually.** Open a terminal and run:
  ```
  C:\Arcwright\venv\Scripts\python.exe C:\Arcwright\scripts\mcp_server\server.py --test
  ```
  This lists all registered tools and attempts a health check against UE. If it reports a connection error, the issue is between the MCP server and UE, not between Cursor and the MCP server.
- **Check verify script.** Run `python C:\Arcwright\scripts\mcp_client\verify.py` to test the raw TCP connection to port 13377 independently of MCP.

### "Connection refused" on port 13377

- The UE Editor is not running, or the Arcwright plugin failed to load.
- Check that the plugin is enabled in your `.uproject` file under the `Plugins` array.
- If the editor is running but the server did not start, check the Output Log for errors containing `LogArcwright`.
- Port 13377 should not require firewall exceptions for localhost connections, but verify if you have restrictive security software.

### Cursor does not use Arcwright tools

- Cursor may default to its built-in code editing tools unless you explicitly direct it. Include "Arcwright", "MCP tools", or "UE5 tools" in your prompt.
- In Composer mode, Cursor has a model context selector. Ensure the model you are using supports tool calling (Claude, GPT-4, etc.).
- If Cursor acknowledges the tools but declines to use them, try a more specific prompt: "Call the arcwright spawn_actor tool to place a cube at 0,0,100."

### Python or venv errors

- If you see errors about missing modules (`ModuleNotFoundError`), the config is pointing to the wrong Python executable. It must be the one inside the Arcwright venv (`C:\Arcwright\venv\Scripts\python.exe`), not the system Python.
- If the venv does not exist, create it:
  ```
  cd C:\Arcwright
  python -m venv venv
  venv\Scripts\pip install -r requirements.txt
  ```

---

## What's Next

- [5-Minute Quickstart](quickstart.md) -- Build a playable level from conversation in 5 minutes.
- [Example Prompts Cookbook](cookbook.md) -- 50 copy-paste prompts for common game development tasks.
- [Claude Desktop Setup](setup_claude_desktop.md) -- Connect Claude Desktop to Arcwright.
- [Any MCP Client](setup_any_mcp_client.md) -- Connect any AI or custom script via MCP or direct TCP.
- [Command Reference](../command_reference.md) -- Full documentation of all 156 TCP commands.
