# Frequently Asked Questions

---

## General

### What is Arcwright?

Arcwright is an Unreal Engine 5 plugin that lets any AI assistant -- Claude, GPT, Cursor, Windsurf, or custom agents -- create Blueprints, build levels, and modify assets inside the running UE5 Editor. It exposes 274 TCP commands and 289 MCP tools that AI assistants call to drive the editor programmatically.

### How much does it cost?

$49.99 one-time purchase on the FAB Marketplace. No subscription, no recurring fees, no per-seat licensing. All 274 commands and 289 MCP tools are available to every purchaser.

### Do I need API keys?

No. Arcwright runs entirely locally. It does not call any external APIs, does not require authentication, and does not phone home. The TCP server runs on `localhost:13377` and only accepts local connections.

### Can I use this offline?

Yes. Arcwright is a local TCP server inside the UE Editor. No internet connection is required for any Arcwright functionality. You only need internet if your AI assistant itself requires it (e.g., Claude Desktop or ChatGPT).

### What AI tools work with Arcwright?

Any AI tool that can either:

- **Call MCP tools** (Claude Desktop, Cursor, Windsurf, Cline, or any MCP-compatible client), or
- **Send TCP/JSON** (ChatGPT with Code Interpreter, custom Python agents, shell scripts, any programming language)

Arcwright is protocol-agnostic. If your tool can open a TCP socket and send JSON, it works.

### Is this an AI model?

No. Arcwright is a bridge/plugin, not an AI model. It does not contain or run any machine learning. Your AI assistant does the thinking; Arcwright executes the commands inside UE5.

---

## Compatibility

### What Unreal Engine versions are supported?

UE 5.4 and newer. This includes UE 5.4, 5.5, 5.6, and 5.7. The plugin uses standard UE5 APIs and does not depend on version-specific features.

### Does it work on Mac or Linux?

Arcwright currently supports Windows 10/11. Mac and Linux support is planned for a future release.

### Does it work with C++ projects or Blueprint-only projects?

Both. Arcwright is a plugin that loads into any UE project regardless of whether you use C++, Blueprints, or both.

### Does it work with World Partition?

Yes. Arcwright's `save_all` command explicitly handles World Partition external actor packages. Spawned actors are saved correctly to the external actor files.

### Does it work with Substrate (UE 5.4+ rendering)?

Yes. The `create_simple_material` command creates materials with `UMaterialExpressionConstant3Vector` nodes that work correctly under both Substrate and traditional rendering. Note: `create_material_instance` does not work reliably with Substrate -- use `create_simple_material` instead.

---

## Commands and Features

### How many commands does Arcwright have?

274 TCP commands and 289 MCP tools. The MCP tools wrap the TCP commands and add compound workflows (operations that combine multiple commands into one tool call).

### What can Arcwright create?

- **Blueprints** -- Event graphs with nodes, connections, and variables
- **Actors** -- Spawn, move, delete, and configure actors in the level
- **Components** -- Static meshes, collision shapes, lights, audio, Niagara, skeletal meshes (11 types)
- **Materials** -- Create materials with color and emissive, apply to actors
- **Widgets** -- UMG Widget Blueprints with full hierarchy (text, buttons, progress bars, containers)
- **Behavior Trees** -- AI Behavior Trees with blackboards, decorators, and services
- **Data Tables** -- Structured data with typed columns and rows
- **Level Sequences** -- Cinematic sequences with keyframed tracks
- **Landscapes and Foliage** -- Terrain and vegetation
- **Splines** -- Path splines for movement or decoration
- **Post-Process Volumes** -- Visual effects (bloom, exposure, vignette)
- **NavMesh** -- Navigation mesh bounds for AI pathfinding

### What are the 29 DSL parsers?

Arcwright includes parsers for 29 UE subsystems: Blueprint, BehaviorTree, DataTable, Widget, AnimBP, Material, Dialogue, Quest, Sequence, GAS, Perception, Physics, Tags, Enhanced Input, Smart Objects, Sound, Replication, Control Rig, State Trees, Vehicles, World Partition, Landscape, Foliage, Mass Entity, Shader, ProcMesh, Paper2D, Composure, and DMX. Each parser converts a domain-specific text format into the corresponding UE asset.

### Can Arcwright run Play In Editor?

Arcwright provides `play_in_editor`, `stop_play`, and `is_playing` commands. It also offers `teleport_player`, `get_player_location`, `teleport_to_actor`, and `get_player_view` for controlling the player during PIE sessions.

### Can I use Arcwright for automated testing?

Yes. You can script entire build-and-test workflows: create Blueprints, spawn actors, start PIE, teleport the player, read logs, and verify results -- all through TCP commands.

---

## Setup and Configuration

### How do I verify Arcwright is running?

Send a `health_check` command to `localhost:13377`:

```json
{"command": "health_check", "params": {}}
```

Or check the UE Output Log for:

```
LogArcwright: Arcwright Command Server started on port 13377
```

### Can I change the port?

The default port is 13377. You can configure the MCP server to connect to a different port using the `BLUEPRINTLLM_PORT` environment variable. The plugin's TCP server port is configured in the plugin settings.

### Do I need Python?

Only if you use the MCP server bridge (for Claude Desktop, Cursor, or Windsurf). If you connect directly via TCP from your own code, no Python is needed.

### Where are generated assets saved?

Arcwright saves generated Blueprints to `/Game/Arcwright/Generated/` and materials to `/Game/Arcwright/Materials/` inside your UE project's Content directory.

---

## Troubleshooting

### "Connection refused" when connecting to port 13377

The UE Editor is not running, or the Arcwright plugin is not loaded. Open UE, go to Edit > Plugins, confirm "Arcwright" is enabled, and restart the editor.

### "Blueprint not found" errors

Blueprint names are case-sensitive. Use `find_blueprints` to search:

```json
{"command": "find_blueprints", "params": {"name_filter": "Pickup"}}
```

### Spawned actors have no Blueprint logic

You are using a short class name instead of the full path. Use:

```json
{"class": "/Game/Arcwright/Generated/BP_Pickup.BP_Pickup_C"}
```

Not:

```json
{"class": "BP_Pickup"}
```

### Materials appear gray on spawned actors

Use `set_actor_material` on placed actors, not `apply_material` on the Blueprint. See [Best Practices](05_best_practices.md) for details.

### Widget colors look wrong (washed out or too bright)

Use the `hex:#RRGGBB` prefix for colors. The plugin converts sRGB hex to linear automatically. Do not pass raw sRGB float values as linear.

### Overlap events never fire

The Blueprint needs a collision component with `generate_overlap_events` set to true. See [Best Practices](05_best_practices.md).

### Editor crashes when overwriting assets

Delete existing assets before recreating them:

```json
{"command": "delete_blueprint", "params": {"name": "BP_Old"}}
{"command": "create_blueprint", "params": {"name": "BP_Old", "parent_class": "Actor"}}
```

### Claude Desktop does not show Arcwright tools

1. Verify `claude_desktop_config.json` has valid JSON (no trailing commas).
2. Fully quit Claude Desktop from the system tray, then reopen.
3. Verify Python can run the server: `python scripts/mcp_server/server.py --test`

See [MCP Setup](03_mcp_setup.md) for full troubleshooting steps.

---

## Performance

### How fast are commands?

Most commands execute in under 100ms. Commands that trigger shader compilation (material creation, material application) or Blueprint compilation may take 1-5 seconds. Large batch operations scale linearly.

### Can I send commands in parallel?

No. The command server processes commands serially on the UE game thread. Send one command at a time and wait for the response before sending the next. Batch commands (`batch_apply_material`, `batch_delete_actors`, etc.) are provided for operations that benefit from grouping.

### Does Arcwright affect editor performance?

The TCP server runs on a background thread and only dispatches work to the game thread when a command arrives. When idle, it has zero impact on editor performance.

---

## Licensing and Support

### Is the source code included?

The full C++ plugin source is included with your purchase. You can inspect, modify, and extend the plugin for your projects.

### Can I use Arcwright in shipped games?

Arcwright is an editor-only plugin. It does not ship with your game and adds no runtime overhead. The Blueprints, widgets, and assets it creates are standard UE assets that work in packaged builds.

### Where do I report bugs?

File an issue at [github.com/Divinity-Alpha/Arcwright/issues](https://github.com/Divinity-Alpha/Arcwright/issues).

### Where can I find more documentation?

| Document | Description |
|---|---|
| [Getting Started](01_getting_started.md) | Installation and first connection |
| [Command Reference](02_command_reference.md) | All 274 TCP commands |
| [MCP Setup](03_mcp_setup.md) | Claude Desktop, Cursor, Windsurf configuration |
| [HTML Translator](04_html_translator.md) | Design UIs in HTML, translate to UE widgets |
| [Best Practices](05_best_practices.md) | Key rules for reliable builds |
| [Widget Cookbook](07_widget_cookbook.md) | Practical widget building examples |
| [Changelog](08_changelog.md) | Version history |
