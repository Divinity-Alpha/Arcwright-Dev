# Cookbook: Level Building

Build a complete game level from scratch using Arcwright commands. This guide follows the standard level setup order and produces a playable FPS level with lighting, terrain, walls, collectibles, hazards, a HUD, and a game mode.

---

## Standard Level Setup Order

Every level population script should follow this order:

1. Scene lighting
2. Floor / ground plane
3. Game Blueprints (import or create)
4. Components on Blueprints
5. Materials
6. Spawn actors into the level
7. Apply materials to placed actors
8. UI (Widget Blueprints)
9. Game mode
10. Save

---

## Step 1: Scene Lighting

Levels built from scratch have no ambient lighting. Always add scene lighting first.

```json
{"command": "setup_scene_lighting", "params": {"preset": "outdoor_day"}}
```

Available presets:

| Preset | Description |
|---|---|
| `indoor_dark` | Dim interior with minimal ambient. |
| `indoor_bright` | Well-lit interior with strong sky light. |
| `outdoor_day` | Full sun, blue sky, atmosphere, height fog. |
| `outdoor_night` | Moonlight with dark atmosphere. |

You can also override individual parameters:

```json
{
  "command": "setup_scene_lighting",
  "params": {
    "preset": "outdoor_day",
    "sun_intensity": 8.0,
    "sun_rotation": {"pitch": -45, "yaw": 160, "roll": 0}
  }
}
```

---

## Step 2: Floor / Ground Plane

Without a floor, the player falls through the void. Spawn a large plane:

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "StaticMeshActor",
    "location": {"x": 0, "y": 0, "z": 0},
    "scale": {"x": 100, "y": 100, "z": 1},
    "label": "Floor"
  }
}
```

The `StaticMeshActor` uses the default plane mesh. Create and apply a floor material:

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_Floor",
    "color": {"r": 0.3, "g": 0.3, "b": 0.35}
  }
}
```

```json
{
  "command": "set_actor_material",
  "params": {
    "actor_label": "Floor",
    "material_path": "/Game/Arcwright/Materials/MAT_Floor"
  }
}
```

---

## Step 3: Create Wall Blueprints

Create a reusable wall Blueprint with a box mesh and collision:

```json
{
  "command": "modify_blueprint",
  "params": {
    "name": "BP_Wall",
    "add_variables": []
  }
}
```

If the Blueprint does not exist, import a minimal IR file first, or create it through `import_from_ir`. Then add components:

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Wall",
    "component_type": "StaticMesh",
    "component_name": "WallMesh",
    "properties": {
      "mesh": "/Engine/BasicShapes/Cube.Cube",
      "scale": {"x": 5.0, "y": 0.2, "z": 3.0}
    }
  }
}
```

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Wall",
    "component_type": "BoxCollision",
    "component_name": "WallCollision",
    "properties": {
      "extent": {"x": 250, "y": 10, "z": 150}
    }
  }
}
```

Create a wall material:

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_Wall",
    "color": {"r": 0.6, "g": 0.55, "b": 0.5}
  }
}
```

---

## Step 4: Spawn Walls to Form a Room

```json
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Wall.BP_Wall", "location": {"x": 0, "y": -1000, "z": 150}, "label": "Wall_North"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Wall.BP_Wall", "location": {"x": 0, "y": 1000, "z": 150}, "label": "Wall_South"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Wall.BP_Wall", "location": {"x": -1000, "y": 0, "z": 150}, "rotation": {"pitch": 0, "yaw": 90, "roll": 0}, "label": "Wall_West"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Wall.BP_Wall", "location": {"x": 1000, "y": 0, "z": 150}, "rotation": {"pitch": 0, "yaw": 90, "roll": 0}, "label": "Wall_East"}}
```

Apply materials to all walls at once using a batch command:

```json
{
  "command": "batch_apply_material",
  "params": {
    "operations": [
      {"actor_label": "Wall_North", "material_path": "/Game/Arcwright/Materials/MAT_Wall"},
      {"actor_label": "Wall_South", "material_path": "/Game/Arcwright/Materials/MAT_Wall"},
      {"actor_label": "Wall_West", "material_path": "/Game/Arcwright/Materials/MAT_Wall"},
      {"actor_label": "Wall_East", "material_path": "/Game/Arcwright/Materials/MAT_Wall"}
    ]
  }
}
```

---

## Step 5: Create Collectible Blueprints

Create a coin pickup that prints "Collected!" when the player overlaps:

```json
{"command": "import_from_ir", "params": {"path": "C:/project/test_ir/BP_Coin.blueprint.json"}}
```

Add components:

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Coin",
    "component_type": "SphereCollision",
    "component_name": "CoinTrigger",
    "properties": {"radius": 80, "generate_overlap_events": true}
  }
}
```

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_Coin",
    "component_type": "StaticMesh",
    "component_name": "CoinMesh",
    "properties": {"mesh": "/Engine/BasicShapes/Cylinder.Cylinder", "scale": {"x": 0.5, "y": 0.5, "z": 0.05}}
  }
}
```

Create a gold material and spawn coins:

```json
{
  "command": "create_simple_material",
  "params": {"name": "MAT_Gold", "color": {"r": 1.0, "g": 0.84, "b": 0.0}, "emissive": 0.3}
}
```

```json
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Coin.BP_Coin", "location": {"x": 300, "y": 300, "z": 30}, "label": "Coin_1"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Coin.BP_Coin", "location": {"x": -300, "y": 400, "z": 30}, "label": "Coin_2"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Coin.BP_Coin", "location": {"x": 500, "y": -200, "z": 30}, "label": "Coin_3"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Coin.BP_Coin", "location": {"x": -400, "y": -500, "z": 30}, "label": "Coin_4"}}
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_Coin.BP_Coin", "location": {"x": 0, "y": 0, "z": 30}, "label": "Coin_5"}}
```

Apply gold material to all coins:

```json
{
  "command": "batch_apply_material",
  "params": {
    "operations": [
      {"actor_label": "Coin_1", "material_path": "/Game/Arcwright/Materials/MAT_Gold"},
      {"actor_label": "Coin_2", "material_path": "/Game/Arcwright/Materials/MAT_Gold"},
      {"actor_label": "Coin_3", "material_path": "/Game/Arcwright/Materials/MAT_Gold"},
      {"actor_label": "Coin_4", "material_path": "/Game/Arcwright/Materials/MAT_Gold"},
      {"actor_label": "Coin_5", "material_path": "/Game/Arcwright/Materials/MAT_Gold"}
    ]
  }
}
```

---

## Step 6: Create a Hazard Zone

Create a damage zone that hurts the player on overlap:

```json
{"command": "import_from_ir", "params": {"path": "C:/project/test_ir/BP_DamageZone.blueprint.json"}}
```

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_DamageZone",
    "component_type": "BoxCollision",
    "component_name": "DamageArea",
    "properties": {"extent": {"x": 200, "y": 200, "z": 20}, "generate_overlap_events": true}
  }
}
```

```json
{
  "command": "create_simple_material",
  "params": {"name": "MAT_Danger", "color": {"r": 0.9, "g": 0.1, "b": 0.1}, "emissive": 1.0}
}
```

```json
{"command": "spawn_actor_at", "params": {"class": "/Game/Arcwright/Generated/BP_DamageZone.BP_DamageZone", "location": {"x": 700, "y": 0, "z": 5}, "label": "HazardZone_1"}}
```

```json
{"command": "set_actor_material", "params": {"actor_label": "HazardZone_1", "material_path": "/Game/Arcwright/Materials/MAT_Danger"}}
```

---

## Step 7: Create a HUD Widget

```json
{"command": "create_widget_blueprint", "params": {"name": "WBP_GameHUD"}}
```

Add a root canvas panel:

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_GameHUD", "widget_type": "CanvasPanel", "widget_name": "RootPanel"}}
```

Add score text:

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_GameHUD", "widget_type": "TextBlock", "widget_name": "ScoreText", "parent_name": "RootPanel"}}
```

```json
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property_name": "text", "value": "Score: 0"}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property_name": "font_size", "value": 24}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property_name": "color", "value": {"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "ScoreText", "property_name": "position", "value": {"x": 20, "y": 20}}}
```

Add a health bar:

```json
{"command": "add_widget_child", "params": {"widget_blueprint": "WBP_GameHUD", "widget_type": "ProgressBar", "widget_name": "HealthBar", "parent_name": "RootPanel"}}
```

```json
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "HealthBar", "property_name": "percent", "value": 1.0}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "HealthBar", "property_name": "fill_color", "value": {"r": 0.0, "g": 0.8, "b": 0.2, "a": 1.0}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "HealthBar", "property_name": "position", "value": {"x": 20, "y": 60}}}
{"command": "set_widget_property", "params": {"widget_blueprint": "WBP_GameHUD", "widget_name": "HealthBar", "property_name": "size", "value": {"x": 300, "y": 30}}}
```

Verify the widget tree:

```json
{"command": "get_widget_tree", "params": {"widget_blueprint": "WBP_GameHUD"}}
```

---

## Step 8: Set Game Mode

If you have set up a game base (FPS, third person, etc.), set the game mode for this level:

```json
{"command": "set_game_mode", "params": {"game_mode": "BP_FirstPersonGameMode"}}
```

---

## Step 9: Add Post-Process Effects (Optional)

Add a subtle visual polish pass:

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

## Step 10: Save Everything

```json
{"command": "save_all", "params": {}}
```

---

## Verify the Level

Query the full actor list:

```json
{"command": "get_actors", "params": {}}
```

Query specific asset types:

```json
{"command": "find_assets", "params": {"type": "Material", "name_filter": "MAT_"}}
{"command": "find_blueprints", "params": {"name_filter": "BP_"}}
```

Get level summary:

```json
{"command": "get_level_info", "params": {}}
```

---

## Tips

### Material Application Order

Always apply materials to placed actors AFTER spawning them. Use `set_actor_material` (not `apply_material`) for reliable results on spawned instances.

### Batch Operations

When placing many actors of the same type or applying the same material to multiple actors, use batch commands (`batch_apply_material`, `batch_set_property`, `batch_delete_actors`) instead of individual calls. They are fault-tolerant -- individual failures do not abort the batch.

### Re-Spawning After Component Changes

If you add or change components on a Blueprint after actors have been spawned, the existing actors do not automatically update. You must delete and re-spawn them:

```json
{"command": "batch_delete_actors", "params": {"class_filter": "BP_Coin"}}
```

Then re-run the spawn commands.

### Replacing Materials Globally

To swap all instances of one material for another across the entire level:

```json
{
  "command": "batch_replace_material",
  "params": {
    "old_material": "/Game/Arcwright/Materials/MAT_Gray",
    "new_material": "/Game/Arcwright/Materials/MAT_Concrete"
  }
}
```

---

## Next Steps

- Add enemies using the [Enemy AI System cookbook](cookbook-enemy-system.md).
- Create cinematic intros with `create_sequence`, `add_sequence_track`, and `add_keyframe`.
- Add foliage with `create_foliage_type` and `paint_foliage` for outdoor levels.
- See the [Command Reference](command-reference.md) for the full command list.
