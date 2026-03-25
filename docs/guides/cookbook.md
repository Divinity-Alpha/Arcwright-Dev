# Arcwright Example Prompts Cookbook

A collection of 50 tested prompts you can paste directly into Claude Desktop, Cursor, or any AI assistant connected to Arcwright via MCP or TCP. Each prompt is written in natural language -- your AI assistant reads it, decides which Arcwright commands to call, and executes them inside Unreal Engine 5.

These prompts assume you have a UE5 project open with the Arcwright plugin loaded and your AI assistant connected. If you need setup help, see the [Claude Desktop Setup](setup_claude_desktop.md) or [Cursor Setup](setup_cursor.md) guide.

---

## Level Setup (5 prompts)

### 1. Dark indoor FPS level

```
Set up an FPS game with dark indoor lighting and a stone floor. Use the first-person game mode.
```

*Behind the scenes: `setup_scene_lighting(preset="indoor_dark")` + `spawn_actor_at` (Plane mesh, large scale) + `create_simple_material` (stone color) + `set_actor_material` + `set_game_mode("BP_FirstPersonGameMode")` + `save_all`*

### 2. Outdoor environment

```
Add bright outdoor lighting with atmosphere and exponential height fog to my level.
```

*Behind the scenes: `setup_scene_lighting(preset="outdoor_day")` -- creates DirectionalLight, SkyLight, SkyAtmosphere, and ExponentialHeightFog in one call*

### 3. Large floor with material

```
Create a large floor 100 meters by 100 meters with a concrete material.
```

*Behind the scenes: `spawn_actor_at` (StaticMeshActor with Plane mesh, scale 100,100,1) + `create_simple_material` (concrete gray) + `set_actor_material`*

### 4. Cinematic post-processing

```
Add cinematic post-processing to my level with strong bloom, subtle vignette, and warm color grading.
```

*Behind the scenes: `add_post_process_volume` (infinite extent) + `set_post_process_settings` (bloom_intensity, vignette_intensity, color_saturation, color_contrast)*

### 5. Set the game mode

```
Set up the game mode for first-person controls.
```

*Behind the scenes: `set_game_mode("BP_FirstPersonGameMode")`*

---

## Create Game Objects (10 prompts)

### 6. Health pickup

```
Create a health pickup called BP_HealthPickup that prints "Healed 25 HP!" on overlap and then destroys itself.
```

*Behind the scenes: `create_blueprint("BP_HealthPickup")` + `add_nodes_batch` (Event_ActorBeginOverlap, PrintString, DestroyActor) + `add_connections_batch`*

### 7. Gold coin

```
Create a gold coin Blueprint called BP_GoldCoin worth 10 points that prints "Collected! +10" and destroys itself when picked up.
```

*Behind the scenes: `create_blueprint` with variables (PointValue: Int = 10) + overlap event nodes + PrintString + DestroyActor*

### 8. Damage zone

```
Create a damage zone called BP_LavaFloor that prints "Ouch! -10 HP" when the player walks over it.
```

*Behind the scenes: `create_blueprint("BP_LavaFloor")` + `add_nodes_batch` (Event_ActorBeginOverlap, PrintString) + `add_connections_batch`*

### 9. Teleporter

```
Create a teleporter Blueprint called BP_Teleporter that prints "Teleporting!" when the player overlaps it.
```

*Behind the scenes: `create_blueprint` + `add_nodes_batch` (Event_ActorBeginOverlap, PrintString) + `add_connections_batch`*

### 10. Locked door

```
Create a locked door Blueprint called BP_LockedDoor with a boolean variable IsLocked that starts as true. On overlap, check if the door is locked. If locked, print "Door is locked!". If unlocked, print "Door opens!".
```

*Behind the scenes: `create_blueprint` with variable (IsLocked: Bool = true) + `add_nodes_batch` (Event_ActorBeginOverlap, VariableGet, Branch, two PrintStrings) + `add_connections_batch`*

### 11. Wave spawner

```
Create a wave spawner Blueprint called BP_WaveSpawner that prints "Wave starting!" on BeginPlay and has an integer variable WaveNumber starting at 1.
```

*Behind the scenes: `create_blueprint` with variable (WaveNumber: Int = 1) + `add_nodes_batch` (Event_BeginPlay, PrintString) + `add_connections_batch`*

### 12. Checkpoint

```
Create a checkpoint Blueprint called BP_Checkpoint that prints "Checkpoint reached!" when the player overlaps it.
```

*Behind the scenes: `create_blueprint` + `add_nodes_batch` (Event_ActorBeginOverlap, PrintString) + `add_connections_batch`*

### 13. Moving platform

```
Create a moving platform Blueprint called BP_MovingPlatform with parent class Pawn. Add a static mesh component and a floating pawn movement component.
```

*Behind the scenes: `create_blueprint("BP_MovingPlatform", parent_class="Pawn")` + `add_component("StaticMesh")` + `add_component("FloatingPawnMovement")`*

### 14. Treasure chest

```
Create a treasure chest Blueprint called BP_TreasureChest with variables Gold (Int, default 50) and IsOpened (Bool, default false).
```

*Behind the scenes: `create_blueprint("BP_TreasureChest", variables=[{name:"Gold", type:"Int", default:"50"}, {name:"IsOpened", type:"Bool", default:"false"}])`*

### 15. Explosive barrel

```
Create an explosive barrel called BP_ExplosiveBarrel with a variable ExplosionRadius (Float, default 500). When it takes any damage, print "BOOM!" to the screen.
```

*Behind the scenes: `create_blueprint` with variable + `add_nodes_batch` (Event_AnyDamage, PrintString) + `add_connections_batch`*

---

## Modify Level (10 prompts)

### 16. Batch set variable

```
Set the Health variable to 200 on all enemy Blueprints in the project.
```

*Behind the scenes: `find_blueprints(name_filter="Enemy")` to discover targets, then `batch_set_variable` with operations for each Blueprint*

### 17. Batch apply material

```
Apply a red brick material to all actors labeled "Wall" in the level.
```

*Behind the scenes: `create_simple_material("MAT_RedBrick", color={r:0.6, g:0.2, b:0.15})` + `find_actors(name_filter="Wall")` + `set_actor_material` on each*

### 18. Delete by class

```
Delete all gold coins from the level.
```

*Behind the scenes: `batch_delete_actors(class_filter="BP_GoldCoin")`*

### 19. Scale enemies

```
Scale all enemies up by 1.5x.
```

*Behind the scenes: `batch_scale_actors(scale={x:1.5, y:1.5, z:1.5}, class_filter="Enemy", mode="multiply")`*

### 20. Spawn in a circle

```
Spawn 8 enemies in a circle with radius 1000 centered at the origin.
```

*Behind the scenes: `spawn_actor_circle(class="BP_Enemy", count=8, radius=1000, center={x:0, y:0, z:50}, face_center=true)`*

### 21. Move actors up

```
Move all health pickups up by 100 units so they float above the ground.
```

*Behind the scenes: `batch_move_actors(offset={x:0, y:0, z:100}, class_filter="BP_HealthPickup", mode="relative")`*

### 22. Add collision component

```
Add a sphere collision component with radius 64 to BP_GoldCoin.
```

*Behind the scenes: `add_component(blueprint="BP_GoldCoin", component_type="SphereCollision", properties={radius: 64, generate_overlap_events: true})`*

### 23. Replace material everywhere

```
Replace all stone materials with brick material across the entire level.
```

*Behind the scenes: `batch_replace_material(old_material="/Game/Arcwright/Materials/MAT_Stone", new_material="/Game/Arcwright/Materials/MAT_Brick")`*

### 24. Spawn a grid of items

```
Spawn a 5x5 grid of coins with 200-unit spacing starting at position (-400, -400, 50).
```

*Behind the scenes: `spawn_actor_grid(class="BP_GoldCoin", rows=5, cols=5, spacing_x=200, spacing_y=200, origin={x:-400, y:-400, z:50})`*

### 25. Add a light component

```
Add a point light component to BP_Torch with warm yellow color and 500 intensity.
```

*Behind the scenes: `add_component(blueprint="BP_Torch", component_type="PointLight", properties={light_color:{r:1.0, g:0.8, b:0.3}, intensity:500})`*

---

## Query (5 prompts)

### 26. Level summary

```
What's in my level right now? Give me a summary of all actors by type.
```

*Behind the scenes: `audit_level` or `get_level_info` + `find_actors` -- returns categorized actor counts and locations*

### 27. Find enemies

```
How many enemies are in the scene and where are they located?
```

*Behind the scenes: `find_actors(class_filter="Enemy")` -- returns list with transforms*

### 28. List Blueprints

```
List all Blueprints I've created in this project.
```

*Behind the scenes: `find_blueprints` or `list_available_blueprints` -- returns names, parent classes, variable/component info*

### 29. Blueprint details

```
Show me the details of BP_Enemy -- what variables, components, and node graph does it have?
```

*Behind the scenes: `get_blueprint_details("BP_Enemy")` -- returns variables, components, nodes, connections, compile status*

### 30. Available materials

```
What materials are available in the project right now?
```

*Behind the scenes: `list_available_materials` -- returns all material assets with paths*

---

## Complex Builds (10 prompts)

### 31. Full arena

```
Build a complete arena: stone floor 50x50 meters, brick walls on all 4 sides each 50 meters long and 5 meters tall, dark indoor lighting, and save everything.
```

*Behind the scenes: `create_arena_layout` or manual sequence of `setup_scene_lighting` + `spawn_actor_at` (floor + 4 walls) + `create_simple_material` (stone, brick) + `set_actor_material` on each + `save_all`*

### 32. Patrol enemy with spawns

```
Create a patrol enemy with 200 health and 25 damage using a Pawn with floating movement, then spawn 3 of them in a line from (-1000,0,50) to (1000,0,50).
```

*Behind the scenes: `create_blueprint("BP_PatrolEnemy", parent_class="Pawn")` + `add_component(FloatingPawnMovement)` + `modify_blueprint` (add Health/Damage variables) + `spawn_actor_line(count=3, start=..., end=...)`*

### 33. Scatter collectibles

```
Create a health pickup and a score coin, then scatter 10 of each randomly around the arena within 2000 units of center.
```

*Behind the scenes: 2x `create_blueprint` + `scatter_actors` or 2x `spawn_actor_circle` with different radii*

### 34. Game HUD

```
Build a game HUD widget with a health bar in the top-left corner and a score counter in the top-right corner.
```

*Behind the scenes: `create_game_hud` or `create_widget_blueprint("WBP_GameHUD")` + `add_widget_child` (CanvasPanel, ProgressBar, TextBlock) + `set_widget_property` (anchors, position, text, colors)*

### 35. Weapons data table

```
Create a weapons data table with columns Name (String), Damage (Float), FireRate (Float), MaxAmmo (Int), and IsAutomatic (Boolean). Add rows for Pistol (25 dmg, 2.0 rate, 12 ammo, not auto), Rifle (15 dmg, 8.0 rate, 30 ammo, auto), and Shotgun (80 dmg, 0.8 rate, 8 ammo, not auto).
```

*Behind the scenes: `create_data_table` -- parses the description into DT DSL, creates UUserDefinedStruct + UDataTable with all columns and rows*

### 36. Cinematic camera sequence

```
Spawn a camera at position (0, 0, 500) looking down. Create a 5-second level sequence that moves it down to (0, 0, 100). Add a bloom post-process volume.
```

*Behind the scenes: `spawn_actor_at` (CameraActor) + `create_sequence` (5s duration) + `add_sequence_track` (Transform) + `add_keyframe` (t=0 and t=5) + `add_post_process_volume` + `set_post_process_settings`*

### 37. Spline path loop

```
Create a closed spline path that goes through (-1000,0,0), (0,1000,0), (1000,0,0), and (0,-1000,0).
```

*Behind the scenes: `create_spline_actor(initial_points=[...], closed=true)`*

### 38. Complete game level

```
Set up a complete game level: first-person controls, dark indoor lighting, stone floor, 4 brick walls forming a 40x40 meter room, 20 gold coins in a 4x5 grid, 4 health pickups in the corners, 6 enemies in a circle in the center, and a HUD with health and score. Save everything when done.
```

*Behind the scenes: 15-20 chained commands -- `set_game_mode` + `setup_scene_lighting` + `spawn_actor_at` (floor, walls) + `create_blueprint` (coin, pickup, enemy) + `spawn_actor_grid` (coins) + `spawn_actor_at` (pickups at corners) + `spawn_actor_circle` (enemies) + `create_game_hud` + `save_all`*

### 39. Import mesh and spawn

```
Import the mesh from C:/Models/crystal.fbx, create a glowing blue material for it, make a Blueprint with that mesh and material, then spawn 6 of them in a circle with radius 500.
```

*Behind the scenes: `import_static_mesh` + `create_simple_material` (blue + emissive) + `create_blueprint` + `add_component` (StaticMesh) + `apply_material` + `spawn_actor_circle(count=6, radius=500)`*

### 40. Compare two Blueprints

```
Compare BP_Enemy and BP_BossEnemy -- what variables, components, and nodes are different between them?
```

*Behind the scenes: `compare_blueprints("BP_Enemy", "BP_BossEnemy")` -- returns a diff of variables, components, and node graphs*

---

## AI and Behavior Trees (5 prompts)

### 41. Patrol loop

```
Create a patrol behavior tree where an enemy moves to a patrol point, waits 3 seconds, then moves to another patrol point. Loop forever.
```

*Behind the scenes: `create_behavior_tree` -- generates BT DSL with Selector root, Sequence child, MoveTo + Wait tasks, Loop decorator*

### 42. Chase and patrol

```
Create a chase-and-patrol AI: when the player is within 800 units, chase them. Otherwise, patrol between two points with a 2-second wait at each.
```

*Behind the scenes: `create_behavior_tree` -- Selector with Chase sequence (BlackboardBased decorator checking TargetActor, MoveTo) and Patrol sequence (MoveTo, Wait, MoveTo, Wait)*

### 43. Wire AI to pawn

```
Set up BP_Enemy to use the BT_Patrol behavior tree with an AI controller.
```

*Behind the scenes: `setup_ai_for_pawn(pawn_name="BP_Enemy", behavior_tree="BT_Patrol")` -- creates AIController BP with RunBehaviorTree on BeginPlay, wires it to the pawn*

### 44. Guard NPC

```
Create a guard NPC behavior tree where the guard stands still and continuously rotates to face the player.
```

*Behind the scenes: `create_behavior_tree` -- simple tree with RotateToFaceBBEntry task and DefaultFocus service tracking the player*

### 45. Turret AI

```
Create a turret behavior tree: if the player is within 1500 units (check via blackboard), rotate to face them and print "Firing!". Otherwise, do nothing.
```

*Behind the scenes: `create_behavior_tree` -- Selector with attack Sequence (BlackboardBased decorator on TargetActor, RotateToFaceBBEntry, Wait) and idle Wait fallback*

---

## Data Tables (5 prompts)

### 46. Weapons table

```
Create a weapons data table called DT_Weapons with columns Name (String), Damage (Float), FireRate (Float), AmmoCapacity (Int), and WeaponType (String). Add rows: Pistol (25, 2.0, 12, Sidearm), Rifle (15, 8.0, 30, Primary), Shotgun (80, 0.8, 8, Primary).
```

*Behind the scenes: `create_data_table` -- DT DSL parsed into UUserDefinedStruct + UDataTable with 5 columns and 3 rows*

### 47. Enemy stats table

```
Create an enemy stats table called DT_EnemyStats with EnemyName (String), Health (Float), Damage (Float), MoveSpeed (Float), and XPReward (Int). Add: Grunt (100, 10, 300, 50), Scout (75, 15, 500, 75), Tank (300, 25, 150, 150).
```

*Behind the scenes: `create_data_table` -- creates struct with 5 columns, populates 3 rows*

### 48. Loot table

```
Create a loot table called DT_LootDrops with columns ItemName (String), DropChance (Float), Rarity (String), and GoldValue (Int). Leave it empty for now -- I'll add rows later.
```

*Behind the scenes: `create_data_table` -- creates struct + empty table with 4 columns*

### 49. Add a row

```
Add a new row to DT_Weapons: Sniper with 120 damage, 0.5 fire rate, 5 ammo capacity, type Marksman.
```

*Behind the scenes: `add_data_table_row(table_name="DT_Weapons", row_name="Sniper", values={Name:"Sniper", Damage:120.0, FireRate:0.5, AmmoCapacity:5, WeaponType:"Marksman"})`*

### 50. Read table contents

```
Show me all the rows in the enemy stats table.
```

*Behind the scenes: `get_data_table_rows("DT_EnemyStats")` -- returns all rows with column values*

---

## Tips for Better Prompts

**Be specific with names.** "Create BP_HealthPickup" gives the AI an exact asset name to use. "Make a health thing" forces it to guess.

**Include values.** "Heals 25 HP" is actionable. "Heals the player" leaves the number up to the AI.

**Reference existing assets.** "Apply the gold material to BP_Coin" works when the material already exists. The AI will check what is available before creating duplicates.

**Chain naturally.** Create objects first, then spawn them, then apply materials. This matches the order the commands need to execute.

**Ask for status.** "What's in my level?" or "List all Blueprints" helps you understand what exists before planning next steps.

**Save often.** End complex multi-step builds with "and save everything" to make sure nothing is lost.

**Start simple.** Build one object, verify it works, then ask for more. Complex prompts with 10+ objects work, but iterating on smaller pieces gives you more control.

**Use specific numbers for layouts.** "5x5 grid with 200-unit spacing" and "circle of 8 with radius 1000" give the AI exact parameters. Vague spatial descriptions like "spread them around" produce less predictable results.
