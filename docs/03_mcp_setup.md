# MCP Setup Guide

Configure the Model Context Protocol (MCP) to connect your AI assistant to Arcwright. Once configured, your AI can create Blueprints, build levels, and modify assets in UE5 through natural conversation.

MCP is a stdio JSON-RPC protocol that Claude Desktop, Cursor, Windsurf, and other AI tools use to call external tools. Arcwright provides an MCP server that translates tool calls into TCP commands sent to the UE5 plugin.

---

## Architecture

```
AI Assistant (Claude / Cursor / Windsurf)
    |
    | stdio JSON-RPC (MCP protocol)
    v
Arcwright MCP Server (Python)     <-- scripts/mcp_server/server.py
    |
    | TCP (newline-delimited JSON)
    v
Arcwright UE Plugin (C++)        <-- port 13377
    |
    | Game thread dispatch
    v
Unreal Engine 5 Editor
```

The MCP server is a lightweight bridge. All real work -- Blueprint creation, asset management, editor actions -- happens inside the UE plugin on the game thread.

---

## Prerequisites

1. **Unreal Engine 5.4+** with the Arcwright plugin installed and running.
2. **Python 3.10+** installed and available on your PATH.
3. The Arcwright MCP server script (included with the plugin at `scripts/mcp_server/server.py`).

---

## Claude Desktop

Claude Desktop has native MCP support. No coding required.

### Step 1: Locate the config file

The config file is at:

```
%APPDATA%\Claude\claude_desktop_config.json
```

On most Windows systems, this expands to:

```
C:\Users\<YourUsername>\AppData\Roaming\Claude\claude_desktop_config.json
```

If the file does not exist, create it.

### Step 2: Add the Arcwright server

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

If you use a Python virtual environment (recommended), point `command` to the venv Python:

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

**Use double backslashes** (`\\`) in JSON paths.

### Step 3: Restart Claude Desktop

Close Claude Desktop completely from the system tray (right-click > Quit). Simply closing the window is not enough -- the process continues in the background. Then reopen it.

### Step 4: Verify

Open a new conversation in Claude Desktop and ask:

> "What Arcwright tools do you have available?"

Claude should list categories of tools (Blueprints, Level, Materials, Widgets, etc.) and confirm it has access to approximately 289 tools. Then try:

> "Use Arcwright to check the UE5 connection."

Claude will call `health_check` and report the server status:

```json
{"server": "Arcwright", "version": "1.0", "engine": "5.5.0"}
```

---

## Cursor

Cursor supports MCP servers via a JSON config file or the settings UI.

### Option A: Project-level config (recommended)

Create `.cursor/mcp.json` in your UE project root:

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

### Option B: Global config

Add to `%USERPROFILE%\.cursor\mcp.json` (applies to all projects):

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

### Option C: Via the Cursor UI

1. Open Cursor.
2. Go to **File > Preferences > Cursor Settings** (or press `Ctrl+Shift+J`).
3. Navigate to the **MCP** section.
4. Click **+ Add new MCP server**.
5. Set Name to `arcwright`, Type to `stdio`, and enter the command/args.

After adding the config:

1. Restart Cursor (or reload the window).
2. Check the MCP panel -- `arcwright` should show a green status indicator.
3. In Composer or Chat, ask: *"Use the arcwright tools to create a Blueprint"*

---

## Windsurf

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

1. Restart Windsurf.
2. Check the Cascade panel for connected MCP servers.
3. Verify `arcwright` appears.
4. Ask Cascade: *"Use arcwright to check the UE5 connection."*

---

## Generic MCP Client

Any application that supports the MCP protocol can use Arcwright. The server uses stdio transport (stdin/stdout JSON-RPC). To integrate:

1. Launch the server process:
   ```
   python scripts/mcp_server/server.py
   ```
2. Send JSON-RPC requests to the process's stdin.
3. Read JSON-RPC responses from the process's stdout.

The server advertises all 289 tools via the standard MCP `tools/list` method.

---

## Config Files Reference

| AI Client | Config File Location | Format |
|---|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` | `{"mcpServers": {"arcwright": {...}}}` |
| Cursor (project) | `<project>/.cursor/mcp.json` | `{"mcpServers": {"arcwright": {...}}}` |
| Cursor (global) | `%USERPROFILE%\.cursor\mcp.json` | `{"mcpServers": {"arcwright": {...}}}` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `{"mcpServers": {"arcwright": {...}}}` |

All clients use the same `mcpServers` JSON structure with `command` and `args`.

---

## Environment Variables

The MCP server supports optional environment variables to customize the connection:

| Variable | Default | Description |
|---|---|---|
| `BLUEPRINTLLM_HOST` | `localhost` | TCP host for the UE command server |
| `BLUEPRINTLLM_PORT` | `13377` | TCP port for the UE command server |
| `BLUEPRINTLLM_TIMEOUT` | `60` | TCP socket timeout in seconds |

To set these in your MCP config:

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

## Direct TCP (No MCP Needed)

If your AI tool does not support MCP but can run Python code (e.g., ChatGPT with Code Interpreter, custom agents), connect directly over TCP:

```python
import socket, json

def send_command(command, params=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("localhost", 13377))
    request = json.dumps({"command": command, "params": params or {}})
    sock.sendall(request.encode("utf-8") + b"\n")

    response = b""
    while b"\n" not in response:
        response += sock.recv(4096)

    sock.close()
    return json.loads(response.decode("utf-8"))

# Example
result = send_command("health_check")
print(result)
```

No MCP server, no Python bridge, no dependencies. Just TCP and JSON.

---

## Troubleshooting

### Claude Desktop does not show Arcwright tools

- Verify the JSON is valid (no trailing commas, correct backslash escaping).
- Fully restart Claude Desktop from the system tray (Quit, not just close the window).
- Verify Python can run the server without errors: `python scripts/mcp_server/server.py --test`
- Check the Claude Desktop developer console for MCP errors.

### "Cannot connect to UE command server"

The MCP server started but cannot reach the plugin on port 13377.

- Ensure UE Editor is running with Arcwright enabled.
- Check the UE Output Log for `LogArcwright: Arcwright Command Server started on port 13377`.
- Verify nothing else is using port 13377.

### Cursor/Windsurf shows server as disconnected

- Verify the Python path in your config is correct and points to a working Python installation.
- Try running the server manually: `python scripts/mcp_server/server.py --test`
- Restart the IDE completely after config changes.

### Config changes not taking effect

All MCP clients cache the config at startup. You must fully restart the application after every edit.

### Tool execution timeout

Some commands (e.g., `import_from_ir` with large files, shader compilation) take longer than the default 60-second timeout. Increase `BLUEPRINTLLM_TIMEOUT` to 120 or higher in your config.
