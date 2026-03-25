# Arcwright Command Reference

Complete reference for all 274 TCP commands available through the Arcwright UE5 plugin. Commands are sent as newline-delimited JSON to `localhost:13377`.

**Protocol format:**
```
Request:  {"command": "<name>", "params": {<params>}}\n
Response: {"status": "ok", "data": {<result>}}\n
Error:    {"status": "error", "message": "<description>"}\n
```

---

## Table of Contents

1. [System and Core](#1-system-and-core)
2. [Blueprint CRUD](#2-blueprint-crud)
3. [Blueprint Nodes and Wiring](#3-blueprint-nodes-and-wiring)
4. [Actor and Level](#4-actor-and-level)
5. [Components](#5-components)
6. [Materials](#6-materials)
7. [Widgets](#7-widgets)
8. [Behavior Trees](#8-behavior-trees)
9. [Data Tables](#9-data-tables)
10. [Batch Operations](#10-batch-operations)
11. [Spawn Patterns](#11-spawn-patterns)
12. [Query and Discovery](#12-query-and-discovery)
13. [Inspection](#13-inspection)
14. [Diagnostics](#14-diagnostics)
15. [PIE Control](#15-pie-control)
16. [DSL Parsers](#16-dsl-parsers)
17. [Sequencer](#17-sequencer)
18. [Splines and Post-Process](#18-splines-and-post-process)
19. [Physics and Movement](#19-physics-and-movement)
20. [Landscape and Foliage](#20-landscape-and-foliage)
21. [Scene Setup and Lighting](#21-scene-setup-and-lighting)
22. [Audio and Navigation](#22-audio-and-navigation)
23. [Collision and Input](#23-collision-and-input)
24. [Niagara](#24-niagara)
25. [Level Management and SaveGame](#25-level-management-and-savegame)
26. [Class Defaults and Properties](#26-class-defaults-and-properties)

---

## 1. System and Core

### health_check

Check that the Arcwright command server is running.

```json
{"command": "health_check", "params": {}}

// Response
{"status": "ok", "data": {"server": "Arcwright", "version": "1.0", "engine": "5.5.0"}}
```

### save_all

Save all dirty packages including World Partition external actor files.

```json
{"command": "save_all", "params": {}}

// Response
{"status": "ok", "data": {"saved": true, "external_actors_saved": 12}}
```

### save_level

Save the current level to disk.

```json
{"command": "save_level", "params": {}}
```

### get_level_info

Get the current level name, path, and actor count.

```json
{"command": "get_level_info", "params": {}}

// Response
{"status": "ok", "data": {"level_name": "ArenaLevel", "level_path": "/Game/Maps/ArenaLevel", "actor_count": 47}}
```

### quit_editor

Cleanly shut down the UE Editor (saves all packages first).

```json
{"command": "quit_editor", "params": {}}
{"command": "quit_editor", "params": {"skip_save": true}}
```

### get_last_error

Get the last error message and the command that caused it.

```json
{"command": "get_last_error", "params": {}}
```

### get_capabilities

List all available commands and their descriptions.

```json
{"command": "get_capabilities", "params": {}}
```

---

## 2. Blueprint CRUD

Commands for creating, reading, updating, and deleting Blueprint assets.

### create_blueprint

Create a new Blueprint asset with optional variables.

```json
{
  "command": "create_blueprint",
  "params": {
    "name": "BP_HealthPickup",
    "parent_class": "Actor",
    "variables": [
      {"name": "HealAmount", "type": "Float", "default": "25.0"},
      {"name": "IsActive", "type": "Boolean", "default": "true"}
    ]
  }
}
```

**Note:** `create_blueprint` automatically creates three default event nodes: `node_0` (BeginPlay), `node_1` (ActorBeginOverlap), and `node_2` (Tick). Do not recreate these in `add_nodes_batch` -- wire to them directly.

### import_from_ir

Import a `.blueprint.json` IR file and create a compiled Blueprint.

```json
{"command": "import_from_ir", "params": {"path": "C:/project/BP_Pickup.blueprint.json"}}

// Response
{"status": "ok", "data": {"blueprint_name": "BP_Pickup", "nodes_created": 8, "connections_wired": 7, "compiled": true}}
```

### create_blueprint_from_dsl

Create a Blueprint directly from raw DSL text.

```json
{
  "command": "create_blueprint_from_dsl",
  "params": {
    "dsl": "BLUEPRINT: BP_Hello\nPARENT: Actor\n\nGRAPH: EventGraph\n\nNODE n1: Event_BeginPlay\nNODE n2: PrintString [InString=\"Hello World\"]\n\nEXEC n1.Then -> n2.Execute"
  }
}
```

### compile_blueprint

Recompile a Blueprint asset after modifications.

```json
{"command": "compile_blueprint", "params": {"name": "BP_HealthPickup"}}
```

### validate_blueprint

Validate a Blueprint and report any issues without modifying it.

```json
{"command": "validate_blueprint", "params": {"name": "BP_HealthPickup"}}

// Response
{"status": "ok", "data": {"valid": true, "total_issues": 0, "issues": []}}
```

### delete_blueprint

Delete a Blueprint asset permanently.

```json
{"command": "delete_blueprint", "params": {"name": "BP_HealthPickup"}}
```

### duplicate_blueprint

Duplicate an existing Blueprint with a new name.

```json
{"command": "duplicate_blueprint", "params": {"source_name": "BP_Pickup", "new_name": "BP_PickupGold"}}
```

### get_blueprint_info

Query a Blueprint's full structure: nodes, connections, variables, and compile status.

```json
{"command": "get_blueprint_info", "params": {"name": "BP_HealthPickup"}}
```

### get_blueprint_details

Extended Blueprint inspection with events, components, and pin details.

```json
{"command": "get_blueprint_details", "params": {"name": "BP_HealthPickup"}}
```

---

## 3. Blueprint Nodes and Wiring

Commands for adding, removing, and connecting Blueprint graph nodes.

### add_nodes_batch

Add multiple nodes to a Blueprint's EventGraph in a single call.

```json
{
  "command": "add_nodes_batch",
  "params": {
    "blueprint": "BP_HealthPickup",
    "nodes": [
      {"node_type": "PrintString", "node_id": "print1", "params": {"InString": "Healed!"}},
      {"node_type": "DestroyActor", "node_id": "destroy1"}
    ]
  }
}
```

### add_connections_batch

Wire multiple pins together in a single call.

```json
{
  "command": "add_connections_batch",
  "params": {
    "blueprint": "BP_HealthPickup",
    "connections": [
      {"source_node": "node_1", "source_pin": "Then", "target_node": "print1", "target_pin": "execute"},
      {"source_node": "print1", "source_pin": "Then", "target_node": "destroy1", "target_pin": "execute"}
    ]
  }
}
```

### add_node

Add a single node to a Blueprint.

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
```

### add_connection

Wire two pins together. Supports auto-conversion (e.g., Float to String).

```json
{
  "command": "add_connection",
  "params": {
    "blueprint": "BP_Test",
    "source_node": "node_0",
    "source_pin": "Then",
    "target_node": "delay_1",
    "target_pin": "Execute"
  }
}
```

### remove_node

Remove a node and all its connections.

```json
{"command": "remove_node", "params": {"blueprint": "BP_Test", "node_id": "delay_1"}}
```

### remove_connection

Disconnect two pins.

```json
{
  "command": "remove_connection",
  "params": {
    "blueprint": "BP_Test",
    "source_node": "node_0",
    "source_pin": "Then",
    "target_node": "delay_1",
    "target_pin": "Execute"
  }
}
```

### set_node_param

Set a pin's default value on an existing node.

```json
{
  "command": "set_node_param",
  "params": {
    "blueprint": "BP_Test",
    "node_id": "delay_1",
    "pin_name": "Duration",
    "value": "5.0"
  }
}
```

### set_variable_default

Set the default value of a Blueprint variable.

```json
{"command": "set_variable_default", "params": {"blueprint": "BP_Test", "variable_name": "MaxHealth", "value": "100"}}
```

---

## 4. Actor and Level

Commands for spawning, moving, querying, and deleting actors in the level.

### spawn_actor_at

Spawn an actor into the editor level.

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_Pickup.BP_Pickup_C",
    "label": "Pickup_1",
    "x": 500, "y": 0, "z": 100
  }
}
```

For Blueprint actors, use the full `/Game/` class path so that Blueprint logic executes at runtime. For native classes, use the short name (e.g., `"StaticMeshActor"`, `"PointLight"`).

### find_actors

Search for actors in the current level.

```json
{"command": "find_actors", "params": {"class_filter": "BP_Pickup"}}

// Response
{"status": "ok", "data": {"count": 3, "actors": [{"label": "Pickup_1", "class": "BP_Pickup_C", "location": {"x": 500, "y": 0, "z": 100}}]}}
```

### delete_actor

Delete a single actor by label.

```json
{"command": "delete_actor", "params": {"label": "Pickup_1"}}
```

### set_actor_transform

Move, rotate, or scale an existing actor.

```json
{
  "command": "set_actor_transform",
  "params": {
    "label": "Pickup_1",
    "location": {"x": 200, "y": 300, "z": 50},
    "rotation": {"pitch": 0, "yaw": 45, "roll": 0},
    "scale": {"x": 2, "y": 2, "z": 2}
  }
}
```

### get_actor_properties

Get all properties of a placed actor.

```json
{"command": "get_actor_properties", "params": {"label": "Pickup_1"}}
```

---

## 5. Components

Add and manage components on Blueprint actors. Arcwright supports 11 component types.

### add_component

Add a component to a Blueprint's Simple Construction Script.

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Enemy",
    "component_type": "StaticMesh",
    "component_name": "EnemyMesh",
    "properties": {
      "mesh": "/Engine/BasicShapes/Cone.Cone",
      "scale": {"x": 1, "y": 1, "z": 2}
    }
  }
}
```

**Supported component types:**

| Type | UE Class | Key Properties |
|---|---|---|
| `StaticMesh` | UStaticMeshComponent | `mesh`, `material`, `scale` |
| `BoxCollision` | UBoxComponent | `extent` (x,y,z), `generate_overlap_events` |
| `SphereCollision` | USphereComponent | `radius`, `generate_overlap_events` |
| `CapsuleCollision` | UCapsuleComponent | `radius`, `half_height` |
| `PointLight` | UPointLightComponent | `intensity`, `light_color`, `attenuation_radius` |
| `SpotLight` | USpotLightComponent | `intensity`, `light_color`, `inner_cone_angle`, `outer_cone_angle` |
| `Audio` | UAudioComponent | `sound` |
| `Arrow` | UArrowComponent | -- |
| `Scene` | USceneComponent | Generic parent for hierarchy |
| `Niagara` | UNiagaraComponent | `system_asset` |
| `SkeletalMesh` | USkeletalMeshComponent | `mesh`, `anim_class` |

All components support: `location`, `rotation`, `scale`, `visibility`.

### get_components

List all components on a Blueprint.

```json
{"command": "get_components", "params": {"blueprint": "BP_Enemy"}}
```

### remove_component

Remove a named component from a Blueprint.

```json
{"command": "remove_component", "params": {"blueprint": "BP_Enemy", "component_name": "OldMesh"}}
```

### set_component_property

Modify a property on an existing component.

```json
{
  "command": "set_component_property",
  "params": {
    "blueprint": "BP_Enemy",
    "component_name": "EnemyMesh",
    "property_name": "scale",
    "value": {"x": 2, "y": 2, "z": 2}
  }
}
```

---

## 6. Materials

Create materials and apply them to actors.

### create_simple_material

Create a `UMaterial` with BaseColor and optional emissive. Works with both Substrate and traditional rendering.

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_Gold",
    "color": {"r": 1.0, "g": 0.84, "b": 0.0},
    "emissive": 0.5
  }
}
```

### apply_material

Apply a material to a Blueprint's mesh component (affects the asset).

```json
{"command": "apply_material", "params": {"blueprint": "BP_Pickup", "component_name": "PickupMesh", "material_path": "/Game/Arcwright/Materials/MAT_Gold"}}
```

### set_actor_material

Apply a material to a placed actor's mesh component (affects the instance). This is the recommended way to apply materials to spawned actors.

```json
{"command": "set_actor_material", "params": {"actor_label": "Pickup_1", "material_path": "/Game/Arcwright/Materials/MAT_Gold"}}
```

### batch_apply_material

Apply materials to multiple actors in one call.

```json
{
  "command": "batch_apply_material",
  "params": {
    "operations": [
      {"actor_label": "Wall_North", "material_path": "/Game/Arcwright/Materials/MAT_Wall"},
      {"actor_label": "Wall_South", "material_path": "/Game/Arcwright/Materials/MAT_Wall"},
      {"actor_label": "Floor", "material_path": "/Game/Arcwright/Materials/MAT_Floor"}
    ]
  }
}
```

---

## 7. Widgets

Create UMG Widget Blueprints and build UI hierarchies.

### create_widget_blueprint

Create a new Widget Blueprint. Defaults to 1920x1080 design size.

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_GameHUD"}}
```

You can specify a custom design size:

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_MobileHUD", "design_width": 1080, "design_height": 1920}}
```

### set_widget_design_size

Change the design-time resolution of an existing Widget Blueprint.

```json
{"command": "set_widget_design_size", "params": {"widget_blueprint": "WBP_GameHUD", "width": 1920, "height": 1080}}
```

### add_widget_child

Add a child widget to the hierarchy.

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_GameHUD", "widget_type": "TextBlock", "widget_name": "ScoreText", "parent_name": "RootPanel"}}
```

**Supported widget types:** `CanvasPanel`, `VerticalBox`, `HorizontalBox`, `Overlay`, `TextBlock`, `Image`, `Button`, `ProgressBar`, `Border`, `SizeBox`, `EditableText`, `ScrollBox`, `UniformGridPanel`, `Spacer`.

### set_widget_property

Set a property on a named widget. Use `hex:#RRGGBB` for colors.

```json
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property_name": "text", "value": "Score: 0"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property_name": "font_size", "value": 24}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property_name": "color", "value": "hex:#E8A624"}}
```

**Supported properties:** `text`, `font_size`, `color`, `position` (x,y), `size` (x,y), `percent`, `fill_color`, `background_color`, `visibility`, `render_opacity`, `padding`, `alignment`, `justification`.

### get_widget_tree

Inspect the full widget hierarchy.

```json
{"command": "get_widget_tree", "params": {"widget_blueprint": "WBP_GameHUD"}}
```

### protect_widget_layout

Lock visual layout widgets so only text (`txt_*`) and button (`Btn_*`) widgets remain modifiable from C++/Blueprint code.

```json
{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_GameHUD"}}
```

---

## 8. Behavior Trees

Create AI Behavior Trees and wire them to pawns.

### create_behavior_tree

Create a Behavior Tree from a JSON IR structure.

```json
{
  "command": "create_behavior_tree",
  "params": {
    "ir_json": "{\"name\": \"BT_Patrol\", \"blackboard_name\": \"BB_Patrol\", \"blackboard_keys\": [{\"name\": \"TargetActor\", \"type\": \"Object\"}, {\"name\": \"PatrolLocation\", \"type\": \"Vector\"}], \"root\": {\"type\": \"Selector\", \"name\": \"Root\", \"children\": [{\"type\": \"Sequence\", \"name\": \"Chase\", \"children\": [{\"type\": \"MoveTo\", \"name\": \"ChaseTarget\", \"params\": {\"Key\": \"TargetActor\"}}]}, {\"type\": \"Sequence\", \"name\": \"Patrol\", \"children\": [{\"type\": \"MoveTo\", \"name\": \"GoToPoint\", \"params\": {\"Key\": \"PatrolLocation\"}}, {\"type\": \"Wait\", \"name\": \"WaitAtPoint\", \"params\": {\"Duration\": \"3.0\"}}]}]}}"
  }
}
```

### get_behavior_tree_info

Query a Behavior Tree's structure.

```json
{"command": "get_behavior_tree_info", "params": {"name": "BT_Patrol"}}
```

### setup_ai_for_pawn

Create an AI Controller, wire `RunBehaviorTree` to BeginPlay, and assign it to a pawn -- all in one command.

```json
{
  "command": "setup_ai_for_pawn",
  "params": {
    "pawn_name": "BP_Enemy",
    "behavior_tree": "BT_Patrol",
    "controller_name": "BP_EnemyAI"
  }
}
```

This replaces a 5-step manual process: creating the controller Blueprint, adding RunBehaviorTree, setting the BT asset, assigning AIControllerClass, and enabling AutoPossessAI.

---

## 9. Data Tables

Create and populate Data Table assets.

### create_data_table

Create a new Data Table with a defined row structure.

```json
{
  "command": "create_data_table",
  "params": {
    "name": "DT_Weapons",
    "struct_name": "WeaponData",
    "columns": [
      {"name": "Damage", "type": "Float"},
      {"name": "FireRate", "type": "Float"},
      {"name": "MaxAmmo", "type": "Integer"},
      {"name": "DisplayName", "type": "String"}
    ]
  }
}
```

### add_data_table_row

Add a row to an existing Data Table.

```json
{
  "command": "add_data_table_row",
  "params": {
    "data_table": "DT_Weapons",
    "row_name": "Pistol",
    "values": {
      "Damage": "25.0",
      "FireRate": "0.5",
      "MaxAmmo": "12",
      "DisplayName": "M1911 Pistol"
    }
  }
}
```

### get_data_table_rows

Query all rows in a Data Table.

```json
{"command": "get_data_table_rows", "params": {"data_table": "DT_Weapons"}}
```

---

## 10. Batch Operations

Perform multiple operations in a single command. Individual failures do not abort the batch.

### batch_set_variable

Set variables on multiple actors at once.

```json
{
  "command": "batch_set_variable",
  "params": {
    "operations": [
      {"actor_label": "Enemy_1", "variable_name": "Health", "value": "200"},
      {"actor_label": "Enemy_2", "variable_name": "Health", "value": "150"}
    ]
  }
}
```

### batch_add_component

Add the same component to multiple Blueprints.

```json
{
  "command": "batch_add_component",
  "params": {
    "blueprints": ["BP_Enemy", "BP_Boss"],
    "component_type": "SphereCollision",
    "component_name": "DetectionSphere",
    "properties": {"radius": 500, "generate_overlap_events": true}
  }
}
```

### batch_delete_actors

Delete multiple actors by class filter.

```json
{"command": "batch_delete_actors", "params": {"class_filter": "BP_Coin"}}
```

### batch_move_actors

Reposition multiple actors in one call.

```json
{
  "command": "batch_move_actors",
  "params": {
    "operations": [
      {"label": "Coin_1", "location": {"x": 100, "y": 0, "z": 50}},
      {"label": "Coin_2", "location": {"x": 200, "y": 0, "z": 50}}
    ]
  }
}
```

---

## 11. Spawn Patterns

Place multiple actors in geometric arrangements.

### spawn_actor_grid

Spawn actors in a rectangular grid.

```json
{
  "command": "spawn_actor_grid",
  "params": {
    "actor_class": "/Game/Arcwright/Generated/BP_Tile.BP_Tile_C",
    "rows": 5,
    "columns": 5,
    "spacing": 200,
    "origin": {"x": 0, "y": 0, "z": 0},
    "label_prefix": "Tile"
  }
}
```

### spawn_actor_circle

Spawn actors in a circle.

```json
{
  "command": "spawn_actor_circle",
  "params": {
    "actor_class": "/Game/Arcwright/Generated/BP_Pillar.BP_Pillar_C",
    "count": 8,
    "radius": 500,
    "center": {"x": 0, "y": 0, "z": 0},
    "label_prefix": "Pillar"
  }
}
```

### spawn_actor_line

Spawn actors along a line.

```json
{
  "command": "spawn_actor_line",
  "params": {
    "actor_class": "/Game/Arcwright/Generated/BP_Fence.BP_Fence_C",
    "count": 10,
    "start": {"x": 0, "y": 0, "z": 0},
    "end": {"x": 2000, "y": 0, "z": 0},
    "label_prefix": "Fence"
  }
}
```

---

## 12. Query and Discovery

Search for assets and actors in the project.

### find_blueprints

Search for Blueprint assets by name pattern.

```json
{"command": "find_blueprints", "params": {"name_filter": "BP_Enemy"}}

// Response
{"status": "ok", "data": {"count": 3, "blueprints": ["BP_EnemyBase", "BP_EnemyRanged", "BP_EnemyMelee"]}}
```

### find_assets

Search the asset registry by type and name.

```json
{"command": "find_assets", "params": {"type": "Material", "name_filter": "MAT_"}}
```

### list_project_assets

List all assets in the project organized by type.

```json
{"command": "list_project_assets", "params": {}}
```

---

## 13. Inspection

Detailed inspection of Blueprints, actors, and the level.

### verify_all_blueprints

Compile and validate every Blueprint in `/Game/Arcwright/Generated/`.

```json
{"command": "verify_all_blueprints", "params": {}}

// Response
{"status": "ok", "data": {"total": 12, "passed": 11, "failed": 1, "failures": ["BP_Broken: Compile error on node 4"]}}
```

### get_stats

Get plugin statistics: commands processed, uptime, Blueprint count.

```json
{"command": "get_stats", "params": {}}
```

---

## 14. Diagnostics

Tools for debugging the editor state.

### run_map_check

Run the UE Map Check and return all warnings/errors.

```json
{"command": "run_map_check", "params": {}}
```

### get_message_log

Read the UE Message Log.

```json
{"command": "get_message_log", "params": {"category": "BlueprintLog"}}
```

### get_output_log

Read the UE output log file with optional filtering.

```json
{"command": "get_output_log", "params": {"last_n_lines": 50, "category": "LogArcwright"}}
```

---

## 15. PIE Control

Control Play In Editor sessions for testing.

### play_in_editor

Start a PIE session.

```json
{"command": "play_in_editor", "params": {}}
```

### stop_play

Stop the current PIE session.

```json
{"command": "stop_play", "params": {}}
```

### is_playing

Check whether a PIE session is active.

```json
{"command": "is_playing", "params": {}}
```

### teleport_player

Move the player pawn to a specific location during PIE.

```json
{"command": "teleport_player", "params": {"x": 1000, "y": 500, "z": 100}}
```

### get_player_location

Get the current player pawn location during PIE.

```json
{"command": "get_player_location", "params": {}}
```

### teleport_to_actor

Teleport the player to a named actor during PIE.

```json
{"command": "teleport_to_actor", "params": {"label": "Checkpoint_1"}}
```

### get_player_view

Get the player's camera location and rotation during PIE.

```json
{"command": "get_player_view", "params": {}}
```

---

## 16. DSL Parsers

Arcwright includes **29 built-in DSL parsers** that convert domain-specific text formats into UE assets. Each parser understands a specific UE subsystem.

| Parser | What It Creates |
|---|---|
| `Blueprint` | Blueprint event graphs with nodes and connections |
| `BehaviorTree` (BT) | AI Behavior Trees with decorators and services |
| `DataTable` (DT) | Data Tables with rows and columns |
| `Widget` | UMG Widget Blueprints |
| `AnimBP` | Animation Blueprints with state machines |
| `Material` | Material graphs |
| `Dialogue` | Dialogue trees |
| `Quest` | Quest systems |
| `Sequence` | Level Sequences (cutscenes) |
| `GAS` | Gameplay Ability System |
| `Perception` | AI Perception configurations |
| `Physics` | Physics constraints and profiles |
| `Tags` | Gameplay tag hierarchies |
| `EnhancedInput` | Enhanced Input action/mapping contexts |
| `SmartObjects` | Smart Object definitions |
| `Sound` | Sound cue/mix configurations |
| `Replication` | Network replication rules |
| `ControlRig` | Control Rig setups |
| `StateTrees` | State Tree definitions |
| `Vehicles` | Vehicle configurations |
| `WorldPartition` | World Partition streaming rules |
| `Landscape` | Landscape layers and painting |
| `Foliage` | Foliage type definitions |
| `MassEntity` | Mass Entity configurations |
| `Shader` | Custom shader graphs |
| `ProcMesh` | Procedural mesh generation |
| `Paper2D` | 2D sprite and flipbook setups |
| `Composure` | Composure compositing setups |
| `DMX` | DMX lighting fixture configurations |

---

## 17. Sequencer

Create and control Level Sequences for cinematics.

### create_sequence

Create a new Level Sequence asset.

```json
{"command": "create_sequence", "params": {"name": "SEQ_Intro"}}
```

### add_sequence_track

Add an actor track to a sequence.

```json
{"command": "add_sequence_track", "params": {"sequence": "SEQ_Intro", "actor_label": "Camera_1", "track_type": "Transform"}}
```

### add_keyframe

Add a keyframe to a sequence track.

```json
{
  "command": "add_keyframe",
  "params": {
    "sequence": "SEQ_Intro",
    "actor_label": "Camera_1",
    "track_type": "Transform",
    "time": 0.0,
    "value": {"location": {"x": 0, "y": 0, "z": 300}, "rotation": {"pitch": -30, "yaw": 0, "roll": 0}}
  }
}
```

---

## 18. Splines and Post-Process

### create_spline

Create a spline actor in the level.

```json
{
  "command": "create_spline",
  "params": {
    "label": "PathSpline",
    "points": [
      {"x": 0, "y": 0, "z": 50},
      {"x": 500, "y": 200, "z": 50},
      {"x": 1000, "y": 0, "z": 50}
    ]
  }
}
```

### add_post_process_volume

Add a post-process volume to the level.

```json
{
  "command": "add_post_process_volume",
  "params": {
    "label": "PPV_Main",
    "infinite_extent": true,
    "settings": {
      "bloom_intensity": 1.0,
      "auto_exposure_min": 1.0,
      "auto_exposure_max": 1.0,
      "vignette_intensity": 0.3
    }
  }
}
```

---

## 19. Physics and Movement

### set_simulate_physics

Enable or disable physics simulation on a component.

```json
{"command": "set_simulate_physics", "params": {"actor_label": "Crate_1", "component_name": "Mesh", "simulate": true}}
```

### set_movement_defaults

Configure movement parameters on a pawn Blueprint.

```json
{
  "command": "set_movement_defaults",
  "params": {
    "blueprint": "BP_Enemy",
    "settings": {
      "max_speed": 600.0,
      "deceleration": 2000.0
    }
  }
}
```

---

## 20. Landscape and Foliage

### create_landscape

Create a landscape actor.

```json
{
  "command": "create_landscape",
  "params": {
    "section_size": 63,
    "sections_per_component": 1,
    "component_count_x": 4,
    "component_count_y": 4
  }
}
```

### create_foliage_type

Define a foliage type for painting.

```json
{"command": "create_foliage_type", "params": {"name": "FT_Grass", "mesh": "/Game/Environment/Grass_01"}}
```

### paint_foliage

Paint foliage instances in the level.

```json
{
  "command": "paint_foliage",
  "params": {
    "foliage_type": "FT_Grass",
    "center": {"x": 0, "y": 0, "z": 0},
    "radius": 2000,
    "density": 100
  }
}
```

---

## 21. Scene Setup and Lighting

### setup_scene_lighting

Set up complete scene lighting from a preset.

```json
{"command": "setup_scene_lighting", "params": {"preset": "outdoor_day"}}
```

Available presets: `indoor_dark`, `indoor_bright`, `outdoor_day`, `outdoor_night`.

### set_world_settings

Configure world-level settings.

```json
{
  "command": "set_world_settings",
  "params": {
    "gravity": -980,
    "game_mode": "BP_MyGameMode"
  }
}
```

---

## 22. Audio and Navigation

### create_nav_mesh_bounds

Create a NavMeshBoundsVolume for AI pathfinding.

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

## 23. Collision and Input

### set_collision_profile

Set the collision profile on a component.

```json
{"command": "set_collision_profile", "params": {"actor_label": "Wall_1", "component_name": "Mesh", "profile": "BlockAll"}}
```

---

## 24. Niagara

### add_niagara_component

Add a Niagara particle system component to a Blueprint.

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Torch",
    "component_type": "Niagara",
    "component_name": "FireFX",
    "properties": {
      "system_asset": "/Game/FX/NS_Fire"
    }
  }
}
```

---

## 25. Level Management and SaveGame

### create_sublevel

Create a new streaming sublevel.

```json
{"command": "create_sublevel", "params": {"name": "SubLevel_Interior"}}
```

---

## 26. Class Defaults and Properties

### set_class_defaults

Modify the Class Default Object (CDO) of a Blueprint. Affects all future instances.

```json
{
  "command": "set_class_defaults",
  "params": {
    "blueprint": "BP_Enemy",
    "properties": {
      "AIControllerClass": "/Game/Arcwright/Generated/BP_EnemyAI.BP_EnemyAI_C",
      "AutoPossessAI": "PlacedInWorldOrSpawned"
    }
  }
}
```

### reparent_blueprint

Change the parent class of a Blueprint.

```json
{"command": "reparent_blueprint", "params": {"name": "BP_Enemy", "new_parent": "Pawn"}}
```

---

## Color Format Reference

Arcwright supports multiple color formats in widget and material commands.

### hex: prefix (recommended for widgets)

Pass colors as `hex:#RRGGBB`. The plugin automatically converts sRGB hex to linear color space.

```json
{"value": "hex:#E8A624"}
{"value": "hex:#3DDC84"}
{"value": "hex:#FF0000"}
```

### srgb: prefix

Pass colors as sRGB float tuples. The plugin converts to linear.

```json
{"value": "srgb:(R=0.91,G=0.65,B=0.14,A=1.0)"}
```

### Raw linear values

Pass pre-converted linear float values directly.

```json
{"value": {"r": 0.807, "g": 0.381, "b": 0.018, "a": 1.0}}
```

---

## Common Mesh Asset Paths

| Shape | Path |
|---|---|
| Cube | `/Engine/BasicShapes/Cube.Cube` |
| Sphere | `/Engine/BasicShapes/Sphere.Sphere` |
| Cylinder | `/Engine/BasicShapes/Cylinder.Cylinder` |
| Cone | `/Engine/BasicShapes/Cone.Cone` |
| Plane | `/Engine/BasicShapes/Plane.Plane` |
