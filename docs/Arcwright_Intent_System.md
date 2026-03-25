# Arcwright — LLM Intent Classification System

> **Purpose:** Replace the local keyword parser with LLM-based intent classification
> **Result:** Every user prompt in any language gets understood, classified, and executed as a structured command plan

---

## Architecture

```
User types anything in any language
    │
    ▼
┌──────────────────────────────┐
│  Arcwright Intent API Call   │
│  POST /v1/intent             │
│  (fast, lightweight)         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  LLM classifies intent       │
│  Extracts entities            │
│  Plans command sequence       │
│  Returns structured JSON      │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Generator Panel receives     │
│  Shows user the plan          │
│  User confirms                │
│  Panel executes commands      │
└──────────────────────────────┘
```

**Key change:** The LLM is called TWICE per user request:
1. **Intent call** (fast, ~200 tokens output): classify and plan
2. **Generate call** (normal, ~500 tokens output): only if CREATE operations need DSL generation

MODIFY and QUERY operations skip the second call entirely — they go straight to plugin commands.

---

## Intent Classification Prompt

This is the system prompt sent with every user request to classify intent:

```
You are Arcwright's intent classifier. Given a user's request about their Unreal Engine 5 project, you must:

1. Determine the MODE: CREATE, MODIFY, QUERY, or MULTI (multiple operations)
2. Plan the exact commands to execute
3. Extract all entities, targets, values, and parameters

You have access to these command categories:

CREATION COMMANDS (make new things):
- create_blueprint: Generate Blueprint logic from description
- create_behavior_tree: Generate AI behavior tree from description  
- create_data_table: Generate data table from description
- create_material_instance: Create a new material
- create_simple_material: Create a material with color
- create_textured_material: Create material from texture
- spawn_actor_at: Place an actor in the level
- create_widget_blueprint: Create a HUD widget
- setup_scene_lighting: Set up level lighting
- set_game_mode: Configure game mode
- create_spline_actor: Create a spline path
- add_post_process_volume: Add post-processing
- create_sequence: Create a cinematic sequence
- create_foliage_type: Create foliage for painting

QUERY COMMANDS (find/list/inspect things):
- find_blueprints: Search Blueprint assets by name, parent class, variables, components
- find_actors: Search placed actors by class, tag, material, location
- find_assets: Search any asset by type and name
- get_level_info: Get level statistics
- get_widget_tree: Inspect widget hierarchy
- get_behavior_tree_info: Inspect a behavior tree
- get_data_table_info: Inspect a data table

MODIFY COMMANDS (change existing things):
- batch_set_variable: Change variable defaults on multiple Blueprints
- batch_add_component: Add components to multiple Blueprints
- batch_apply_material: Change material on multiple actors
- batch_set_property: Change transform/visibility/tags on multiple actors
- batch_delete_actors: Remove actors from the level
- batch_replace_material: Swap one material for another everywhere
- modify_blueprint: Edit nodes/connections on an existing Blueprint
- rename_asset: Rename any asset
- reparent_blueprint: Change Blueprint parent class
- set_actor_material: Change material on a specific actor
- set_component_property: Change a property on a component
- set_node_param: Change a parameter on a Blueprint node
- set_variable_default: Change a variable's default value
- set_actor_transform: Move/rotate/scale a specific actor

Respond ONLY with valid JSON. No explanation. No markdown. The JSON schema:

{
  "mode": "CREATE" | "MODIFY" | "QUERY" | "MULTI",
  "summary": "Brief description of what will happen (in the user's language)",
  "requires_confirmation": true/false,
  "operations": [
    {
      "step": 1,
      "command": "command_name",
      "description": "What this step does",
      "params": {
        // command-specific parameters
      },
      "depends_on": null | step_number
    }
  ]
}

Rules:
- For MODIFY operations that affect multiple assets, set requires_confirmation: true
- For QUERY operations, set requires_confirmation: false
- For CREATE operations, set requires_confirmation: false
- For MULTI operations, set requires_confirmation: true
- When a MODIFY needs to find targets first, the find command is step 1 and the batch command is step 2 with depends_on: 1
- When creating DSL (blueprint/bt/dt), set params.prompt to the description to generate from
- For material changes, params.material should be the desired material name or description
- If the user's request is vague (e.g. "make it better"), ask for clarification by returning mode: "CLARIFY" with a question in summary
- Always respond in the same language the user wrote in
- Entity names should use fuzzy matching descriptors, not exact asset names
```

---

## Example Intent Classifications

### Simple Create
**User:** "Create a health pickup that restores 25 HP"
```json
{
  "mode": "CREATE",
  "summary": "Create a new Blueprint for a health pickup that heals 25 HP on overlap",
  "requires_confirmation": false,
  "operations": [
    {
      "step": 1,
      "command": "create_blueprint",
      "description": "Generate health pickup Blueprint",
      "params": {
        "domain": "blueprint",
        "prompt": "Create a health pickup that restores 25 HP when the player overlaps it and then destroys itself"
      },
      "depends_on": null
    }
  ]
}
```

### Simple Modify
**User:** "Change the wall texture to brick"
```json
{
  "mode": "MODIFY",
  "summary": "Find all wall actors and change their material to brick",
  "requires_confirmation": true,
  "operations": [
    {
      "step": 1,
      "command": "find_actors",
      "description": "Find all actors with 'wall' in the name",
      "params": {
        "name_pattern": "*wall*"
      },
      "depends_on": null
    },
    {
      "step": 2,
      "command": "batch_apply_material",
      "description": "Apply brick material to all found walls",
      "params": {
        "actors": "$step1.results",
        "material_search": "brick"
      },
      "depends_on": 1
    }
  ]
}
```

### Query
**User:** "How many enemies are in the level?"
```json
{
  "mode": "QUERY",
  "summary": "Count all enemy actors in the current level",
  "requires_confirmation": false,
  "operations": [
    {
      "step": 1,
      "command": "find_actors",
      "description": "Find all actors with 'enemy' in the class name",
      "params": {
        "class_pattern": "*enemy*"
      },
      "depends_on": null
    }
  ]
}
```

### Multi-Step
**User:** "Make a dark dungeon with tough enemies and gold loot"
```json
{
  "mode": "MULTI",
  "summary": "Set up dark lighting, create strong enemies, create gold loot pickups, and populate the level",
  "requires_confirmation": true,
  "operations": [
    {
      "step": 1,
      "command": "setup_scene_lighting",
      "description": "Set dark indoor lighting",
      "params": {
        "preset": "indoor_dark"
      },
      "depends_on": null
    },
    {
      "step": 2,
      "command": "create_blueprint",
      "description": "Create tough enemy Blueprint",
      "params": {
        "domain": "blueprint",
        "prompt": "Create an enemy with 200 HP, 25 damage, that patrols and chases the player"
      },
      "depends_on": null
    },
    {
      "step": 3,
      "command": "create_blueprint",
      "description": "Create gold loot pickup",
      "params": {
        "domain": "blueprint",
        "prompt": "Create a gold coin pickup that adds 50 gold when collected and destroys itself"
      },
      "depends_on": null
    },
    {
      "step": 4,
      "command": "create_behavior_tree",
      "description": "Create patrol and chase AI",
      "params": {
        "domain": "bt",
        "prompt": "Patrol between waypoints, chase player when detected within 800 units"
      },
      "depends_on": 2
    },
    {
      "step": 5,
      "command": "spawn_actor_at",
      "description": "Spawn 5 enemies in the level",
      "params": {
        "class": "$step2.asset_name",
        "count": 5,
        "spread": "random",
        "spread_radius": 2000
      },
      "depends_on": 2
    },
    {
      "step": 6,
      "command": "spawn_actor_at",
      "description": "Spawn 10 gold pickups in the level",
      "params": {
        "class": "$step3.asset_name",
        "count": 10,
        "spread": "random",
        "spread_radius": 3000
      },
      "depends_on": 3
    }
  ]
}
```

### Non-English
**User:** "壁のテクスチャをレンガに変えて" (Japanese: "Change the wall texture to brick")
```json
{
  "mode": "MODIFY",
  "summary": "壁のアクターを検索し、マテリアルをレンガに変更します",
  "requires_confirmation": true,
  "operations": [
    {
      "step": 1,
      "command": "find_actors",
      "description": "壁のアクターを検索",
      "params": {
        "name_pattern": "*wall*"
      },
      "depends_on": null
    },
    {
      "step": 2,
      "command": "batch_apply_material",
      "description": "レンガのマテリアルを適用",
      "params": {
        "actors": "$step1.results",
        "material_search": "brick"
      },
      "depends_on": 1
    }
  ]
}
```

### Vague / Needs Clarification
**User:** "Make it better"
```json
{
  "mode": "CLARIFY",
  "summary": "I need more details. What would you like to improve? For example:\n- Change materials or lighting?\n- Add more enemies or pickups?\n- Modify game logic?\n- Improve the HUD?",
  "requires_confirmation": false,
  "operations": []
}
```

### Conversational / Complaint
**User:** "These walls are too plain"
```json
{
  "mode": "MODIFY",
  "summary": "The walls could use more visual interest. I'll find all wall actors and suggest material options.",
  "requires_confirmation": true,
  "operations": [
    {
      "step": 1,
      "command": "find_actors",
      "description": "Find all wall actors",
      "params": {
        "name_pattern": "*wall*"
      },
      "depends_on": null
    },
    {
      "step": 2,
      "command": "find_assets",
      "description": "List available materials to choose from",
      "params": {
        "type": "MaterialInstance",
        "path": "/Game/"
      },
      "depends_on": null
    }
  ]
}
```

---

## API Endpoint

```
POST /v1/intent
Authorization: Bearer ak_live_xxxx
Content-Type: application/json

{
  "prompt": "Change the wall texture to brick",
  "context": {
    "level_name": "TempleLevel",
    "known_assets": ["BP_TempleKey", "BP_Enemy", "MI_Stone", "MI_Brick"],
    "known_actors": ["Wall_01", "Wall_02", "Enemy_01", "Torch_01"]
  }
}

Response:
{
  "mode": "MODIFY",
  "summary": "Find all wall actors and change their material to MI_Brick",
  "requires_confirmation": true,
  "operations": [...]
}
```

The `context` field is optional but improves accuracy — if the LLM knows what assets exist, it can use exact names instead of fuzzy patterns.

---

## Generator Panel Flow (Replaces Keyword Parser)

```
User types prompt
    │
    ▼
Panel sends POST /v1/intent (or local LLM call)
    │
    ▼
Receives JSON plan
    │
    ├── mode: CLARIFY → Show question, wait for more input
    │
    ├── mode: CREATE → Show plan, execute immediately
    │   └── For DSL commands: call /v1/generate for each
    │
    ├── mode: QUERY → Execute find commands, display results
    │
    ├── mode: MODIFY → Show plan + target count
    │   └── "Found 12 walls. Apply brick material?" [Confirm] [Cancel]
    │   └── On confirm: execute batch commands
    │
    └── mode: MULTI → Show full operation plan
        └── "6 operations planned:" [list] [Confirm] [Cancel]
        └── On confirm: execute in order, show progress per step
```

---

## What Gets Removed From the Plugin

The local keyword parser in ArcwrightGeneratorPanel.cpp:
- Remove ParseIntent() with all keyword lists
- Remove EIntentMode enum (replaced by JSON mode string)
- Remove EBatchOpType enum (replaced by command names in JSON)
- Remove all stop word / action verb / property word lists
- Keep the execution logic (ExecuteBatchIntent, etc.) but feed it from JSON instead of parsed structs
- Keep the confirmation flow UI
- Keep the mode badge display (now driven by JSON mode field)

The panel becomes a thin executor that:
1. Sends prompt to LLM
2. Displays the plan
3. Asks for confirmation if needed
4. Executes commands in order
5. Shows results

All intelligence lives in the LLM. The plugin is just hands.

---

## Offline Fallback

When no API connection is available:
- Panel shows "Offline Mode — CREATE only"
- All prompts route to the existing DSL generation path
- MODIFY and QUERY require API connection (need the LLM for intent parsing)
- This is an acceptable limitation — batch operations are a connected feature

---

## Training Note

The intent classification uses the BASE model (LLaMA 3.1 70B) with a system prompt — it does NOT need a fine-tuned LoRA adapter. Intent classification is a general language understanding task, not a domain-specific generation task. The LoRA adapters are only used when the plan includes a create_blueprint/create_behavior_tree/create_data_table operation.

This means:
- Intent classification: base model + system prompt (fast, no adapter switch)
- DSL generation: base model + domain LoRA adapter (existing pipeline)
- Two separate inference calls, but the intent call is very fast (~200 tokens)

---

*All intelligence in the LLM. All execution in the plugin. All languages supported. All phrasing understood.*
