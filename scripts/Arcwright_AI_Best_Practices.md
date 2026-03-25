# Arcwright AI Best Practices Guide
# This file teaches AI assistants (Claude, GPT, Cursor, etc.) how to use Arcwright correctly.
# Include this in your AI's context when working with Arcwright, or reference it via the
# get_arcwright_quickstart MCP teaching tool.
#
# Last updated: 2026-03-21
# Version: 1.0

---

## 1. Connection & Communication

### TCP Protocol
- Arcwright runs a TCP server on `localhost:13377`
- Send JSON commands terminated with `\n`
- Format: `{"command": "command_name", "params": {key: value}}\n`
- Response is JSON terminated with `\n`
- Always check `response.status` — "ok" means success, "error" means failure

### Connection Stability
- Reconnect every 30-40 commands as a safety measure
- If a command times out, reconnect and retry once before reporting failure
- The server sets TCP_NODELAY and 256KB buffers — large responses are fine

### DO NOT assume "ok" means the asset is complete
- `create_blueprint` returning "ok" means the asset FILE was created
- It does NOT mean nodes, variables, or connections were added
- Always verify critical assets by opening them or querying their contents

---

## 2. Blueprint Creation — CRITICAL

### The correct workflow for creating Blueprints with logic:

**Step 1: Create the Blueprint asset**
```json
{"command": "create_blueprint", "params": {"name": "BP_MyActor", "parent_class": "Actor"}}
```

**Step 2: Add variables (if needed)**
```json
{"command": "add_blueprint_variable", "params": {"blueprint": "BP_MyActor", "name": "Health", "type": "Float", "default": "100.0"}}
```

**Step 3: Add nodes in batch**
```json
{"command": "add_nodes_batch", "params": {"blueprint": "BP_MyActor", "nodes": [
  {"id": "1", "type": "K2Node_Event", "event": "ReceiveBeginPlay", "position": [0, 0]},
  {"id": "2", "type": "K2Node_CallFunction", "function": "/Script/Engine.KismetSystemLibrary.PrintString", "position": [300, 0], "params": {"InString": "Hello!"}}
]}}
```

**Step 4: Wire connections in batch**
```json
{"command": "add_connections_batch", "params": {"blueprint": "BP_MyActor", "connections": [
  {"from_node": "1", "from_pin": "then", "to_node": "2", "to_pin": "execute"}
]}}
```

**Step 5: Compile**
```json
{"command": "compile_blueprint", "params": {"blueprint": "BP_MyActor"}}
```

### OR use the single-command IR JSON approach:
```json
{"command": "import_from_ir", "params": {"ir": "{\"metadata\":{\"name\":\"BP_MyActor\",\"parent_class\":\"Actor\"},\"variables\":[],\"nodes\":[...],\"connections\":[...]}"}}
```

### CRITICAL: IR JSON format
The IR JSON MUST use the metadata wrapper:
```json
{
  "metadata": {"name": "BP_Name", "parent_class": "Actor"},
  "variables": [...],
  "nodes": [...],
  "connections": [...]
}
```

**WRONG** (will crash or create empty Blueprint):
```json
{"blueprint_name": "BP_Name", "parent_class": "Actor", "nodes": [...]}
```

### Supported node types:
| Node Type | K2Node Class | Use For |
|---|---|---|
| Event | K2Node_Event | BeginPlay, Tick, ActorBeginOverlap, AnyDamage |
| CustomEvent | K2Node_CustomEvent | User-defined events (two-pass: definition then call) |
| CallFunction | K2Node_CallFunction | Any UFunction — PrintString, math, gameplay statics |
| Branch | K2Node_IfThenElse | If/then/else flow control |
| Sequence | K2Node_ExecutionSequence | Execute multiple outputs in order |
| ForLoop | K2Node_ForLoop | For loop (macro) |
| ForEachLoop | K2Node_ForEachLoop | Iterate arrays |
| WhileLoop | K2Node_WhileLoop | While loop |
| VariableGet | K2Node_VariableGet | Read a variable |
| VariableSet | K2Node_VariableSet | Write a variable |
| SpawnActor | K2Node_SpawnActorFromClass | Spawn actor at runtime |
| Cast | K2Node_DynamicCast | Cast to a specific class |
| SwitchInt | K2Node_SwitchInteger | Switch on integer |
| SwitchString | K2Node_SwitchString | Switch on string |
| BreakStruct | K2Node_BreakStruct | Break a struct into pins |
| InputAction | K2Node_InputAction | Respond to input action |
| FlipFlop | FlipFlop macro | Alternates between two outputs |
| DoOnce | DoOnce macro | Execute only once |
| Gate | Gate macro | Controllable gate |
| MultiGate | MultiGate macro | Route to multiple outputs |

### Pin naming conventions:
- Execution pins: "execute" (input), "then" (output)
- Branch: "Condition" (input bool), "True" (output), "False" (output)
- ForLoop: "FirstIndex", "LastIndex", "LoopBody", "Index", "Completed"
- Function params: match the UFunction parameter names exactly
- Return value: "ReturnValue"

---

## 3. Widget UI Creation

### The correct workflow:

**Step 1: Create the Widget Blueprint**
```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_MyHUD"}}
```

**Step 2: Add a root Canvas Panel**
```json
{"command": "add_widget_child", "params": {"widget_name": "WBP_MyHUD", "type": "CanvasPanel", "name": "Root"}}
```

**Step 3: Add child widgets**
```json
{"command": "add_widget_child", "params": {"widget_name": "WBP_MyHUD", "type": "TextBlock", "name": "TitleText", "parent": "Root"}}
```

**Step 4: Set properties**
```json
{"command": "set_widget_property", "params": {"widget_name": "WBP_MyHUD", "target": "TitleText", "property": "Text", "value": "My Game"}}
```

### Widget types supported:
TextBlock, ProgressBar, Image, Button, VerticalBox, HorizontalBox, CanvasPanel, Overlay, SizeBox, Border, Spacer, ScrollBox, CheckBox, EditableTextBox

### Anchoring:
Use `set_widget_anchor` with presets: TopLeft, TopCenter, TopRight, CenterLeft, Center, CenterRight, BottomLeft, BottomCenter, BottomRight, TopFill, BottomFill, LeftFill, RightFill, Fill

### Styling tips for game UIs:
- Use the Widget DSL theme system — 8 built-in themes (SciFi, Medieval, Racing, Fighting, Simulation, Normal, Horror, Cartoon)
- Color values are hex strings: "#FF3A5C"
- Font sizes are integers
- Always set anchor and offset for Canvas Panel children

---

## 4. Data Table Creation

### The correct workflow:

**Step 1: Create the table with column schema**
```json
{"command": "create_data_table", "params": {
  "name": "DT_Weapons",
  "columns": {"WeaponID": "Name", "Damage": "Float", "FireRate": "Float", "AmmoCapacity": "Integer", "WeaponName": "String"}
}}
```

**Step 2: Add rows**
```json
{"command": "add_data_table_row", "params": {
  "table_name": "DT_Weapons",
  "row_name": "Pistol",
  "values": {"WeaponID": "Pistol", "Damage": 25.0, "FireRate": 0.3, "AmmoCapacity": 12, "WeaponName": "M1911"}
}}
```

### Important: 
- `row_name` is the row identifier — must be unique per table
- `values` is a dict, NOT a JSON string
- Column types: Name, String, Float, Integer, Bool
- The first column is typically the row key

---

## 5. Spawning & Level Building

### Spawn an actor from a Blueprint:
```json
{"command": "spawn_actor_at", "params": {"blueprint": "BP_MyActor", "label": "MyActor_01", "x": 100, "y": 200, "z": 0}}
```

### Spawn a basic mesh:
```json
{"command": "spawn_actor_at", "params": {"label": "Floor", "x": 0, "y": 0, "z": 0, "mesh": "/Engine/BasicShapes/Cube", "scale_x": 10, "scale_y": 10, "scale_z": 0.1}}
```

### Apply materials:
```json
{"command": "apply_material", "params": {"actor": "Floor", "material": "M_MyMaterial"}}
```

### Set properties:
```json
{"command": "set_actor_property", "params": {"actor": "MyActor_01", "property": "Mobility", "value": "Movable"}}
```

### Player Start:
- Find existing: `find_actors` with class_name "PlayerStart"
- Move it: `set_actor_transform` with x, y, z, yaw
- The player spawns here on Play

### Game Mode:
- Set via: `set_game_mode` with game_mode parameter
- The GameMode Blueprint controls what player controller and HUD are used

---

## 6. Common Mistakes to Avoid

### Blueprint creation:
- ❌ Sending `{"blueprint_name": "BP_Test"}` — WRONG field name, will crash
- ✅ Sending `{"metadata": {"name": "BP_Test", "parent_class": "Actor"}}` — correct IR format
- ❌ Creating a Blueprint and assuming it has nodes — it starts EMPTY
- ✅ Always add nodes and connections after creation
- ❌ Using `create_blueprint("Make a health system")` as natural language — the command takes structured params, not descriptions
- ✅ Design the Blueprint logic yourself, then express it as nodes and connections

### Widget creation:
- ❌ Adding children without a root CanvasPanel — widgets need a layout parent
- ✅ Always create CanvasPanel "Root" first, then add children to it
- ❌ Setting position directly — use anchors and offsets instead
- ✅ Use `set_widget_anchor` with named presets

### Data Tables:
- ❌ Passing `values` as a JSON string: `"values": "{\"key\": \"val\"}"`
- ✅ Passing `values` as a dict: `"values": {"key": "val"}`

### Actor spawning:
- ❌ Spawning actors at z=0 when the floor is at z=0 — actors clip into floor
- ✅ Spawn actors slightly above the floor (z=50 or higher)
- ❌ Forgetting to save: changes are in-memory until `save_all` is called
- ✅ Call `save_all` after building a batch of assets

### Materials:
- ❌ Applying a material that doesn't exist yet
- ✅ Create the material first with `create_material_graph`, then apply it

### General:
- ❌ Sending 200+ commands without reconnecting — connection may drop
- ✅ Reconnect every 30-40 commands
- ❌ Assuming the level has content — a new project has an empty default level
- ✅ Build the environment (floor, walls, lights) before placing gameplay objects
- ❌ Pressing Play expecting to see results without setting GameMode and placing actors
- ✅ Set GameMode, place PlayerStart, spawn actors, add HUD manager, then Play

---

## 7. Recommended Build Order for a New Game

1. **Data Tables** first — define your game data (weapons, enemies, items, stats)
2. **Input System** — set up controls
3. **Gameplay Tags** — tag hierarchy for your systems
4. **Materials** — create visual materials
5. **Level Environment** — floor, walls, lights, player start
6. **Blueprints** — game logic (managers, controllers, gameplay)
7. **Widget UIs** — HUD, menus, panels
8. **Dialogue & Quests** — narrative content
9. **Sound Design** — audio environment
10. **Animation** — character animation (if applicable)
11. **Level Sequences** — cinematics
12. **Wire everything** — set GameMode, spawn managers, add HUD
13. **Save and test** — `save_all`, then Play in Editor

---

## 8. Debugging

### Check what exists:
```json
{"command": "find_blueprints"}
{"command": "find_actors"}
{"command": "find_assets", "params": {"class_name": "DataTable"}}
{"command": "get_level_info"}
{"command": "get_widget_tree", "params": {"widget_name": "WBP_MyHUD"}}
```

### If a Blueprint is empty:
- It was created but nodes weren't added
- Use `add_nodes_batch` and `add_connections_batch` to populate it
- Then `compile_blueprint` to compile

### If nothing shows on Play:
- Check GameMode is set: `get_game_mode`
- Check PlayerStart exists and is positioned correctly
- Check actors are actually in the level: `find_actors`
- Check the HUD is being created on BeginPlay
- Check lighting exists — no lights = black screen

### If commands return "error":
- Read the error message — it usually tells you exactly what's wrong
- Common: asset not found (wrong name), invalid parameter type, missing required param

---

## 9. Teaching Tools

Call these MCP tools to learn DSL formats on demand:
- `get_arcwright_quickstart` — overview of all capabilities
- `get_blueprint_dsl_guide` — Blueprint IR JSON format with examples
- `get_animation_dsl_guide` — Animation Blueprint DSL format
- `get_material_dsl_guide` — Material Graph DSL format
- `get_widget_dsl_guide` — Widget UI DSL format (if available)
- `get_dialogue_dsl_guide` — Dialogue Tree format
- `get_quest_dsl_guide` — Quest System format
- `get_sequence_dsl_guide` — Level Sequence format
- `get_gas_dsl_guide` — Gameplay Ability System format
- `get_tags_dsl_guide` — Gameplay Tags format
- `get_input_dsl_guide` — Enhanced Input format
- `get_perception_dsl_guide` — AI Perception format
- `get_physics_dsl_guide` — Physics Constraints format
- `get_sound_dsl_guide` — Sound Design format
- `get_replication_dsl_guide` — Multiplayer Replication format
- And more — one guide per DSL system

Each guide returns the format spec, valid types, and working examples.

---

## 10. Performance Tips

- Batch operations are faster than individual commands (use add_nodes_batch, not individual add_node calls)
- Create all Data Tables before Blueprints (Blueprints may reference table data)
- Create materials before applying them to actors
- Save periodically with save_all — don't wait until the end
- Use find_actors to verify placement before moving on to the next system
