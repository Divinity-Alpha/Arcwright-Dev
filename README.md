# Arcwright

**The Bridge Between AI and Unreal Engine.**

Arcwright is a UE5 plugin that gives any AI assistant the power to create Blueprints, build UI, manage assets, and control the editor through 267 TCP commands and 289 MCP tools.

Connect Claude, GPT, Cursor, Windsurf, or any MCP-compatible AI. Your AI describes. Arcwright executes. Everything happens inside your running Unreal Editor.

## Quick Start

### 1. Install the plugin
Copy the `Arcwright` folder to your project's `Plugins` directory. Rebuild your project.

### 2. Connect your AI via MCP
Add to your Claude Desktop (or other AI) config:

```json
{
  "mcpServers": {
    "arcwright": {
      "command": "python",
      "args": ["C:\\path\\to\\Arcwright\\scripts\\mcp_server\\server.py"]
    }
  }
}
```

### 3. Start the TCP server
Open your UE project. The Arcwright TCP server starts automatically on port 13377.

### 4. Verify connection
Ask your AI: "Check if Arcwright is connected"
Or run: `python scripts/mcp_client/verify.py`

## What Your AI Can Build

| Category | Examples |
|----------|----------|
| **Widget Blueprints & UI** | Complete HUD screens, menus, inventory systems |
| **Blueprints** | Blueprint classes, components, event graphs, variables |
| **Actors & Levels** | Spawn actors, set transforms, manage levels |
| **Materials** | Create materials, add nodes, connect graphs |
| **Data Tables** | Create, populate, query structured data |
| **Fonts** | Import TTF families, map typeface slots |
| **Assets** | Import textures, audio; rename, move, duplicate |

## Widget DSL

Build complete UIs in one call with the declarative Widget DSL:

```
SCREEN "WBP_StatusBar" 3840x2160
  BORDER "Border_Status" AT 0 2000 SIZE 1344 96 Z 1
    COLOR #000000 / 0.35  BOX  HALIGN Fill  VALIGN Fill
    HBOX "HBox_Chips"
      BORDER "Chip_Cash" FILL COLOR bg-card ROUND
        TEXT "Label" { TEXT "CASH" FONT condensed 17 COLOR text-dim }
        TEXT "Value" { TEXT "$4,820" FONT mono 22 COLOR green }
      END
    END
  END
END SCREEN
```

See [Widget DSL Guide](scripts/dsl_parser/WIDGET_DSL_GUIDE.md) for full syntax.

## Documentation

- [Widget DSL Guide](scripts/dsl_parser/WIDGET_DSL_GUIDE.md)
- [Update Guide](scripts/mcp_server/UPDATE_GUIDE.md)

## Requirements

- Unreal Engine 5.5 or later
- Python 3.9+
- Any MCP-compatible AI assistant

## Version

Current: 1.0.0

## License

Proprietary. See LICENSE file for terms.
