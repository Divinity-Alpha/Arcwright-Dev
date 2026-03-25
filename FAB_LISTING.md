# FAB Listing — Arcwright

## Title
Arcwright — AI Bridge for Unreal Engine 5

## Short Description (160 chars)
Connect any AI assistant to Unreal Engine 5. 274 TCP commands, 289 MCP tools. Your AI builds — Arcwright executes.

## Full Description

### The Bridge Between AI and Unreal Engine

Arcwright is a UE5 plugin that gives any AI assistant — Claude, GPT, Cursor, Windsurf, or any MCP-compatible agent — direct control over the Unreal Editor through a comprehensive command API.

Your AI designs. Arcwright executes. Everything happens inside your running project.

---

### What Your AI Can Build

**Widget Blueprints & UI**
Build complete UI screens from natural language or HTML designs. The Widget DSL turns a 25-line description into 200+ executed commands. Supports Canvas, HBox, VBox, Grid, ListView, TileView, WrapBox, ScrollBox, and 7 more widget types.

**Blueprints**
Create Blueprint classes, add components, wire event graphs, set variables, and compile — all programmatically.

**Actors & Levels**
Spawn actors, set transforms, manage components, build level layouts.

**Materials**
Create materials, add nodes, connect graphs, assign to assets. Supports Surface, UI, and PostProcess material domains.

**Data Tables**
Create, populate, and query data tables from any structured data.

**Assets**
Import textures, fonts, audio. Manage the content browser. Rename, move, duplicate assets at scale.

---

### Widget DSL — UI in One Call

```
SCREEN "WBP_HUD" 3840x2160
  FONTS { condensed: "/Game/UI/Fonts/F_BarlowCondensed" Bold }
  BORDER "Border_Status" AT 0 2000 SIZE 1344 96 Z 1
    COLOR #000000 / 0.35  BOX  HALIGN Fill  VALIGN Fill
    HBOX "HBox_Chips"
      BORDER "Chip_Cash"  FILL  COLOR bg-card  ROUND
        TEXT "Label" { TEXT "CASH" FONT condensed 17 COLOR text-dim }
        TEXT "Value" { TEXT "$4,820" FONT condensed 22 COLOR green }
      END
    END
  END
END SCREEN
```

One `build_widget_ui` call. Widget Blueprint ready in seconds.

---

### By the Numbers

- 274 TCP commands
- 289 MCP tools
- 29 DSL parsers (Blueprint, Widget, BehaviorTree, DataTable, Material, and 24 more)
- `hex:#RRGGBB` color support — matches HTML/CSS exactly
- Widget design canvas defaults to 1920x1080
- HTML-to-UMG translator pipeline
- Built-in feedback system
- Works with Claude, GPT, Cursor, Windsurf, and any MCP-compatible agent

---

### New in 1.0.2

- **hex: colors** — Use familiar `hex:#E8A624` in any color property. Plugin auto-converts sRGB to linear.
- **Widget design size** — `set_widget_design_size` command. Defaults to 1920x1080.
- **HTML translator** — Design UIs in HTML/CSS, translate to UMG widget blueprints.
- **protect_widget_layout** — Lock visual layers so C++ only touches text and button widgets.
- **Feedback system** — Submit feature requests and bug reports directly from the plugin dashboard.

---

### How It Works

1. Install the plugin — TCP server starts automatically on port 13377
2. Configure your AI assistant to use the MCP server
3. Your AI connects and discovers all available tools
4. Describe what you want — your AI issues commands — Arcwright executes

No cloud required. No API keys. No subscription. Everything runs locally inside your UE project.

---

### Requirements

- Unreal Engine 5.4+
- Python 3.9+ (for MCP server)
- Any MCP-compatible AI assistant

---

### Support & Updates

Updates are delivered in two layers:
- C++ plugin updates via FAB
- Python tool updates via `git pull` (no recompile needed)

Arcwright checks for updates automatically and notifies your AI when a new version is available.
Full documentation at github.com/Divinity-Alpha/Arcwright.

---

## Tags
unreal-engine, ue5, ai, mcp, blueprint, widget, ui, automation, claude, gpt, cursor, tool, plugin, game-development

## Category
Code Plugins > Scripting

## Price
$49.99

## Supported Engine Versions
5.4, 5.5, 5.6, 5.7

## Supported Platforms
Windows
