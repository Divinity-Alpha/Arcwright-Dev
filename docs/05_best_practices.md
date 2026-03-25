# Arcwright Best Practices

Essential rules and patterns for reliable Blueprint creation, widget building, and level population through Arcwright. Following these practices will prevent the most common issues.

---

## 1. Do Not Duplicate Default Event Nodes

When you call `create_blueprint`, Arcwright automatically creates three event nodes:

| Node ID | Event |
|---|---|
| `node_0` | Event BeginPlay |
| `node_1` | Event ActorBeginOverlap |
| `node_2` | Event Tick |

**Never recreate these events in `add_nodes_batch`.** Adding a duplicate `Event_BeginPlay` or `Event_ActorBeginOverlap` creates a node named "Event None" that will never fire. Instead, wire directly to the existing default nodes:

```json
{
  "command": "add_connections_batch",
  "params": {
    "blueprint": "BP_Pickup",
    "connections": [
      {"source_node": "node_1", "source_pin": "Then", "target_node": "print1", "target_pin": "execute"}
    ]
  }
}
```

Here `node_1` is the pre-existing ActorBeginOverlap event. No need to create it -- just wire to it.

---

## 2. Spawn Blueprint Actors with the Full Class Path

If a Blueprint has logic (overlap events, variables, custom events), always spawn it using the full `/Game/` class path:

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_Pickup.BP_Pickup_C",
    "label": "Pickup_1",
    "x": 0, "y": 0, "z": 100
  }
}
```

Do **not** use a short name like `"BP_Pickup"` or `"StaticMeshActor"` when you need Blueprint logic to run. Short names may resolve to a plain AActor, and none of your Blueprint event graphs will execute.

---

## 3. Use hex: Prefix for Widget Colors

When setting colors on widgets, always use the `hex:#RRGGBB` prefix. The plugin automatically converts sRGB hex values to the correct linear color space that UE expects:

```json
{"command": "set_widget_property", "params": {
    "widget_blueprint": "WBP_HUD",
    "widget_name": "ScoreText",
    "property_name": "color",
    "value": "hex:#E8A624"
}}
```

Do not pass raw sRGB float values as linear values -- the colors will look washed out. The `hex:` and `srgb:` prefixes handle the conversion automatically.

| Format | Example | Converts to Linear? |
|---|---|---|
| `hex:#RRGGBB` | `"hex:#E8A624"` | Yes (recommended) |
| `srgb:(R=,G=,B=,A=)` | `"srgb:(R=0.91,G=0.65,B=0.14,A=1.0)"` | Yes |
| Raw `{r,g,b,a}` object | `{"r": 0.807, "g": 0.381, "b": 0.018, "a": 1.0}` | No -- must already be linear |

---

## 4. Widget Design Size: 1920x1080

All widget blueprints should use 1920x1080 design size. This is the default when calling `create_widget_blueprint`. If you need to set or reset it explicitly:

```json
{"command": "set_widget_design_size", "params": {"widget_blueprint": "WBP_HUD", "width": 1920, "height": 1080}}
```

Design all positions and sizes in pixels relative to this 1920x1080 canvas.

---

## 5. Delete Before Re-Import

When recreating a Blueprint that already exists, delete the old one first. Overwriting an existing asset without deleting can crash the editor due to partially-loaded package conflicts:

```json
{"command": "delete_blueprint", "params": {"name": "BP_Pickup"}}
{"command": "create_blueprint", "params": {"name": "BP_Pickup", "parent_class": "Actor"}}
```

This applies to all asset types: Blueprints, Widget Blueprints, Behavior Trees, Data Tables, and Materials.

---

## 6. Compile After Adding Nodes

After adding nodes and connections to a Blueprint, always compile it:

```json
{"command": "add_nodes_batch", "params": {"blueprint": "BP_Pickup", "nodes": [...]}}
{"command": "add_connections_batch", "params": {"blueprint": "BP_Pickup", "connections": [...]}}
{"command": "compile_blueprint", "params": {"name": "BP_Pickup"}}
```

An uncompiled Blueprint will not execute any logic when spawned. The `compile_blueprint` command returns compilation status and any errors.

---

## 7. Apply Materials to Placed Actors, Not Blueprints

SCS `OverrideMaterials` set on a Blueprint asset do not reliably persist through the compile and spawn pipeline. Always use `set_actor_material` on placed actors instead of `apply_material` on the Blueprint:

```json
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Wall.BP_Wall_C", "label": "Wall_1", "x": 0, "y": 0, "z": 150}}
{"command": "set_actor_material", "params": {"actor_label": "Wall_1", "material_path": "/Game/Arcwright/Materials/MAT_Stone"}}
```

For multiple actors, use `batch_apply_material` for efficiency.

---

## 8. Use create_simple_material, Not create_material_instance

UE 5.4+ uses Substrate rendering, which does not expose `BaseColor` as a modifiable parameter on `BasicShapeMaterial` material instances. Use `create_simple_material` instead -- it creates a proper `UMaterial` with expression nodes that work under both Substrate and traditional rendering:

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_Red",
    "color": {"r": 1.0, "g": 0.0, "b": 0.0},
    "emissive": 0.0
  }
}
```

---

## 9. Re-Spawn Actors After Component Changes

Adding or removing components on a Blueprint updates the asset, but actors already placed in the level do not pick up the changes. Delete and re-spawn them:

```json
{"command": "delete_actor", "params": {"label": "Enemy_1"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Enemy.BP_Enemy_C", "label": "Enemy_1", "x": 1000, "y": 0, "z": 50}}
```

For bulk operations:

```json
{"command": "batch_delete_actors", "params": {"class_filter": "BP_Enemy"}}
```

Then re-run your spawn commands.

---

## 10. Overlap Events Require Collision Components

A Blueprint with `Event_ActorBeginOverlap` will never fire that event unless it has a collision component with `generate_overlap_events` set to true:

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Pickup",
    "component_type": "SphereCollision",
    "component_name": "PickupTrigger",
    "properties": {
      "radius": 100,
      "generate_overlap_events": true
    }
  }
}
```

This is the most common reason for "my Blueprint does not work" reports.

---

## 11. Save Frequently with save_all

Changes only exist in memory until saved. A UE crash loses everything. Call `save_all` after completing each logical step of your build:

```json
{"command": "save_all", "params": {}}
```

`save_all` handles World Partition external actor files automatically. The response includes an `external_actors_saved` count so you can verify actors were persisted.

---

## 12. Use Batch Commands for Efficiency

When performing the same operation on multiple targets, prefer batch commands over individual calls. They are faster and fault-tolerant -- a single failure does not abort the entire batch:

| Instead of | Use |
|---|---|
| Multiple `set_actor_material` calls | `batch_apply_material` |
| Multiple `delete_actor` calls | `batch_delete_actors` |
| Multiple `set_actor_transform` calls | `batch_move_actors` |

---

## 13. Protect Widget Layouts After Building

After constructing a widget hierarchy, call `protect_widget_layout` to lock the visual structure. Only widgets named with `txt_` or `Btn_` prefixes remain accessible from Blueprint/C++ code:

```json
{"command": "protect_widget_layout", "params": {"widget_blueprint": "WBP_GameHUD"}}
```

This prevents runtime code from accidentally modifying background panels, borders, or layout containers.

---

## 14. Use Pawn (Not Character) for Simple AI

For AI enemies that patrol and chase, use `Pawn` with `FloatingPawnMovement` as the parent class instead of `Character`. The `Character` class has a complex inherited component hierarchy that can conflict with components added via `add_component`. Reparent with:

```json
{"command": "reparent_blueprint", "params": {"name": "BP_Enemy", "new_parent": "Pawn"}}
```

---

## 15. Float Values in UE 5.4+

UE 5.4+ internally uses `Double` for float operations. Arcwright automatically remaps float functions (e.g., `Add_FloatFloat` becomes `Add_DoubleDouble`). Write your DSL and parameters using `Float` names -- the plugin translates them.

---

## Standard Build Order

When populating a level from scratch, follow this order to avoid issues:

1. **Scene lighting** -- `setup_scene_lighting`
2. **Ground plane** -- Spawn a floor mesh
3. **Blueprints** -- Create or import all Blueprints
4. **Components** -- Add collision, meshes, lights to Blueprints
5. **Compile** -- `compile_blueprint` for each
6. **Materials** -- `create_simple_material` for each
7. **Spawn actors** -- `spawn_actor_at` to place instances
8. **Apply materials** -- `set_actor_material` or `batch_apply_material`
9. **Widgets** -- Build UI last (it references game state)
10. **Save** -- `save_all`

---

## Quick Reference Card

| Rule | Summary |
|---|---|
| Default events | Wire to `node_0`/`node_1`/`node_2` -- do not recreate them |
| Spawn class path | Use `/Game/Arcwright/Generated/BP_Name.BP_Name_C` for Blueprint actors |
| Widget colors | Always use `hex:#RRGGBB` format |
| Widget size | Default 1920x1080 |
| Delete first | Delete existing assets before re-creating them |
| Compile | Always compile after adding nodes/connections |
| Materials on actors | Use `set_actor_material`, not `apply_material` |
| Material creation | Use `create_simple_material`, not `create_material_instance` |
| Re-spawn | Delete and re-spawn actors after changing their Blueprint's components |
| Overlap events | Require a collision component with `generate_overlap_events: true` |
| Save often | Call `save_all` after each build step |
| Protect widgets | Call `protect_widget_layout` after building widget hierarchy |
