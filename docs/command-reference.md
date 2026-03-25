# Arcwright Command Reference

Complete reference for all TCP commands available through the Arcwright UE5 plugin. Commands are sent as newline-delimited JSON to `localhost:13377`.

**Protocol format:**
```
Request:  {"command": "<name>", "params": {<params>}}\n
Response: {"status": "ok", "data": {<result>}}\n
Error:    {"status": "error", "message": "<description>"}\n
```

---

## Table of Contents

- [Core](#core)
- [Blueprint CRUD](#blueprint-crud)
- [Node Editing](#node-editing)
- [Level Actors](#level-actors)
- [Components](#components)
- [Materials](#materials)
- [Widgets](#widgets)
- [Behavior Trees](#behavior-trees)
- [Data Tables](#data-tables)
- [Splines](#splines)
- [Post-Process](#post-process)
- [Physics](#physics)
- [Movement](#movement)
- [Sequencer](#sequencer)
- [Landscape and Foliage](#landscape-and-foliage)
- [Asset Import](#asset-import)
- [Scene Setup](#scene-setup)
- [Query and Discovery](#query-and-discovery)
- [Batch Operations](#batch-operations)
- [In-Place Modification](#in-place-modification)
- [Properties and Configuration](#properties-and-configuration)
- [PIE and Debugging](#pie-and-debugging)

---

## Core

### health_check

Check that the Arcwright command server is running.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "health_check", "params": {}}

// Response
{"status": "ok", "data": {"server": "Arcwright", "version": "1.0", "engine": "5.7.0"}}
```

### save_all

Save all dirty packages (equivalent to Ctrl+Shift+S). Automatically handles World Partition external actor packages.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "save_all", "params": {}}

// Response
{"status": "ok", "data": {"saved": true, "external_actors_saved": 12}}
```

**Note:** Skips untitled maps to avoid blocking "Save As" dialogs.

### save_level

Save the current level to disk.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | No | Level name. Uses current level if omitted. |

```json
{"command": "save_level", "params": {}}
```

### get_level_info

Get the current level name, path, and actor count.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "get_level_info", "params": {}}

// Response
{"status": "ok", "data": {"level_name": "ArenaLevel", "level_path": "/Game/Maps/ArenaLevel", "actor_count": 47}}
```

### quit_editor

Cleanly shut down the UE Editor. Stops PIE, saves all packages, then exits.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `skip_save` | bool | No | If true, skip saving before exit. Default: false. |

```json
{"command": "quit_editor", "params": {}}
```

**Note:** The response is sent before the editor begins shutting down. The TCP connection will close shortly after.

---

## Blueprint CRUD

### import_from_ir

Import a `.blueprint.json` IR file and create a compiled Blueprint asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | Yes | Absolute path to the `.blueprint.json` file. |

```json
{"command": "import_from_ir", "params": {"path": "C:/project/test_ir/BP_Pickup.blueprint.json"}}

// Response
{
  "status": "ok",
  "data": {
    "blueprint_name": "BP_Pickup",
    "nodes_created": 8,
    "connections_wired": 7,
    "compiled": true,
    "variables": ["Score", "IsActive"]
  }
}
```

**Note:** Delete existing Blueprints with the same name before re-importing. Overwriting causes crashes.

### get_blueprint_info

Query a Blueprint's full structure including nodes, connections, variables, and compile status.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name (e.g. `"BP_Pickup"`). |

```json
{"command": "get_blueprint_info", "params": {"name": "BP_Pickup"}}

// Response
{
  "status": "ok",
  "data": {
    "name": "BP_Pickup",
    "parent_class": "Actor",
    "compiled": true,
    "nodes": [...],
    "connections": [...],
    "variables": [{"name": "Score", "type": "Integer", "default": "10"}]
  }
}
```

### get_blueprint_details

Extended Blueprint inspection with variables, node list, events, and components.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |

```json
{"command": "get_blueprint_details", "params": {"name": "BP_Pickup"}}
```

### compile_blueprint

Recompile a Blueprint asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |

```json
{"command": "compile_blueprint", "params": {"name": "BP_Pickup"}}
```

### delete_blueprint

Delete a Blueprint asset. Uses `ForceDeleteObjects`.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |

```json
{"command": "delete_blueprint", "params": {"name": "BP_Pickup"}}
```

### duplicate_blueprint

Duplicate an existing Blueprint with a new name.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `source_name` | string | Yes | Source Blueprint name. |
| `new_name` | string | Yes | Name for the duplicate. |

```json
{"command": "duplicate_blueprint", "params": {"source_name": "BP_Pickup", "new_name": "BP_PickupGold"}}
```

### create_blueprint_from_dsl

Create a Blueprint from raw DSL text. Parses the DSL, generates IR, and creates the Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `dsl` | string | Yes | Raw Blueprint DSL text. |
| `name` | string | No | Blueprint name override. Extracted from DSL if omitted. |

```json
{
  "command": "create_blueprint_from_dsl",
  "params": {
    "dsl": "BLUEPRINT: BP_Test\nPARENT: Actor\n\nNODE Event_BeginPlay: UK2Node_Event [ue_event=ReceiveBeginPlay]\nNODE PrintHello: UK2Node_CallFunction [ue_function=PrintString] {I=\"Hello\"}\n\nEXEC Event_BeginPlay.Then -> PrintHello.Execute"
  }
}
```

---

## Node Editing

### add_node

Add a single node to a Blueprint's EventGraph.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `node_type` | string | Yes | Node type name. Common values: `Delay`, `Branch`, `PrintString`, `Sequence`, `ForLoop`, `SpawnActorFromClass`. For UE functions, use the full path: `/Script/Engine.KismetSystemLibrary:PrintString`. |
| `node_id` | string | No | Custom ID for the node. Auto-generated if omitted. |
| `params` | object | No | Pin default values (e.g. `{"Duration": "2.0"}`). |
| `pos_x` | number | No | Graph X position. |
| `pos_y` | number | No | Graph Y position. |

```json
{
  "command": "add_node",
  "params": {
    "blueprint": "BP_Test",
    "node_type": "Delay",
    "node_id": "delay_1",
    "params": {"Duration": "3.0"}
  }
}

// Response
{"status": "ok", "data": {"node_id": "delay_1", "node_type": "Delay", "pins": [...]}}
```

### remove_node

Remove a node and all its connections from a Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `node_id` | string | Yes | Node GUID or friendly ID. |

```json
{"command": "remove_node", "params": {"blueprint": "BP_Test", "node_id": "delay_1"}}
```

### add_connection

Wire two pins together. Supports auto-conversion (e.g. Float to String).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `source_node` | string | Yes | Source node ID. |
| `source_pin` | string | Yes | Source pin name (DSL aliases supported). |
| `target_node` | string | Yes | Target node ID. |
| `target_pin` | string | Yes | Target pin name (DSL aliases supported). |

```json
{
  "command": "add_connection",
  "params": {
    "blueprint": "BP_Test",
    "source_node": "event_beginplay",
    "source_pin": "Then",
    "target_node": "delay_1",
    "target_pin": "Execute"
  }
}
```

### remove_connection

Disconnect two pins.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `source_node` | string | Yes | Source node ID. |
| `source_pin` | string | Yes | Source pin name. |
| `target_node` | string | Yes | Target node ID. |
| `target_pin` | string | Yes | Target pin name. |

```json
{
  "command": "remove_connection",
  "params": {
    "blueprint": "BP_Test",
    "source_node": "event_beginplay",
    "source_pin": "Then",
    "target_node": "delay_1",
    "target_pin": "Execute"
  }
}
```

### set_node_param

Set a pin's default value on an existing node.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `node_id` | string | Yes | Node ID. |
| `param_name` | string | Yes | Pin name (DSL aliases supported). |
| `value` | string | Yes | Value to set. For object pins, use the full asset path. |

```json
{
  "command": "set_node_param",
  "params": {
    "blueprint": "BP_Test",
    "node_id": "delay_1",
    "param_name": "Duration",
    "value": "5.0"
  }
}
```

**Note:** For object/class pins (PC_Object, PC_Class), the value must be a full asset path. The command uses `LoadObject` and sets `Pin->DefaultObject` instead of `Pin->DefaultValue`.

### set_variable_default

Set the default value of a Blueprint variable.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `variable_name` | string | Yes | Variable name. |
| `value` | string | Yes | Default value. |

```json
{
  "command": "set_variable_default",
  "params": {
    "blueprint": "BP_Test",
    "variable_name": "MaxHealth",
    "value": "100"
  }
}
```

---

## Level Actors

### spawn_actor_at

Spawn an actor into the editor level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `class` | string | Yes | Native class name (e.g. `"StaticMeshActor"`) or Blueprint path (e.g. `"/Game/Arcwright/Generated/BP_Pickup.BP_Pickup"`). |
| `location` | object | No | `{x, y, z}`. Default: `{0, 0, 0}`. |
| `rotation` | object | No | `{pitch, yaw, roll}`. Default: `{0, 0, 0}`. |
| `scale` | object | No | `{x, y, z}`. Default: `{1, 1, 1}`. |
| `label` | string | No | Display label in the Outliner. Auto-generated if omitted. |

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_Pickup.BP_Pickup",
    "location": {"x": 500, "y": 200, "z": 50},
    "label": "Pickup_Gold_1"
  }
}

// Response
{
  "status": "ok",
  "data": {
    "label": "Pickup_Gold_1",
    "class": "BP_Pickup_C",
    "location": {"x": 500.0, "y": 200.0, "z": 50.0}
  }
}
```

**Note:** For Blueprint classes, use the full `/Game/` path with the `_C` suffix pattern for the class parameter: `/Game/Arcwright/Generated/BP_Name.BP_Name`. Short names like `"BP_Pickup"` may resolve incorrectly via `TObjectIterator`.

### get_actors

List actors in the current level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `class_filter` | string | No | Case-insensitive substring filter on class name. |

```json
{"command": "get_actors", "params": {"class_filter": "Pickup"}}

// Response
{
  "status": "ok",
  "data": {
    "count": 3,
    "actors": [
      {"label": "Pickup_Gold_1", "class": "BP_Pickup_C", "location": {"x": 500.0, "y": 200.0, "z": 50.0}},
      {"label": "Pickup_Gold_2", "class": "BP_Pickup_C", "location": {"x": 800.0, "y": -100.0, "z": 50.0}},
      {"label": "Pickup_Health_1", "class": "BP_HealthPickup_C", "location": {"x": 0.0, "y": 300.0, "z": 50.0}}
    ]
  }
}
```

### set_actor_transform

Update an actor's transform. Only provided fields are changed.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Actor label in the Outliner. |
| `location` | object | No | `{x, y, z}`. |
| `rotation` | object | No | `{pitch, yaw, roll}`. |
| `scale` | object | No | `{x, y, z}`. |

```json
{
  "command": "set_actor_transform",
  "params": {
    "label": "Pickup_Gold_1",
    "location": {"x": 600, "y": 200, "z": 100}
  }
}
```

### delete_actor

Delete an actor from the level by label. Idempotent -- returns success even if the actor does not exist.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Actor label. |

```json
{"command": "delete_actor", "params": {"label": "Pickup_Gold_1"}}
```

### get_actor_properties

Read current property values from a placed actor.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |

```json
{"command": "get_actor_properties", "params": {"actor_label": "Pickup_Gold_1"}}
```

### set_actor_tags

Set tags on a placed actor (used for batch filtering).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `tags` | array | Yes | Array of tag strings. |

```json
{"command": "set_actor_tags", "params": {"actor_label": "Pickup_Gold_1", "tags": ["Collectible", "Gold"]}}
```

---

## Components

### add_component

Add a component to a Blueprint's Simple Construction Script (SCS).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_type` | string | Yes | Component type (see table below). |
| `component_name` | string | Yes | Name for the component. |
| `properties` | object | No | Component-specific properties. |

**Supported component types:**

| Friendly Name | UE Class | Key Properties |
|---|---|---|
| `BoxCollision` | UBoxComponent | `extent`, `generate_overlap_events`, `collision_profile` |
| `SphereCollision` | USphereComponent | `radius`, `generate_overlap_events` |
| `CapsuleCollision` | UCapsuleComponent | `radius`, `half_height` |
| `StaticMesh` | UStaticMeshComponent | `mesh` (asset path, e.g. `"/Engine/BasicShapes/Sphere.Sphere"`) |
| `PointLight` | UPointLightComponent | `intensity`, `light_color` (`{r, g, b}` in 0-1 range), `attenuation_radius` |
| `SpotLight` | USpotLightComponent | `intensity`, `light_color`, `attenuation_radius` |
| `Audio` | UAudioComponent | |
| `Arrow` | UArrowComponent | |
| `Scene` | USceneComponent | |
| `Camera` | UCameraComponent | |
| `SpringArm` | USpringArmComponent | |

All components support: `location`, `rotation`, `scale` (relative transform).

Any UActorComponent subclass name also works as a fallback via `TObjectIterator` scan.

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Pickup",
    "component_type": "SphereCollision",
    "component_name": "PickupTrigger",
    "properties": {
      "radius": 150.0,
      "generate_overlap_events": true
    }
  }
}
```

**Note:** Components added via SCS require re-spawning placed actors to take effect. Delete existing actors and re-spawn them after adding components.

### get_components

List all SCS components on a Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |

```json
{"command": "get_components", "params": {"blueprint": "BP_Pickup"}}

// Response
{
  "status": "ok",
  "data": {
    "components": [
      {"name": "PickupTrigger", "class": "SphereComponent", "parent": "DefaultSceneRoot"},
      {"name": "PickupMesh", "class": "StaticMeshComponent", "parent": "DefaultSceneRoot"}
    ]
  }
}
```

### remove_component

Remove a component from a Blueprint. Idempotent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_name` | string | Yes | Component name to remove. |

```json
{"command": "remove_component", "params": {"blueprint": "BP_Pickup", "component_name": "PickupTrigger"}}
```

### set_component_property

Set a property on a Blueprint's SCS component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_name` | string | Yes | Component name. |
| `property_name` | string | Yes | Property name (e.g. `static_mesh`, `material`, `location`, `rotation`, `scale`, or any UPROPERTY). |
| `value` | varies | Yes | Value to set. |

```json
{
  "command": "set_component_property",
  "params": {
    "blueprint": "BP_Pickup",
    "component_name": "PickupMesh",
    "property_name": "static_mesh",
    "value": "/Engine/BasicShapes/Sphere.Sphere"
  }
}
```

---

## Materials

### create_simple_material

Create a `UMaterial` with a constant color. Works with UE 5.7 Substrate rendering.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Material name (e.g. `"MAT_Gold"`). |
| `color` | object | Yes | `{r, g, b}` in 0.0-1.0 range. |
| `emissive` | number | No | Emissive intensity multiplier. Default: 0. |

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_Gold",
    "color": {"r": 1.0, "g": 0.84, "b": 0.0},
    "emissive": 0.3
  }
}

// Response
{"status": "ok", "data": {"name": "MAT_Gold", "path": "/Game/Arcwright/Materials/MAT_Gold"}}
```

**Preferred over `create_material_instance`** -- works reliably with Substrate rendering.

### create_material_instance

Create a `MaterialInstanceConstant` with scalar and vector parameters.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Material instance name. |
| `parent` | string | No | Parent material path. Default: `BasicShapeMaterial`. |
| `scalar_params` | object | No | Scalar parameter overrides. |
| `vector_params` | object | No | Vector parameter overrides. |

```json
{
  "command": "create_material_instance",
  "params": {
    "name": "MI_Shiny",
    "scalar_params": {"Roughness": 0.1, "Metallic": 0.9}
  }
}
```

**Warning:** `create_material_instance` does NOT work reliably with UE 5.7 Substrate rendering for color parameters. Use `create_simple_material` instead for colored materials.

### create_textured_material

Create a `UMaterial` with a texture sample connected to BaseColor.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Material name. |
| `texture_path` | string | Yes | Texture asset path or friendly name from the texture library (e.g. `"concrete"`, `"stone_wall"`). |
| `roughness` | number | No | Roughness value. Default: 0.5. |
| `metallic` | number | No | Metallic value. Default: 0.0. |
| `tiling` | number | No | UV tiling multiplier. Default: 1.0. |

```json
{
  "command": "create_textured_material",
  "params": {
    "name": "MAT_StoneWall",
    "texture_path": "stone_wall",
    "roughness": 0.8,
    "tiling": 2.0
  }
}
```

### apply_material

Apply a material to a Blueprint's SCS mesh component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_name` | string | Yes | Mesh component name. |
| `material_path` | string | Yes | Full material asset path (e.g. `"/Game/Arcwright/Materials/MAT_Gold"`). |

```json
{
  "command": "apply_material",
  "params": {
    "blueprint": "BP_Pickup",
    "component_name": "PickupMesh",
    "material_path": "/Game/Arcwright/Materials/MAT_Gold"
  }
}
```

**Important:** SCS materials may not persist on spawned actor instances. For reliable results on placed actors, use `set_actor_material` instead.

### set_actor_material

Apply a material directly to a placed actor's mesh component. This is the reliable method for materials on spawned actors.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label in the Outliner. |
| `material_path` | string | Yes | Material asset path. |
| `component_name` | string | No | Specific component name. Uses first mesh component if omitted. |
| `slot_index` | number | No | Material slot index. Default: 0. |

```json
{
  "command": "set_actor_material",
  "params": {
    "actor_label": "Pickup_Gold_1",
    "material_path": "/Game/Arcwright/Materials/MAT_Gold"
  }
}
```

---

## Widgets

### create_widget_blueprint

Create a Widget Blueprint (UUserWidget).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Widget name (e.g. `"WBP_GameHUD"`). |
| `parent_class` | string | No | Parent class. Default: `UserWidget`. |

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_GameHUD"}}
```

### add_widget_child

Add a widget to a Widget Blueprint's hierarchy.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |
| `widget_type` | string | Yes | Widget type: `TextBlock`, `ProgressBar`, `Image`, `Button`, `VerticalBox`, `HorizontalBox`, `CanvasPanel`, `Overlay`, `SizeBox`. |
| `widget_name` | string | Yes | Name for the widget. |
| `parent_name` | string | No | Parent widget name. Adds to root if omitted. |

```json
{
  "command": "add_widget_child",
  "params": {
    "widget_blueprint": "WBP_GameHUD",
    "widget_type": "CanvasPanel",
    "widget_name": "RootPanel"
  }
}
```

### set_widget_property

Set properties on a widget.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |
| `widget_name` | string | Yes | Widget name. |
| `property_name` | string | Yes | Property name (see below). |
| `value` | varies | Yes | Property value. |

**Supported properties:**

| Property | Applies To | Value Type |
|---|---|---|
| `text` | TextBlock | string |
| `font_size` | TextBlock | number |
| `color` | TextBlock | `{r, g, b, a}` (0-1) |
| `justification` | TextBlock | `"Left"`, `"Center"`, `"Right"` |
| `percent` | ProgressBar | number (0.0 - 1.0) |
| `fill_color` | ProgressBar | `{r, g, b, a}` |
| `position` | Any (in CanvasPanel) | `{x, y}` |
| `size` | Any (in CanvasPanel) | `{x, y}` |
| `anchors` | Any (in CanvasPanel) | `{min_x, min_y, max_x, max_y}` |
| `visibility` | Any | `"Visible"`, `"Hidden"`, `"Collapsed"` |

```json
{
  "command": "set_widget_property",
  "params": {
    "widget_blueprint": "WBP_GameHUD",
    "widget_name": "ScoreText",
    "property_name": "text",
    "value": "Score: 0"
  }
}
```

### get_widget_tree

List all widgets with hierarchy, types, and properties.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |

```json
{"command": "get_widget_tree", "params": {"widget_blueprint": "WBP_GameHUD"}}
```

### remove_widget

Remove a widget from a Widget Blueprint. Idempotent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |
| `widget_name` | string | Yes | Widget name to remove. |

```json
{"command": "remove_widget", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText"}}
```

---

## Behavior Trees

### create_behavior_tree

Create a BehaviorTree + Blackboard from IR JSON.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ir_json` | string | Yes | JSON string containing the BT IR. |

The IR JSON describes composites, tasks, decorators, services, and blackboard keys. Assets are saved to `/Game/Arcwright/BehaviorTrees/`.

**Supported composites:** Selector, Sequence, SimpleParallel
**Supported tasks:** MoveTo, Wait, RotateToFaceBBEntry, WaitBlackboardTime, FinishWithResult, PlaySound, PlayAnimation, RunBehavior, GameplayTask, PushPawnAction, StopBehaviorTree, SetTagCooldown, MakeNoise
**Supported decorators:** BlackboardBased, Cooldown, Loop, TimeLimit, ForceSuccess, IsAtLocation, ConeCheck, IsBBEntryOfClass, CompareBBEntries, TagCooldown, CheckGameplayTag, KeepInCone
**Supported services:** DefaultFocus, RunEQS, SetDefaultFocus, BlackboardBase, GameplayFocus, GameplayTask
**Blackboard key types:** Bool, Int, Float, String, Name, Vector, Rotator, Object, Class, Enum

### get_behavior_tree_info

Query an existing BehaviorTree's structure and Blackboard keys.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | BehaviorTree asset name (e.g. `"BT_EnemyPatrol"`). |

```json
{"command": "get_behavior_tree_info", "params": {"name": "BT_EnemyPatrol"}}
```

### setup_ai_for_pawn

One-command AI setup: creates an AIController Blueprint with RunBehaviorTree wired to BeginPlay, sets AIControllerClass and AutoPossessAI on the pawn.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `pawn_name` | string | Yes | Name of the Pawn/Character Blueprint to wire AI to. |
| `behavior_tree` | string | Yes | BehaviorTree asset name. |
| `controller_name` | string | No | Custom AIController name. Auto-generated if omitted. |

```json
{
  "command": "setup_ai_for_pawn",
  "params": {
    "pawn_name": "BP_Enemy",
    "behavior_tree": "BT_EnemyPatrol",
    "controller_name": "BP_EnemyAIController"
  }
}
```

---

## Data Tables

### create_data_table

Create a UUserDefinedStruct + UDataTable from IR JSON.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ir_json` | string | Yes | JSON string containing the DT IR. |

**Supported column types:** String, Float, Int, Boolean, Name, Text, Vector, Rotator, Transform, Color

Assets are saved to `/Game/Arcwright/DataTables/`.

### get_data_table_info

Query a DataTable's structure, columns, types, and row data.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | DataTable asset name (e.g. `"DT_Weapons"`). |

```json
{"command": "get_data_table_info", "params": {"name": "DT_Weapons"}}
```

---

## Splines

### create_spline_actor

Create a Blueprint with a SplineComponent and initial points.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint name. |
| `initial_points` | array | Yes | Array of `{x, y, z}` points (minimum 2). |
| `closed` | bool | No | Whether the spline forms a closed loop. Default: false. |

```json
{
  "command": "create_spline_actor",
  "params": {
    "name": "BP_PatrolPath",
    "initial_points": [
      {"x": 0, "y": 0, "z": 0},
      {"x": 500, "y": 0, "z": 0},
      {"x": 500, "y": 500, "z": 0},
      {"x": 0, "y": 500, "z": 0}
    ],
    "closed": true
  }
}
```

### add_spline_point

Add a point to an existing Blueprint's SplineComponent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `point` | object | Yes | `{x, y, z}` point. |
| `index` | number | No | Insertion index. -1 appends to end (default). |

```json
{"command": "add_spline_point", "params": {"blueprint": "BP_PatrolPath", "point": {"x": 250, "y": 250, "z": 100}}}
```

### get_spline_info

Get spline data: points, length, and closed status.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |

```json
{"command": "get_spline_info", "params": {"blueprint": "BP_PatrolPath"}}

// Response
{
  "status": "ok",
  "data": {
    "point_count": 4,
    "spline_length": 2000.0,
    "closed": true,
    "points": [
      {"x": 0.0, "y": 0.0, "z": 0.0},
      {"x": 500.0, "y": 0.0, "z": 0.0},
      {"x": 500.0, "y": 500.0, "z": 0.0},
      {"x": 0.0, "y": 500.0, "z": 0.0}
    ]
  }
}
```

---

## Post-Process

### add_post_process_volume

Spawn a PostProcessVolume into the level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | No | Actor label. |
| `location` | object | No | `{x, y, z}`. |
| `infinite_extent` | bool | No | If true, affects the entire level. Default: true. |
| `settings` | object | No | Initial post-process settings (see `set_post_process_settings`). |

```json
{
  "command": "add_post_process_volume",
  "params": {
    "label": "PPV_Main",
    "infinite_extent": true,
    "settings": {"bloom_intensity": 1.5, "auto_exposure_min": 1.0, "auto_exposure_max": 1.0}
  }
}
```

### set_post_process_settings

Update visual settings on a PostProcessVolume.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | PostProcessVolume actor label. |
| `settings` | object | Yes | Settings to apply. |

**Supported settings:**

| Setting | Type | Description |
|---|---|---|
| `bloom_intensity` | number | Bloom strength. |
| `bloom_threshold` | number | Bloom brightness threshold. |
| `auto_exposure_min` | number | Minimum auto-exposure EV100. |
| `auto_exposure_max` | number | Maximum auto-exposure EV100. |
| `ambient_occlusion_intensity` | number | AO strength. |
| `vignette_intensity` | number | Vignette strength. |
| `color_saturation` | object | `{r, g, b, a}` saturation multiplier. |
| `color_contrast` | object | `{r, g, b, a}` contrast multiplier. |
| `color_gamma` | object | `{r, g, b, a}` gamma multiplier. |
| `color_gain` | object | `{r, g, b, a}` gain multiplier. |
| `dof_focal_distance` | number | Depth of field focal distance. |
| `dof_fstop` | number | DoF aperture. |
| `motion_blur_amount` | number | Motion blur intensity. |

```json
{
  "command": "set_post_process_settings",
  "params": {
    "label": "PPV_Main",
    "settings": {
      "bloom_intensity": 2.0,
      "vignette_intensity": 0.4,
      "color_saturation": {"r": 1.2, "g": 1.0, "b": 0.8, "a": 1.0}
    }
  }
}
```

---

## Physics

### add_physics_constraint

Spawn a physics constraint between two actors.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Constraint actor label. |
| `constraint_type` | string | Yes | `"Fixed"`, `"Hinge"`, `"Prismatic"`, or `"BallSocket"`. |
| `actor1` | string | Yes | First constrained actor label. |
| `actor2` | string | Yes | Second constrained actor label. |
| `location` | object | No | `{x, y, z}` constraint location. |

```json
{
  "command": "add_physics_constraint",
  "params": {
    "label": "DoorHinge",
    "constraint_type": "Hinge",
    "actor1": "DoorFrame",
    "actor2": "Door",
    "location": {"x": 100, "y": 0, "z": 150}
  }
}
```

### break_constraint

Disable a physics constraint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Constraint actor label. |

```json
{"command": "break_constraint", "params": {"label": "DoorHinge"}}
```

---

## Movement

### set_movement_defaults

Set movement properties on a Blueprint's movement component. Works with both `CharacterMovementComponent` and `FloatingPawnMovement`.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `settings` | object | Yes | Movement settings. |

**Common settings:**

| Setting | Type | Description |
|---|---|---|
| `max_walk_speed` | number | Maximum walk speed (CharacterMovement). |
| `max_speed` | number | Maximum speed (FloatingPawnMovement). |
| `jump_z_velocity` | number | Jump impulse. |
| `air_control` | number | Air control factor (0-1). |
| `gravity_scale` | number | Gravity multiplier. |
| `braking_deceleration` | number | Deceleration when not accelerating. |

```json
{
  "command": "set_movement_defaults",
  "params": {
    "blueprint": "BP_Enemy",
    "settings": {"max_speed": 400.0, "deceleration": 1000.0}
  }
}
```

---

## Sequencer

### create_sequence

Create a ULevelSequence asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Sequence name. |
| `duration` | number | No | Duration in seconds. Default: 5.0. |

```json
{"command": "create_sequence", "params": {"name": "SEQ_Intro", "duration": 10.0}}
```

### add_sequence_track

Bind an actor and add a track to a sequence.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sequence_name` | string | Yes | Sequence name. |
| `actor_label` | string | Yes | Actor label to bind. |
| `track_type` | string | Yes | `"Transform"`, `"Visibility"`, or `"Float"`. |

```json
{
  "command": "add_sequence_track",
  "params": {
    "sequence_name": "SEQ_Intro",
    "actor_label": "Camera_1",
    "track_type": "Transform"
  }
}
```

### add_keyframe

Add a keyframe to a sequence track.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sequence_name` | string | Yes | Sequence name. |
| `actor_label` | string | Yes | Actor label. |
| `track_type` | string | Yes | Track type. |
| `time` | number | Yes | Time in seconds. |
| `value` | varies | Yes | Keyframe value (transform object, bool, or float). |

```json
{
  "command": "add_keyframe",
  "params": {
    "sequence_name": "SEQ_Intro",
    "actor_label": "Camera_1",
    "track_type": "Transform",
    "time": 0.0,
    "value": {
      "location": {"x": 0, "y": 0, "z": 500},
      "rotation": {"pitch": -45, "yaw": 0, "roll": 0}
    }
  }
}
```

### get_sequence_info

Query a sequence's duration, tracks, and bound actors.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Sequence name. |

```json
{"command": "get_sequence_info", "params": {"name": "SEQ_Intro"}}
```

### play_sequence

Play a sequence in editor preview.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Sequence name. |

**Note:** Has the same PIE limitation as `play_in_editor` -- may not function reliably in UE 5.7.

---

## Landscape and Foliage

### get_landscape_info

Query landscape existence and properties. Safe to call even if no landscape exists.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "get_landscape_info", "params": {}}
```

### set_landscape_material

Apply a material to the landscape.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `material_path` | string | Yes | Material asset path. |

```json
{"command": "set_landscape_material", "params": {"material_path": "/Game/Materials/MAT_Grass"}}
```

### create_foliage_type

Create a UFoliageType asset for procedural foliage placement.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Foliage type name. |
| `mesh` | string | No | Static mesh asset path. |
| `density` | number | No | Placement density. |
| `scale_min` | number | No | Minimum random scale. |
| `scale_max` | number | No | Maximum random scale. |

```json
{
  "command": "create_foliage_type",
  "params": {
    "name": "FT_Trees",
    "mesh": "/Game/Meshes/SM_Tree",
    "scale_min": 0.8,
    "scale_max": 1.2
  }
}
```

### paint_foliage

Procedurally place foliage instances in a circular area with ground tracing.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `foliage_type` | string | Yes | Foliage type name. |
| `center` | object | Yes | `{x, y, z}` center of placement area. |
| `radius` | number | Yes | Placement radius. |
| `count` | number | Yes | Number of instances to place. |

```json
{
  "command": "paint_foliage",
  "params": {
    "foliage_type": "FT_Trees",
    "center": {"x": 0, "y": 0, "z": 0},
    "radius": 5000,
    "count": 50
  }
}
```

### get_foliage_info

List foliage types and instance counts.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "get_foliage_info", "params": {}}
```

---

## Asset Import

### import_static_mesh

Import a .fbx or .obj file as a UStaticMesh.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | Yes | Absolute path to the source file. |
| `asset_name` | string | Yes | Name for the imported asset (e.g. `"SM_HealthCrystal"`). |
| `destination` | string | No | UE content path. Default: `/Game/Arcwright/Meshes/`. |

```json
{
  "command": "import_static_mesh",
  "params": {
    "file_path": "C:/exports/crystal.fbx",
    "asset_name": "SM_HealthCrystal"
  }
}
```

### import_texture

Import a .png, .jpg, or .tga file as a UTexture2D.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | Yes | Absolute path to the image file. |
| `asset_name` | string | Yes | Name for the imported asset (e.g. `"T_CrystalDiffuse"`). |
| `destination` | string | No | UE content path. Default: `/Game/Arcwright/Textures/`. |

```json
{
  "command": "import_texture",
  "params": {
    "file_path": "C:/exports/crystal_diffuse.png",
    "asset_name": "T_CrystalDiffuse"
  }
}
```

### import_sound

Import a .wav, .ogg, or .mp3 file as a USoundWave.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | Yes | Absolute path to the audio file. |
| `asset_name` | string | Yes | Name for the imported asset (e.g. `"SFX_PickupChime"`). |
| `destination` | string | No | UE content path. Default: `/Game/Arcwright/Sounds/`. |

```json
{
  "command": "import_sound",
  "params": {
    "file_path": "C:/exports/pickup_chime.wav",
    "asset_name": "SFX_PickupChime"
  }
}
```

**Note:** Re-importing over existing assets can crash or hang. If you need to re-import, delete the existing asset first with `delete_blueprint`, then import again.

---

## Scene Setup

### setup_scene_lighting

Create standard scene lighting: DirectionalLight + SkyLight + optional SkyAtmosphere and ExponentialHeightFog.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `preset` | string | No | `"indoor_dark"`, `"indoor_bright"`, `"outdoor_day"`, `"outdoor_night"`. Default: `"indoor_dark"`. |
| `sun_intensity` | number | No | Override DirectionalLight intensity. |
| `sky_intensity` | number | No | Override SkyLight intensity. |
| `sun_rotation` | object | No | Override `{pitch, yaw, roll}` for sun direction. |

```json
{"command": "setup_scene_lighting", "params": {"preset": "outdoor_day"}}
```

**Important:** Always add scene lighting as the first step when building a level from scratch. Levels created purely through `spawn_actor_at` have no ambient lighting by default.

### set_game_mode

Set the level's GameMode override in World Settings.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `game_mode` | string | Yes | GameMode Blueprint name (e.g. `"BP_FirstPersonGameMode"`). |

```json
{"command": "set_game_mode", "params": {"game_mode": "BP_FirstPersonGameMode"}}
```

### set_class_defaults

Set CDO (Class Default Object) properties on a Blueprint. Supports generic UPROPERTY reflection.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `properties` | object | Yes | Property name/value pairs. |

```json
{
  "command": "set_class_defaults",
  "params": {
    "blueprint": "BP_GameMode",
    "properties": {
      "default_pawn_class": "BP_FPSCharacter",
      "player_controller_class": "BP_FPSController"
    }
  }
}
```

### create_nav_mesh_bounds

Create a NavMeshBoundsVolume for AI pathfinding.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `location` | object | Yes | `{x, y, z}` center. |
| `extents` | object | Yes | `{x, y, z}` half-extents. |

```json
{
  "command": "create_nav_mesh_bounds",
  "params": {
    "location": {"x": 0, "y": 0, "z": 0},
    "extents": {"x": 5000, "y": 5000, "z": 500}
  }
}
```

---

## Query and Discovery

### find_blueprints

Search Blueprint assets by name, parent class, variable, or component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name_filter` | string | No | Substring filter on Blueprint name. |
| `parent_class` | string | No | Filter by parent class. |
| `has_variable` | string | No | Filter by variable name. |
| `has_component` | string | No | Filter by component type. |
| `path` | string | No | Content path to search. |

```json
{"command": "find_blueprints", "params": {"has_variable": "Health"}}

// Response
{
  "status": "ok",
  "data": {
    "count": 2,
    "blueprints": [
      {"name": "BP_Enemy", "path": "/Game/Arcwright/Generated/BP_Enemy", "variables": ["Health", "Speed"], "components": ["Mesh", "Collision"]},
      {"name": "BP_Player", "path": "/Game/Arcwright/Generated/BP_Player", "variables": ["Health", "Score"], "components": ["Camera"]}
    ]
  }
}
```

### find_actors

Search level actors by name, class, tag, component, material, or proximity.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name_filter` | string | No | Substring filter on actor label. |
| `class_filter` | string | No | Class name filter. |
| `tag` | string | No | Filter by actor tag. |
| `has_component` | string | No | Filter by component type. |
| `material_name` | string | No | Filter by material name. |
| `radius` | number | No | Proximity search radius. |
| `center` | object | No | `{x, y, z}` center for proximity search. |

```json
{"command": "find_actors", "params": {"tag": "Enemy"}}
```

### find_assets

Search the asset registry by type and name.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `type` | string | No | Asset type: `Blueprint`, `Material`, `Texture2D`, `StaticMesh`, `SoundWave`, `BehaviorTree`. |
| `name_filter` | string | No | Substring filter. |
| `path` | string | No | Content path to search. |
| `max_results` | number | No | Maximum results. Default: 100. |

```json
{"command": "find_assets", "params": {"type": "Material", "name_filter": "Gold"}}
```

### list_available_materials

List all material assets currently available.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "list_available_materials", "params": {}}
```

### list_available_blueprints

List all Blueprint assets currently available.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "list_available_blueprints", "params": {}}
```

### get_last_error

Get the last error message and the command that caused it.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "get_last_error", "params": {}}

// Response
{"status": "ok", "data": {"last_error": "Blueprint 'BP_Missing' not found", "last_error_command": "get_blueprint_info"}}
```

---

## Batch Operations

All batch commands are fault-tolerant: individual operation failures do not abort the entire batch. The response includes `succeeded`, `failed`, and `errors` arrays.

### batch_set_variable

Set variable defaults on multiple Blueprints.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{blueprint, variable_name, default_value}`. |

```json
{
  "command": "batch_set_variable",
  "params": {
    "operations": [
      {"blueprint": "BP_Enemy", "variable_name": "Health", "default_value": "50"},
      {"blueprint": "BP_Boss", "variable_name": "Health", "default_value": "200"}
    ]
  }
}
```

### batch_add_component

Add components to multiple Blueprints.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{blueprint, component_type, component_name, properties}`. |

```json
{
  "command": "batch_add_component",
  "params": {
    "operations": [
      {"blueprint": "BP_Coin", "component_type": "SphereCollision", "component_name": "Trigger", "properties": {"radius": 80}},
      {"blueprint": "BP_Gem", "component_type": "SphereCollision", "component_name": "Trigger", "properties": {"radius": 80}}
    ]
  }
}
```

### batch_apply_material

Apply materials to actors or Blueprint templates in bulk.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{actor_label OR blueprint, material_path, slot}`. |

```json
{
  "command": "batch_apply_material",
  "params": {
    "operations": [
      {"actor_label": "Wall_1", "material_path": "/Game/Arcwright/Materials/MAT_Concrete"},
      {"actor_label": "Wall_2", "material_path": "/Game/Arcwright/Materials/MAT_Concrete"},
      {"actor_label": "Floor_1", "material_path": "/Game/Arcwright/Materials/MAT_Stone"}
    ]
  }
}
```

### batch_set_property

Set actor properties (location, rotation, scale, visibility, tag) in bulk.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{actor_label, property, value, relative}`. |

```json
{
  "command": "batch_set_property",
  "params": {
    "operations": [
      {"actor_label": "Light_1", "property": "visibility", "value": false},
      {"actor_label": "Enemy_1", "property": "location", "value": {"x": 100, "y": 200, "z": 0}}
    ]
  }
}
```

### batch_delete_actors

Delete actors by labels, class filter, or tag. Idempotent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `labels` | array | No | Array of actor labels to delete. |
| `class_filter` | string | No | Delete all actors matching this class. |
| `tag` | string | No | Delete all actors with this tag. |

```json
{"command": "batch_delete_actors", "params": {"tag": "TempObject"}}
```

### batch_replace_material

Replace all occurrences of one material across the entire level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `old_material` | string | Yes | Material path to replace. |
| `new_material` | string | Yes | New material path. |

```json
{
  "command": "batch_replace_material",
  "params": {
    "old_material": "/Game/Arcwright/Materials/MAT_Gray",
    "new_material": "/Game/Arcwright/Materials/MAT_Concrete"
  }
}

// Response
{"status": "ok", "data": {"replacements": 14, "affected_actors": ["Wall_1", "Wall_2", "Floor_1"]}}
```

---

## In-Place Modification

### modify_blueprint

Compound Blueprint edit: add/remove variables and set CDO defaults in one command.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |
| `add_variables` | array | No | Array of `{name, type, default}` to add. |
| `remove_variables` | array | No | Array of variable names to remove. |
| `set_class_defaults` | object | No | CDO property/value pairs. |

```json
{
  "command": "modify_blueprint",
  "params": {
    "name": "BP_Enemy",
    "add_variables": [
      {"name": "AttackDamage", "type": "Float", "default": "25.0"},
      {"name": "IsAggressive", "type": "Boolean", "default": "true"}
    ],
    "set_class_defaults": {"MaxHealth": "100"}
  }
}
```

### rename_asset

Rename a Blueprint or other asset. Creates a redirector at the old path.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `old_name` | string | Yes | Current asset name. |
| `new_name` | string | Yes | New asset name. |

```json
{"command": "rename_asset", "params": {"old_name": "BP_OldName", "new_name": "BP_NewName"}}
```

### reparent_blueprint

Change a Blueprint's parent class.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |
| `new_parent` | string | Yes | Native class name (e.g. `"Pawn"`, `"Character"`) or Blueprint path. |

```json
{"command": "reparent_blueprint", "params": {"name": "BP_Enemy", "new_parent": "Pawn"}}
```

---

## Properties and Configuration

### set_collision_preset

Set collision channel and response on an actor or component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `target` | string | Yes | Actor label or blueprint::component. |
| `preset` | string | Yes | Collision preset name (e.g. `"OverlapAll"`, `"BlockAll"`, `"NoCollision"`). |

```json
{"command": "set_collision_preset", "params": {"target": "BP_Pickup::PickupTrigger", "preset": "OverlapAll"}}
```

### set_collision_shape

Resize a collision component on a placed actor.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `shape_type` | string | Yes | `"Box"`, `"Sphere"`, or `"Capsule"`. |
| `extents` | object | No | `{x, y, z}` half-extents (box). |
| `radius` | number | No | Radius (sphere/capsule). |
| `half_height` | number | No | Half-height (capsule). |

```json
{"command": "set_collision_shape", "params": {"actor_label": "TriggerZone", "shape_type": "Box", "extents": {"x": 200, "y": 200, "z": 100}}}
```

### set_camera_properties

Configure camera or spring arm properties.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `fov` | number | No | Field of view in degrees. |
| `arm_length` | number | No | Spring arm length. |
| `pitch_min` | number | No | Minimum pitch constraint. |
| `pitch_max` | number | No | Maximum pitch constraint. |

```json
{"command": "set_camera_properties", "params": {"actor_label": "PlayerCamera", "fov": 90, "arm_length": 300}}
```

### set_audio_properties

Configure audio component properties.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `target` | string | Yes | Actor label or blueprint::component. |
| `attenuation_radius` | number | No | Sound attenuation radius. |
| `inner_radius` | number | No | Inner attenuation radius. |
| `volume` | number | No | Volume multiplier. |

```json
{"command": "set_audio_properties", "params": {"target": "Ambient_Sound_1", "attenuation_radius": 2000, "volume": 0.7}}
```

---

## PIE and Debugging

### play_in_editor

Request a Play In Editor (PIE) session.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

**Known limitation:** In UE 5.7, `RequestPlaySession()` queues a PIE request but the engine tick loop does not process it from external TCP commands. The command returns success but PIE may not actually start. Use the Play button in the editor manually.

### stop_play

Stop the current PIE session.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
{"command": "stop_play", "params": {}}
```

### get_output_log

Read the last N lines from the UE output log file.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `last_n_lines` | number | No | Number of lines to return. Default: 50. |
| `filter` | string | No | Substring filter for log lines. |

```json
{"command": "get_output_log", "params": {"last_n_lines": 20, "filter": "Arcwright"}}
```
