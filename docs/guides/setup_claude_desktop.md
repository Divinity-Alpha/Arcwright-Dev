# Connecting Claude Desktop to Arcwright

Arcwright is a UE5 plugin that gives AI assistants the power to create Blueprints, build levels, and modify assets inside a running Unreal Editor. It exposes 156 TCP commands and 188 MCP tools. This guide walks through connecting Claude Desktop to Arcwright so that Claude can drive your Unreal Editor through natural conversation.

The setup takes about 10 minutes.

---

## Prerequisites

Before you begin, make sure you have the following installed:

- **Unreal Engine 5.4+** (installed via Epic Games Launcher)
- **A UE5 project** (C++ or Blueprint-only -- both work)
- **Python 3.11+** (installed and available on your system PATH)
- **Claude Desktop** (download from [claude.ai/download](https://claude.ai/download))
- **Windows 10 or 11**

You do not need any prior experience with MCP (Model Context Protocol). This guide covers everything from scratch.

---

## Step 1: Install the Arcwright Plugin

Copy the Arcwright plugin into your UE5 project's `Plugins` folder. If the `Plugins` folder does not exist, create it first.

### From source

Open a terminal and run:

```
xcopy /E /I /Y C:\BlueprintLLM\ue_plugin\BlueprintLLM "C:\YourProject\Plugins\BlueprintLLM"
```

Replace `C:\YourProject` with the actual path to your UE5 project directory.

### From FAB (future)

Arcwright will be available on the Unreal Marketplace (FAB) as a one-click install. Once published, you can search for "Arcwright" in the Epic Games Launcher and install directly to your engine version.

---

## Step 2: Build and Launch the Editor

Arcwright includes C++ source that must be compiled before use. Build the editor from the command line, then launch with the `-skipcompile` flag.

### Build

```
"C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" ^
    YourProjectEditor Win64 Development ^
    "C:\YourProject\YourProject.uproject"
```

Replace `UE_5.7` with your engine version (e.g., `UE_5.4`) and `YourProject` with your project name and path.

### Launch

```
"C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" ^
    "C:\YourProject\YourProject.uproject" -skipcompile
```

**Important:** Do not double-click the `.uproject` file to open it. The in-editor recompilation does not work after a command-line build. Always launch with `-skipcompile` from the command line or a shortcut.

Once the editor finishes loading, the Arcwright TCP command server starts automatically on port 13377.

---

## Step 3: Verify the Plugin is Running

Open the UE Output Log by going to **Window > Output Log** in the editor menu. Look for this message:

```
LogArcwright: Arcwright Command Server listening on port 13377
```

If you see this line, the plugin is running and ready to accept connections.

### Optional: verify from the command line

If you have the Arcwright source repository, you can also run the verification script:

```
python C:\BlueprintLLM\scripts\mcp_client\verify.py
```

This sends a `health_check` command to the plugin and prints the response. A successful output looks like:

```
Arcwright Command Server: OK
  Server: Arcwright
  Version: 1.0
  Engine: 5.7.0
```

---

## Step 4: Configure Claude Desktop

Claude Desktop discovers MCP servers through a JSON configuration file. You need to tell it where to find the Arcwright MCP server.

### Locate the config file

The configuration file lives at:

```
%APPDATA%\Claude\claude_desktop_config.json
```

On most Windows installations, this expands to:

```
C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json
```

If the file does not exist yet, create it. If the `Claude` folder does not exist under `AppData\Roaming`, create that too.

**Note:** The correct location is `AppData\Roaming` (`%APPDATA%`), not `AppData\Local` (`%LOCALAPPDATA%`). Using the wrong directory is a common mistake.

### Add the Arcwright server entry

Open `claude_desktop_config.json` in any text editor and set its contents to:

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

**Adjust the paths to match your setup:**

- `command` -- The path to your Python executable. If you are using the Arcwright virtual environment, point to `venv\Scripts\python.exe` inside the Arcwright directory. If Python is on your system PATH, you can use `"python"` instead.
- `args` -- The path to the MCP server script. This must be an absolute path to `server.py` inside the Arcwright `scripts/mcp_server/` directory.

All backslashes in the JSON must be doubled (`\\`). This is standard JSON escaping for Windows paths.

### If the config file already exists

If you already have other MCP servers configured, merge the `arcwright` entry into the existing `mcpServers` object. For example:

```json
{
  "mcpServers": {
    "some-other-server": {
      "command": "...",
      "args": ["..."]
    },
    "arcwright": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

---

## Step 5: Restart Claude Desktop

Claude Desktop reads its MCP configuration only at startup. After editing the config file, you must fully restart the application.

**Closing the window is not enough.** Claude Desktop continues running in the system tray after you close the main window.

To fully restart:

1. Right-click the Claude icon in the Windows system tray (bottom-right of the taskbar, near the clock).
2. Click **Quit** or **Exit**.
3. Wait a few seconds for the process to end.
4. Relaunch Claude Desktop from the Start menu or desktop shortcut.

---

## Step 6: Verify the Connection

Open Claude Desktop and start a new conversation.

1. Look at the chat input area. You should see a hammer icon (or a tools indicator) showing that MCP tools are available. Click it to confirm you see approximately 188 tools listed under the Arcwright server.

2. Type the following prompt to verify the full pipeline works:

   > What Arcwright tools do you have access to?

   Claude should list the available tool categories: Blueprint creation, actor spawning, material management, query tools, and more.

3. If you want to test the live connection to Unreal Engine, ask:

   > Run a health check on the Unreal Editor.

   Claude will call the `health_check` tool and report the server name, version, and engine version. If this succeeds, the full chain is working: Claude Desktop to MCP server to UE plugin.

---

## Step 7: Try It

Here are three prompts to get started. Each demonstrates a different capability.

### Query your level

> What's in my UE level right now?

Claude will call `get_level_info` and `get_actors` to report the current map name, actor count, and a list of placed actors. This is a read-only operation that does not modify anything.

### Create a Blueprint

> Create a health pickup Blueprint called BP_HealthPickup. It should have a sphere collision component, a sphere mesh, and a gold material. When an actor overlaps it, print "Healed 25 HP" and destroy the pickup.

Claude will use several tools in sequence: `create_blueprint` to make the asset, `add_component` to attach collision and mesh components, `create_simple_material` for the gold color, and `import_from_ir` or node-level commands to wire up the overlap logic. You can watch the Blueprint appear in the Content Browser in real time.

### Spawn actors in a pattern

> Spawn 5 copies of BP_HealthPickup in a circle with a radius of 500 units at the center of the level.

Claude will call `spawn_actor_circle` with the appropriate parameters. Five actors will appear in your viewport arranged in a ring.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| No tools showing in Claude Desktop | Verify the config file is at `%APPDATA%\Claude\claude_desktop_config.json` (not `%LOCALAPPDATA%`). Check that the JSON is valid -- no trailing commas, all backslashes doubled. Fully restart Claude Desktop from the system tray, not just close the window. |
| Connection refused on port 13377 | The UE Editor is not running, or the Arcwright plugin did not load. Open the editor and check the Output Log for `LogArcwright: Arcwright Command Server listening on port 13377`. If the message is missing, go to **Tools > Arcwright** in the editor menu and toggle the server on. |
| Timeout errors on commands | Windows Firewall may be blocking localhost connections. Add an exception for port 13377, or temporarily disable the firewall for testing. Also try increasing the timeout by adding an `"env"` block to your config (see below). |
| Commands fail with errors | Open the UE Output Log (**Window > Output Log**) and filter for `LogArcwright`. The log shows every command received and any errors encountered during execution. This is the best place to diagnose issues. |
| Blueprint not found | Use the Blueprint name without any path prefix. Arcwright searches `/Game/Arcwright/Generated/` and the full asset registry automatically. For example, use `"BP_HealthPickup"`, not `"/Game/Arcwright/Generated/BP_HealthPickup"`. |
| Tools show in Claude Desktop but every command fails | The MCP server is starting but cannot reach the UE plugin over TCP. Verify the editor is running and the plugin is loaded. Run `python C:\BlueprintLLM\scripts\mcp_client\verify.py` from a terminal to test the TCP connection independently. |
| Claude says "server disconnected" | The MCP server process crashed. Check that Python 3.11+ is installed and the `mcp` package is available. Run `python C:\BlueprintLLM\scripts\mcp_server\server.py --test` from a terminal to see if the server starts without errors. |

### Increasing the timeout

If you are working with large Blueprints or complex operations that take longer than the default timeout, add an `env` block to your config:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "C:\\Arcwright\\venv\\Scripts\\python.exe",
      "args": ["C:\\Arcwright\\scripts\\mcp_server\\server.py"],
      "env": {
        "BLUEPRINTLLM_TIMEOUT": "120"
      }
    }
  }
}
```

This sets the TCP socket timeout to 120 seconds (default is 60).

---

## What's Next

Now that Claude Desktop is connected to your Unreal Editor, explore what you can build:

- **[Example Prompts Cookbook](cookbook.md)** -- 50 copy-paste prompts for building levels, creating game objects, and more.
- **[5-Minute Quickstart](quickstart.md)** -- Build a playable level from conversation in 5 minutes.
- **[Cursor Setup](setup_cursor.md)** -- Connect Cursor IDE to Arcwright.
- **[Any MCP Client](setup_any_mcp_client.md)** -- Connect any AI or custom script via MCP or direct TCP.
- **[Command Reference](../command_reference.md)** -- Full documentation of all 156 TCP commands.

---

## Architecture Overview

For those curious about how the pieces fit together:

```
Claude Desktop
    |
    |  stdio JSON-RPC (MCP protocol)
    v
Arcwright MCP Server (Python)     scripts/mcp_server/server.py
    |
    |  TCP, newline-delimited JSON
    v
Arcwright Plugin (C++)            UE Editor, port 13377
    |
    |  Game thread dispatch
    v
Unreal Engine 5 Editor            Blueprints, actors, materials, levels
```

Claude Desktop communicates with the MCP server using the standard Model Context Protocol over stdio. The MCP server is a lightweight Python process that translates each tool call into a TCP command and forwards it to the Arcwright plugin running inside the Unreal Editor. The plugin executes all commands on the UE game thread, ensuring thread safety for all editor operations.

The MCP server is stateless -- it does not cache or transform data. All logic for creating Blueprints, spawning actors, managing materials, and querying assets runs inside the C++ plugin.
