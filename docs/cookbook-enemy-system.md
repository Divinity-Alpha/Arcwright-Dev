# Cookbook: Enemy AI System

Build a complete enemy AI system from scratch: an enemy pawn with mesh and collision, a patrol behavior tree, an AI controller, and spawned patrol enemies in the level.

This guide shows the exact TCP command sequence. All commands can be sent through MCP tools or directly via TCP.

---

## What We Will Build

1. **BP_PatrolEnemy** -- A Pawn Blueprint with mesh, collision, and a floating movement component.
2. **BT_EnemyPatrol** -- A Behavior Tree that patrols between points and chases when a target is detected.
3. **BP_EnemyAIController** -- An AI Controller wired to run the behavior tree on BeginPlay.
4. Three patrol enemies placed in the level.

---

## Step 1: Create the Enemy Pawn Blueprint

First, create a simple Blueprint from IR or use `modify_blueprint` to set it up:

```json
{"command": "import_from_ir", "params": {"path": "C:/project/test_ir/BP_PatrolEnemy.blueprint.json"}}
```

Or build it incrementally:

```json
{
  "command": "modify_blueprint",
  "params": {
    "name": "BP_PatrolEnemy",
    "add_variables": [
      {"name": "Health", "type": "Float", "default": "100.0"},
      {"name": "MoveSpeed", "type": "Float", "default": "300.0"},
      {"name": "DetectionRange", "type": "Float", "default": "1500.0"}
    ]
  }
}
```

**Note:** If the Blueprint does not exist yet, create it first using `import_from_ir` with a minimal IR file. The `modify_blueprint` command works on existing Blueprints only.

---

## Step 2: Add Components

Add a collision sphere, a static mesh for the body, and a point light for visual effect:

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_PatrolEnemy",
    "component_type": "CapsuleCollision",
    "component_name": "EnemyCollision",
    "properties": {
      "radius": 42.0,
      "half_height": 96.0,
      "generate_overlap_events": true
    }
  }
}
```

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_PatrolEnemy",
    "component_type": "StaticMesh",
    "component_name": "EnemyMesh",
    "properties": {
      "mesh": "/Engine/BasicShapes/Cone.Cone",
      "location": {"x": 0, "y": 0, "z": -90}
    }
  }
}
```

```json
{
  "command": "add_component",
  "params": {
    "blueprint": "BP_PatrolEnemy",
    "component_type": "PointLight",
    "component_name": "EyeGlow",
    "properties": {
      "intensity": 5000.0,
      "light_color": {"r": 1.0, "g": 0.0, "b": 0.0},
      "attenuation_radius": 200.0,
      "location": {"x": 0, "y": 0, "z": 60}
    }
  }
}
```

---

## Step 3: Reparent to Pawn (if needed)

For simple AI enemies, use Pawn (not Character) to avoid the complex inherited component hierarchy:

```json
{"command": "reparent_blueprint", "params": {"name": "BP_PatrolEnemy", "new_parent": "Pawn"}}
```

Then set movement defaults for FloatingPawnMovement:

```json
{
  "command": "set_movement_defaults",
  "params": {
    "blueprint": "BP_PatrolEnemy",
    "settings": {
      "max_speed": 400.0,
      "deceleration": 1000.0
    }
  }
}
```

---

## Step 4: Create the Behavior Tree

Create a patrol behavior tree that:
- Chases a target actor if one is detected (Blackboard key `TargetActor` is set)
- Otherwise patrols to a random location and waits

```json
{
  "command": "create_behavior_tree",
  "params": {
    "ir_json": "{\"name\": \"BT_EnemyPatrol\", \"blackboard_name\": \"BB_EnemyPatrol\", \"blackboard_keys\": [{\"name\": \"TargetActor\", \"type\": \"Object\"}, {\"name\": \"PatrolLocation\", \"type\": \"Vector\"}], \"root\": {\"type\": \"Selector\", \"name\": \"Root\", \"children\": [{\"type\": \"Sequence\", \"name\": \"Chase\", \"decorators\": [{\"type\": \"BlackboardBased\", \"params\": {\"Key\": \"TargetActor\", \"Condition\": \"IsSet\", \"AbortMode\": \"LowerPriority\"}}], \"children\": [{\"type\": \"MoveTo\", \"name\": \"MoveToTarget\", \"params\": {\"Key\": \"TargetActor\", \"AcceptableRadius\": \"200\"}}]}, {\"type\": \"Sequence\", \"name\": \"Patrol\", \"children\": [{\"type\": \"MoveTo\", \"name\": \"MoveToPatrol\", \"params\": {\"Key\": \"PatrolLocation\", \"AcceptableRadius\": \"50\"}}, {\"type\": \"Wait\", \"name\": \"WaitAtPoint\", \"params\": {\"Duration\": \"3.0\"}}]}]}}"
  }
}
```

Verify the BT was created:

```json
{"command": "get_behavior_tree_info", "params": {"name": "BT_EnemyPatrol"}}
```

---

## Step 5: Wire AI Controller with setup_ai_for_pawn

This single command creates an AI Controller Blueprint, wires `RunBehaviorTree` to its BeginPlay, and sets `AIControllerClass` + `AutoPossessAI` on the pawn:

```json
{
  "command": "setup_ai_for_pawn",
  "params": {
    "pawn_name": "BP_PatrolEnemy",
    "behavior_tree": "BT_EnemyPatrol",
    "controller_name": "BP_EnemyAIController"
  }
}
```

This replaces what would otherwise be a 5-step manual process:
1. Create AIController Blueprint
2. Add RunBehaviorTree node wired to BeginPlay
3. Set the BT asset on the RunBehaviorTree node
4. Set `AIControllerClass` on the pawn CDO
5. Set `AutoPossessAI` to `PlacedInWorldOrSpawned`

---

## Step 6: Create a Material for the Enemy

```json
{
  "command": "create_simple_material",
  "params": {
    "name": "MAT_Enemy",
    "color": {"r": 0.8, "g": 0.1, "b": 0.1},
    "emissive": 0.2
  }
}
```

---

## Step 7: Spawn Enemies at Patrol Points

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_PatrolEnemy.BP_PatrolEnemy",
    "location": {"x": 1000, "y": 0, "z": 50},
    "label": "Enemy_1"
  }
}
```

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_PatrolEnemy.BP_PatrolEnemy",
    "location": {"x": -500, "y": 800, "z": 50},
    "label": "Enemy_2"
  }
}
```

```json
{
  "command": "spawn_actor_at",
  "params": {
    "class": "/Game/Arcwright/Generated/BP_PatrolEnemy.BP_PatrolEnemy",
    "location": {"x": 200, "y": -600, "z": 50},
    "label": "Enemy_3"
  }
}
```

Apply the material to each placed enemy:

```json
{"command": "set_actor_material", "params": {"actor_label": "Enemy_1", "material_path": "/Game/Arcwright/Materials/MAT_Enemy"}}
{"command": "set_actor_material", "params": {"actor_label": "Enemy_2", "material_path": "/Game/Arcwright/Materials/MAT_Enemy"}}
{"command": "set_actor_material", "params": {"actor_label": "Enemy_3", "material_path": "/Game/Arcwright/Materials/MAT_Enemy"}}
```

---

## Step 8: Save

```json
{"command": "save_all", "params": {}}
```

---

## Verify the Result

Check that all enemies are placed:

```json
{"command": "find_actors", "params": {"class_filter": "PatrolEnemy"}}
```

Check the enemy Blueprint structure:

```json
{"command": "get_components", "params": {"blueprint": "BP_PatrolEnemy"}}
```

---

## Key Design Decisions

### Pawn vs Character for AI Enemies

Use **Pawn + FloatingPawnMovement** for simple AI enemies, not Character. Character has a complex inherited component hierarchy (CapsuleComponent, CharacterMovement, SkeletalMesh) that causes issues with SCS components added via `add_component`. Pawn is simpler and sufficient for enemies that patrol and chase.

### NavMesh Considerations

The `MoveTo` task in the behavior tree uses pathfinding by default. If NavMesh is not available in your level (common in World Partition maps), set `bUsePathfinding=false` in the MoveTo task parameters for direct-line movement:

```json
{"type": "MoveTo", "params": {"Key": "TargetActor", "AcceptableRadius": "200", "bUsePathfinding": "false"}}
```

Alternatively, create a NavMeshBoundsVolume:

```json
{
  "command": "create_nav_mesh_bounds",
  "params": {
    "location": {"x": 0, "y": 0, "z": 0},
    "extents": {"x": 5000, "y": 5000, "z": 500}
  }
}
```

### Material Application

Always use `set_actor_material` (not `apply_material`) for placed actors. SCS `OverrideMaterials` do not reliably persist through the Blueprint compile and spawn pipeline.

---

## Next Steps

- Add damage-dealing overlap events to the enemy Blueprint using `import_from_ir` with an IR file that includes Event_ActorBeginOverlap nodes.
- Create a health pickup using the `collectible_health` template.
- Add a wave spawner using the `manager_wave_spawner` template.
- See [Cookbook: Level Building](cookbook-level-building.md) for a complete level setup.
