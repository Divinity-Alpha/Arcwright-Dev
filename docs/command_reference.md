# Arcwright TCP Command Reference

Complete reference for all 150 TCP commands available through the Arcwright UE5 plugin.

**Protocol:** Newline-delimited JSON on `localhost:13377`.

```
Request:  {"command": "<name>", "params": {<params>}}\n
Response: {"status": "ok", "data": {<result>}}\n
Error:    {"status": "error", "message": "<description>"}\n
```

**Python client:**
```python
from scripts.mcp_client.blueprint_client import ArcwrightClient
with ArcwrightClient() as client:
    result = client.health_check()
```

---

## Table of Contents

1. [System](#1-system)
2. [Blueprint CRUD](#2-blueprint-crud)
3. [Blueprint Nodes and Wiring](#3-blueprint-nodes-and-wiring)
4. [Components](#4-components)
5. [Materials](#5-materials)
6. [Actors and Level](#6-actors-and-level)
7. [Spawn Patterns](#7-spawn-patterns)
8. [Batch Operations](#8-batch-operations)
9. [Search and Query](#9-search-and-query)
10. [Widget UI](#10-widget-ui)
11. [Behavior Trees](#11-behavior-trees)
12. [Data Tables](#12-data-tables)
13. [Animation](#13-animation)
14. [Sequencer](#14-sequencer)
15. [Splines](#15-splines)
16. [Post-Process](#16-post-process)
17. [Physics](#17-physics)
18. [Landscape and Foliage](#18-landscape-and-foliage)
19. [Lighting and Scene](#19-lighting-and-scene)
20. [Asset Import](#20-asset-import)
21. [Collision and Input](#21-collision-and-input)
22. [Audio and Navigation](#22-audio-and-navigation)
23. [Niagara](#23-niagara)
24. [Level Management](#24-level-management)
25. [SaveGame](#25-savegame)
26. [Movement](#26-movement)
27. [Class Defaults](#27-class-defaults)
28. [PIE](#28-pie)

---

## 1. System

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

---

### save_all

Save all dirty packages (equivalent to Ctrl+Shift+S).

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "save_all", "params": {}}

// Response
{"status": "ok", "data": {"saved": true, "external_actors_saved": 12}}
```

**Notes:**
- Skips untitled maps to avoid blocking "Save As" dialogs.
- Explicitly saves World Partition external actor packages via TObjectIterator scan.

---

### save_level

Save the current level to disk.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | No | Level name. Uses current level if omitted. |

```json
// Request
{"command": "save_level", "params": {}}

// Response
{"status": "ok", "data": {"saved": true, "level_name": "ArenaLevel"}}
```

**Notes:**
- Uses SavePackage directly with explicit path for untitled maps.
- Calls SaveDirtyPackages after to flush World Partition external actor files.

---

### get_level_info

Get the current level name, path, and actor count.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "get_level_info", "params": {}}

// Response
{"status": "ok", "data": {"level_name": "ArenaLevel", "level_path": "/Game/Maps/ArenaLevel", "actor_count": 47}}
```

---

### get_output_log

Read the last N lines from the UE output log file.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `last_n_lines` | int | No | Number of lines to return. Default: 50. |
| `category` | string | No | Filter by log category (e.g. `"LogBlueprintUserMessages"`). |
| `text_filter` | string | No | Filter by text substring. |

```json
// Request
{"command": "get_output_log", "params": {"last_n_lines": 20, "category": "LogArcwright"}}

// Response
{"status": "ok", "data": {"lines": ["[2026.03.14] LogArcwright: Server started on port 13377"], "total": 15420, "filtered": 87, "returned": 20}}
```

---

### quit_editor

Clean editor shutdown: stops PIE, saves all dirty packages, then calls RequestExit.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `skip_save` | bool | No | If true, skip saving before exit. Default: false. |

```json
// Request
{"command": "quit_editor", "params": {}}

// Response
{"status": "ok", "data": {"saved": true, "message": "Editor shutting down"}}
```

**Notes:**
- Response is sent before the editor actually exits (~500ms delay for TCP flush).
- Prefer this over `taskkill` to avoid autosave restore prompts on next launch.

---

### get_last_error

Get the last error message and command that caused it.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "get_last_error", "params": {}}

// Response
{"status": "ok", "data": {"last_error_message": "Blueprint not found: BP_Missing", "last_error_command": "get_blueprint_info"}}
```

---

### get_world_settings

Query world configuration: gravity, kill Z, game mode, time dilation.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "get_world_settings", "params": {}}

// Response
{"status": "ok", "data": {"global_gravity_z": -980.0, "kill_z": -10000.0, "world_gravity_z": -980.0, "default_game_mode": "BP_FPSGameMode", "time_dilation": 1.0}}
```

---

### set_world_settings

Modify world physics and pacing settings.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `gravity` | float | No | Global gravity Z value (negative = downward). |
| `kill_z` | float | No | Z height at which actors are destroyed. |
| `time_dilation` | float | No | Time dilation factor (0.0001 to 20.0). |

```json
// Request
{"command": "set_world_settings", "params": {"gravity": -490.0, "time_dilation": 0.5}}

// Response
{"status": "ok", "data": {"gravity": -490.0, "time_dilation": 0.5}}
```

---

### set_viewport_camera

Move the editor viewport camera to a specific location and/or rotation.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `location` | object | No | `{x, y, z}` world location. |
| `rotation` | object | No | `{pitch, yaw, roll}` rotation in degrees. |

```json
// Request
{"command": "set_viewport_camera", "params": {"location": {"x": 0, "y": 0, "z": 500}, "rotation": {"pitch": -45, "yaw": 0, "roll": 0}}}

// Response
{"status": "ok", "data": {"location": {"x": 0, "y": 0, "z": 500}, "rotation": {"pitch": -45, "yaw": 0, "roll": 0}}}
```

**Notes:**
- Both `location` and `rotation` are optional; provide either or both.
- Useful for positioning the editor camera before taking screenshots.

---

### take_screenshot

Capture the editor viewport to a PNG file.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `filename` | string | No | Output filename (without path). Saved to project's `Saved/Screenshots/`. Auto-generated if omitted. |

```json
// Request
{"command": "take_screenshot", "params": {"filename": "level_overview.png"}}

// Response
{"status": "ok", "data": {"filepath": "C:/Junk/ArcwrightTest/Saved/Screenshots/level_overview.png", "width": 1920, "height": 1080}}
```

**Notes:**
- Uses `FScreenshotRequest::RequestScreenshot()` internally. Direct `ReadPixels` returns stale/blank content from TCP context (Lesson #39).
- Combine with `set_viewport_camera` for positioned screenshots.

---

### get_viewport_info

Get the current editor viewport camera position and settings.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "get_viewport_info", "params": {}}

// Response
{"status": "ok", "data": {"location": {"x": 100, "y": 200, "z": 300}, "rotation": {"pitch": -30, "yaw": 45, "roll": 0}, "fov": 90.0}}
```

---

## 2. Blueprint CRUD

### create_blueprint_from_dsl

Create a Blueprint from an IR JSON string (parsed DSL).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ir_json` | string | Yes | JSON string of the Blueprint IR. |
| `name` | string | No | Override Blueprint name from the IR. |

```json
// Request
{"command": "create_blueprint_from_dsl", "params": {"ir_json": "{\"metadata\":{\"name\":\"BP_Test\",\"parent_class\":\"Actor\"},\"variables\":[],\"nodes\":[],\"connections\":[]}"}}

// Response
{"status": "ok", "data": {"blueprint_name": "BP_Test", "nodes_created": 0, "connections_wired": 0, "compiled": true, "asset_path": "/Game/Arcwright/Generated/BP_Test"}}
```

---

### import_from_ir

Import a `.blueprint.json` IR file from disk into UE5.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | Yes | Absolute path to the IR file. |

```json
// Request
{"command": "import_from_ir", "params": {"path": "C:/Arcwright/test_ir/T1_01_HelloWorld.blueprint.json"}}

// Response
{"status": "ok", "data": {"blueprint_name": "BP_HelloWorld", "nodes_created": 3, "connections_wired": 2, "compiled": true}}
```

**Notes:**
- Calls the same ParseIR + CreateBlueprint code path as the Tools menu import (Rule 17).
- Deletes existing Blueprint with the same name before creation.

---

### get_blueprint_info

Query an existing Blueprint's structure: nodes, connections, variables.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name (e.g. `"BP_HelloWorld"`). |

```json
// Request
{"command": "get_blueprint_info", "params": {"name": "BP_HelloWorld"}}

// Response
{"status": "ok", "data": {"name": "BP_HelloWorld", "compiled": true, "node_count": 3, "connection_count": 2, "nodes": [...], "variables": [...]}}
```

---

### get_blueprint_details

Get detailed Blueprint info including variables, components, events, and node counts.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |

```json
// Request
{"command": "get_blueprint_details", "params": {"name": "BP_Enemy"}}

// Response
{"status": "ok", "data": {"name": "BP_Enemy", "parent_class": "Pawn", "variables": [{"name": "Health", "type": "Float", "default": "100.0"}], "components": [{"name": "Mesh", "class": "StaticMeshComponent"}], "node_count": 12, "compiled": true}}
```

---

### compile_blueprint

Recompile a Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |

```json
// Request
{"command": "compile_blueprint", "params": {"name": "BP_HelloWorld"}}

// Response
{"status": "ok", "data": {"name": "BP_HelloWorld", "compiled": true}}
```

---

### delete_blueprint

Delete a Blueprint asset using ForceDeleteObjects.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |

```json
// Request
{"command": "delete_blueprint", "params": {"name": "BP_HelloWorld"}}

// Response
{"status": "ok", "data": {"name": "BP_HelloWorld", "deleted": true}}
```

**Notes:**
- Always delete before re-importing to avoid crashes (Rule 8).

---

### duplicate_blueprint

Duplicate an existing Blueprint to a new name.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `source_name` | string | Yes | Source Blueprint asset name. |
| `new_name` | string | Yes | Name for the duplicate. |

```json
// Request
{"command": "duplicate_blueprint", "params": {"source_name": "BP_Enemy", "new_name": "BP_BossEnemy"}}

// Response
{"status": "ok", "data": {"source_name": "BP_Enemy", "new_name": "BP_BossEnemy", "asset_path": "/Game/Arcwright/Generated/BP_BossEnemy", "compiled": true}}
```

---

### modify_blueprint

Modify a Blueprint in-place: add/remove variables, set CDO defaults.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |
| `add_variables` | array | No | Variables to add: `[{"name": "Score", "type": "Int", "default": "0"}]`. |
| `remove_variables` | array | No | Variable names to remove: `["OldVar"]`. |
| `set_class_defaults` | object | No | CDO properties to set: `{"AutoPossessAI": "PlacedInWorldOrSpawned"}`. |

```json
// Request
{"command": "modify_blueprint", "params": {"name": "BP_Enemy", "add_variables": [{"name": "Damage", "type": "Float", "default": "10.0"}], "set_class_defaults": {"AutoPossessAI": "PlacedInWorldOrSpawned"}}}

// Response
{"status": "ok", "data": {"name": "BP_Enemy", "variables_added": 1, "variables_removed": 0, "defaults_set": 1, "compiled": true}}
```

---

### rename_asset

Rename a Blueprint or other asset. Creates a redirector at the old path.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `old_name` | string | Yes | Current asset name. |
| `new_name` | string | Yes | New asset name. |

```json
// Request
{"command": "rename_asset", "params": {"old_name": "BP_Coin", "new_name": "BP_GoldCoin"}}

// Response
{"status": "ok", "data": {"old_name": "BP_Coin", "new_name": "BP_GoldCoin", "renamed": true}}
```

---

### reparent_blueprint

Change a Blueprint's parent class. Calls RefreshAllNodes and recompiles.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint asset name. |
| `new_parent` | string | Yes | Native class name (e.g. `"Character"`) or Blueprint path. |

```json
// Request
{"command": "reparent_blueprint", "params": {"name": "BP_Enemy", "new_parent": "Character"}}

// Response
{"status": "ok", "data": {"name": "BP_Enemy", "new_parent": "Character", "compiled": true}}
```

---

## 3. Blueprint Nodes and Wiring

### add_node

Add a single node to a Blueprint's EventGraph.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `node_type` | string | Yes | DSL node type (e.g. `"Delay"`, `"Branch"`, `"PrintString"`) or full UE function path. |
| `node_id` | string | No | Custom ID for the node. Auto-generated if empty. |
| `params` | object | No | Pin default values: `{"Duration": "2.0"}`. |
| `pos_x` | float | No | Graph X position. |
| `pos_y` | float | No | Graph Y position. |

```json
// Request
{"command": "add_node", "params": {"blueprint": "BP_Test", "node_type": "Delay", "params": {"Duration": "3.0"}}}

// Response
{"status": "ok", "data": {"node_id": "abc123-...", "node_type": "Delay", "class": "UK2Node_CallFunction", "pins": [...], "compiled": true}}
```

**Notes:**
- For UE functions not in the friendly name map, use the full path: `/Script/AIModule.AIController:MoveToLocation`.
- Cannot create VariableGet/Set nodes -- use `import_from_ir` with proper IR for those.

---

### remove_node

Remove a node and all its connections from a Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `node_id` | string | Yes | Node GUID or index (e.g. `"node_3"` from get_blueprint_info). |

```json
// Request
{"command": "remove_node", "params": {"blueprint": "BP_Test", "node_id": "node_3"}}

// Response
{"status": "ok", "data": {"node_id": "node_3", "deleted": true, "compiled": true}}
```

---

### add_connection

Wire two pins together. Uses TryCreateConnection which auto-inserts type conversion nodes.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `source_node` | string | Yes | Source node GUID or index. |
| `source_pin` | string | Yes | Source pin name (DSL aliases supported). |
| `target_node` | string | Yes | Target node GUID or index. |
| `target_pin` | string | Yes | Target pin name (DSL aliases supported). |

```json
// Request
{"command": "add_connection", "params": {"blueprint": "BP_Test", "source_node": "node_0", "source_pin": "Then", "target_node": "node_1", "target_pin": "Execute"}}

// Response
{"status": "ok", "data": {"connected": true, "source": {"node": "node_0", "pin": "Then"}, "target": {"node": "node_1", "pin": "Execute"}, "compiled": true}}
```

**Notes:**
- DSL pin aliases are resolved automatically (e.g. `"C"` maps to `"Condition"`, `"I"` maps to `"InString"`).
- Auto-inserts Float-to-String, Int-to-Float, etc. conversion nodes via TryCreateConnection.

---

### remove_connection

Disconnect two pins.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `source_node` | string | Yes | Source node GUID or index. |
| `source_pin` | string | Yes | Source pin name. |
| `target_node` | string | Yes | Target node GUID or index. |
| `target_pin` | string | Yes | Target pin name. |

```json
// Request
{"command": "remove_connection", "params": {"blueprint": "BP_Test", "source_node": "node_0", "source_pin": "Then", "target_node": "node_1", "target_pin": "Execute"}}

// Response
{"status": "ok", "data": {"disconnected": true, "compiled": true}}
```

---

### set_node_param

Set a pin's default value on a node.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `node_id` | string | Yes | Node GUID or index. |
| `pin_name` | string | Yes | Pin name (DSL aliases supported). |
| `value` | string | Yes | Value to set as string. |

```json
// Request
{"command": "set_node_param", "params": {"blueprint": "BP_Test", "node_id": "node_2", "pin_name": "Duration", "value": "5.0"}}

// Response
{"status": "ok", "data": {"node_id": "node_2", "pin_name": "Duration", "value": "5.0", "compiled": true}}
```

**Notes:**
- For object/class pins (PC_Object, PC_Class), uses LoadObject and sets Pin->DefaultObject. Use full path with `_C` suffix for Blueprint classes: `/Game/Arcwright/Generated/BP_Enemy.BP_Enemy_C`.

---

### set_variable_default

Set a Blueprint variable's default value.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `variable_name` | string | Yes | Variable name. |
| `default_value` | string | Yes | Default value as string. |

```json
// Request
{"command": "set_variable_default", "params": {"blueprint": "BP_Enemy", "variable_name": "Health", "default_value": "200.0"}}

// Response
{"status": "ok", "data": {"variable_name": "Health", "default_value": "200.0", "type": "Float", "compiled": true}}
```

---

## 4. Components

### add_component

Add a component to a Blueprint's SimpleConstructionScript (SCS).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_type` | string | Yes | One of: `BoxCollision`, `SphereCollision`, `CapsuleCollision`, `StaticMesh`, `PointLight`, `SpotLight`, `Audio`, `Arrow`, `Scene`, `Camera`, `SpringArm`. |
| `component_name` | string | Yes | Name for the new component. |
| `parent` | string | No | Parent component name. Attaches to root if omitted. |
| `properties` | object | No | Component-specific properties (see below). |

**Properties by type:**
- **BoxCollision:** `extent` ({x,y,z}), `generate_overlap_events` (bool), `collision_profile` (string)
- **SphereCollision:** `radius` (float), `generate_overlap_events` (bool)
- **CapsuleCollision:** `radius` (float), `half_height` (float)
- **StaticMesh:** `mesh` (string, asset path e.g. `"/Engine/BasicShapes/Sphere.Sphere"`)
- **PointLight/SpotLight:** `intensity` (float), `light_color` ({r,g,b} 0-1 range), `attenuation_radius` (float)
- **Camera:** `field_of_view` (float), `aspect_ratio` (float)
- **SpringArm:** `target_arm_length` (float), `socket_offset` ({x,y,z}), `use_pawn_control_rotation` (bool)
- **All types:** `location` ({x,y,z}), `rotation` ({pitch,yaw,roll}), `scale` ({x,y,z})

```json
// Request
{"command": "add_component", "params": {"blueprint": "BP_Pickup", "component_type": "SphereCollision", "component_name": "OverlapSphere", "properties": {"radius": 100.0, "generate_overlap_events": true}}}

// Response
{"status": "ok", "data": {"component_name": "OverlapSphere", "component_class": "USphereComponent", "parent": "DefaultSceneRoot", "compiled": true}}
```

**Notes:**
- Already-placed actors do NOT pick up new components. You must delete and re-spawn the actor.

---

### get_components

List all SCS components on a Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |

```json
// Request
{"command": "get_components", "params": {"blueprint": "BP_Pickup"}}

// Response
{"status": "ok", "data": {"count": 2, "components": [{"name": "DefaultSceneRoot", "class": "USceneComponent", "parent": ""}, {"name": "OverlapSphere", "class": "USphereComponent", "parent": "DefaultSceneRoot"}]}}
```

---

### remove_component

Remove a component from a Blueprint. Idempotent (missing component returns success).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_name` | string | Yes | Component to remove. |

```json
// Request
{"command": "remove_component", "params": {"blueprint": "BP_Pickup", "component_name": "OverlapSphere"}}

// Response
{"status": "ok", "data": {"component_name": "OverlapSphere", "deleted": true, "compiled": true}}
```

---

### set_component_property

Set a property on a Blueprint's SCS component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_name` | string | Yes | Component name in the SCS. |
| `property_name` | string | Yes | Property to set (see below). |
| `value` | varies | Yes | Property value. |

**Supported properties:**
- **Any:** `relative_location` ({x,y,z}), `relative_rotation` ({pitch,yaw,roll}), `relative_scale` ({x,y,z}), `visibility` (bool)
- **StaticMesh:** `static_mesh` (asset path string), `material` (material asset path)
- **Box:** `box_extent` ({x,y,z}), `generate_overlap_events` (bool), `collision_profile_name` (string)
- **Sphere:** `sphere_radius` (float), `generate_overlap_events` (bool)
- **Light:** `intensity` (float), `light_color` ({r,g,b} 0-1), `attenuation_radius` (float)
- **Collision:** `collision_enabled` (string), `collision_profile_name` (string)
- **Generic UPROPERTY:** `bUsePawnControlRotation` (bool), `FieldOfView` (float), or any property discoverable via FindPropertyByName.

```json
// Request
{"command": "set_component_property", "params": {"blueprint": "BP_Torch", "component_name": "Light", "property_name": "intensity", "value": 5000.0}}

// Response
{"status": "ok", "data": {"component_name": "Light", "property_name": "intensity", "compiled": true}}
```

---

## 5. Materials

### create_material_instance

Create a MaterialInstanceConstant asset with scalar and vector parameter overrides.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name (e.g. `"MI_Gold"`). |
| `parent` | string | Yes | Parent material path (e.g. `"/Engine/BasicShapes/BasicShapeMaterial"`). |
| `scalar_params` | object | No | Scalar parameter overrides: `{"Roughness": 0.3}`. |
| `vector_params` | object | No | Vector parameter overrides: `{"BaseColor": {"r": 1, "g": 0.8, "b": 0}}`. |

```json
// Request
{"command": "create_material_instance", "params": {"name": "MI_Gold", "parent": "/Engine/BasicShapes/BasicShapeMaterial", "vector_params": {"BaseColor": {"r": 1, "g": 0.84, "b": 0, "a": 1}}}}

// Response
{"status": "ok", "data": {"name": "MI_Gold", "asset_path": "/Game/Arcwright/Materials/MI_Gold", "parent": "/Engine/BasicShapes/BasicShapeMaterial"}}
```

**Notes:**
- Does NOT work with UE 5.7 Substrate rendering. Use `create_simple_material` instead.
- Crashes on partially-loaded existing assets. Delete the asset first if recreating.

---

### create_simple_material

Create a UMaterial with a solid color. Works with Substrate rendering.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name (e.g. `"MAT_Red"`). |
| `color` | object | Yes | Color as `{r, g, b}` with values 0.0-1.0. |
| `emissive_strength` | float | No | Emissive glow multiplier. 0 = no glow. Default: 0. |

```json
// Request
{"command": "create_simple_material", "params": {"name": "MAT_Red", "color": {"r": 1, "g": 0, "b": 0}, "emissive_strength": 2.0}}

// Response
{"status": "ok", "data": {"name": "MAT_Red", "asset_path": "/Game/Arcwright/Materials/MAT_Red", "color": {"r": 1, "g": 0, "b": 0}, "emissive_strength": 2.0}}
```

**Notes:**
- Creates a full UMaterial with UMaterialExpressionConstant3Vector nodes. This is the recommended material creation method for UE 5.7.

---

### create_textured_material

Create a UMaterial with a texture sample node connected to BaseColor.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name (e.g. `"MAT_StoneWall"`). |
| `texture_path` | string | Yes | Full UE asset path or texture library friendly name (e.g. `"stone_wall"`). |
| `roughness` | float | No | Roughness value 0-1. Default: 0.5. |
| `metallic` | float | No | Metallic value 0-1. Default: 0.0. |
| `tiling` | float | No | UV tiling multiplier. Default: 1.0. |

```json
// Request
{"command": "create_textured_material", "params": {"name": "MAT_StoneWall", "texture_path": "stone_wall", "roughness": 0.8, "tiling": 2.0}}

// Response
{"status": "ok", "data": {"name": "MAT_StoneWall", "asset_path": "/Game/Arcwright/Materials/MAT_StoneWall", "texture": "/Game/Arcwright/Textures/T_StoneWall"}}
```

---

### apply_material

Apply a material to a Blueprint's SCS mesh/primitive component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint asset name. |
| `component_name` | string | Yes | Component name in the SCS. |
| `material_path` | string | Yes | Material asset path. |
| `slot_index` | int | No | Material slot index. Default: 0. |

```json
// Request
{"command": "apply_material", "params": {"blueprint": "BP_Pickup", "component_name": "Mesh", "material_path": "/Game/Arcwright/Materials/MAT_Gold"}}

// Response
{"status": "ok", "data": {"blueprint": "BP_Pickup", "component_name": "Mesh", "material_path": "/Game/Arcwright/Materials/MAT_Gold", "slot_index": 0, "compiled": true}}
```

**Notes:**
- SCS OverrideMaterials may not persist on spawned actors. Use `set_actor_material` on placed actors instead.

---

### set_actor_material

Apply a material to a placed actor's mesh component. Works on registered actor components.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label in Outliner. |
| `material_path` | string | Yes | Material asset path. |
| `component_name` | string | No | Specific component name. Uses first mesh if omitted. |
| `slot_index` | int | No | Material slot index. Default: 0. |

```json
// Request
{"command": "set_actor_material", "params": {"actor_label": "Pickup_01", "material_path": "/Game/Arcwright/Materials/MAT_Gold"}}

// Response
{"status": "ok", "data": {"actor_label": "Pickup_01", "material_path": "/Game/Arcwright/Materials/MAT_Gold", "applied": true}}
```

**Notes:**
- This is the reliable way to apply materials to placed actors. Must be called after each `spawn_actor_at`. Must be re-applied after re-spawn.

---

## 6. Actors and Level

### spawn_actor_at

Spawn an actor in the editor level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `class` | string | Yes | Native class name (e.g. `"StaticMeshActor"`) or Blueprint path (e.g. `"/Game/Arcwright/Generated/BP_Enemy"`). |
| `location` | object | No | `{x, y, z}`. Default: origin. |
| `rotation` | object | No | `{pitch, yaw, roll}`. Default: zero. |
| `scale` | object | No | `{x, y, z}`. Default: `{1,1,1}`. |
| `label` | string | No | Display label in Outliner. Auto-generated if omitted. |

```json
// Request
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Enemy", "location": {"x": 500, "y": 0, "z": 50}, "label": "Enemy_01"}}

// Response
{"status": "ok", "data": {"label": "Enemy_01", "class": "BP_Enemy_C", "location": {"x": 500, "y": 0, "z": 50}}}
```

**Notes:**
- Use full `/Game/` path for Blueprint classes. Short names may resolve incorrectly.
- For `StaticMeshActor`, use `set_component_property` to set the mesh and `set_actor_material` for materials.

---

### get_actors

List actors in the editor level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `class_filter` | string | No | Case-insensitive substring to filter by class name. |

```json
// Request
{"command": "get_actors", "params": {"class_filter": "BP_Enemy"}}

// Response
{"status": "ok", "data": {"count": 3, "actors": [{"label": "Enemy_01", "class": "BP_Enemy_C", "location": {"x": 500, "y": 0, "z": 50}}, ...]}}
```

---

### set_actor_transform

Update an actor's transform. Only provided fields are changed.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Actor label in Outliner. |
| `location` | object | No | `{x, y, z}`. |
| `rotation` | object | No | `{pitch, yaw, roll}`. |
| `scale` | object | No | `{x, y, z}`. |

```json
// Request
{"command": "set_actor_transform", "params": {"label": "Enemy_01", "location": {"x": 1000, "y": 200, "z": 50}}}

// Response
{"status": "ok", "data": {"label": "Enemy_01", "location": {"x": 1000, "y": 200, "z": 50}}}
```

---

### delete_actor

Remove an actor from the level by label. Idempotent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Actor label in Outliner. |

```json
// Request
{"command": "delete_actor", "params": {"label": "Enemy_01"}}

// Response
{"status": "ok", "data": {"label": "Enemy_01", "deleted": true}}
```

---

### copy_actor

Duplicate a placed actor with optional offset and new label.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor to duplicate. |
| `new_label` | string | No | Label for the copy. Auto-generated if omitted. |
| `offset` | object | No | Position offset `{x, y, z}` from original. |

```json
// Request
{"command": "copy_actor", "params": {"actor_label": "Enemy_01", "new_label": "Enemy_02", "offset": {"x": 300, "y": 0, "z": 0}}}

// Response
{"status": "ok", "data": {"original": "Enemy_01", "copy": "Enemy_02", "location": {"x": 800, "y": 0, "z": 50}}}
```

---

### set_actor_tags

Set tags on a level actor (replaces existing tags).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `tags` | array | Yes | Array of tag strings: `["enemy", "wave1"]`. |

```json
// Request
{"command": "set_actor_tags", "params": {"actor_label": "Enemy_01", "tags": ["enemy", "wave1"]}}

// Response
{"status": "ok", "data": {"actor_label": "Enemy_01", "tags": ["enemy", "wave1"]}}
```

---

### set_actor_visibility

Show or hide an actor in the game.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `visible` | bool | Yes | True to show, false to hide. |
| `propagate` | bool | No | Propagate to children. Default: true. |

```json
// Request
{"command": "set_actor_visibility", "params": {"actor_label": "SecretDoor", "visible": false}}

// Response
{"status": "ok", "data": {"actor_label": "SecretDoor", "visible": false}}
```

---

### set_actor_mobility

Set actor mobility: Static, Stationary, or Movable.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `mobility` | string | Yes | One of `"Static"`, `"Stationary"`, `"Movable"`. |

```json
// Request
{"command": "set_actor_mobility", "params": {"actor_label": "Platform_01", "mobility": "Movable"}}

// Response
{"status": "ok", "data": {"actor_label": "Platform_01", "mobility": "Movable"}}
```

---

### set_actor_scale

Set the scale of a placed actor (uniform or per-axis).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `scale` | number or object | Yes | Uniform float (e.g. `2.0`) or per-axis `{x, y, z}`. |
| `relative` | bool | No | If true, multiply current scale. Default: false. |

```json
// Request
{"command": "set_actor_scale", "params": {"actor_label": "Floor", "scale": {"x": 100, "y": 100, "z": 1}}}

// Response
{"status": "ok", "data": {"actor_label": "Floor", "scale": {"x": 100, "y": 100, "z": 1}}}
```

---

### attach_actor_to

Attach an actor to a parent actor (parent-child relationship).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor to attach. |
| `parent_label` | string | Yes | Parent actor. |
| `socket_name` | string | No | Socket to attach to. |
| `rule` | string | No | One of `"KeepWorld"`, `"KeepRelative"`, `"SnapToTarget"`. Default: `"KeepWorld"`. |

```json
// Request
{"command": "attach_actor_to", "params": {"actor_label": "Weapon", "parent_label": "Character", "socket_name": "hand_r", "rule": "SnapToTarget"}}

// Response
{"status": "ok", "data": {"actor_label": "Weapon", "parent_label": "Character", "attached": true}}
```

---

### detach_actor

Detach an actor from its parent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor to detach. |
| `rule` | string | No | One of `"KeepWorld"`, `"KeepRelative"`. Default: `"KeepWorld"`. |

```json
// Request
{"command": "detach_actor", "params": {"actor_label": "Weapon", "rule": "KeepWorld"}}

// Response
{"status": "ok", "data": {"actor_label": "Weapon", "detached": true}}
```

---

### get_actor_properties

Get detailed actor info: transform, tags, components, visibility, mobility.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |

```json
// Request
{"command": "get_actor_properties", "params": {"actor_label": "Enemy_01"}}

// Response
{"status": "ok", "data": {"label": "Enemy_01", "class": "BP_Enemy_C", "location": {"x": 500, "y": 0, "z": 50}, "rotation": {"pitch": 0, "yaw": 0, "roll": 0}, "scale": {"x": 1, "y": 1, "z": 1}, "tags": ["enemy"], "components": [...], "visible": true, "mobility": "Movable"}}
```

---

### get_actor_class

Get class info and Blueprint ancestry of a placed actor.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |

```json
// Request
{"command": "get_actor_class", "params": {"actor_label": "Enemy_01"}}

// Response
{"status": "ok", "data": {"class_name": "BP_Enemy_C", "class_path": "/Game/Arcwright/Generated/BP_Enemy", "is_blueprint": true, "parent_classes": ["Pawn", "Actor", "Object"]}}
```

---

### get_actor_bounds

Get an actor's bounding box origin and extent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |

```json
// Request
{"command": "get_actor_bounds", "params": {"actor_label": "Wall_01"}}

// Response
{"status": "ok", "data": {"actor_label": "Wall_01", "origin": {"x": 0, "y": 0, "z": 50}, "box_extent": {"x": 50, "y": 200, "z": 100}}}
```

---

### set_actor_enabled

Enable or disable an actor (hidden + no collision + no tick).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `enabled` | bool | Yes | True to enable, false to disable. |

```json
// Request
{"command": "set_actor_enabled", "params": {"actor_label": "SecretArea", "enabled": false}}

// Response
{"status": "ok", "data": {"actor_label": "SecretArea", "enabled": false}}
```

---

### set_actor_tick

Enable or disable actor tick and set tick interval.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `enabled` | bool | Yes | Enable/disable tick. |
| `interval` | float | No | Tick interval in seconds (0 = every frame). |

```json
// Request
{"command": "set_actor_tick", "params": {"actor_label": "Spinner", "enabled": true, "interval": 0.1}}

// Response
{"status": "ok", "data": {"actor_label": "Spinner", "tick_enabled": true, "tick_interval": 0.1}}
```

---

### set_actor_lifespan

Set actor auto-destroy lifespan.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `lifespan` | float | Yes | Seconds until auto-destroy. 0 = infinite (no auto-destroy). |

```json
// Request
{"command": "set_actor_lifespan", "params": {"actor_label": "Projectile_01", "lifespan": 5.0}}

// Response
{"status": "ok", "data": {"actor_label": "Projectile_01", "lifespan": 5.0}}
```

---

## 7. Spawn Patterns

### spawn_actor_grid

Spawn actors in a rows x cols grid pattern.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `class` | string | Yes | Actor class or Blueprint path. |
| `rows` | int | No | Number of rows. Default: 3. |
| `cols` | int | No | Number of columns. Default: 3. |
| `spacing_x` | float | No | X spacing between actors. Default: 200. |
| `spacing_y` | float | No | Y spacing between actors. Default: 200. |
| `origin` | object | No | `{x, y, z}` grid origin. Default: world origin. |
| `center` | bool | No | Center grid on origin. Default: true. |
| `label_prefix` | string | No | Prefix for actor labels. |
| `rotation` | object | No | `{pitch, yaw, roll}` for all actors. |
| `scale` | object | No | `{x, y, z}` for all actors. |

```json
// Request
{"command": "spawn_actor_grid", "params": {"class": "/Game/Arcwright/Generated/BP_Pillar", "rows": 4, "cols": 4, "spacing_x": 500, "spacing_y": 500, "label_prefix": "Pillar"}}

// Response
{"status": "ok", "data": {"spawned": 16, "actors": [{"label": "Pillar_0_0", "location": {...}}, ...]}}
```

---

### spawn_actor_circle

Spawn actors in a circle pattern.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `class` | string | Yes | Actor class or Blueprint path. |
| `count` | int | No | Number of actors. Default: 8. |
| `radius` | float | No | Circle radius. Default: 500. |
| `center` | object | No | `{x, y, z}` circle center. Default: world origin. |
| `face_center` | bool | No | Rotate actors to face center. Default: false. |
| `start_angle` | float | No | Starting angle in degrees. Default: 0. |
| `label_prefix` | string | No | Prefix for actor labels. |
| `scale` | object | No | `{x, y, z}` for all actors. |

```json
// Request
{"command": "spawn_actor_circle", "params": {"class": "/Game/Arcwright/Generated/BP_Torch", "count": 6, "radius": 800, "face_center": true, "label_prefix": "Torch"}}

// Response
{"status": "ok", "data": {"spawned": 6, "actors": [...]}}
```

---

### spawn_actor_line

Spawn actors evenly distributed along a line from start to end.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `class` | string | Yes | Actor class or Blueprint path. |
| `count` | int | Yes | Number of actors. |
| `start` | object | Yes | `{x, y, z}` line start point. |
| `end` | object | Yes | `{x, y, z}` line end point. |
| `face_direction` | bool | No | Rotate actors to face along the line. Default: false. |
| `label_prefix` | string | No | Prefix for actor labels. |
| `scale` | object | No | `{x, y, z}` for all actors. |

```json
// Request
{"command": "spawn_actor_line", "params": {"class": "/Game/Arcwright/Generated/BP_Coin", "count": 10, "start": {"x": 0, "y": 0, "z": 50}, "end": {"x": 2000, "y": 0, "z": 50}, "label_prefix": "Coin"}}

// Response
{"status": "ok", "data": {"spawned": 10, "actors": [...]}}
```

---

## 8. Batch Operations

### batch_set_variable

Set variable defaults on multiple Blueprints. Fault-tolerant: individual failures do not abort the batch.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{"blueprint": str, "variable_name": str, "default_value": str}`. |

```json
// Request
{"command": "batch_set_variable", "params": {"operations": [{"blueprint": "BP_Enemy", "variable_name": "Health", "default_value": "200"}, {"blueprint": "BP_Boss", "variable_name": "Health", "default_value": "500"}]}}

// Response
{"status": "ok", "data": {"succeeded": 2, "failed": 0, "errors": []}}
```

---

### batch_add_component

Add components to multiple Blueprints.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{"blueprint": str, "component_type": str, "component_name": str, "properties": {}}`. |

```json
// Request
{"command": "batch_add_component", "params": {"operations": [{"blueprint": "BP_Pickup", "component_type": "SphereCollision", "component_name": "Overlap", "properties": {"radius": 100}}]}}

// Response
{"status": "ok", "data": {"succeeded": 1, "failed": 0, "errors": []}}
```

---

### batch_apply_material

Apply materials to multiple actors or Blueprint templates.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{"actor_label": str, "material_path": str, "slot": int}` or `{"blueprint": str, "material_path": str}`. |

```json
// Request
{"command": "batch_apply_material", "params": {"operations": [{"actor_label": "Wall_01", "material_path": "/Game/Arcwright/Materials/MAT_Stone"}, {"actor_label": "Wall_02", "material_path": "/Game/Arcwright/Materials/MAT_Stone"}]}}

// Response
{"status": "ok", "data": {"succeeded": 2, "failed": 0, "errors": []}}
```

---

### batch_set_property

Set properties on multiple actors (location, rotation, scale, visibility, tag).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operations` | array | Yes | Array of `{"actor_label": str, "property": str, "value": ..., "relative": bool}`. |

```json
// Request
{"command": "batch_set_property", "params": {"operations": [{"actor_label": "Enemy_01", "property": "location", "value": {"x": 100, "y": 0, "z": 50}}, {"actor_label": "Enemy_02", "property": "tag", "value": "wave2"}]}}

// Response
{"status": "ok", "data": {"succeeded": 2, "failed": 0, "errors": []}}
```

---

### batch_delete_actors

Delete actors by label list, class filter, or tag. Idempotent (missing actors count as success).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `labels` | array | No | Specific actor labels to delete. |
| `class_filter` | string | No | Delete all actors of this class. |
| `tag` | string | No | Delete all actors with this tag. |

```json
// Request
{"command": "batch_delete_actors", "params": {"tag": "wave1"}}

// Response
{"status": "ok", "data": {"deleted": 5, "not_found": 0}}
```

---

### batch_replace_material

Replace all occurrences of one material with another across all level actors.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `old_material` | string | Yes | Material path to replace. |
| `new_material` | string | Yes | Replacement material path. |

```json
// Request
{"command": "batch_replace_material", "params": {"old_material": "/Game/Arcwright/Materials/MAT_Old", "new_material": "/Game/Arcwright/Materials/MAT_New"}}

// Response
{"status": "ok", "data": {"replacements": 12, "affected_actors": ["Wall_01", "Wall_02", "Floor"]}}
```

---

### batch_scale_actors

Scale multiple actors by filter.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `scale` | object | Yes | `{x, y, z}` scale values. |
| `labels` | array | No | Specific actor labels. |
| `name_filter` | string | No | Actor name substring filter. |
| `class_filter` | string | No | Class name filter. |
| `tag` | string | No | Tag filter. |
| `mode` | string | No | `"multiply"` (default) or `"set"`. |

```json
// Request
{"command": "batch_scale_actors", "params": {"scale": {"x": 2, "y": 2, "z": 2}, "tag": "pickup", "mode": "multiply"}}

// Response
{"status": "ok", "data": {"affected": 8, "actors": [...]}}
```

---

### batch_move_actors

Move multiple actors by filter.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `offset` | object | No | `{x, y, z}` relative offset (for `mode: "relative"`). |
| `location` | object | No | `{x, y, z}` absolute position (for `mode: "set"`). |
| `labels` | array | No | Specific actor labels. |
| `name_filter` | string | No | Actor name substring filter. |
| `class_filter` | string | No | Class name filter. |
| `tag` | string | No | Tag filter. |
| `mode` | string | No | `"relative"` (default) or `"set"`. |

```json
// Request
{"command": "batch_move_actors", "params": {"offset": {"x": 0, "y": 0, "z": 100}, "tag": "floating", "mode": "relative"}}

// Response
{"status": "ok", "data": {"affected": 4, "actors": [...]}}
```

---

## 9. Search and Query

### find_blueprints

Search Blueprint assets by name, parent class, variables, or components.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name_filter` | string | No | Substring match on Blueprint name. |
| `parent_class` | string | No | Filter by parent class. |
| `has_variable` | string | No | Filter by variable name. |
| `has_component` | string | No | Filter by component type. |
| `path` | string | No | Asset path to search in. |

```json
// Request
{"command": "find_blueprints", "params": {"name_filter": "Enemy", "has_variable": "Health"}}

// Response
{"status": "ok", "data": {"count": 2, "blueprints": [{"name": "BP_Enemy", "path": "/Game/Arcwright/Generated/BP_Enemy", "parent_class": "Pawn", "variables": ["Health", "Speed"], "components": ["Mesh", "Collision"]}]}}
```

---

### find_actors

Search level actors by name, class, tag, component, material, or proximity.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name_filter` | string | No | Actor name substring. |
| `class_filter` | string | No | Class name filter. |
| `tag` | string | No | Filter by tag. |
| `has_component` | string | No | Filter by component type. |
| `material_name` | string | No | Filter by material name. |
| `radius` | float | No | Proximity search radius. Requires `center`. |
| `center` | object | No | `{x, y, z}` proximity search center. |

```json
// Request
{"command": "find_actors", "params": {"tag": "enemy", "radius": 1000, "center": {"x": 0, "y": 0, "z": 0}}}

// Response
{"status": "ok", "data": {"count": 3, "actors": [{"label": "Enemy_01", "class": "BP_Enemy_C", "location": {"x": 500, "y": 0, "z": 50}, "tags": ["enemy"], "components": [...]}]}}
```

---

### find_assets

Search the asset registry by type and name.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `type` | string | No | Asset type: `Blueprint`, `Material`, `Texture2D`, `StaticMesh`, `SoundWave`, `BehaviorTree`. |
| `name_filter` | string | No | Name substring filter. |
| `path` | string | No | Asset path to search in. |
| `max_results` | int | No | Maximum results. Default: 100. |

```json
// Request
{"command": "find_assets", "params": {"type": "Material", "name_filter": "MAT_"}}

// Response
{"status": "ok", "data": {"count": 5, "assets": [{"name": "MAT_Gold", "path": "/Game/Arcwright/Materials/MAT_Gold", "type": "MaterialInstanceConstant"}]}}
```

---

### list_available_materials

List all material assets in the project.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name_filter` | string | No | Name substring filter. |
| `max_results` | int | No | Maximum results. Default: 50. |

```json
// Request
{"command": "list_available_materials", "params": {"max_results": 10}}

// Response
{"status": "ok", "data": {"count": 10, "materials": [{"name": "MAT_Gold", "path": "/Game/Arcwright/Materials/MAT_Gold"}]}}
```

---

### list_available_blueprints

List all Blueprint assets in the project.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name_filter` | string | No | Name substring filter. |
| `max_results` | int | No | Maximum results. Default: 50. |

```json
// Request
{"command": "list_available_blueprints", "params": {"name_filter": "BP_"}}

// Response
{"status": "ok", "data": {"count": 12, "blueprints": [{"name": "BP_Enemy", "path": "/Game/Arcwright/Generated/BP_Enemy", "parent_class": "Pawn"}]}}
```

---

### list_project_assets

Search project assets by type, path, or name filter.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `asset_type` | string | No | Asset type to search. 8 supported types. |
| `path` | string | No | Path to search in. |
| `name_filter` | string | No | Name substring filter. |
| `max_results` | int | No | Maximum results. Default: 100. |

```json
// Request
{"command": "list_project_assets", "params": {"asset_type": "StaticMesh", "max_results": 20}}

// Response
{"status": "ok", "data": {"count": 8, "assets": [{"name": "SM_HealthCrystal", "path": "/Game/Arcwright/Meshes/SM_HealthCrystal"}]}}
```

---

## 10. Widget UI

### create_widget_blueprint

Create a Widget Blueprint (UUserWidget subclass).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name (e.g. `"WBP_HUD"`). Saved to `/Game/UI/`. |
| `parent_class` | string | No | Parent class. Default: UUserWidget. |

```json
// Request
{"command": "create_widget_blueprint", "params": {"name": "WBP_GameHUD"}}

// Response
{"status": "ok", "data": {"name": "WBP_GameHUD", "asset_path": "/Game/UI/WBP_GameHUD", "parent_class": "UserWidget", "compiled": true}}
```

---

### add_widget_child

Add a widget to a Widget Blueprint's hierarchy.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |
| `widget_type` | string | Yes | One of: `TextBlock`, `ProgressBar`, `Image`, `Button`, `VerticalBox`, `HorizontalBox`, `CanvasPanel`, `Overlay`, `SizeBox`. |
| `widget_name` | string | Yes | Unique name for the new widget. |
| `parent_widget` | string | No | Parent widget name. Added to root if omitted. |

```json
// Request
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_GameHUD", "widget_type": "TextBlock", "widget_name": "ScoreText", "parent_widget": "RootCanvas"}}

// Response
{"status": "ok", "data": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "widget_type": "TextBlock", "parent": "RootCanvas", "compiled": true}}
```

---

### set_widget_property

Set a property on a widget in a Widget Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |
| `widget_name` | string | Yes | Widget name. |
| `property` | string | Yes | Property name (see below). |
| `value` | varies | Yes | Property value. |

**Supported properties:**
- **TextBlock:** `text` (string), `font_size` (int), `color` ({r,g,b,a} 0-1), `justification` (string)
- **ProgressBar:** `percent` (float 0-1), `fill_color` ({r,g,b,a}), `background_color` ({r,g,b,a})
- **Image:** `color_and_opacity` ({r,g,b,a}), `brush_color` ({r,g,b,a})
- **Button:** `background_color` ({r,g,b,a})
- **Any widget:** `visibility` (string), `is_enabled` (bool), `render_opacity` (float 0-1)
- **Layout:** `padding` (float or {left,top,right,bottom}), `horizontal_alignment` (string), `vertical_alignment` (string)
- **CanvasPanel slot:** `position` ({x,y}), `size` ({x,y}), `anchors` ({min_x,min_y,max_x,max_y}), `alignment` ({x,y})

```json
// Request
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property": "text", "value": "Score: 0"}}

// Response
{"status": "ok", "data": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property": "text", "compiled": true}}
```

---

### get_widget_tree

List all widgets in a Widget Blueprint with hierarchy and properties.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |

```json
// Request
{"command": "get_widget_tree", "params": {"widget_blueprint": "WBP_GameHUD"}}

// Response
{"status": "ok", "data": {"widget_blueprint": "WBP_GameHUD", "total_widgets": 5, "has_root": true, "tree": {"name": "RootCanvas", "type": "CanvasPanel", "children": [...]}}}
```

---

### remove_widget

Remove a widget from a Widget Blueprint. Idempotent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `widget_blueprint` | string | Yes | Widget Blueprint name. |
| `widget_name` | string | Yes | Widget to remove. |

```json
// Request
{"command": "remove_widget", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText"}}

// Response
{"status": "ok", "data": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "deleted": true, "compiled": true}}
```

---

## 11. Behavior Trees

### create_behavior_tree

Create a BehaviorTree and Blackboard from IR JSON.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ir_json` | string | Yes | JSON string of the BT IR (from bt_parser). |

```json
// Request
{"command": "create_behavior_tree", "params": {"ir_json": "{\"metadata\":{\"tree_name\":\"BT_Patrol\",\"blackboard_name\":\"BB_Patrol\"},\"blackboard_keys\":[{\"name\":\"TargetActor\",\"type\":\"Object\"}],\"tree\":{\"type\":\"Selector\",\"name\":\"Root\",\"children\":[...]}}"}}

// Response
{"status": "ok", "data": {"tree_name": "BT_Patrol", "tree_asset_path": "/Game/Arcwright/BehaviorTrees/BT_Patrol", "blackboard_asset_path": "/Game/Arcwright/BehaviorTrees/BB_Patrol", "composite_count": 2, "task_count": 3, "decorator_count": 1, "service_count": 0}}
```

**Notes:**
- Supports: Selector, Sequence, SimpleParallel composites; 13 task types; 12 decorator types; 6 service types.
- Assets saved to `/Game/Arcwright/BehaviorTrees/`.
- SelfActor key is auto-added to all Blackboards.

---

### get_behavior_tree_info

Query an existing BehaviorTree asset's structure and Blackboard keys.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | BehaviorTree asset name (e.g. `"BT_Patrol"`). |

```json
// Request
{"command": "get_behavior_tree_info", "params": {"name": "BT_Patrol"}}

// Response
{"status": "ok", "data": {"name": "BT_Patrol", "blackboard": "BB_Patrol", "composite_count": 2, "task_count": 3, "keys": [{"name": "TargetActor", "type": "Object"}, {"name": "SelfActor", "type": "Object"}]}}
```

---

### setup_ai_for_pawn

One-command AI setup: creates AIController Blueprint with RunBehaviorTree on BeginPlay, sets AIControllerClass and AutoPossessAI on the pawn.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `pawn_name` | string | Yes | Pawn Blueprint name to attach AI to. |
| `behavior_tree` | string | Yes | BehaviorTree asset name to run. |
| `controller_name` | string | No | Custom controller name. Default: `BP_<pawn_name>_AIController`. |

```json
// Request
{"command": "setup_ai_for_pawn", "params": {"pawn_name": "BP_Enemy", "behavior_tree": "BT_Patrol"}}

// Response
{"status": "ok", "data": {"pawn": "BP_Enemy", "controller": "BP_Enemy_AIController", "behavior_tree": "BT_Patrol", "controller_created": true, "auto_possess": "PlacedInWorldOrSpawned"}}
```

**Notes:**
- Replaces a 5-step manual AI wiring process.
- If a controller with the same name already exists, it is reused (not recreated).

---

### set_blackboard_key_default

Set a default value on a Blackboard key. Note: UE Blackboard keys do not have asset-level defaults for most types. The command acknowledges the value and reports the key type, but Vector, Float, and other keys must be set at runtime via the AIController (e.g. `SetValueAsVector`).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blackboard` | string | Yes | Blackboard asset name (e.g. `"BB_Enemy"`). |
| `key` | string | Yes | Key name (e.g. `"PatrolLocation"`). |
| `value` | varies | No | Value to set. For Vector: `{x, y, z}` object. For Float: number. |

```json
// Request
{"command": "set_blackboard_key_default", "params": {"blackboard": "BB_Enemy", "key": "PatrolLocation", "value": {"x": 500, "y": 0, "z": 0}}}

// Response
{"status": "ok", "data": {"blackboard": "BB_Enemy", "key": "PatrolLocation", "key_type": "BlackboardKeyType_Vector", "note": "Vector BB keys have no asset-level default. Set via AIController at runtime using SetValueAsVector."}}
```

**Notes:**
- Blackboard asset must exist at `/Game/Arcwright/BehaviorTrees/<name>`.
- Most key types do not support asset-level defaults in UE. Use this command to validate key existence and type, then set values at runtime in the AIController Blueprint.

---

## 12. Data Tables

### create_data_table

Create a UUserDefinedStruct and UDataTable from DT IR JSON.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ir_json` | string | Yes | JSON string of the DT IR (from dt_parser). |

```json
// Request
{"command": "create_data_table", "params": {"ir_json": "{\"metadata\":{\"table_name\":\"DT_Weapons\",\"struct_name\":\"WeaponData\"},\"columns\":[{\"name\":\"Name\",\"type\":\"String\"},{\"name\":\"Damage\",\"type\":\"Float\",\"default\":\"0.0\"}],\"rows\":[{\"name\":\"Pistol\",\"values\":{\"Name\":\"Pistol\",\"Damage\":\"25.0\"}}]}"}}

// Response
{"status": "ok", "data": {"table_name": "DT_Weapons", "table_asset_path": "/Game/Arcwright/DataTables/DT_Weapons", "struct_asset_path": "/Game/Arcwright/DataTables/WeaponData", "column_count": 2, "row_count": 1}}
```

**Notes:**
- Supported column types: String, Float, Int, Boolean, Name, Text, Vector, Rotator, Transform, Color.
- Assets saved to `/Game/Arcwright/DataTables/`.

---

### get_data_table_info

Query a DataTable's structure, columns, and row names.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | DataTable asset name. |

```json
// Request
{"command": "get_data_table_info", "params": {"name": "DT_Weapons"}}

// Response
{"status": "ok", "data": {"name": "DT_Weapons", "struct_name": "WeaponData", "columns": [{"name": "Name", "type": "String"}, {"name": "Damage", "type": "Float"}], "row_count": 3, "row_names": ["Pistol", "Rifle", "Shotgun"]}}
```

---

### add_data_table_row

Add a new row to an existing DataTable.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `table_name` | string | Yes | DataTable asset name. |
| `row_name` | string | Yes | Unique row name/key. |
| `values` | object | Yes | Column values: `{"Name": "Sword", "Damage": "50.0"}`. |

```json
// Request
{"command": "add_data_table_row", "params": {"table_name": "DT_Weapons", "row_name": "Sword", "values": {"Name": "Sword", "Damage": "50.0"}}}

// Response
{"status": "ok", "data": {"table_name": "DT_Weapons", "row_name": "Sword", "added": true}}
```

---

### edit_data_table_row

Edit values in an existing DataTable row.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `table_name` | string | Yes | DataTable asset name. |
| `row_name` | string | Yes | Row name to edit. |
| `values` | object | Yes | Column values to update. |

```json
// Request
{"command": "edit_data_table_row", "params": {"table_name": "DT_Weapons", "row_name": "Pistol", "values": {"Damage": "30.0"}}}

// Response
{"status": "ok", "data": {"table_name": "DT_Weapons", "row_name": "Pistol", "edited": true}}
```

---

### get_data_table_rows

Get all rows and their values from a DataTable.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `table_name` | string | Yes | DataTable asset name. |

```json
// Request
{"command": "get_data_table_rows", "params": {"table_name": "DT_Weapons"}}

// Response
{"status": "ok", "data": {"table_name": "DT_Weapons", "columns": ["Name", "Damage"], "rows": [{"row_name": "Pistol", "values": {"Name": "Pistol", "Damage": "25.0"}}, {"row_name": "Rifle", "values": {"Name": "Rifle", "Damage": "15.0"}}]}}
```

---

## 13. Animation

### create_anim_blueprint

Create an Animation Blueprint for a skeleton.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name. |
| `skeleton` | string | Yes | Skeleton asset path. |

```json
// Request
{"command": "create_anim_blueprint", "params": {"name": "ABP_Character", "skeleton": "/Game/Characters/Mannequin/Skeleton"}}

// Response
{"status": "ok", "data": {"name": "ABP_Character", "asset_path": "/Game/Arcwright/Generated/ABP_Character", "skeleton": "/Game/Characters/Mannequin/Skeleton"}}
```

---

### add_anim_state

Add a state node to an AnimBP state machine.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `anim_blueprint` | string | Yes | AnimBP asset name. |
| `state_name` | string | Yes | Name for the new state. |

```json
// Request
{"command": "add_anim_state", "params": {"anim_blueprint": "ABP_Character", "state_name": "Idle"}}

// Response
{"status": "ok", "data": {"anim_blueprint": "ABP_Character", "state_name": "Idle", "added": true}}
```

---

### add_anim_transition

Add a transition between two AnimBP states.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `anim_blueprint` | string | Yes | AnimBP asset name. |
| `from_state` | string | Yes | Source state name. |
| `to_state` | string | Yes | Target state name. |

```json
// Request
{"command": "add_anim_transition", "params": {"anim_blueprint": "ABP_Character", "from_state": "Idle", "to_state": "Walk"}}

// Response
{"status": "ok", "data": {"anim_blueprint": "ABP_Character", "from_state": "Idle", "to_state": "Walk", "added": true}}
```

---

### set_anim_state_animation

Set the animation sequence for an AnimBP state.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `anim_blueprint` | string | Yes | AnimBP asset name. |
| `state_name` | string | Yes | State name. |
| `animation` | string | Yes | UAnimSequence asset path. |

```json
// Request
{"command": "set_anim_state_animation", "params": {"anim_blueprint": "ABP_Character", "state_name": "Idle", "animation": "/Game/Characters/Animations/Idle_Anim"}}

// Response
{"status": "ok", "data": {"anim_blueprint": "ABP_Character", "state_name": "Idle", "animation": "/Game/Characters/Animations/Idle_Anim"}}
```

---

### create_anim_montage

Create an Animation Montage from a source animation sequence.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name. |
| `animation` | string | Yes | Source UAnimSequence asset path. |

```json
// Request
{"command": "create_anim_montage", "params": {"name": "AM_Attack", "animation": "/Game/Characters/Animations/Attack_Anim"}}

// Response
{"status": "ok", "data": {"name": "AM_Attack", "asset_path": "/Game/Arcwright/Generated/AM_Attack"}}
```

---

### add_montage_section

Add a section to an Animation Montage.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `montage_name` | string | Yes | Montage asset name. |
| `section_name` | string | Yes | Section name. |
| `start_time` | float | No | Start time in seconds. Default: 0.0. |

```json
// Request
{"command": "add_montage_section", "params": {"montage_name": "AM_Attack", "section_name": "WindUp", "start_time": 0.0}}

// Response
{"status": "ok", "data": {"montage_name": "AM_Attack", "section_name": "WindUp", "start_time": 0.0}}
```

---

### create_blend_space

Create a BlendSpace (1D or 2D) for a skeleton.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name. |
| `skeleton` | string | Yes | Skeleton asset path. |
| `dimensions` | int | No | 1 or 2. Default: 2. |
| `axis_x` | string | No | X axis name. Default: `"Speed"`. |
| `axis_y` | string | No | Y axis name (2D only). Default: `"Direction"`. |
| `x_min` | float | No | X axis minimum. Default: -180. |
| `x_max` | float | No | X axis maximum. Default: 180. |
| `y_min` | float | No | Y axis minimum (2D only). Default: -180. |
| `y_max` | float | No | Y axis maximum (2D only). Default: 180. |

```json
// Request
{"command": "create_blend_space", "params": {"name": "BS_Locomotion", "skeleton": "/Game/Characters/Mannequin/Skeleton", "dimensions": 2, "axis_x": "Speed", "axis_y": "Direction"}}

// Response
{"status": "ok", "data": {"name": "BS_Locomotion", "asset_path": "/Game/Arcwright/Generated/BS_Locomotion"}}
```

---

### add_blend_space_sample

Add an animation sample point to a BlendSpace.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blend_space` | string | Yes | BlendSpace asset name. |
| `animation` | string | Yes | UAnimSequence asset path. |
| `x` | float | No | X axis position. Default: 0.0. |
| `y` | float | No | Y axis position (2D only). Default: 0.0. |

```json
// Request
{"command": "add_blend_space_sample", "params": {"blend_space": "BS_Locomotion", "animation": "/Game/Characters/Animations/Walk_Fwd", "x": 150, "y": 0}}

// Response
{"status": "ok", "data": {"blend_space": "BS_Locomotion", "animation": "/Game/Characters/Animations/Walk_Fwd", "x": 150, "y": 0}}
```

---

### set_skeletal_mesh

Set a SkeletalMesh on a Blueprint component or placed actor.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `mesh` | string | Yes | SkeletalMesh asset path. |
| `actor_label` | string | No | Target placed actor (mutually exclusive with `blueprint`). |
| `blueprint` | string | No | Target Blueprint (mutually exclusive with `actor_label`). |
| `component_name` | string | No | Specific component name. Uses first skeletal mesh component if omitted. |

```json
// Request
{"command": "set_skeletal_mesh", "params": {"blueprint": "BP_Character", "mesh": "/Game/Characters/Mannequin/SK_Mannequin"}}

// Response
{"status": "ok", "data": {"mesh": "/Game/Characters/Mannequin/SK_Mannequin", "applied": true}}
```

---

### play_animation

Play an animation on an actor's SkeletalMeshComponent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `animation` | string | Yes | UAnimSequence asset path. |
| `looping` | bool | No | Loop the animation. Default: false. |

```json
// Request
{"command": "play_animation", "params": {"actor_label": "Character_01", "animation": "/Game/Characters/Animations/Dance", "looping": true}}

// Response
{"status": "ok", "data": {"actor_label": "Character_01", "animation": "/Game/Characters/Animations/Dance", "looping": true}}
```

---

### get_skeleton_bones

List all bones in a skeleton with hierarchy.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `skeleton` | string | Yes | Skeleton asset path. |

```json
// Request
{"command": "get_skeleton_bones", "params": {"skeleton": "/Game/Characters/Mannequin/Skeleton"}}

// Response
{"status": "ok", "data": {"skeleton": "/Game/Characters/Mannequin/Skeleton", "bone_count": 65, "bones": [{"name": "root", "index": 0, "parent": ""}, {"name": "pelvis", "index": 1, "parent": "root"}]}}
```

---

### get_available_animations

Search for animation assets, optionally filtered by skeleton or name.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `skeleton` | string | No | Filter by target skeleton. |
| `name_filter` | string | No | Name substring filter. |
| `max_results` | int | No | Maximum results. Default: 100. |

```json
// Request
{"command": "get_available_animations", "params": {"skeleton": "/Game/Characters/Mannequin/Skeleton", "max_results": 10}}

// Response
{"status": "ok", "data": {"count": 5, "animations": [{"name": "Idle_Anim", "path": "/Game/Characters/Animations/Idle_Anim", "duration": 2.5}]}}
```

---

## 14. Sequencer

### create_sequence

Create a ULevelSequence asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Sequence name (e.g. `"LS_Intro"`). |
| `duration` | float | No | Duration in seconds. Default: 5.0. |

```json
// Request
{"command": "create_sequence", "params": {"name": "LS_Intro", "duration": 10.0}}

// Response
{"status": "ok", "data": {"name": "LS_Intro", "asset_path": "/Game/Arcwright/Sequences/LS_Intro", "duration": 10.0, "track_count": 0}}
```

---

### add_sequence_track

Bind an actor and add a track to a sequence.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sequence_name` | string | Yes | Sequence name. |
| `actor_label` | string | Yes | Actor to bind. |
| `track_type` | string | No | One of `"Transform"`, `"Visibility"`, `"Float"`. Default: `"Transform"`. |

```json
// Request
{"command": "add_sequence_track", "params": {"sequence_name": "LS_Intro", "actor_label": "Camera_01", "track_type": "Transform"}}

// Response
{"status": "ok", "data": {"sequence_name": "LS_Intro", "actor_label": "Camera_01", "track_type": "Transform", "binding_guid": "..."}}
```

---

### add_keyframe

Add a keyframe to a sequence track.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sequence_name` | string | Yes | Sequence name. |
| `actor_label` | string | Yes | Bound actor label. |
| `track_type` | string | Yes | `"Transform"`, `"Visibility"`, or `"Float"`. |
| `time` | float | Yes | Time in seconds. |
| `value` | varies | Yes | For Transform: `{location:{x,y,z}, rotation:{pitch,yaw,roll}, scale:{x,y,z}}`. For Visibility: bool. For Float: number. |

```json
// Request
{"command": "add_keyframe", "params": {"sequence_name": "LS_Intro", "actor_label": "Camera_01", "track_type": "Transform", "time": 0.0, "value": {"location": {"x": 0, "y": 0, "z": 500}, "rotation": {"pitch": -45, "yaw": 0, "roll": 0}}}}

// Response
{"status": "ok", "data": {"sequence_name": "LS_Intro", "actor_label": "Camera_01", "track_type": "Transform", "time": 0.0, "keys_added": 3}}
```

---

### get_sequence_info

Query a sequence's structure: duration, tracks, bound actors.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Sequence name. |

```json
// Request
{"command": "get_sequence_info", "params": {"name": "LS_Intro"}}

// Response
{"status": "ok", "data": {"name": "LS_Intro", "duration": 10.0, "total_tracks": 2, "bound_actors": ["Camera_01", "Door_01"]}}
```

---

### play_sequence

Play a sequence in editor preview.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Sequence name. |

```json
// Request
{"command": "play_sequence", "params": {"name": "LS_Intro"}}

// Response
{"status": "ok", "data": {"name": "LS_Intro", "playing": true}}
```

**Notes:**
- Has the same PIE limitation as `play_in_editor` -- the request may be queued but not processed by the engine tick loop.

---

## 15. Splines

### create_spline_actor

Create a Blueprint with a SplineComponent and initial points.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Blueprint name (e.g. `"BP_RacePath"`). |
| `initial_points` | array | No | Array of `{x, y, z}` dicts (minimum 2 if provided). |
| `closed` | bool | No | Whether the spline forms a closed loop. Default: false. |

```json
// Request
{"command": "create_spline_actor", "params": {"name": "BP_RacePath", "initial_points": [{"x": 0, "y": 0, "z": 0}, {"x": 1000, "y": 0, "z": 0}, {"x": 1000, "y": 1000, "z": 0}], "closed": true}}

// Response
{"status": "ok", "data": {"blueprint_name": "BP_RacePath", "spline_component": "SplineComponent", "point_count": 3, "closed": true, "compiled": true}}
```

---

### add_spline_point

Add a point to an existing Blueprint's SplineComponent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `point` | object | Yes | `{x, y, z}` location. |
| `index` | int | No | Insert index. -1 = append to end. Default: -1. |

```json
// Request
{"command": "add_spline_point", "params": {"blueprint": "BP_RacePath", "point": {"x": 500, "y": 500, "z": 100}}}

// Response
{"status": "ok", "data": {"blueprint": "BP_RacePath", "point_index": 3, "total_points": 4, "compiled": true}}
```

---

### get_spline_info

Get spline data: points, length, closed status.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |

```json
// Request
{"command": "get_spline_info", "params": {"blueprint": "BP_RacePath"}}

// Response
{"status": "ok", "data": {"blueprint": "BP_RacePath", "point_count": 4, "spline_length": 2414.2, "closed": true, "points": [{"x": 0, "y": 0, "z": 0}, {"x": 1000, "y": 0, "z": 0}, {"x": 1000, "y": 1000, "z": 0}, {"x": 500, "y": 500, "z": 100}]}}
```

---

## 16. Post-Process

### add_post_process_volume

Spawn a PostProcessVolume in the level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | No | Actor label in Outliner. |
| `location` | object | No | `{x, y, z}` location. |
| `infinite_extent` | bool | No | Whether the volume has infinite bounds. Default: true. |
| `settings` | object | No | Post-process settings to apply immediately. |

```json
// Request
{"command": "add_post_process_volume", "params": {"label": "PP_Global", "infinite_extent": true, "settings": {"bloom_intensity": 1.5, "vignette_intensity": 0.4}}}

// Response
{"status": "ok", "data": {"label": "PP_Global", "location": {"x": 0, "y": 0, "z": 0}, "infinite_extent": true}}
```

---

### set_post_process_settings

Update visual settings on an existing PostProcessVolume.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | PostProcessVolume actor label. |
| `settings` | object | Yes | Settings to update (see below). |

**Supported settings:**
- `bloom_intensity` (float), `bloom_threshold` (float)
- `auto_exposure_min` (float), `auto_exposure_max` (float)
- `ambient_occlusion_intensity` (float)
- `color_saturation` ({x,y,z,w}), `color_contrast` ({x,y,z,w}), `color_gamma` ({x,y,z,w}), `color_gain` ({x,y,z,w})
- `vignette_intensity` (float)
- `depth_of_field_focal_distance` (float), `depth_of_field_fstop` (float)
- `motion_blur_amount` (float), `motion_blur_max` (float)

```json
// Request
{"command": "set_post_process_settings", "params": {"label": "PP_Global", "settings": {"bloom_intensity": 2.0, "color_saturation": {"x": 1.2, "y": 1.0, "z": 0.8, "w": 1.0}}}}

// Response
{"status": "ok", "data": {"label": "PP_Global", "settings_applied": 2}}
```

---

## 17. Physics

### add_physics_constraint

Spawn a physics constraint between two actors.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Label for the constraint actor. |
| `actor_a` | string | Yes | Label of first constrained actor. |
| `actor_b` | string | Yes | Label of second constrained actor. |
| `constraint_type` | string | No | One of `"Fixed"`, `"Hinge"`, `"Prismatic"`, `"BallSocket"`. Default: `"Fixed"`. |
| `location` | object | No | `{x, y, z}` override. Default: midpoint of actors. |

```json
// Request
{"command": "add_physics_constraint", "params": {"label": "Hinge_01", "actor_a": "Door", "actor_b": "DoorFrame", "constraint_type": "Hinge"}}

// Response
{"status": "ok", "data": {"label": "Hinge_01", "actor_a": "Door", "actor_b": "DoorFrame", "constraint_type": "Hinge"}}
```

---

### break_constraint

Break (disable) a physics constraint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | Yes | Constraint actor label. |

```json
// Request
{"command": "break_constraint", "params": {"label": "Hinge_01"}}

// Response
{"status": "ok", "data": {"label": "Hinge_01", "broken": true}}
```

---

### set_physics_enabled

Enable or disable physics simulation on a component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `enabled` | bool | Yes | True to enable simulation, false to disable. |
| `actor_label` | string | No | Target placed actor (mutually exclusive with `blueprint`). |
| `blueprint` | string | No | Target Blueprint (mutually exclusive with `actor_label`). |
| `component_name` | string | No | Specific component. Uses first primitive if omitted. |

```json
// Request
{"command": "set_physics_enabled", "params": {"actor_label": "Crate_01", "enabled": true}}

// Response
{"status": "ok", "data": {"actor_label": "Crate_01", "enabled": true, "collision_mode": "QueryAndPhysics"}}
```

---

## 18. Landscape and Foliage

### get_landscape_info

Query if a landscape exists and get its properties.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "get_landscape_info", "params": {}}

// Response
{"status": "ok", "data": {"exists": true, "bounds": {"min": {"x": -5000, "y": -5000}, "max": {"x": 5000, "y": 5000}}, "component_count": 4, "material": "/Game/Materials/M_Landscape"}}
```

**Notes:**
- Returns `{"exists": false}` safely if no landscape is present.
- Landscape creation requires manual setup in the editor.

---

### set_landscape_material

Apply a material to the landscape.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `material_path` | string | Yes | Material asset path. |

```json
// Request
{"command": "set_landscape_material", "params": {"material_path": "/Game/Arcwright/Materials/MAT_Grass"}}

// Response
{"status": "ok", "data": {"landscape": true, "material_path": "/Game/Arcwright/Materials/MAT_Grass"}}
```

---

### create_foliage_type

Create a UFoliageType_InstancedStaticMesh asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name. |
| `mesh` | string | No | Static mesh path. Default: Sphere. |
| `density` | float | No | Foliage density. Default: 100.0. |
| `scale_min` | float | No | Minimum random scale. Default: 1.0. |
| `scale_max` | float | No | Maximum random scale. Default: 1.0. |

```json
// Request
{"command": "create_foliage_type", "params": {"name": "FT_Bush", "mesh": "/Game/Arcwright/Meshes/SM_Bush", "scale_min": 0.8, "scale_max": 1.2}}

// Response
{"status": "ok", "data": {"name": "FT_Bush", "asset_path": "/Game/Arcwright/Foliage/FT_Bush", "mesh": "/Game/Arcwright/Meshes/SM_Bush"}}
```

---

### paint_foliage

Procedurally place foliage instances in a radius with ground tracing and random rotation/scale.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `foliage_type` | string | Yes | Foliage type asset path. |
| `center` | object | Yes | `{x, y, z}` center position. |
| `radius` | float | No | Placement radius. Default: 500. |
| `count` | int | No | Number of instances to place. Default: 10. |

```json
// Request
{"command": "paint_foliage", "params": {"foliage_type": "/Game/Arcwright/Foliage/FT_Bush", "center": {"x": 0, "y": 0, "z": 0}, "radius": 1000, "count": 50}}

// Response
{"status": "ok", "data": {"foliage_type": "/Game/Arcwright/Foliage/FT_Bush", "placed": 50, "center": {"x": 0, "y": 0, "z": 0}, "radius": 1000}}
```

---

### get_foliage_info

List foliage types and instance counts.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "get_foliage_info", "params": {}}

// Response
{"status": "ok", "data": {"foliage_type_count": 2, "total_instances": 150, "foliage_types": [{"name": "FT_Bush", "mesh": "SM_Bush", "instance_count": 100}, {"name": "FT_Rock", "mesh": "SM_Rock", "instance_count": 50}]}}
```

---

## 19. Lighting and Scene

### setup_scene_lighting

Create standard scene lighting: DirectionalLight + SkyLight + optional SkyAtmosphere and ExponentialHeightFog. Removes existing lights of the same type first.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `preset` | string | No | One of `"indoor_dark"`, `"indoor_bright"`, `"outdoor_day"`, `"outdoor_night"`. Default: `"indoor_dark"`. |
| `directional_intensity` | float | No | Override directional light intensity (lux). |
| `sky_intensity` | float | No | Override sky light intensity. |
| `directional_pitch` | float | No | Sun pitch angle (degrees, negative = angled down). |
| `directional_yaw` | float | No | Sun yaw angle. |
| `directional_color` | object | No | Light color `{r, g, b}` (0-1 floats). |
| `add_atmosphere` | bool | No | Whether to add SkyAtmosphere. |
| `add_fog` | bool | No | Whether to add ExponentialHeightFog. |
| `fog_density` | float | No | Fog density. |

```json
// Request
{"command": "setup_scene_lighting", "params": {"preset": "outdoor_day", "add_atmosphere": true, "add_fog": true}}

// Response
{"status": "ok", "data": {"preset": "outdoor_day", "actors_created": 4, "actors": ["DirectionalLight", "SkyLight", "SkyAtmosphere", "ExponentialHeightFog"]}}
```

**Notes:**
- Always call this as the first step of level population. Levels built from scratch have no ambient lighting.

---

### set_game_mode

Set the level's GameMode override in World Settings.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `game_mode` | string | Yes | GameMode Blueprint name (e.g. `"BP_FPSGameMode"`). Must inherit from GameModeBase. |

```json
// Request
{"command": "set_game_mode", "params": {"game_mode": "BP_FirstPersonGameMode"}}

// Response
{"status": "ok", "data": {"game_mode": "BP_FirstPersonGameMode", "applied": true}}
```

---

## 20. Asset Import

### import_static_mesh

Import a .fbx or .obj file as a UStaticMesh asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | Yes | Absolute path to the source file. |
| `asset_name` | string | Yes | Name for the UE asset (use `SM_` prefix convention). |
| `destination` | string | No | Destination folder. Default: `"/Game/Arcwright/Meshes"`. |

```json
// Request
{"command": "import_static_mesh", "params": {"file_path": "C:/Arcwright/exports/crystal.fbx", "asset_name": "SM_Crystal"}}

// Response
{"status": "ok", "data": {"asset_path": "/Game/Arcwright/Meshes/SM_Crystal", "vertices": 2048, "triangles": 3072, "imported_count": 1}}
```

**Notes:**
- Uses UFactory::StaticImportObject (not ImportAssetsAutomated which crashes in AsyncTask context).
- If the asset already exists on disk, returns existing info without re-importing. Delete first via `delete_blueprint` to force re-import.

---

### import_texture

Import a .png, .jpg, or .tga file as a UTexture2D asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | Yes | Absolute path to the image file. |
| `asset_name` | string | Yes | Name for the UE asset (use `T_` prefix convention). |
| `destination` | string | No | Destination folder. Default: `"/Game/Arcwright/Textures"`. |

```json
// Request
{"command": "import_texture", "params": {"file_path": "C:/Arcwright/exports/stone_wall.png", "asset_name": "T_StoneWall"}}

// Response
{"status": "ok", "data": {"asset_path": "/Game/Arcwright/Textures/T_StoneWall", "width": 1024, "height": 1024, "format": "PF_B8G8R8A8", "imported_count": 1}}
```

---

### import_sound

Import a .wav, .ogg, or .mp3 file as a USoundWave asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | Yes | Absolute path to the audio file. |
| `asset_name` | string | Yes | Name for the UE asset (use `SFX_` prefix convention). |
| `destination` | string | No | Destination folder. Default: `"/Game/Arcwright/Sounds"`. |

```json
// Request
{"command": "import_sound", "params": {"file_path": "C:/Arcwright/exports/pickup.wav", "asset_name": "SFX_Pickup"}}

// Response
{"status": "ok", "data": {"asset_path": "/Game/Arcwright/Sounds/SFX_Pickup", "duration": 0.5, "channels": 1, "sample_rate": 44100, "imported_count": 1}}
```

**Notes:**
- Sound re-import can hang. Delete the existing asset first if you need to re-import.

---

## 21. Collision and Input

### set_collision_preset

Set a collision profile on an actor or Blueprint component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `preset_name` | string | Yes | Collision preset name (e.g. `"BlockAll"`, `"OverlapAllDynamic"`, `"NoCollision"`). |
| `actor_label` | string | No | Target placed actor. |
| `blueprint` | string | No | Target Blueprint. |
| `component_name` | string | No | Specific component. Uses first primitive if omitted. |

```json
// Request
{"command": "set_collision_preset", "params": {"actor_label": "Trigger_01", "preset_name": "OverlapAllDynamic"}}

// Response
{"status": "ok", "data": {"preset_name": "OverlapAllDynamic", "applied": true}}
```

---

### set_collision_shape

Set collision shape dimensions (extents, radius, half_height) on a component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | No | Target placed actor. |
| `blueprint` | string | No | Target Blueprint. |
| `component_name` | string | No | Specific component. |
| `extents` | object | No | Box extents `{x, y, z}` (for BoxComponent). |
| `radius` | float | No | Radius (for SphereComponent/CapsuleComponent). |
| `half_height` | float | No | Half height (for CapsuleComponent). |

```json
// Request
{"command": "set_collision_shape", "params": {"blueprint": "BP_Pickup", "component_name": "Overlap", "radius": 150.0}}

// Response
{"status": "ok", "data": {"component_name": "Overlap", "applied": true}}
```

---

### set_camera_properties

Set camera and spring arm properties on a Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `fov` | float | No | Field of view in degrees. |
| `arm_length` | float | No | Spring arm length. |
| `use_pawn_control_rotation` | bool | No | Use pawn control rotation. |
| `do_collision_test` | bool | No | Spring arm collision test. |
| `camera_lag_speed` | float | No | Camera lag speed. |
| `camera_rotation_lag_speed` | float | No | Camera rotation lag speed. |

```json
// Request
{"command": "set_camera_properties", "params": {"blueprint": "BP_Player", "fov": 90.0, "arm_length": 400.0}}

// Response
{"status": "ok", "data": {"blueprint": "BP_Player", "applied": true}}
```

---

### create_input_action

Create an Enhanced Input Action asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Action name (e.g. `"IA_Jump"`). |
| `value_type` | string | No | One of `"bool"`, `"axis1d"`, `"axis2d"`, `"axis3d"`. Default: `"bool"`. |

```json
// Request
{"command": "create_input_action", "params": {"name": "IA_Jump", "value_type": "bool"}}

// Response
{"status": "ok", "data": {"name": "IA_Jump", "asset_path": "/Game/Arcwright/Input/IA_Jump", "value_type": "bool"}}
```

---

### bind_input_to_blueprint

Wire an input action to a Blueprint event.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `action` | string | Yes | Input action name. |
| `trigger` | string | No | Trigger type. Default: `"Pressed"`. |

```json
// Request
{"command": "bind_input_to_blueprint", "params": {"blueprint": "BP_Player", "action": "IA_Jump"}}

// Response
{"status": "ok", "data": {"blueprint": "BP_Player", "action": "IA_Jump", "bound": true}}
```

---

### add_input_mapping

Add a key mapping to an Input Mapping Context.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `context` | string | Yes | Context name or asset path. |
| `action` | string | Yes | Action name or asset path. |
| `key` | string | Yes | Key name (e.g. `"SpaceBar"`, `"E"`, `"W"`, `"LeftMouseButton"`). |

```json
// Request
{"command": "add_input_mapping", "params": {"context": "IMC_Default", "action": "IA_Jump", "key": "SpaceBar"}}

// Response
{"status": "ok", "data": {"context": "IMC_Default", "action": "IA_Jump", "key": "SpaceBar", "added": true}}
```

---

### set_player_input_mapping

Set an input mapping context on a Blueprint.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `context` | string | Yes | Input Mapping Context asset name. |

```json
// Request
{"command": "set_player_input_mapping", "params": {"blueprint": "BP_PlayerController", "context": "IMC_Default"}}

// Response
{"status": "ok", "data": {"blueprint": "BP_PlayerController", "context": "IMC_Default", "applied": true}}
```

---

### setup_input_context

Create a UInputMappingContext asset.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Context name (e.g. `"IMC_Combat"`). |

```json
// Request
{"command": "setup_input_context", "params": {"name": "IMC_Combat"}}

// Response
{"status": "ok", "data": {"name": "IMC_Combat", "asset_path": "/Game/Arcwright/Input/IMC_Combat"}}
```

**Notes:**
- Creates the asset at `/Game/Arcwright/Input/`. Use `add_input_mapping` to bind actions and keys to it.

---

### add_input_action

Create a UInputAction asset (B29 input pipeline).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Action name (e.g. `"IA_Crouch"`). |
| `value_type` | string | No | One of `"bool"`, `"axis1d"`, `"axis2d"`, `"axis3d"`. Default: `"bool"`. |

```json
// Request
{"command": "add_input_action", "params": {"name": "IA_Crouch", "value_type": "bool"}}

// Response
{"status": "ok", "data": {"name": "IA_Crouch", "asset_path": "/Game/Arcwright/Input/IA_Crouch", "value_type": "bool"}}
```

**Notes:**
- Similar to `create_input_action` but part of the B29 input mapping batch. Both create UInputAction assets.

---

### get_input_actions

List all UInputAction assets in the project.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | No | Restrict search to a specific content path. Default: all paths. |

```json
// Request
{"command": "get_input_actions", "params": {}}

// Response
{"status": "ok", "data": {"actions": [{"name": "IA_Jump", "path": "/Game/Arcwright/Input/IA_Jump", "value_type": "bool"}, {"name": "IA_Move", "path": "/Game/Input/IA_Move", "value_type": "axis2d"}]}}
```

---

## 22. Audio and Navigation

### set_audio_properties

Set audio component properties (volume, pitch, auto_activate).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | No | Target placed actor. |
| `blueprint` | string | No | Target Blueprint. |
| `component_name` | string | No | Specific audio component. |
| `volume_multiplier` | float | No | Volume multiplier. |
| `pitch_multiplier` | float | No | Pitch multiplier. |
| `auto_activate` | bool | No | Auto-activate on begin play. |
| `is_ui_sound` | bool | No | Mark as UI sound (ignores distance attenuation). |

```json
// Request
{"command": "set_audio_properties", "params": {"actor_label": "Speaker_01", "volume_multiplier": 0.5, "auto_activate": true}}

// Response
{"status": "ok", "data": {"applied": true}}
```

---

### play_sound_at_location

Play a sound at a world location (fire-and-forget).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `sound` | string | Yes | Sound asset path or name. |
| `location` | object | Yes | `{x, y, z}` world location. |
| `volume` | float | No | Volume multiplier. Default: 1.0. |
| `pitch` | float | No | Pitch multiplier. Default: 1.0. |

```json
// Request
{"command": "play_sound_at_location", "params": {"sound": "/Game/Arcwright/Sounds/SFX_Pickup", "location": {"x": 500, "y": 0, "z": 50}, "volume": 0.8}}

// Response
{"status": "ok", "data": {"sound": "/Game/Arcwright/Sounds/SFX_Pickup", "played": true}}
```

---

### create_nav_mesh_bounds

Create a NavMeshBoundsVolume for AI pathfinding.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `label` | string | No | Actor label. Default: `"NavMeshBounds"`. |
| `location` | object | No | `{x, y, z}` center location. |
| `extents` | object | No | `{x, y, z}` box extents. |

```json
// Request
{"command": "create_nav_mesh_bounds", "params": {"location": {"x": 0, "y": 0, "z": 0}, "extents": {"x": 5000, "y": 5000, "z": 500}}}

// Response
{"status": "ok", "data": {"label": "NavMeshBounds", "location": {"x": 0, "y": 0, "z": 0}, "extents": {"x": 5000, "y": 5000, "z": 500}}}
```

**Notes:**
- NavMesh may not auto-build in World Partition. Use `MoveToLocation(bUsePathfinding=false)` as a workaround.

---

### add_audio_component

Add a UAudioComponent to a Blueprint's SCS.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `name` | string | No | Component name. Default: `"Audio"`. |
| `sound` | string | No | Sound asset path to assign. |
| `auto_activate` | bool | No | Auto-activate on begin play. Default: true. |

```json
// Request
{"command": "add_audio_component", "params": {"blueprint": "BP_MusicBox", "name": "AmbientSound", "sound": "/Game/Arcwright/Sounds/SFX_Ambient", "auto_activate": true}}

// Response
{"status": "ok", "data": {"blueprint": "BP_MusicBox", "component": "AmbientSound", "added": true}}
```

---

### get_sound_assets

List available sound assets in the project.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | No | Content path to search. Default: `"/Game"`. |
| `search_subfolders` | bool | No | Include subfolders. Default: true. |

```json
// Request
{"command": "get_sound_assets", "params": {"path": "/Game/Arcwright/Sounds"}}

// Response
{"status": "ok", "data": {"sounds": [{"name": "SFX_Pickup", "path": "/Game/Arcwright/Sounds/SFX_Pickup", "duration": 0.5}, {"name": "SFX_Ambient", "path": "/Game/Arcwright/Sounds/SFX_Ambient", "duration": 30.0}]}}
```

---

## 23. Niagara

### set_niagara_parameter

Set a parameter on a NiagaraComponent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `parameter_name` | string | Yes | Parameter name. |
| `float_value` | float | No | Float value (provide exactly one value type). |
| `int_value` | int | No | Int value. |
| `bool_value` | bool | No | Bool value. |
| `vector_value` | object | No | `{x, y, z}` vector value. |
| `color_value` | object | No | `{r, g, b, a}` color value. |

```json
// Request
{"command": "set_niagara_parameter", "params": {"actor_label": "Emitter_01", "parameter_name": "SpawnRate", "float_value": 100.0}}

// Response
{"status": "ok", "data": {"actor_label": "Emitter_01", "parameter_name": "SpawnRate", "applied": true}}
```

---

### activate_niagara

Activate or deactivate a NiagaraComponent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |
| `activate` | bool | No | True to activate, false to deactivate. Default: true. |
| `component_name` | string | No | Specific Niagara component. |

```json
// Request
{"command": "activate_niagara", "params": {"actor_label": "Emitter_01", "activate": false}}

// Response
{"status": "ok", "data": {"actor_label": "Emitter_01", "activate": false}}
```

---

### get_niagara_parameters

List parameters on a NiagaraComponent.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor label. |

```json
// Request
{"command": "get_niagara_parameters", "params": {"actor_label": "Emitter_01"}}

// Response
{"status": "ok", "data": {"actor_label": "Emitter_01", "parameters": [{"name": "SpawnRate", "type": "Float", "value": 100.0}]}}
```

---

### spawn_niagara_at_location

Spawn a Niagara particle system in the world (fire-and-forget).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `system` | string | Yes | Niagara system asset path. |
| `location` | object | Yes | `{x, y, z}` world location. |
| `rotation` | object | No | `{pitch, yaw, roll}` rotation. |
| `auto_destroy` | bool | No | Destroy after completion. Default: true. |

```json
// Request
{"command": "spawn_niagara_at_location", "params": {"system": "/Game/FX/NS_Explosion", "location": {"x": 500, "y": 0, "z": 100}, "auto_destroy": true}}

// Response
{"status": "ok", "data": {"system": "/Game/FX/NS_Explosion", "location": {"x": 500, "y": 0, "z": 100}, "spawned": true}}
```

**Notes:**
- The spawned system is a world actor, not a Blueprint component. For persistent particle effects attached to Blueprints, use `add_niagara_component`.

---

### add_niagara_component

Add a UNiagaraComponent to a Blueprint's SCS.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `name` | string | No | Component name. Default: `"Niagara"`. |
| `system` | string | No | Niagara system asset path to assign. |
| `auto_activate` | bool | No | Auto-activate on begin play. Default: true. |

```json
// Request
{"command": "add_niagara_component", "params": {"blueprint": "BP_Torch", "name": "FireEffect", "system": "/Game/FX/NS_Fire", "auto_activate": true}}

// Response
{"status": "ok", "data": {"blueprint": "BP_Torch", "component": "FireEffect", "added": true}}
```

---

### get_niagara_assets

List available Niagara system assets in the project.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | No | Content path to search. Default: `"/Game"`. |
| `search_subfolders` | bool | No | Include subfolders. Default: true. |

```json
// Request
{"command": "get_niagara_assets", "params": {"path": "/Game/FX"}}

// Response
{"status": "ok", "data": {"systems": [{"name": "NS_Fire", "path": "/Game/FX/NS_Fire"}, {"name": "NS_Explosion", "path": "/Game/FX/NS_Explosion"}]}}
```

---

## 24. Level Management

### create_sublevel

Create and add a streaming sublevel.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Sublevel name. |

```json
// Request
{"command": "create_sublevel", "params": {"name": "SubLevel_Combat"}}

// Response
{"status": "ok", "data": {"name": "SubLevel_Combat", "created": true}}
```

**Notes:**
- Pre-creates the level package on disk before adding as streaming to avoid blocking dialogs.

---

### set_level_visibility

Set a sublevel's visibility and load state.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `level_name` | string | Yes | Sublevel name. |
| `visible` | bool | No | True to show and load, false to hide. Default: true. |

```json
// Request
{"command": "set_level_visibility", "params": {"level_name": "SubLevel_Combat", "visible": true}}

// Response
{"status": "ok", "data": {"level_name": "SubLevel_Combat", "visible": true}}
```

---

### get_sublevel_list

List persistent and streaming levels.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "get_sublevel_list", "params": {}}

// Response
{"status": "ok", "data": {"count": 3, "levels": [{"name": "PersistentLevel", "visible": true, "loaded": true, "persistent": true}, {"name": "SubLevel_Combat", "visible": true, "loaded": true, "persistent": false}]}}
```

---

### move_actor_to_sublevel

Move an actor to a different streaming level.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `actor_label` | string | Yes | Actor to move. |
| `level_name` | string | Yes | Target sublevel name. |

```json
// Request
{"command": "move_actor_to_sublevel", "params": {"actor_label": "Enemy_01", "level_name": "SubLevel_Combat"}}

// Response
{"status": "ok", "data": {"actor_label": "Enemy_01", "level_name": "SubLevel_Combat", "moved": true}}
```

---

## 25. SaveGame

### create_save_game

Create a SaveGame Blueprint with typed variables.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Asset name. |
| `variables` | array | No | Array of `{"name": str, "type": str}` variable definitions. |

```json
// Request
{"command": "create_save_game", "params": {"name": "SG_PlayerProgress", "variables": [{"name": "Level", "type": "Int"}, {"name": "Score", "type": "Float"}, {"name": "PlayerName", "type": "String"}]}}

// Response
{"status": "ok", "data": {"name": "SG_PlayerProgress", "asset_path": "/Game/Arcwright/Generated/SG_PlayerProgress", "parent_class": "SaveGame", "variables_added": 3}}
```

---

## 26. Movement

### set_movement_defaults

Set movement properties on a Blueprint's movement component.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| `properties` | object | Yes | Movement settings (see below). |

**CharacterMovementComponent properties:**
- `max_walk_speed` (float), `max_acceleration` (float), `jump_z_velocity` (float)
- `gravity_scale` (float), `air_control` (float)
- `braking_deceleration_walking` (float), `braking_friction` (float)

**FloatingPawnMovement properties:**
- `max_speed` (float), `acceleration` (float), `deceleration` (float), `turning_boost` (float)

```json
// Request
{"command": "set_movement_defaults", "params": {"blueprint": "BP_Player", "properties": {"max_walk_speed": 800.0, "jump_z_velocity": 600.0, "air_control": 0.5}}}

// Response
{"status": "ok", "data": {"blueprint": "BP_Player", "movement_class": "CharacterMovementComponent", "settings_applied": 3}}
```

---

## 27. Class Defaults

### set_class_defaults

Set arbitrary CDO (Class Default Object) properties on a Blueprint via UPROPERTY reflection.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `blueprint` | string | Yes | Blueprint name. |
| *(additional keys)* | varies | Yes | Property name-value pairs at the top level of params. |

**Common properties:**
- `AutoPossessAI` (string: `"Disabled"`, `"PlacedInWorld"`, `"Spawned"`, `"PlacedInWorldOrSpawned"`)
- `AIControllerClass` (string: Blueprint name)
- `bShowMouseCursor` (bool)
- `DefaultMouseCursor` (string)
- `default_pawn_class` (string: Blueprint name)
- `player_controller_class` (string: Blueprint name)

```json
// Request
{"command": "set_class_defaults", "params": {"blueprint": "BP_Enemy", "AutoPossessAI": "PlacedInWorldOrSpawned", "AIControllerClass": "BP_EnemyAI"}}

// Response
{"status": "ok", "data": {"blueprint": "BP_Enemy", "properties_set": 2, "compiled": true}}
```

**Notes:**
- Supports bool, enum, int, float, string, and name types via FindPropertyByName reflection.
- Blueprint recreation invalidates CDO references on other BPs. Re-apply set_class_defaults after recreating referenced BPs.

---

## 28. PIE

### play_in_editor

Request a Play In Editor (PIE) session start.

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "play_in_editor", "params": {}}

// Response
{"status": "ok", "data": {"requested": true}}
```

**Notes:**
- Known UE 5.7 limitation: RequestPlaySession queues the request but FEngineLoop::Tick does not process it from TCP context. The command returns OK but PIE does not actually start. The user must click Play manually in the editor.

---

### stop_play

Stop the current PIE session. Idempotent (returns OK if not playing).

| Parameter | Type | Required | Description |
|---|---|---|---|
| *(none)* | | | |

```json
// Request
{"command": "stop_play", "params": {}}

// Response
{"status": "ok", "data": {"stopped": true}}
```
