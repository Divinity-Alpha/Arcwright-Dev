# MCP Setup for Cursor IDE

This guide configures Cursor to connect to Arcwright via MCP. Once connected, Cursor's AI can create Blueprints, build levels, and manage UE5 assets directly from your editor.

---

## Prerequisites

1. **Unreal Engine 5.7+** with the Arcwright plugin installed and running.
2. **Python 3.11+** installed and available on PATH.
3. **Cursor** installed (download from [cursor.com](https://cursor.com)).
4. The Arcwright MCP server script at `scripts/mcp_server/server.py`.

---

## Step 1: Open Cursor MCP Settings

1. Open Cursor.
2. Go to **File > Preferences > Cursor Settings** (or press `Ctrl+Shift+J`).
3. Navigate to the **MCP** section in the sidebar.
4. Click **+ Add new MCP server**.

---

## Step 2: Configure the Arcwright Server

### Option A: Via the Cursor UI

Fill in the fields:

| Field | Value |
|---|---|
| **Name** | `arcwright` |
| **Type** | `stdio` |
| **Command** | `python` (or full path to your Python executable) |
| **Arguments** | `C:\Arcwright\scripts\mcp_server\server.py` |

If using a virtual environment, use the full path to the venv Python:

| Field | Value |
|---|---|
| **Command** | `C:\Arcwright\venv\Scripts\python.exe` |
| **Arguments** | `C:\Arcwright\scripts\mcp_server\server.py` |

### Option B: Via the JSON Config File

Cursor stores MCP configuration in your project's `.cursor/mcp.json` file (for project-scoped servers) or in the global settings. Create or edit `.cursor/mcp.json` in your project root:

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

Alternatively, for a global configuration that applies to all projects, add to Cursor's global settings via **File > Preferences > Cursor Settings > MCP**.

---

## Step 3: Verify the Connection

1. After adding the server, Cursor should show a green status indicator next to `arcwright` in the MCP settings panel.
2. If it shows red or disconnected, click the refresh icon.
3. Open the Cursor AI chat (`Ctrl+L`) and try:

> Use the arcwright health_check tool to verify the UE5 connection.

You should see output like:

```json
{
  "server": "Arcwright",
  "version": "1.0",
  "engine": "5.7.0"
}
```

---

## Step 4: Using Arcwright in Cursor

In Cursor's AI chat or inline editing, you can now reference Arcwright tools:

**Example prompts:**

> "List all actors in my Unreal level using Arcwright."

> "Create a Blueprint called BP_HealthPickup with a sphere collision component."

> "Find all Blueprint assets that have a Health variable."

Cursor's AI will call the appropriate Arcwright MCP tools and return the results.

---

## Environment Variables

The MCP server supports optional environment variables for custom configurations:

| Variable | Default | Description |
|---|---|---|
| `BLUEPRINTLLM_HOST` | `localhost` | TCP host for the UE command server |
| `BLUEPRINTLLM_PORT` | `13377` | TCP port for the UE command server |
| `BLUEPRINTLLM_TIMEOUT` | `60` | TCP socket timeout in seconds |

To set these in Cursor's MCP config:

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

### Server shows as disconnected

**Fixes:**
- Ensure Unreal Editor is running with the Arcwright plugin.
- Verify Python can run the server: open a terminal and run `python C:\Arcwright\scripts\mcp_server\server.py --test`. This should list available tools and exit.
- Check that your Python path is correct in the config. Use the full path to avoid PATH resolution issues.
- Restart Cursor after config changes.

### "Cannot connect to UE command server"

The MCP server started but cannot reach the UE plugin.

**Fixes:**
- Confirm the UE Editor is open with a project that has the Arcwright plugin.
- Check port 13377 is not blocked by a firewall.
- Look for `LogArcwright: Arcwright Command Server started on port 13377` in UE's output log.

### Tools are not visible to the AI

**Fixes:**
- Make sure the server status shows green in Cursor's MCP settings.
- Try removing and re-adding the server.
- Restart Cursor completely.

---

## Architecture

```
Cursor AI
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

The same MCP server works for Cursor, Claude Desktop, Windsurf, Cline, and any other MCP-compatible AI client. The only difference is the config format.

---

## Also Works With

| AI Client | Config Location | Setup |
|---|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | See [MCP Setup for Claude Desktop](mcp-setup-claude.md) |
| Windsurf | Windsurf MCP settings panel | Same `command` + `args` format |
| Cline | VS Code extension settings | Same `command` + `args` format |
| Custom agents | Direct TCP to `localhost:13377` | No MCP needed -- send JSON directly |
