# Arcwright Update Guide

## How Updates Work

Arcwright checks for updates automatically on each session start.
When an update is available, your AI will tell you immediately.

## Update Notification Example

  Arcwright 1.1.0 is available (you have 1.0.0).
  Released: 2026-04-15
  What's new:
    - New widget types: Carousel, TabPanel
    - DSL improvements: REPEAT macro for grids
  Download: https://www.fab.com/listings/arcwright

## Manual Version Check

Ask your AI: "Check if Arcwright is up to date"

Or run directly:
  python -c "from mcp_server.version_check import get_current_version; print(get_current_version())"

Via TCP:
  {"command": "health_check", "params": {}}
  Returns: {"version": "1.0.0", ...}

## Two Update Layers

### Layer 1: C++ Plugin (FAB Marketplace)
- Download from: https://www.fab.com/listings/arcwright
- Install by replacing the plugin folder
- Requires project recompilation
- Updated when: new UE version support, new TCP commands

### Layer 2: Python Scripts (Git)
- Update with: git pull in C:\BlueprintLLM\
- No recompilation needed
- Updated when: new DSL features, bug fixes, new patterns
- Restart the MCP server after pulling
