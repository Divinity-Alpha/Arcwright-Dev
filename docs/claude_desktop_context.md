# Arcwright — Claude Desktop Context

> Quick-reference for Claude Desktop when building UE5 games via MCP.
> Last updated: 2026-03-07

---

## MCP Tool Reference (47 tools)

### Core Blueprint Tools

| Tool | Description |
|---|---|
| `health_check` | Verify UE Editor connection is live |
| `create_blueprint_from_dsl` | Parse DSL text -> compile Blueprint asset |
| `create_blueprint` | Natural language -> Blueprint (placeholder, not yet implemented) |
| `import_blueprint_ir` | Import a `.blueprint.json` IR file into UE |
| `get_blueprint_info` | Query Blueprint: nodes, pins, connections, variables, compile status |
| `duplicate_blueprint` | Duplicate a Blueprint asset with a new name |

### Node & Connection Editing

| Tool | Description |
|---|---|
| `add_node` | Add a single node to a Blueprint EventGraph by type name |
| `remove_node` | Remove a node and all its connections |
| `add_connection` | Wire two pins together (uses DSL name aliases) |
| `remove_connection` | Disconnect two pins |
| `set_node_param` | Set a pin's default value on a node |
| `set_variable_default` | Set a Blueprint variable's default value |

### Actor & Level Management

| Tool | Description |
|---|---|
| `spawn_actor` | Place an actor in the level at a position/rotation |
| `get_actors` | List all actors in the current level |
| `move_actor` | Update an actor's transform (location/rotation/scale) |
| `delete_actor` | Remove an actor from the level |
| `get_level_info` | Get current level name, path, and actor count |

### Component Management (SCS)

| Tool | Description |
|---|---|
| `add_component` | Add a component to a Blueprint (collision, mesh, light, etc.) |
| `get_components` | List all SCS components on a Blueprint |
| `remove_component` | Remove a component by name (idempotent) |
| `set_component_property` | Set a property on a Blueprint component |

### Materials

| Tool | Description |
|---|---|
| `create_material_instance` | Create a MaterialInstanceConstant (does NOT work with Substrate) |
| `create_simple_material` | Create a UMaterial with color + optional emissive (WORKS with Substrate) |
| `apply_material` | Apply a material to a Blueprint's mesh component |

### Widget / UI

| Tool | Description |
|---|---|
| `create_widget_blueprint` | Create a Widget Blueprint (UUserWidget) |
| `add_widget_child` | Add a widget to a Widget Blueprint hierarchy |
| `set_widget_property` | Set widget properties (text, color, size, position, anchors) |
| `get_widget_tree` | List widget hierarchy with types and properties |
| `remove_widget` | Remove a widget from a Widget Blueprint |

### Input System

| Tool | Description |
|---|---|
| `setup_input_context` | Create an Enhanced Input Mapping Context asset |
| `add_input_action` | Create an Enhanced Input Action asset |
| `add_input_mapping` | Bind a key to an action in a mapping context |
| `get_input_actions` | List all Input Action assets in the project |

### Audio

| Tool | Description |
|---|---|
| `play_sound_at_location` | Play a sound at a world location (fire-and-forget) |
| `add_audio_component` | Add a UAudioComponent to a Blueprint's SCS |
| `get_sound_assets` | List available sound assets (SoundWave, SoundCue) |

### Viewport & Screenshots

| Tool | Description |
|---|---|
| `set_viewport_camera` | Move the editor viewport camera to a position/rotation |
| `take_screenshot` | Capture editor viewport to PNG |
| `get_viewport_info` | Get viewport camera position, rotation, FOV, view mode |

### Niagara Particles

| Tool | Description |
|---|---|
| `spawn_niagara_at_location` | Spawn a Niagara particle system at a world location |
| `add_niagara_component` | Add a UNiagaraComponent to a Blueprint's SCS |
| `get_niagara_assets` | List available Niagara system assets |

### Behavior Trees

| Tool | Description |
|---|---|
| `create_behavior_tree_from_dsl` | Create BehaviorTree + Blackboard from BT DSL text |
| `get_behavior_tree_info` | Query BT structure: node counts, BB keys, hierarchy |

### Editor Session

| Tool | Description |
|---|---|
| `save_all` | Save all dirty packages (Ctrl+Shift+S equivalent) |
| `save_level` | Save the current level |
| `play_in_editor` | Request PIE start (queues only — user must click Play) |
| `stop_play` | Stop current PIE session |
| `get_output_log` | Read last N lines from UE output log |
| `quit_editor` | Clean shutdown: stop PIE, save all, exit |

---

## Template Library

### 1. Basic Actor Blueprint (BeginPlay + PrintString)

```
DSL:
BLUEPRINT: BP_MyActor
PARENT: Actor

GRAPH: EventGraph

EVENT: BeginPlay -> print1
CALL: PrintString | print1 | I="Hello World"
```

IR equivalent:
```json
{
  "metadata": {"name": "BP_MyActor", "parent_class": "Actor", "category": null},
  "variables": [],
  "nodes": [
    {"id": "n1", "dsl_type": "Event_BeginPlay", "params": {},
     "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay", "position": [0, 0]},
    {"id": "n2", "dsl_type": "PrintString", "params": {"InString": "Hello World"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "position": [300, 0]}
  ],
  "connections": [
    {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute", "type": "exec"}
  ]
}
```

### 2. Overlap Pickup (no Cast — works with DefaultPawn)

```json
{
  "metadata": {"name": "BP_Pickup", "parent_class": "Actor", "category": null},
  "variables": [],
  "nodes": [
    {"id": "n1", "dsl_type": "Event_ActorBeginOverlap", "params": {},
     "ue_class": "UK2Node_Event", "ue_event": "ReceiveActorBeginOverlap", "position": [0, 0]},
    {"id": "n2", "dsl_type": "PrintString", "params": {"InString": "Picked up!"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "position": [300, 0]},
    {"id": "n3", "dsl_type": "DestroyActor", "params": {},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.Actor:K2_DestroyActor", "position": [600, 0]}
  ],
  "connections": [
    {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute", "type": "exec"},
    {"src_node": "n2", "src_pin": "Then", "dst_node": "n3", "dst_pin": "Execute", "type": "exec"}
  ]
}
```

### 3. Patrol + Chase AI Controller

```json
{
  "metadata": {"name": "BP_EnemyAI", "parent_class": "AIController", "category": null},
  "variables": [],
  "nodes": [
    {"id": "n1", "dsl_type": "Event_BeginPlay", "params": {},
     "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay", "position": [0, 0]},
    {"id": "n2", "dsl_type": "PrintString", "params": {"InString": "AI Active"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "position": [300, 0]},
    {"id": "n3", "dsl_type": "MoveToLocation_A", "params": {"AcceptanceRadius": "100.0"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/AIModule.AIController:MoveToLocation", "position": [600, 0]},
    {"id": "n4", "dsl_type": "MakeVector_A", "params": {"X": "300.0", "Y": "-400.0", "Z": "50.0"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.KismetMathLibrary:MakeVector", "position": [400, 200]},
    {"id": "n5", "dsl_type": "Delay_A", "params": {"Duration": "2.0"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.KismetSystemLibrary:Delay", "position": [900, 0]},
    {"id": "n9", "dsl_type": "Event_Tick", "params": {},
     "ue_class": "UK2Node_Event", "ue_event": "ReceiveTick", "position": [0, 500]},
    {"id": "n10", "dsl_type": "GetPlayerPawn", "params": {"PlayerIndex": "0"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.GameplayStatics:GetPlayerPawn", "position": [200, 700]},
    {"id": "n11", "dsl_type": "GetDistanceTo", "params": {},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.Actor:GetDistanceTo", "position": [500, 700]},
    {"id": "n12", "dsl_type": "Less_DoubleDouble", "params": {"B": "800.0"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.KismetMathLibrary:Less_DoubleDouble", "position": [750, 700]},
    {"id": "n13", "dsl_type": "Branch", "params": {},
     "ue_class": "UK2Node_IfThenElse", "position": [400, 500]},
    {"id": "n14", "dsl_type": "PrintString_Chase", "params": {"InString": "CHASING!"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.KismetSystemLibrary:PrintString", "position": [700, 500]},
    {"id": "n15", "dsl_type": "GetActorLocation_Player", "params": {},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/Engine.Actor:K2_GetActorLocation", "position": [700, 800]},
    {"id": "n16", "dsl_type": "MoveToLocation_Chase",
     "params": {"AcceptanceRadius": "50.0"},
     "ue_class": "UK2Node_CallFunction",
     "ue_function": "/Script/AIModule.AIController:MoveToLocation", "position": [1000, 500]}
  ],
  "connections": [
    {"src_node": "n1", "src_pin": "Then", "dst_node": "n2", "dst_pin": "Execute", "type": "exec"},
    {"src_node": "n2", "src_pin": "Then", "dst_node": "n3", "dst_pin": "Execute", "type": "exec"},
    {"src_node": "n4", "src_pin": "ReturnValue", "dst_node": "n3", "dst_pin": "Dest", "type": "data"},
    {"src_node": "n3", "src_pin": "Then", "dst_node": "n5", "dst_pin": "Execute", "type": "exec"},
    {"src_node": "n9", "src_pin": "Then", "dst_node": "n13", "dst_pin": "Execute", "type": "exec"},
    {"src_node": "n10", "src_pin": "ReturnValue", "dst_node": "n11", "dst_pin": "OtherActor", "type": "data"},
    {"src_node": "n11", "src_pin": "ReturnValue", "dst_node": "n12", "dst_pin": "A", "type": "data"},
    {"src_node": "n12", "src_pin": "ReturnValue", "dst_node": "n13", "dst_pin": "Condition", "type": "data"},
    {"src_node": "n13", "src_pin": "Then", "dst_node": "n14", "dst_pin": "Execute", "type": "exec"},
    {"src_node": "n14", "src_pin": "Then", "dst_node": "n16", "dst_pin": "Execute", "type": "exec"},
    {"src_node": "n10", "src_pin": "ReturnValue", "dst_node": "n15", "dst_pin": "T", "type": "data"},
    {"src_node": "n15", "src_pin": "ReturnValue", "dst_node": "n16", "dst_pin": "Dest", "type": "data"}
  ]
}
```

### 4. Behavior Tree (Patrol + Chase)

```
BEHAVIORTREE: BT_EnemyPatrol
BLACKBOARD: BB_EnemyPatrol

KEY TargetActor: Object
KEY PatrolLocation: Vector

TREE:

SELECTOR: Root
  SEQUENCE: Chase
    DECORATOR: BlackboardBased [Key=TargetActor, Condition=IsSet, AbortMode=LowerPriority]
    TASK: MoveTo [Key=TargetActor, AcceptableRadius=200]
  SEQUENCE: Patrol
    TASK: MoveTo [Key=PatrolLocation, AcceptableRadius=50]
    TASK: Wait [Duration=3.0]
```

### 5. Widget HUD (Health Bar + Score Text)

```python
# Create Widget Blueprint
create_widget_blueprint(name="WBP_GameHUD")

# Build layout
add_widget_child(widget_blueprint="WBP_GameHUD", widget_name="RootCanvas", widget_type="CanvasPanel")
add_widget_child(widget_blueprint="WBP_GameHUD", widget_name="HealthBar", widget_type="ProgressBar", parent="RootCanvas")
add_widget_child(widget_blueprint="WBP_GameHUD", widget_name="ScoreText", widget_type="TextBlock", parent="RootCanvas")

# Style health bar
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="HealthBar",
    property_name="percent", value="0.75")
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="HealthBar",
    property_name="fill_color", value={"r": 0.0, "g": 1.0, "b": 0.0, "a": 1.0})
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="HealthBar",
    property_name="position", value={"x": 20, "y": 20})
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="HealthBar",
    property_name="size", value={"x": 300, "y": 30})

# Style score text
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="ScoreText",
    property_name="text", value="Score: 0")
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="ScoreText",
    property_name="font_size", value="24")
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="ScoreText",
    property_name="color", value={"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0})
set_widget_property(widget_blueprint="WBP_GameHUD", widget_name="ScoreText",
    property_name="position", value={"x": 20, "y": 60})
```

---

## Known Constraints

### Hard Blockers
1. **Cast To Character fails with DefaultPawn.** Default UE test projects use DefaultPawn (spectator camera), not a Character. Cast silently fails and the success exec pin never fires. Wire overlap events directly to PrintString/logic without casting.
2. **PIE cannot start programmatically.** `play_in_editor` queues the request but UE 5.7's engine tick loop doesn't process it. User must click Play manually.
3. **UE cannot launch while training saturates the PRO 6000.** DXGI enumerates ALL GPU adapters. If the training GPU is at 99%+ VRAM, the probe hangs indefinitely.
4. **SetMaterial() silently fails on SCS templates.** Use `OverrideMaterials` array directly. The `apply_material` and `set_component_property` tools handle this.
5. **MaterialInstance doesn't work with Substrate rendering.** Use `create_simple_material` instead of `create_material_instance` for visible colors.

### Behavioral Quirks
6. **SCS components need actor re-spawn to take effect.** After `add_component`, already-placed actors don't update. Must `delete_actor` + `spawn_actor` to see changes.
7. **World Partition stores actors as external packages.** Saving just the map doesn't save actors. Use `save_all` to flush everything.
8. **`save_level` blocks on untitled maps.** A "Save As" dialog pops up. Always save with a name first, or use `save_all` which skips untitled maps.
9. **Delete before re-import.** Overwriting an existing Blueprint causes crashes. Always delete first.
10. **add_node has limited type support.** Complex node types (CallFunction with specific UE paths) may produce nodes with 0 pins. Use IR import for reliable results.

### IR Format Rules
11. **Connection fields**: `src_node`, `src_pin`, `dst_node`, `dst_pin`, `type` (NOT `source_node`/`target_node`).
12. **Metadata fields**: `metadata.name`, `metadata.parent_class` (NOT `blueprint_name`).
13. **UE function paths**: `/Script/<Module>.<ClassName>:<FunctionName>` — ClassName uses the UE reflection name WITHOUT C++ 'A' prefix (e.g., `AIController` not `AAIController`, `Actor` not `AActor`).
14. **spawn_actor parameter**: Use `class` (NOT `blueprint`) as the JSON field. Full path: `/Game/Arcwright/Generated/BP_Name.BP_Name`.

---

## Proven Workflow Order

### Creating a Game Scene from Scratch

```
1. health_check                       -- verify connection
2. create_blueprint_from_dsl / import_blueprint_ir  -- create BPs
3. add_component (collision, mesh)     -- add physics/visuals
4. create_simple_material              -- create colored materials
5. apply_material                      -- apply to BP meshes
6. spawn_actor (for each instance)     -- place in level
7. save_all                            -- persist everything
```

### Modifying Existing Blueprints

```
1. get_blueprint_info                  -- inspect current state
2. add_node / remove_node              -- modify graph
3. add_connection / remove_connection  -- rewire pins
4. set_node_param                      -- set default values
5. save_all                            -- persist
```

### After Changing a Blueprint's Components

```
1. add_component / remove_component    -- modify BP
2. get_actors                          -- find placed instances
3. For each instance:
   a. Note its transform (from get_actors)
   b. delete_actor
   c. spawn_actor with same transform  -- re-spawn with updated BP
4. save_all
```

### Building a Widget HUD

```
1. create_widget_blueprint             -- create the WBP
2. add_widget_child (CanvasPanel)      -- root layout
3. add_widget_child (children)         -- add TextBlock, ProgressBar, etc.
4. set_widget_property (per widget)    -- text, color, size, position
5. get_widget_tree                     -- verify structure
6. save_all
```

### Creating a Behavior Tree

```
1. Write BT DSL text (indentation-based)
2. create_behavior_tree_from_dsl       -- creates BT + Blackboard assets
3. get_behavior_tree_info              -- verify structure
4. save_all
```

---

## Common Mesh Paths

| Shape | Asset Path |
|---|---|
| Cube | `/Engine/BasicShapes/Cube.Cube` |
| Sphere | `/Engine/BasicShapes/Sphere.Sphere` |
| Cylinder | `/Engine/BasicShapes/Cylinder.Cylinder` |
| Cone | `/Engine/BasicShapes/Cone.Cone` |
| Plane | `/Engine/BasicShapes/Plane.Plane` |

### Setting a Mesh on a Component

```python
set_component_property(
    blueprint="BP_MyActor",
    component_name="StaticMesh",
    property_name="static_mesh",
    value="/Engine/BasicShapes/Sphere.Sphere"
)
```

---

## Common UE Function Paths

| Function | Path |
|---|---|
| PrintString | `/Script/Engine.KismetSystemLibrary:PrintString` |
| Delay | `/Script/Engine.KismetSystemLibrary:Delay` |
| DestroyActor | `/Script/Engine.Actor:K2_DestroyActor` |
| GetActorLocation | `/Script/Engine.Actor:K2_GetActorLocation` |
| SetActorLocation | `/Script/Engine.Actor:K2_SetActorLocation` |
| GetDistanceTo | `/Script/Engine.Actor:GetDistanceTo` |
| GetPlayerPawn | `/Script/Engine.GameplayStatics:GetPlayerPawn` |
| SpawnActor | `/Script/Engine.GameplayStatics:BeginDeferredActorSpawnFromClass` |
| MakeVector | `/Script/Engine.KismetMathLibrary:MakeVector` |
| Add_DoubleDouble | `/Script/Engine.KismetMathLibrary:Add_DoubleDouble` |
| Subtract_DoubleDouble | `/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble` |
| Multiply_DoubleDouble | `/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble` |
| Less_DoubleDouble | `/Script/Engine.KismetMathLibrary:Less_DoubleDouble` |
| Greater_DoubleDouble | `/Script/Engine.KismetMathLibrary:Greater_DoubleDouble` |
| MoveToLocation | `/Script/AIModule.AIController:MoveToLocation` |
| MoveToActor | `/Script/AIModule.AIController:MoveToActor` |
| PlaySoundAtLocation | `/Script/Engine.GameplayStatics:PlaySoundAtLocation` |

**Note:** UE 5.7 uses `Double` instead of `Float` for math functions. Always use `Add_DoubleDouble`, not `Add_FloatFloat`.

---

## DSL Syntax Reference (Condensed)

### Blueprint DSL

```
BLUEPRINT: <name>
PARENT: <parent_class>

VARIABLE: <name> | <type> [= <default>]

GRAPH: EventGraph

EVENT: <event_type> -> <next_node_id>
CALL: <function> | <node_id> | <param>=<value>, ...
BRANCH: <node_id> | C=<condition_source>
  TRUE -> <node_id>
  FALSE -> <node_id>
SEQUENCE: <node_id>
  A -> <node_id>
  B -> <node_id>

EXEC: <src_id> -> <dst_id>
DATA: <src_id>.<pin> -> <dst_id>.<pin>
```

### Connection Types
- `EXEC` lines: execution flow (white wires in UE)
- `DATA` lines: data flow (colored wires in UE)

### Node ID Convention
- Each node gets a unique ID (e.g., `print1`, `branch1`, `delay1`)
- IDs are referenced in EXEC/DATA lines to wire nodes together

### Behavior Tree DSL

```
BEHAVIORTREE: <name>
BLACKBOARD: <bb_name>

KEY <name>: <type>

TREE:

<COMPOSITE_TYPE>: <name>
  <COMPOSITE_TYPE>: <name>
    DECORATOR: <type> [Key=<val>, ...]
    SERVICE: <type> [Interval=<val>, ...]
    TASK: <type> [Key=<val>, ...]
```

Indentation (2 spaces) defines parent-child hierarchy.

**Composite types:** Selector, Sequence, SimpleParallel
**Task types:** MoveTo, Wait, RotateToFaceBBEntry, WaitBlackboardTime, FinishWithResult, PlaySound, PlayAnimation, RunBehavior, GameplayTask, PushPawnAction, StopBehaviorTree, SetTagCooldown, MakeNoise
**Decorator types:** BlackboardBased, Cooldown, Loop, TimeLimit, ForceSuccess, IsAtLocation, ConeCheck, IsBBEntryOfClass, CompareBBEntries, TagCooldown, CheckGameplayTag, KeepInCone
**BB Key types:** Bool, Int, Float, String, Name, Vector, Rotator, Object, Class, Enum

---

## Supported Component Types

| Friendly Name | Use For |
|---|---|
| `BoxCollision` | Rectangular collision/trigger volumes |
| `SphereCollision` | Spherical collision/trigger volumes |
| `CapsuleCollision` | Character-shaped collision |
| `StaticMesh` | Visible 3D geometry |
| `PointLight` | Omnidirectional light |
| `SpotLight` | Directional cone light |
| `Audio` | Sound playback |
| `Arrow` | Debug direction indicator |
| `Scene` | Empty transform parent |

### Common Component Properties

```python
# Collision
add_component(blueprint="BP_X", component_type="SphereCollision", component_name="Trigger",
    properties={"radius": 150.0, "generate_overlap_events": True})

# Static Mesh
add_component(blueprint="BP_X", component_type="StaticMesh", component_name="Mesh",
    properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere"})

# Point Light
add_component(blueprint="BP_X", component_type="PointLight", component_name="Glow",
    properties={"intensity": 5000.0, "light_color": {"r": 255, "g": 200, "b": 50},
                "attenuation_radius": 500.0})
```

---

## Widget Types

| Type | Use For |
|---|---|
| `CanvasPanel` | Root layout container (absolute positioning) |
| `VerticalBox` | Stack children vertically |
| `HorizontalBox` | Stack children horizontally |
| `Overlay` | Layer children on top of each other |
| `SizeBox` | Force a specific size on a child |
| `TextBlock` | Display text |
| `ProgressBar` | Health bars, loading bars |
| `Image` | Display textures/icons |
| `Button` | Clickable button |

### Widget Properties

| Property | Applies To | Value Type |
|---|---|---|
| `text` | TextBlock | string |
| `font_size` | TextBlock | int |
| `color` | TextBlock | `{r, g, b, a}` (0.0-1.0) |
| `percent` | ProgressBar | float (0.0-1.0) |
| `fill_color` | ProgressBar | `{r, g, b, a}` |
| `position` | Any (in CanvasPanel) | `{x, y}` |
| `size` | Any (in CanvasPanel) | `{x, y}` |
| `alignment` | Any (in CanvasPanel) | `{x, y}` (0.0-1.0) |

---

## Quick Reference: spawn_actor

```python
# Spawn from a generated Blueprint
spawn_actor(
    actor_class="/Game/Arcwright/Generated/BP_Pickup.BP_Pickup",
    label="Pickup_1",
    x=500.0, y=0.0, z=100.0
)

# Spawn a plain empty actor
spawn_actor(actor_class="", label="EmptyActor", x=0.0, y=0.0, z=0.0)
```

Always use the full `/Game/...` path with the asset name doubled (folder path + `.ClassName`).

---

## Error Recovery Patterns

### "Blueprint already exists" on re-import
```python
# Delete first, then import
import_blueprint_ir(ir_path="C:/path/to/file.blueprint.json", delete_existing=True)
```

### Actor not showing component changes
```python
# Re-spawn the actor after modifying its Blueprint
actors = get_actors()  # find the old instance
delete_actor(label="OldActor_1")
spawn_actor(actor_class="/Game/Arcwright/Generated/BP_Updated.BP_Updated",
    label="OldActor_1", x=..., y=..., z=...)
```

### Material appears gray (Substrate rendering)
```python
# Use create_simple_material, NOT create_material_instance
create_simple_material(name="MAT_Red", color={"r": 1.0, "g": 0.0, "b": 0.0})
```
