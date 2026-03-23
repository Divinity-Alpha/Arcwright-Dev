# Arcwright Check & Confirm — Standard Operating Procedure
# This file is loaded by the get_arcwright_quickstart MCP tool.
# Every AI session should follow these procedures.
#
# PRINCIPLE: No action is complete until its effect is verified.
# PRINCIPLE: Never trust "ok" — always inspect the result.
# PRINCIPLE: When verification fails, fix and retry before moving on.

---

## Rule Zero: StateManager Integration

**Every build script MUST use StateManager.** Direct `cmd()` calls bypass duplicate protection.

```python
from scripts.state_manager import StateManager

sm = StateManager(project_dir="/c/Projects/BoreandStroke")

# These check before creating — never duplicate
sm.safe_create_blueprint("BP_Economy", "Actor", variables=[...])
sm.safe_spawn_actor("Light_Main", x=0, y=0, z=290, ...)
sm.safe_setup_lighting("outdoor_day")
sm.safe_create_material("MAT_Gold", {"r": 1, "g": 0.84, "b": 0})

# Clean up duplicates from prior builds
sm.clean_duplicate_lights()

# Report what exists vs what Arcwright owns
sm.report()
```

### Build Sequence with StateManager:
1. `sm = StateManager(project_dir=...)` — load manifest
2. `sm.clean_duplicate_lights()` — fix prior build artifacts
3. `sm.safe_create_blueprint(...)` for each BP — skips if exists with nodes
4. Skeleton compile → add_nodes_batch → add_connections_batch → final compile
5. `sm.safe_spawn_actor(...)` for each actor — skips if label exists
6. `sm.save_manifest()` — persist what Arcwright created
7. Verify with Check & Confirm procedures below

---

## Quick Reference: Verification Commands

| Command | Purpose | When To Use |
|---|---|---|
| `get_blueprint_graph` | Inspect nodes, connections, compile status | After every Blueprint modification |
| `get_compile_status` | Check if Blueprint compiles clean | After add_nodes_batch / add_connections_batch |
| `verify_all_blueprints` | Batch compile check all Blueprints | After Blueprint phase is complete |
| `get_level_snapshot` | All actors with positions, classes, scales | After spawning actors or level setup |
| `get_actor_details` | Deep inspect one actor (components, properties) | When an actor doesn't look right |
| `get_asset_list` | List all assets by type on disk | After any phase to verify persistence |
| `get_widget_tree` | Widget hierarchy with properties | After widget creation |
| `get_log_output` | Recent UE log lines and errors | After PIE or when debugging |
| `take_viewport_screenshot` | Editor viewport capture | To see editor state |
| `get_player_view` | PIE player camera capture | To see what player sees at runtime |
| `get_player_location` | Player pawn position during PIE | To verify player is where expected |
| `teleport_player` | Move player to x,y,z during PIE | Navigate to verify different areas |
| `teleport_to_actor` | Move player near a named actor | Visit and verify specific objects |
| `look_at` | Point player camera at target | Face a specific actor for screenshot |
| `is_playing` | Check if PIE is running | Before issuing PIE-only commands |
| `play_in_editor` | Start PIE | Begin runtime verification |
| `stop_play` | Stop PIE | End runtime verification |

---

## Standard Verification Procedures

### After Creating a Blueprint:

```python
# 1. Create
cmd("create_blueprint", name="BP_MyActor", parent_class="Actor")

# 2. Add nodes
cmd("add_nodes_batch", blueprint="BP_MyActor", nodes=[...])

# 3. Add connections  
cmd("add_connections_batch", blueprint="BP_MyActor", connections=[...])

# 4. Compile
cmd("compile_blueprint", name="BP_MyActor")

# 5. CHECK: Verify everything
r = cmd("get_blueprint_graph", name="BP_MyActor")
data = r.get("data", {})
nodes = data.get("node_count", 0)
conns = data.get("connection_count", 0)
compiles = data.get("compiles", False)

# 6. CONFIRM or RETRY
if nodes >= EXPECTED_NODES and conns >= EXPECTED_CONNS and compiles:
    print(f"CONFIRMED: {name} — {nodes} nodes, {conns} connections, compiles=True")
else:
    print(f"DISCREPANCY: Expected {EXPECTED_NODES} nodes, got {nodes}. Expected {EXPECTED_CONNS} conns, got {conns}. Compiles={compiles}")
    # Diagnose: get_compile_status for error details
    # Fix: adjust nodes/connections
    # Retry: rebuild the Blueprint
```

### After Reparenting a Widget Blueprint:

```python
# 1. Reparent (auto-resolves function conflicts)
r = cmd("reparent_widget_blueprint", name="WBP_MyWidget", new_parent="MyCppWidget")
print(f"Compiled: {r['data']['compiled']}")
print(f"Conflicts resolved: {r['data']['conflicts_resolved']}")

# 2. If compile fails, check conflicts
if not r['data']['compiled']:
    for c in r['data']['conflicts_resolved']:
        print(f"  {c['function']}: {c['reason']} -> {c['action']}")

# 3. Verify parent class
r = cmd("get_blueprint_details", blueprint="WBP_MyWidget")
# Should show new parent in class info

# 4. PIE verify — widget visible with correct children
cmd("play_in_editor")
time.sleep(3)
r = cmd("get_viewport_widgets")
for w in r['data']['widgets']:
    if w['in_viewport']:
        print(f"HUD visible: {w['class']}, {w['child_count']} children")
cmd("stop_play")
```

### After Creating a Widget:

```python
# 1. Create
cmd("create_widget_blueprint", name="WBP_MyHUD")

# 2. Add children
cmd("add_widget_child", widget_name="WBP_MyHUD", type="CanvasPanel", name="Root")
cmd("add_widget_child", widget_name="WBP_MyHUD", type="TextBlock", name="Title", parent="Root")

# 3. CHECK: Verify hierarchy
r = cmd("get_widget_tree", name="WBP_MyHUD")
# Confirm: root exists, children are in correct order, properties set
```

### After Spawning Actors:

```python
# 1. Spawn
cmd("spawn_actor_at", label="Station_Degriming", x=-800, y=-600, z=50,
    mesh="/Engine/BasicShapes/Cube", scale_x=2, scale_y=1.5, scale_z=1)

# 2. CHECK: Verify position and scale
r = cmd("get_level_snapshot")
for actor in r.get("data", {}).get("actors", []):
    if actor.get("label") == "Station_Degriming":
        loc = actor.get("location")
        scale = actor.get("scale")
        print(f"CONFIRMED: Station_Degriming at {loc} scale {scale}")
        # Verify location matches what we sent
        assert abs(loc[0] - (-800)) < 1, f"X mismatch: expected -800, got {loc[0]}"
        assert abs(loc[1] - (-600)) < 1, f"Y mismatch: expected -600, got {loc[1]}"
        break
```

### After Level Setup (Full Verification):

```python
# 1. Save everything
cmd("save_all")

# 2. Verify all assets on disk
r = cmd("get_asset_list", type="Blueprint")
bp_count = len(r.get("assets", []))
print(f"Blueprints on disk: {bp_count}")

r = cmd("get_asset_list", type="DataTable")
dt_count = len(r.get("assets", []))
print(f"Data Tables on disk: {dt_count}")

# 3. Verify all Blueprints compile
r = cmd("verify_all_blueprints")
data = r.get("data", {})
print(f"Blueprints: {data.get('pass')}/{data.get('total')} compile clean")

# 4. Verify level actors
r = cmd("get_level_snapshot")
print(f"Actors in level: {r.get('data', {}).get('actor_count')}")

# 5. Visual verification — editor viewport
cmd("take_viewport_screenshot", filename="editor_verify.png")
```

### Play Test Cycle (Runtime Verification):

```python
# 1. Save first
cmd("save_all")

# 2. Start PIE
cmd("play_in_editor")
import time
time.sleep(3)  # Let game initialize

# 3. Verify player location
r = cmd("get_player_location")
loc = r.get("data", {}).get("location", [0,0,0])
print(f"Player spawned at: {loc}")

# 4. Capture what player sees
cmd("get_player_view", filename="player_spawn_view.png")

# 5. Check game logic is running
r = cmd("get_log_output", filter="BlueprintUserMessages", lines=50)
log_lines = r.get("data", {}).get("lines", [])
print(f"Blueprint messages: {len(log_lines)}")
for line in log_lines:
    print(f"  {line}")

# 6. QA Tour — visit key locations
locations = [
    ("Station_Degriming", "qa_degriming.png"),
    ("Station_Inspection", "qa_inspection.png"),
    ("Wall_North", "qa_wall_north.png"),
]
for actor_label, screenshot in locations:
    cmd("teleport_to_actor", actor=actor_label, distance=200)
    time.sleep(1)
    cmd("get_player_view", filename=screenshot)
    print(f"  Captured {actor_label}")

# 7. Stop PIE
cmd("stop_play")

# 8. Analyze screenshots
# Read each screenshot, check brightness/content
# Dark scene = indoor/correct, Bright scene = outdoor/sky/wrong
from PIL import Image
for _, screenshot in locations:
    img = Image.open(screenshot)
    pixels = list(img.getdata())
    avg = sum((p[0]+p[1]+p[2])/3 for p in pixels) / len(pixels)
    status = "INDOOR" if avg < 120 else "OUTDOOR/SKY"
    print(f"  {screenshot}: brightness={avg:.0f} — {status}")
```

---

## Discrepancy Resolution

When CHECK doesn't match EXPECTED, follow this protocol:

### Severity 1 — Auto-Fix (common parameter issues):
- Wrong param name → try alternative (blueprint vs name vs blueprint_name)
- Wrong pin name → try variations (then vs Then, execute vs Execute)
- Wrong function path → check ARCWRIGHT_AI_GUIDE.md for correct path
- **Action: Fix params, retry command, re-check**

### Severity 2 — Diagnose and Fix:
- Blueprint doesn't compile → `get_compile_status` for error details
- Connections missing → check node IDs, pin names, retry
- Actor not visible → check position/scale with `get_actor_details`
- Widget wrong → check hierarchy with `get_widget_tree`
- **Action: Get diagnostic info, understand root cause, rebuild**

### Severity 3 — Redesign:
- Node type not supported → find alternative approach
- Feature limitation → document and work around
- **Action: Log limitation, find alternative, update AI guide**

### Severity 4 — Escalate:
- After 3 retries with no resolution
- Crash that can't be diagnosed
- Visual issue requiring human judgment
- **Action: Take screenshot, log full state, report to user**

---

## Critical Lessons (from real testing)

### Blueprint Creation:
1. `create_blueprint` creates default BeginPlay at node_0. Do NOT create another in add_nodes_batch. Use node_0 for connections.
2. Function paths go AS the node type, not in params.FunctionReference:
   - WRONG: `{"type": "CallFunction", "params": {"FunctionReference": "/Script/..."}}`
   - RIGHT: `{"type": "/Script/Engine.KismetSystemLibrary:PrintString"}`
3. `compile_blueprint` parameter is `name`, not `blueprint`.
4. Always compile after adding nodes/connections — this triggers save to disk.
5. Verify with `get_blueprint_graph` after every Blueprint build.

### Level Building:
1. UE BasicShapes default to 100x100x100 units at scale 1. Scale appropriately.
2. PlayerStart must be INSIDE your geometry, not at default template position.
3. Light intensity for indoor scenes: 20000-50000 for PointLights.
4. Always `save_all` after level modifications.
5. Delete template geometry from starter maps before building your level.
6. `spawn_actor_at` uses top-level x,y,z and scale_x,scale_y,scale_z params.

### Persistence:
1. Blueprints are saved to disk when `compile_blueprint` runs (after the persistence fix).
2. Always call `compile_blueprint` after modifying a Blueprint's nodes/connections.
3. Verify persistence with `get_asset_list` — if the .uasset exists, it persisted.
4. Data Tables and Materials save immediately on creation.

### PIE (Play In Editor):
1. Use `play_in_editor` → `get_player_view` → `stop_play` for runtime verification.
2. `take_viewport_screenshot` captures the EDITOR camera, not the player's view.
3. `get_player_view` captures what the player actually sees during PIE.
4. Check `get_log_output` with filter="BlueprintUserMessages" to see PrintString output.
5. `teleport_to_actor` + `get_player_view` verifies specific areas of the level.

---

## Recommended Build Order with Verification

```
Phase 1: Data Tables
  → Quick check: response status
  → End-of-phase: get_asset_list type=DataTable

Phase 2: Input System
  → Quick check: response status

Phase 3: Gameplay Tags
  → Quick check: response status

Phase 4: Materials
  → Quick check: response status
  → End-of-phase: get_asset_list type=Material

Phase 5: Blueprints [CRITICAL — full verification]
  → Per-blueprint: get_blueprint_graph (nodes, connections, compiles)
  → End-of-phase: verify_all_blueprints

Phase 6: Widget UIs
  → Per-widget: get_widget_tree
  → End-of-phase: get_asset_list type=WidgetBlueprint

Phase 7: Level Setup
  → Per-actor: get_level_snapshot to verify positions
  → End-of-phase: take_viewport_screenshot

Phase 8: Final Verification
  → save_all
  → get_asset_list (all types)
  → verify_all_blueprints
  → play_in_editor → get_player_view → get_log_output → stop_play
  → QA Tour: teleport_to_actor for each key location → get_player_view
  → Full report: assets, nodes, connections, compile status, screenshots
```

---

## Widget Modification Safety Check

Before calling `set_widget_property`, verify:

1. **Is the widget in `/Game/UI/`?** (created by Arcwright's `create_widget_blueprint`)
   - **YES** → safe to modify
   - **NO** → **DO NOT MODIFY.** Read only via `get_widget_tree`.

2. If you must modify an external widget, the command now requires `force: true`
   and will log a warning. But **strongly prefer C++ runtime modification instead.**

3. **After ANY widget modification**, verify file size hasn't dramatically shrunk:
   ```python
   import os
   size_before = os.path.getsize("Content/UI/WBP_MyWidget.uasset")
   cmd("set_widget_property", ...)
   cmd("save_all")
   size_after = os.path.getsize("Content/UI/WBP_MyWidget.uasset")
   if size_after < size_before * 0.7:
       print("CORRUPTION DETECTED — restore from git!")
       os.system("git checkout -- Content/UI/WBP_MyWidget.uasset")
   ```

4. **Never report widget modifications as "PASS"** based on `get_viewport_widgets` alone.
   Widget tree data shows in-memory state, not what the player sees.
   Require `capture_full_screen` screenshot or user visual confirmation.
