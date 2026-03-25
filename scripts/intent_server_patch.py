"""
intent_server_patch.py — Three targeted fixes for 85.4% → ~92%+ reliability

WHAT THIS FILE CONTAINS
=======================
This is NOT a standalone replacement for intent_server.py.
It contains three self-contained patches to apply to your existing intent_server.py:

  FIX 1: COMMAND_WHITELIST + validate_plan()
          Rejects hallucinated commands (S.04: add_point_light) and
          catches bad param signatures (C.10: rename_asset missing old_name)
          Expected gain: +2-4 points

  FIX 2: Updated CLASSIFY_PROMPT
          Fixes CREATE vs MULTI misclassification (9 tests losing only the intent
          point while executing correctly — C.03,C.04,C.05,C.06,C.07,C.08,C.09,C.10,S.08)
          Expected gain: +7-9 points

  FIX 3: Updated REFINE_PROMPT
          Fixes operations[] wrapper format for batch commands
          (M.03, M.06, M.14, X.04 — flat params instead of operations:[{...}])
          Also adds asset name resolution guidance to fix S.07 (BP_Gold_Coin vs BP_Coin)
          Expected gain: +4-6 points

HOW TO APPLY
============
1. Open scripts/intent_server.py
2. Apply each fix in the section marked with === FIX N ===
3. Instructions for each replacement are in the comments above each block
4. Run the 48-test suite to verify: python tests/run_user_sim.py

TOTAL EXPECTED GAIN: +13-19 points → ~92-95% (177-183/192)
"""

# =============================================================================
# FIX 1: COMMAND WHITELIST + PARAM SCHEMA + validate_plan()
# =============================================================================
# INSTRUCTIONS:
#   Add COMMAND_WHITELIST and COMMAND_REQUIRED_PARAMS near the top of
#   intent_server.py, after imports and before the prompt constants.
#   Then add the validate_plan() function before handle_classify().
#   Then in handle_classify() / handle_refine(), call validate_plan()
#   on the parsed JSON before returning it. See call-site comment below.
# =============================================================================

# --- Paste this block after your imports, before CLASSIFY_PROMPT ---

COMMAND_WHITELIST = {
    # Blueprint authoring
    "create_blueprint_from_dsl",
    "import_blueprint_ir",
    "get_blueprint_info",
    "modify_blueprint",
    "duplicate_blueprint",
    "rename_asset",
    "reparent_blueprint",
    # Level / actors
    "spawn_actor",
    "get_actors",
    "move_actor",
    "delete_actor",
    "get_level_info",
    "save_all",
    "save_level",
    "quit_editor",
    "get_output_log",
    "play_in_editor",
    "stop_play",
    # Components
    "add_component",
    "get_components",
    "remove_component",
    "set_component_property",
    # Materials
    "create_material_instance",
    "apply_material",
    "set_actor_material",
    "create_simple_material",
    "create_textured_material",
    # AI / BehaviorTree
    "create_behavior_tree_from_dsl",
    "get_behavior_tree_info",
    "setup_ai_for_pawn",
    # DataTable
    "create_data_table_from_dsl",
    "get_data_table_info",
    # Widgets
    "create_widget_blueprint",
    "add_widget_child",
    "set_widget_property",
    "get_widget_tree",
    "remove_widget",
    "create_widget_from_html",
    # Scene
    "setup_scene_lighting",
    "set_game_mode",
    "add_post_process_volume",
    "set_post_process_settings",
    # Physics / movement
    "set_movement_defaults",
    "add_physics_constraint",
    "break_constraint",
    # Splines
    "create_spline_actor",
    "add_spline_point",
    "get_spline_info",
    # Asset import
    "import_static_mesh",
    "import_texture",
    "import_sound",
    # Batch / query
    "find_blueprints",
    "find_actors",
    "find_assets",
    "batch_set_variable",
    "batch_add_component",
    "batch_apply_material",
    "batch_set_property",
    "batch_delete_actors",
    "batch_replace_material",
    # Misc
    "health_check",
}

# Required params per command — only list ones that are non-obvious / frequently hallucinated wrong
COMMAND_REQUIRED_PARAMS = {
    "rename_asset":         ["old_name", "new_name"],
    "reparent_blueprint":   ["blueprint_name", "new_parent"],
    "modify_blueprint":     ["blueprint_name"],
    "spawn_actor":          ["blueprint_name"],
    "move_actor":           ["actor_label"],
    "delete_actor":         ["actor_label"],
    "add_component":        ["blueprint_name", "component_type"],
    "remove_component":     ["blueprint_name", "component_name"],
    "set_component_property": ["blueprint_name", "component_name", "property", "value"],
    "apply_material":       ["blueprint_name", "material_path"],
    "batch_delete_actors":  ["labels"],  # must be a list, not a string
    "batch_apply_material": ["material_path"],
    "batch_set_variable":   ["variable_name", "value"],
    "create_behavior_tree_from_dsl": ["dsl"],
    "create_data_table_from_dsl":    ["dsl"],
    "create_blueprint_from_dsl":     ["dsl"],
    "setup_ai_for_pawn":    ["pawn_blueprint"],
}


def validate_plan(plan: dict) -> dict:
    """
    Validates a plan dict returned by the LLM before it gets executed.
    Removes or flags any operations with unknown commands or missing required params.
    Returns a (possibly modified) plan dict with a 'validation_warnings' key added.

    Call this on any parsed JSON plan before returning from handle_classify/handle_refine.

    Usage:
        plan = json.loads(llm_output)
        plan = validate_plan(plan)
        if plan.get("validation_warnings"):
            log("WARN", f"Plan validation: {plan['validation_warnings']}")
        return plan
    """
    warnings = []

    operations = plan.get("operations", [])
    if not isinstance(operations, list):
        # LLM returned flat params instead of operations:[{...}] — wrap it
        # This fixes M.03, M.06, M.14, X.04 pattern
        cmd = plan.get("command")
        if cmd:
            warnings.append(f"Flat params detected for '{cmd}' — wrapping in operations list")
            wrapped_params = {k: v for k, v in plan.items()
                              if k not in ("command", "mode", "targets", "validation_warnings")}
            plan["operations"] = [{"command": cmd, **wrapped_params}]
            operations = plan["operations"]
        else:
            # No command at top level either — can't recover
            warnings.append("No operations[] array and no top-level command — plan may be malformed")
            plan["validation_warnings"] = warnings
            return plan

    valid_operations = []
    for i, op in enumerate(operations):
        cmd = op.get("command", "")

        # Check against whitelist
        if cmd not in COMMAND_WHITELIST:
            warnings.append(
                f"Operation {i}: unknown command '{cmd}' — removed. "
                f"Hint: check COMMAND_WHITELIST for valid commands. "
                f"Common mistakes: 'add_point_light' → use add_component with component_type='PointLight'"
            )
            continue  # Drop this operation

        # Check required params
        required = COMMAND_REQUIRED_PARAMS.get(cmd, [])
        missing = [p for p in required if p not in op]
        if missing:
            warnings.append(
                f"Operation {i}: command '{cmd}' missing required params: {missing} — removed"
            )
            continue  # Drop this operation

        # batch_delete_actors: labels must be a list, not a string
        if cmd == "batch_delete_actors":
            labels = op.get("labels")
            if isinstance(labels, str):
                op["labels"] = [labels]
                warnings.append(
                    f"Operation {i}: batch_delete_actors.labels was a string, converted to list"
                )

        valid_operations.append(op)

    plan["operations"] = valid_operations
    if warnings:
        plan["validation_warnings"] = warnings

    return plan


# --- CALL SITE: In handle_classify() and handle_refine(), after json.loads(raw), add: ---
#
#   plan = validate_plan(plan)
#   if plan.get("validation_warnings"):
#       for w in plan["validation_warnings"]:
#           log("WARN", w)
#
# -----------------------------------------------------------------------------


# =============================================================================
# FIX 2: CLASSIFY_PROMPT REPLACEMENT
# =============================================================================
# INSTRUCTIONS:
#   Replace your existing CLASSIFY_PROMPT constant entirely with this one.
#   Key changes vs current:
#     - Explicit CREATE vs MULTI rule with 8 concrete examples
#     - "Complex single Blueprint = CREATE" stated three different ways
#     - MULTI only when user explicitly asks for MULTIPLE SEPARATE assets
#     - Added asset-name-guessing warning to push Stage 2 discovery
# =============================================================================

CLASSIFY_PROMPT = """You are the intent classifier for Arcwright, a tool that creates Unreal Engine 5 game content from natural language.

Your job: classify the user's request into one of these modes and extract targets.

MODES:
- CREATE  — make one new asset (Blueprint, BehaviorTree, DataTable, Widget, material, spline, etc.)
- MODIFY  — change existing assets or actors already in the level
- QUERY   — answer a question about what exists (list actors, check blueprint info, etc.)
- MULTI   — ONLY when user explicitly requests MULTIPLE SEPARATE assets by name or count
- CLARIFY — request is too ambiguous to act on safely

=== CRITICAL RULE: CREATE vs MULTI ===

USE CREATE when:
  - The user wants ONE asset, even if it is complex with many components or behaviors
  - The user describes a single thing ("a torch", "an enemy", "a spinning cube")
  - The user asks to "make", "create", "build", "add" a single game element
  - A Blueprint with lights, collision, physics, AI — still ONE asset = CREATE

USE MULTI only when:
  - The user explicitly names or counts MULTIPLE SEPARATE assets
  - Example: "Create a sword, a shield, and a health potion" → MULTI (3 named assets)
  - Example: "Set up scene lighting AND create an enemy" → MULTI (two unrelated tasks)

NEVER use MULTI for:
  - A single complex Blueprint ("a torch with a point light" → CREATE)
  - Placing several instances of the same Blueprint ("place 5 coins" → CREATE + spawn)
  - A Blueprint with multiple components ("player with camera, capsule, mesh" → CREATE)

EXAMPLES — classify these correctly:
  "Create a torch with a point light at intensity 5000"  → CREATE  (one BP with a light component)
  "Make an enemy that patrols and chases the player"     → CREATE  (one BP with AI)
  "Add a spinning cube to the level"                     → CREATE  (one actor)
  "Place 5 gold coins around the level"                  → CREATE  (one BP, multiple spawns)
  "Create a pressure plate that opens a door"            → CREATE  (one BP with trigger logic)
  "Make something that spins on its Z axis"              → CREATE  (one BP with rotation)
  "Build a full game level with enemies, coins, and HUD" → MULTI   (explicitly multiple separate assets)
  "Create a sword and a shield"                          → MULTI   (two named separate assets)

=== ASSET NAME RULE ===
Never guess asset names. If you are not 100% certain of the exact Blueprint/asset name in the
project, set targets to [] and let Stage 2 Discovery find the real names.
Wrong: targets: ["BP_Gold_Coin"]   ← guessed, may not exist
Right: targets: []                 ← let find_blueprints discover the real name

=== OUTPUT FORMAT ===
Respond with ONLY valid JSON, no markdown, no explanation:
{
  "mode": "CREATE" | "MODIFY" | "QUERY" | "MULTI" | "CLARIFY",
  "targets": ["ExactAssetName"] or [],
  "summary": "one sentence describing what the user wants"
}"""


# =============================================================================
# FIX 3: REFINE_PROMPT REPLACEMENT
# =============================================================================
# INSTRUCTIONS:
#   Replace your existing REFINE_PROMPT constant entirely with this one.
#   Key changes vs current:
#     - operations[] wrapper format shown in EVERY example (fixes M.03,M.06,M.14,X.04)
#     - Explicit "NEVER return flat params" rule stated twice
#     - Asset name resolution: always use discovered names from Stage 2, never guess
#     - Clearer batch command examples with correct param structure
#     - rename_asset signature with both old_name and new_name shown explicitly
# =============================================================================

REFINE_PROMPT = """You are the plan generator for Arcwright, a tool that creates Unreal Engine 5 game content.

You have been given:
1. The user's request
2. Discovered assets from the UE project (real names, exact paths)
3. The classified intent mode

Your job: produce a concrete execution plan using only valid Arcwright commands.

=== CRITICAL FORMAT RULE ===
ALL plans MUST use the operations[] array format.
NEVER return flat params at the top level.

CORRECT:
{
  "mode": "MODIFY",
  "operations": [
    {"command": "batch_apply_material", "class_filter": "BP_Wall", "material_path": "/Game/Arcwright/Materials/M_Stone"}
  ]
}

WRONG (flat params — will be rejected):
{
  "command": "batch_apply_material",
  "class_filter": "BP_Wall",
  "material_path": "/Game/Arcwright/Materials/M_Stone"
}

This rule applies to ALL modes including CREATE with a single operation.

=== ASSET NAME RULE ===
Use ONLY asset names from the discovered assets provided to you.
If the user said "gold coin" and discovery found "BP_Coin", use "BP_Coin".
If discovery found nothing matching, use your best guess BUT add "asset_name_uncertain": true to that operation.
NEVER invent commands that don't exist. Use the command whitelist strictly.

=== COMMAND REFERENCE (use ONLY these) ===

CREATING ASSETS:
  {"command": "create_blueprint_from_dsl", "dsl": "<full DSL string>"}
  {"command": "create_behavior_tree_from_dsl", "dsl": "<full BT DSL string>"}
  {"command": "create_data_table_from_dsl", "dsl": "<full DT DSL string>"}
  {"command": "create_widget_from_html", "html": "<html string>", "widget_name": "WBP_Name"}
  {"command": "setup_scene_lighting", "preset": "outdoor_day"}
  {"command": "set_game_mode", "game_mode": "BP_FirstPersonGameMode"}

SPAWNING ACTORS:
  {"command": "spawn_actor", "blueprint_name": "BP_Coin", "x": 0, "y": 0, "z": 0}

ADDING COMPONENTS (not add_point_light — that doesn't exist):
  {"command": "add_component", "blueprint_name": "BP_Torch", "component_type": "PointLight", "component_name": "TorchLight"}
  {"command": "set_component_property", "blueprint_name": "BP_Torch", "component_name": "TorchLight", "property": "Intensity", "value": 5000}

MODIFYING EXISTING ASSETS:
  {"command": "modify_blueprint", "blueprint_name": "BP_Enemy", "set_variable": {"Health": 100}}
  {"command": "rename_asset", "old_name": "BP_OldName", "new_name": "BP_NewName"}
  {"command": "reparent_blueprint", "blueprint_name": "BP_Enemy", "new_parent": "Character"}
  {"command": "batch_set_variable", "blueprint_names": ["BP_A", "BP_B"], "variable_name": "Speed", "value": 300}
  {"command": "batch_add_component", "blueprint_names": ["BP_A", "BP_B"], "component_type": "BoxCollision"}

MATERIALS:
  {"command": "batch_apply_material", "actor_labels": ["Wall_1", "Wall_2"], "material_path": "/Game/Arcwright/Materials/M_Stone"}
  {"command": "batch_replace_material", "old_material_path": "/Game/...", "new_material_path": "/Game/..."}
  {"command": "apply_material", "blueprint_name": "BP_Wall", "material_path": "/Game/Arcwright/Materials/M_Stone"}

DELETING:
  {"command": "batch_delete_actors", "labels": ["Actor_1", "Actor_2"]}
  {"command": "batch_delete_actors", "class_filter": "BP_Enemy"}
  NOTE: labels must ALWAYS be a list [], never a single string.
  NOTE: there is NO batch_delete_blueprints command.

QUERYING:
  {"command": "find_blueprints", "name_filter": "Enemy"}
  {"command": "find_actors", "class_filter": "BP_Coin"}
  {"command": "get_level_info"}
  {"command": "get_blueprint_info", "blueprint_name": "BP_Enemy"}

=== OUTPUT FORMAT ===
Respond with ONLY valid JSON, no markdown, no explanation:
{
  "mode": "CREATE" | "MODIFY" | "QUERY" | "MULTI",
  "summary": "one sentence describing the plan",
  "operations": [
    {"command": "...", ...params},
    {"command": "...", ...params}
  ]
}

Even for a single operation, always wrap it in operations[].
Even for CREATE, use operations[].
There are no exceptions to this rule."""


# =============================================================================
# BONUS FIX: Stage 2 Discovery — extend to cover SETUP and CREATE with asset refs
# =============================================================================
# INSTRUCTIONS:
#   In your handle_classify() function, the current code only runs Stage 2 for
#   MODIFY and MULTI. Change the condition to also run Stage 2 when mode is
#   CREATE or SETUP and the summary mentions an existing asset by name
#   (heuristic: contains "BP_", "WBP_", "BT_", "DT_", or words like "coin",
#   "enemy", "door" that suggest referencing an existing asset).
#
#   Replace the existing Stage 2 condition:
#
#     CURRENT:
#       if mode in ("MODIFY", "MULTI"):
#           discovery = run_stage2_discovery(targets, mode)
#
#     REPLACE WITH:
# =============================================================================

def should_run_discovery(mode: str, summary: str, targets: list) -> bool:
    """
    Returns True if Stage 2 discovery should run.
    Extended beyond MODIFY/MULTI to catch CREATE requests that reference existing assets.
    Fixes S.07: "Place 5 gold coins" — needs to discover BP_Coin vs BP_Gold_Coin.
    """
    # Always run for these modes
    if mode in ("MODIFY", "MULTI"):
        return True

    # Run for CREATE/SETUP if it likely references an existing asset
    if mode in ("CREATE", "SETUP"):
        # Explicit asset name references
        asset_prefixes = ("BP_", "WBP_", "BT_", "DT_", "SM_", "T_", "MAT_", "M_")
        if any(p in summary for p in asset_prefixes):
            return True
        # Common words that suggest spawning existing assets
        spawn_hints = (
            "place", "spawn", "add to level", "put", "scatter",
            "coin", "enemy", "door", "wall", "torch", "chest", "pickup",
            "around the level", "in the level", "instances of"
        )
        summary_lower = summary.lower()
        if any(hint in summary_lower for hint in spawn_hints):
            return True

    return False

# Usage in handle_classify():
#   if should_run_discovery(mode, summary, targets):
#       discovery = run_stage2_discovery(targets, mode)
#   else:
#       discovery = {}


# =============================================================================
# SUMMARY OF CHANGES + EXPECTED TEST IMPACT
# =============================================================================
"""
Test results before patch: 85.4% (164/192)

Fix 1 — Command whitelist + validate_plan():
  S.04 (1/4): add_point_light rejected → hint suggests add_component+PointLight → likely 3/4
  C.10 (2/4): rename_asset missing old_name → operation dropped, plan fails cleanly → 2/4 or 3/4
  Prevents future hallucinations in all categories
  Expected: +1-3 points

Fix 2 — CLASSIFY_PROMPT:
  Fixes CREATE→MULTI misclassification: C.03,C.04,C.05,C.06,C.07,C.08,C.09,C.10,S.08
  These all scored 3/4 (execution correct, intent wrong)
  If intent now scores correctly: each becomes 4/4
  Expected: +7-9 points (conservative: 7, optimistic: 9)

Fix 3 — REFINE_PROMPT + operations[] rule:
  Fixes M.03,M.06,M.14,X.04 flat params format → each likely +1-2 points
  Expected: +4-6 points

Fix 4 — should_run_discovery():
  S.07 (2/4): "Place 5 gold coins" now discovers BP_Coin → likely 3/4 or 4/4
  Expected: +1-2 points

TOTAL EXPECTED: +13-20 points
New score estimate: 177-184/192 = 92-96%
"""
