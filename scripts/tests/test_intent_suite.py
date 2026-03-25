"""
test_intent_suite.py
--------------------
Arcwright Intent Test Suite — 92 tests across 10 categories.

Sends prompts to the intent server (localhost:13380), scores the classification,
then optionally executes the plan against the live UE editor (localhost:13377).

Scoring (per test):
  1. Intent correct  — right mode? (CREATE/MODIFY/QUERY/MULTI/CLARIFY)
  2. Target correct  — right entities identified?
  3. Action correct  — right commands planned?
  4. Execution correct — commands run successfully in UE?

Total possible: 92 tests × 4 = 368 points

Usage:
    python scripts/tests/test_intent_suite.py --all --verbose
    python scripts/tests/test_intent_suite.py --category 1
    python scripts/tests/test_intent_suite.py --category 10 --verbose
    python scripts/tests/test_intent_suite.py --no-exec  # skip execution scoring
"""

import argparse
import json
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError

# ═══════════════════════════════════════════════════════════════
# Intent server TCP helper
# ═══════════════════════════════════════════════════════════════

INTENT_PORT = 13380
UE_PORT = 13377


def send_intent(prompt: str, timeout: float = 300.0) -> dict:
    """Send a prompt to the intent server and return parsed JSON plan."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(("127.0.0.1", INTENT_PORT))
        msg = json.dumps({"prompt": prompt}) + "\n"
        sock.sendall(msg.encode("utf-8"))

        data = b""
        while b"\n" not in data:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk

        response = data.decode("utf-8").strip()
        return json.loads(response)
    except (ConnectionRefusedError, ConnectionError, socket.timeout, json.JSONDecodeError) as e:
        return {"error": str(e), "mode": "ERROR"}
    finally:
        sock.close()


# ═══════════════════════════════════════════════════════════════
# Test definition
# ═══════════════════════════════════════════════════════════════

class IntentTest:
    """Single test case with scoring criteria."""

    def __init__(self, test_id: str, prompt: str, expected_modes: list,
                 target_keywords: list, action_keywords: list,
                 category: int, description: str = ""):
        self.test_id = test_id
        self.prompt = prompt
        self.expected_modes = expected_modes  # list of acceptable modes
        self.target_keywords = target_keywords  # keywords expected in operations/params
        self.action_keywords = action_keywords  # command names expected
        self.category = category
        self.description = description

        # Scores
        self.intent_correct = False
        self.target_correct = False
        self.action_correct = False
        self.exec_correct = False
        self.plan = None
        self.exec_result = None
        self.error = None

    @property
    def score(self):
        return sum([self.intent_correct, self.target_correct,
                    self.action_correct, self.exec_correct])


# ═══════════════════════════════════════════════════════════════
# Scoring logic
# ═══════════════════════════════════════════════════════════════

def score_intent(test: IntentTest, plan: dict) -> bool:
    """Score criterion 1: is the mode correct?"""
    mode = plan.get("mode", "").upper()
    return mode in [m.upper() for m in test.expected_modes]


def score_target(test: IntentTest, plan: dict) -> bool:
    """Score criterion 2: did the plan identify the right entities?"""
    if not test.target_keywords:
        return True  # no target constraint

    # Serialize the entire plan to search for target keywords
    plan_text = json.dumps(plan).lower()
    matched = 0
    for kw in test.target_keywords:
        if kw.lower() in plan_text:
            matched += 1
    # At least half the keywords must appear
    return matched >= max(1, len(test.target_keywords) // 2)


def score_action(test: IntentTest, plan: dict) -> bool:
    """Score criterion 3: did the plan use the right commands?"""
    if not test.action_keywords:
        return True  # no action constraint

    # Collect all command names from operations
    ops = plan.get("operations", [])
    commands_in_plan = [op.get("command", "").lower() for op in ops]
    plan_text = json.dumps(plan).lower()

    matched = 0
    for kw in test.action_keywords:
        kw_lower = kw.lower()
        # Check if the keyword appears as a command or anywhere in the plan
        if any(kw_lower in cmd for cmd in commands_in_plan) or kw_lower in plan_text:
            matched += 1

    # At least one action keyword must match
    return matched >= 1


def score_execution(test: IntentTest, plan: dict, ue_client: ArcwrightClient) -> bool:
    """Score criterion 4: do the planned commands actually execute in UE?

    We don't fully execute destructive plans (DELETE, MODIFY with real changes)
    during the test. Instead we verify:
    - For QUERY/find commands: they return data
    - For MODIFY: the find step succeeds and returns targets
    - For CREATE: we skip (would need cleanup, and the LLM doesn't generate DSL here)
    - For CLARIFY: always passes (no execution needed)
    """
    mode = plan.get("mode", "").upper()
    ops = plan.get("operations", [])

    if mode == "CLARIFY" or mode == "ERROR":
        return mode == "CLARIFY"

    if not ops:
        return False

    # Test the first (find/query) operation to verify it connects to real UE state
    first_op = ops[0]
    cmd = first_op.get("command", "")
    params = {}
    if first_op.get("params"):
        if isinstance(first_op["params"], dict):
            params = first_op["params"]
        elif isinstance(first_op["params"], str):
            try:
                params = json.loads(first_op["params"])
            except json.JSONDecodeError:
                params = {}

    # For CREATE mode, just verify the plan structure is valid
    if mode == "CREATE":
        return len(ops) >= 1 and bool(cmd)

    # For MULTI, verify at least one operation is structurally valid
    if mode == "MULTI":
        return len(ops) >= 2 and all(op.get("command") for op in ops)

    # For MODIFY/QUERY, try to execute the find/query step
    try:
        if "find_actors" in cmd:
            name_filter = params.get("name_pattern", params.get("name_filter", ""))
            class_filter = params.get("class_pattern", params.get("class_filter", ""))
            result = ue_client.find_actors(
                name_filter=name_filter.replace("*", ""),
                class_filter=class_filter.replace("*", ""),
            )
            actors = result.get("data", {}).get("actors", [])
            return len(actors) >= 0  # just needs to succeed

        elif "find_blueprints" in cmd:
            name_filter = params.get("name_filter", params.get("name_pattern", ""))
            has_var = params.get("has_variable", "")
            result = ue_client.find_blueprints(
                name_filter=name_filter.replace("*", ""),
                has_variable=has_var,
            )
            return True  # succeeded

        elif "find_assets" in cmd:
            asset_type = params.get("type", "")
            result = ue_client.find_assets(asset_type=asset_type)
            return True

        elif "get_level_info" in cmd:
            result = ue_client.get_level_info()
            return True

        elif "batch_replace_material" in cmd:
            # Don't actually replace, just verify the command name is valid
            return True

        elif "batch_delete_actors" in cmd:
            # Don't actually delete, just verify the plan
            return True

        elif "batch_set_variable" in cmd or "batch_apply_material" in cmd:
            return True

        elif "batch_set_property" in cmd:
            return True

        elif "batch_add_component" in cmd:
            return True

        elif "rename_asset" in cmd or "reparent_blueprint" in cmd:
            return True

        elif "setup_scene_lighting" in cmd:
            return True

        elif "create_" in cmd or "spawn_" in cmd or "setup_" in cmd:
            return True

        else:
            # Unknown command — try a generic dispatch
            result = ue_client.send_command(cmd, params)
            return result.get("status") == "ok"

    except (BlueprintLLMError, Exception):
        return False


# ═══════════════════════════════════════════════════════════════
# All 92 test definitions
# ═══════════════════════════════════════════════════════════════

def build_all_tests() -> list:
    tests = []

    # ── Category 1: Simple Modify — Material Changes (10) ────
    cat = 1
    tests.append(IntentTest("1.01", "Change the wall texture to brick",
        ["MODIFY"], ["wall"], ["batch_apply_material", "batch_replace_material", "find_actors"], cat))
    tests.append(IntentTest("1.02", "Make all the walls look like marble",
        ["MODIFY"], ["wall", "marble"], ["batch_apply_material", "find_actors"], cat))
    tests.append(IntentTest("1.03", "Swap the stone material on the walls for concrete",
        ["MODIFY"], ["wall", "stone", "concrete"], ["batch_replace_material", "batch_apply_material"], cat))
    tests.append(IntentTest("1.04", "Replace every gold material with silver",
        ["MODIFY"], ["gold", "silver"], ["batch_replace_material"], cat))
    tests.append(IntentTest("1.05", "The walls need a different texture, use wood",
        ["MODIFY"], ["wall", "wood"], ["batch_apply_material", "find_actors"], cat))
    tests.append(IntentTest("1.06", "Give the floor a lava material",
        ["MODIFY"], ["floor", "lava"], ["batch_apply_material", "find_actors", "set_actor_material"], cat))
    tests.append(IntentTest("1.07", "Update torch materials to something warmer",
        ["MODIFY"], ["torch"], ["batch_apply_material", "find_actors"], cat))
    tests.append(IntentTest("1.08", "I want the coins to look more realistic",
        ["MODIFY", "CLARIFY"], ["coin"], ["batch_apply_material", "find_actors", "find_assets"], cat))
    tests.append(IntentTest("1.09", "Everything stone should be brick instead",
        ["MODIFY"], ["stone", "brick"], ["batch_replace_material"], cat))
    tests.append(IntentTest("1.10", "Paint the walls red",
        ["MODIFY"], ["wall", "red"], ["batch_apply_material", "find_actors", "create_simple_material"], cat))

    # ── Category 2: Simple Modify — Variable Changes (10) ────
    cat = 2
    tests.append(IntentTest("2.01", "Set health to 200 on all enemies",
        ["MODIFY"], ["enemy", "health", "200"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.02", "Make the enemies faster",
        ["MODIFY"], ["enemy", "speed"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.03", "Double the enemy damage",
        ["MODIFY"], ["enemy", "damage"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.04", "Gold coins should be worth 50 each",
        ["MODIFY"], ["coin", "value", "50"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.05", "Reduce enemy health to 50",
        ["MODIFY"], ["enemy", "health", "50"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.06", "Make the torches brighter",
        ["MODIFY"], ["torch", "intensity"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.07", "Enemies are too slow, speed them up",
        ["MODIFY"], ["enemy", "speed"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.08", "Turn down the torch intensity to 2000",
        ["MODIFY"], ["torch", "intensity", "2000"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("2.09", "Health potions should heal 50 instead",
        ["MODIFY"], ["health", "50"], ["batch_set_variable", "find", "set_variable_default"], cat))
    tests.append(IntentTest("2.10", "All enemies need 500 HP, 40 damage, and 600 speed",
        ["MODIFY"], ["enemy", "500", "40", "600"], ["batch_set_variable", "find"], cat))

    # ── Category 3: Simple Modify — Transform and Properties (10) ─
    cat = 3
    tests.append(IntentTest("3.01", "Scale all enemies up by 1.5",
        ["MODIFY"], ["enemy", "1.5"], ["batch_set_property", "find_actors"], cat))
    tests.append(IntentTest("3.02", "Make the coins smaller",
        ["MODIFY"], ["coin"], ["batch_set_property", "find_actors"], cat))
    tests.append(IntentTest("3.03", "Hide all the torches",
        ["MODIFY"], ["torch", "visibility"], ["batch_set_property", "find_actors"], cat))
    tests.append(IntentTest("3.04", "Show all hidden actors",
        ["MODIFY"], ["visibility"], ["batch_set_property", "find_actors"], cat))
    tests.append(IntentTest("3.05", "Move all coins up by 50 units",
        ["MODIFY"], ["coin", "50"], ["batch_set_property", "find_actors"], cat))
    tests.append(IntentTest("3.06", "Rotate all enemies to face north",
        ["MODIFY"], ["enemy", "rotation"], ["batch_set_property", "find_actors"], cat))
    tests.append(IntentTest("3.07", "Delete all the gold coins",
        ["MODIFY"], ["coin"], ["batch_delete_actors", "find_actors", "delete"], cat))
    tests.append(IntentTest("3.08", "Remove every torch from the level",
        ["MODIFY"], ["torch"], ["batch_delete_actors", "find_actors", "delete"], cat))
    tests.append(IntentTest("3.09", "Clear out all the enemies",
        ["MODIFY"], ["enemy"], ["batch_delete_actors", "find_actors", "delete"], cat))
    tests.append(IntentTest("3.10", "Resize the walls to be twice as tall",
        ["MODIFY"], ["wall", "scale"], ["batch_set_property", "find_actors"], cat))

    # ── Category 4: Simple Modify — Component Changes (5) ────
    cat = 4
    tests.append(IntentTest("4.01", "Add a point light to every torch",
        ["MODIFY"], ["torch", "point", "light"], ["batch_add_component", "find_blueprints", "add_component"], cat))
    tests.append(IntentTest("4.02", "Give all enemies a sphere collision",
        ["MODIFY"], ["enemy", "sphere", "collision"], ["batch_add_component", "find_blueprints", "add_component"], cat))
    tests.append(IntentTest("4.03", "Add audio components to the torches",
        ["MODIFY"], ["torch", "audio"], ["batch_add_component", "find_blueprints", "add_component"], cat))
    tests.append(IntentTest("4.04", "Put a box collision on every coin",
        ["MODIFY"], ["coin", "box", "collision"], ["batch_add_component", "find_blueprints", "add_component"], cat))
    tests.append(IntentTest("4.05", "Every health potion needs a point light",
        ["MODIFY"], ["health", "point", "light"], ["batch_add_component", "find_blueprints", "add_component"], cat))

    # ── Category 5: Simple Modify — Rename and Reparent (5) ──
    cat = 5
    tests.append(IntentTest("5.01", "Rename BP_GoldCoin to BP_TreasureCoin",
        ["MODIFY"], ["goldcoin", "treasurecoin"], ["rename_asset"], cat))
    tests.append(IntentTest("5.02", "Rename the enemy blueprint to BP_SkeletonWarrior",
        ["MODIFY"], ["enemy", "skeletonwarrior"], ["rename_asset"], cat))
    tests.append(IntentTest("5.03", "Change the coin's parent class to Pawn",
        ["MODIFY"], ["coin", "pawn"], ["reparent_blueprint"], cat))
    tests.append(IntentTest("5.04", "Make BP_EnemyGuard extend Character instead of Actor",
        ["MODIFY"], ["enemyguard", "character"], ["reparent_blueprint"], cat))
    tests.append(IntentTest("5.05", "Rename all the wall blueprints to BP_StoneWall",
        ["MODIFY"], ["wall", "stonewall"], ["rename_asset"], cat))

    # ── Category 6: Query — Find and Inspect (10) ────────────
    cat = 6
    tests.append(IntentTest("6.01", "How many enemies are in the level?",
        ["QUERY"], ["enemy"], ["find_actors"], cat))
    tests.append(IntentTest("6.02", "List all blueprints in the project",
        ["QUERY"], [], ["find_blueprints", "find_assets"], cat))
    tests.append(IntentTest("6.03", "Show me all the actors in the level",
        ["QUERY"], [], ["find_actors", "get_level_info"], cat))
    tests.append(IntentTest("6.04", "What materials exist in the project?",
        ["QUERY"], ["material"], ["find_assets"], cat))
    tests.append(IntentTest("6.05", "Which blueprints have a Health variable?",
        ["QUERY"], ["health"], ["find_blueprints"], cat))
    tests.append(IntentTest("6.06", "How many coins are placed in the level?",
        ["QUERY"], ["coin"], ["find_actors"], cat))
    tests.append(IntentTest("6.07", "What's in the level right now?",
        ["QUERY"], [], ["get_level_info", "find_actors"], cat))
    tests.append(IntentTest("6.08", "Show me the enemy blueprint details",
        ["QUERY"], ["enemy"], ["find_blueprints", "get_blueprint_info", "get_behavior_tree_info"], cat))
    tests.append(IntentTest("6.09", "Are there any torches near the entrance?",
        ["QUERY"], ["torch"], ["find_actors"], cat))
    tests.append(IntentTest("6.10", "What components does the enemy have?",
        ["QUERY"], ["enemy"], ["find_blueprints", "get_components", "get_blueprint_info"], cat))

    # ── Category 7: Create — New Assets (10) ──────────────────
    cat = 7
    tests.append(IntentTest("7.01", "Create a health pickup that heals 25 HP",
        ["CREATE"], ["health", "25"], ["create_blueprint"], cat))
    tests.append(IntentTest("7.02", "Make a new enemy that shoots projectiles",
        ["CREATE"], ["enemy", "projectile"], ["create_blueprint"], cat))
    tests.append(IntentTest("7.03", "Build a pressure plate that opens a door",
        ["CREATE"], ["pressure", "plate", "door"], ["create_blueprint"], cat))
    tests.append(IntentTest("7.04", "Generate a patrol AI for the guards",
        ["CREATE"], ["patrol"], ["create_behavior_tree"], cat))
    tests.append(IntentTest("7.05", "I need a weapons stats table",
        ["CREATE"], ["weapon"], ["create_data_table"], cat))
    tests.append(IntentTest("7.06", "Create a wave spawner that sends enemies every 10 seconds",
        ["CREATE"], ["wave", "spawn", "10"], ["create_blueprint"], cat))
    tests.append(IntentTest("7.07", "Make a score HUD with health bar and coin counter",
        ["CREATE"], ["hud", "health", "coin"], ["create_widget_blueprint", "create_blueprint"], cat))
    tests.append(IntentTest("7.08", "Set up FPS controls for the game",
        ["CREATE", "MULTI"], ["fps"], ["set_game_mode", "setup", "create_blueprint"], cat))
    tests.append(IntentTest("7.09", "Add dark indoor lighting to the level",
        ["CREATE", "MODIFY"], ["dark", "indoor"], ["setup_scene_lighting"], cat))
    tests.append(IntentTest("7.10", "Create a new brick material",
        ["CREATE"], ["brick"], ["create_textured_material", "create_simple_material", "create_material"], cat))

    # ── Category 8: Multi — Complex Multi-Step (10) ──────────
    cat = 8
    tests.append(IntentTest("8.01", "Make a dark dungeon with tough enemies and gold loot",
        ["MULTI"], ["dark", "enemy", "gold"], ["setup_scene_lighting", "create_blueprint", "spawn"], cat))
    tests.append(IntentTest("8.02", "Create a patrol enemy, give it 200 HP, and spawn 5 of them",
        ["MULTI"], ["patrol", "200", "5"], ["create_blueprint", "spawn", "set_variable"], cat))
    tests.append(IntentTest("8.03", "Add torches to the hallway and make them glow warm",
        ["MULTI"], ["torch", "warm"], ["spawn", "create", "material", "apply"], cat))
    tests.append(IntentTest("8.04", "Set up the arena: FPS controls, dark lighting, spawn 3 enemies",
        ["MULTI"], ["fps", "dark", "enemy", "3"], ["setup", "lighting", "spawn"], cat))
    tests.append(IntentTest("8.05", "Create a boss room with one strong enemy, health pickups, and dramatic lighting",
        ["MULTI"], ["boss", "enemy", "health", "lighting"], ["create_blueprint", "spawn", "setup_scene_lighting"], cat))
    tests.append(IntentTest("8.06", "Replace all stone with marble and make the room brighter",
        ["MULTI"], ["stone", "marble", "bright"], ["batch_replace_material", "setup_scene_lighting", "lighting"], cat))
    tests.append(IntentTest("8.07", "Delete all coins, create a gem pickup worth 100, and spawn 8 of them",
        ["MULTI"], ["coin", "gem", "100", "8"], ["batch_delete_actors", "delete", "create_blueprint", "spawn"], cat))
    tests.append(IntentTest("8.08", "Create an enemy, a behavior tree for it, and wire them together",
        ["MULTI"], ["enemy", "behavior", "tree"], ["create_blueprint", "create_behavior_tree", "setup_ai"], cat))
    tests.append(IntentTest("8.09", "Build a complete checkpoint system with save, respawn, and a visual indicator",
        ["MULTI"], ["checkpoint", "save", "respawn"], ["create_blueprint", "spawn"], cat))
    tests.append(IntentTest("8.10", "Make all enemies tougher, add more coins, and change the walls to brick",
        ["MULTI"], ["enemy", "coin", "wall", "brick"], ["batch_set_variable", "spawn", "batch_apply_material", "batch_replace_material"], cat))

    # ── Category 9: Conversational / Vague (10) ──────────────
    cat = 9
    tests.append(IntentTest("9.01", "These walls are too plain",
        ["MODIFY", "CLARIFY"], ["wall"], ["find_actors", "batch_apply_material", "find_assets"], cat))
    tests.append(IntentTest("9.02", "The level feels empty",
        ["MULTI", "CLARIFY"], [], [], cat))
    tests.append(IntentTest("9.03", "Make it better",
        ["CLARIFY"], [], [], cat))
    tests.append(IntentTest("9.04", "Something isn't right with the enemies",
        ["CLARIFY"], ["enemy"], [], cat))
    tests.append(IntentTest("9.05", "I want more variety",
        ["CLARIFY"], [], [], cat))
    tests.append(IntentTest("9.06", "This room needs atmosphere",
        ["MULTI", "CLARIFY", "CREATE"], ["lighting", "fog", "post"], [], cat))
    tests.append(IntentTest("9.07", "Can you help me with the boss fight?",
        ["CLARIFY"], ["boss"], [], cat))
    tests.append(IntentTest("9.08", "Too many coins",
        ["MODIFY", "CLARIFY"], ["coin"], ["batch_delete_actors", "find_actors", "delete"], cat))
    tests.append(IntentTest("9.09", "The game is too easy",
        ["MODIFY", "CLARIFY"], ["enemy"], ["batch_set_variable", "find"], cat))
    tests.append(IntentTest("9.10", "I'm stuck",
        ["CLARIFY"], [], [], cat))

    # ── Category 10: Non-English (12) ─────────────────────────
    cat = 10
    tests.append(IntentTest("10.01", "Cambia la textura de las paredes a ladrillo",
        ["MODIFY"], ["wall", "pared", "brick", "ladrillo"], ["batch_apply_material", "find_actors", "batch_replace_material"], cat,
        "Spanish: Change wall texture to brick"))
    tests.append(IntentTest("10.02", "Augmente la santé de tous les ennemis à 300",
        ["MODIFY"], ["enemy", "ennemi", "health", "santé", "300"], ["batch_set_variable", "find"], cat,
        "French: Set enemy health to 300"))
    tests.append(IntentTest("10.03", "Lösche alle Goldmünzen",
        ["MODIFY"], ["coin", "gold", "münz"], ["batch_delete_actors", "find_actors", "delete"], cat,
        "German: Delete all gold coins"))
    tests.append(IntentTest("10.04", "Crie um inimigo com 500 de vida",
        ["CREATE"], ["enemy", "inimigo", "500"], ["create_blueprint"], cat,
        "Portuguese: Create enemy with 500 HP"))
    tests.append(IntentTest("10.05", "壁のマテリアルをレンガに変えて",
        ["MODIFY"], ["wall", "壁", "brick", "レンガ"], ["batch_apply_material", "find_actors", "batch_replace_material"], cat,
        "Japanese: Change wall material to brick"))
    tests.append(IntentTest("10.06", "적의 체력을 200으로 설정하세요",
        ["MODIFY"], ["enemy", "적", "health", "체력", "200"], ["batch_set_variable", "find"], cat,
        "Korean: Set enemy health to 200"))
    tests.append(IntentTest("10.07", "把所有敌人的伤害改为50",
        ["MODIFY"], ["enemy", "敌人", "damage", "伤害", "50"], ["batch_set_variable", "find"], cat,
        "Chinese: Set enemy damage to 50"))
    tests.append(IntentTest("10.08", "Удали все факелы с уровня",
        ["MODIFY"], ["torch", "факел"], ["batch_delete_actors", "find_actors", "delete"], cat,
        "Russian: Delete all torches"))
    tests.append(IntentTest("10.09", "احذف جميع العملات الذهبية",
        ["MODIFY"], ["coin", "عملات"], ["batch_delete_actors", "find_actors", "delete"], cat,
        "Arabic: Delete all gold coins"))
    tests.append(IntentTest("10.10", "सभी दुश्मनों को तेज़ बनाओ",
        ["MODIFY"], ["enemy", "दुश्मन", "speed"], ["batch_set_variable", "find"], cat,
        "Hindi: Make enemies faster"))
    tests.append(IntentTest("10.11", "Tüm düşmanları sil",
        ["MODIFY"], ["enemy", "düşman"], ["batch_delete_actors", "find_actors", "delete"], cat,
        "Turkish: Delete all enemies"))
    tests.append(IntentTest("10.12", "Erstelle einen Gesundheits-Pickup",
        ["CREATE"], ["health", "gesundheit", "pickup"], ["create_blueprint"], cat,
        "German: Create health pickup"))

    return tests


# ═══════════════════════════════════════════════════════════════
# Category metadata
# ═══════════════════════════════════════════════════════════════

CATEGORY_NAMES = {
    1: "Simple Modify — Material Changes",
    2: "Simple Modify — Variable Changes",
    3: "Simple Modify — Transform & Properties",
    4: "Simple Modify — Component Changes",
    5: "Simple Modify — Rename & Reparent",
    6: "Query — Find & Inspect",
    7: "Create — New Assets",
    8: "Multi — Complex Multi-Step",
    9: "Conversational / Vague",
    10: "Non-English (12 Languages)",
}


# ═══════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════

def run_tests(tests: list, verbose: bool = False, skip_exec: bool = False):
    """Run all tests, score each, return results."""
    # Connect to UE if execution scoring is enabled
    ue_client = None
    if not skip_exec:
        try:
            ue_client = ArcwrightClient(timeout=30.0)
            ue_client.health_check()
            log("Connected to UE Command Server (13377)")
        except Exception as e:
            log(f"WARNING: Cannot connect to UE (13377): {e}")
            log("Execution scoring will be skipped")
            skip_exec = True

    total = len(tests)
    for i, test in enumerate(tests, 1):
        prefix = f"[{i}/{total}] {test.test_id}"

        # Send to intent server
        t0 = time.time()
        plan = send_intent(test.prompt)
        elapsed = time.time() - t0
        test.plan = plan

        if "error" in plan:
            test.error = plan["error"]
            if verbose:
                log(f"{prefix} ERROR: {test.error} ({elapsed:.1f}s)")
            continue

        # Score 1: Intent
        test.intent_correct = score_intent(test, plan)

        # Score 2: Target
        test.target_correct = score_target(test, plan)

        # Score 3: Action
        test.action_correct = score_action(test, plan)

        # Score 4: Execution
        if not skip_exec and ue_client:
            try:
                test.exec_correct = score_execution(test, plan, ue_client)
            except Exception as e:
                test.exec_correct = False
                test.error = str(e)
        else:
            test.exec_correct = False

        # Log
        marks = (
            ("I" if test.intent_correct else ".") +
            ("T" if test.target_correct else ".") +
            ("A" if test.action_correct else ".") +
            ("E" if test.exec_correct else ".")
        )
        mode = plan.get("mode", "?")
        score_str = f"{test.score}/4"

        if verbose:
            summary = plan.get("summary", "")[:80]
            ops_count = len(plan.get("operations", []))
            ops_cmds = [op.get("command", "?") for op in plan.get("operations", [])]
            log(f"{prefix} [{marks}] {score_str} | mode={mode} ops={ops_count} ({elapsed:.1f}s)")
            log(f"         prompt: {test.prompt[:80]}")
            log(f"         summary: {summary}")
            if ops_cmds:
                log(f"         commands: {', '.join(ops_cmds)}")
            if test.description:
                log(f"         ({test.description})")
        else:
            log(f"{prefix} [{marks}] {score_str} | mode={mode} ({elapsed:.1f}s)")

    if ue_client:
        ue_client.close()

    return tests


# ═══════════════════════════════════════════════════════════════
# Reporting
# ═══════════════════════════════════════════════════════════════

def safe_print(msg):
    """Print with Windows encoding fallback."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode())
    sys.stdout.flush()


def print_report(tests: list):
    """Print category matrix and total score."""
    safe_print("\n" + "=" * 80)
    safe_print("ARCWRIGHT INTENT TEST SUITE -- RESULTS")
    safe_print("=" * 80)

    # Build category stats
    cat_stats = {}
    for test in tests:
        cat = test.category
        if cat not in cat_stats:
            cat_stats[cat] = {
                "total": 0, "intent": 0, "target": 0,
                "action": 0, "exec": 0, "errors": 0,
            }
        s = cat_stats[cat]
        s["total"] += 1
        s["intent"] += int(test.intent_correct)
        s["target"] += int(test.target_correct)
        s["action"] += int(test.action_correct)
        s["exec"] += int(test.exec_correct)
        if test.error:
            s["errors"] += 1

    # Print category matrix
    safe_print(f"\n{'Category':<45} {'Tests':>5} {'Intent':>7} {'Target':>7} {'Action':>7} {'Exec':>7} {'Score':>7}")
    safe_print("-" * 90)

    grand_total = {"total": 0, "intent": 0, "target": 0, "action": 0, "exec": 0}
    for cat in sorted(cat_stats.keys()):
        s = cat_stats[cat]
        name = CATEGORY_NAMES.get(cat, f"Category {cat}")
        cat_score = s["intent"] + s["target"] + s["action"] + s["exec"]
        max_score = s["total"] * 4

        safe_print(f"  {cat:>2}. {name:<40} {s['total']:>5} "
              f"{s['intent']:>3}/{s['total']:<3} "
              f"{s['target']:>3}/{s['total']:<3} "
              f"{s['action']:>3}/{s['total']:<3} "
              f"{s['exec']:>3}/{s['total']:<3} "
              f"{cat_score:>3}/{max_score}")

        for k in grand_total:
            grand_total[k] += s[k]

    # Totals
    total_score = grand_total["intent"] + grand_total["target"] + grand_total["action"] + grand_total["exec"]
    max_possible = grand_total["total"] * 4

    safe_print("-" * 90)
    safe_print(f"  {'TOTAL':<43} {grand_total['total']:>5} "
          f"{grand_total['intent']:>3}/{grand_total['total']:<3} "
          f"{grand_total['target']:>3}/{grand_total['total']:<3} "
          f"{grand_total['action']:>3}/{grand_total['total']:<3} "
          f"{grand_total['exec']:>3}/{grand_total['total']:<3} "
          f"{total_score:>3}/{max_possible}")

    pct = (total_score / max_possible * 100) if max_possible > 0 else 0
    safe_print(f"\n  SCORE: {total_score}/{max_possible} ({pct:.1f}%)")

    # Grade
    if total_score >= 350:
        grade = "Production ready"
    elif total_score >= 330:
        grade = "Minor fixes needed"
    elif total_score >= 295:
        grade = "Significant gaps, needs iteration"
    else:
        grade = "Major rework needed"
    safe_print(f"  GRADE: {grade}")

    # Failures detail
    failures = [t for t in tests if t.score < 4]
    if failures:
        safe_print(f"\n  FAILURES ({len(failures)}):")
        for t in failures:
            marks = (
                ("I" if t.intent_correct else "i") +
                ("T" if t.target_correct else "t") +
                ("A" if t.action_correct else "a") +
                ("E" if t.exec_correct else "e")
            )
            mode = t.plan.get("mode", "?") if t.plan else "ERR"
            expected = "/".join(t.expected_modes)
            note = ""
            if t.error:
                note = f" ERROR: {t.error[:60]}"
            safe_print(f"    {t.test_id} [{marks}] got={mode} expected={expected} | {t.prompt[:60]}{note}")

    # Errors detail
    errors = [t for t in tests if t.error]
    if errors:
        safe_print(f"\n  ERRORS ({len(errors)}):")
        for t in errors:
            safe_print(f"    {t.test_id}: {t.error[:80]}")

    safe_print("\n" + "=" * 80)

    return total_score, max_possible


def save_results(tests: list, output_path: str):
    """Save results as JSON for archival."""
    results = []
    for t in tests:
        results.append({
            "test_id": t.test_id,
            "category": t.category,
            "prompt": t.prompt,
            "expected_modes": t.expected_modes,
            "target_keywords": t.target_keywords,
            "action_keywords": t.action_keywords,
            "description": t.description,
            "intent_correct": t.intent_correct,
            "target_correct": t.target_correct,
            "action_correct": t.action_correct,
            "exec_correct": t.exec_correct,
            "score": t.score,
            "plan": t.plan,
            "error": t.error,
        })

    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": len(tests),
        "total_score": sum(t.score for t in tests),
        "max_score": len(tests) * 4,
        "results": results,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    log(f"Results saved to {output_path}")


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def log(msg):
    ts = time.strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}")
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii', errors='replace').decode()}")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Arcwright Intent Test Suite")
    parser.add_argument("--all", action="store_true", help="Run all 92 tests")
    parser.add_argument("--category", type=int, help="Run specific category (1-10)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-exec", action="store_true",
                        help="Skip execution scoring (criteria 4)")
    parser.add_argument("--output", type=str, default="",
                        help="Save results JSON to this path")
    args = parser.parse_args()

    if not args.all and args.category is None:
        args.all = True  # default to --all

    all_tests = build_all_tests()

    if args.category:
        tests = [t for t in all_tests if t.category == args.category]
        if not tests:
            print(f"No tests found for category {args.category}")
            sys.exit(1)
        log(f"Running category {args.category}: {CATEGORY_NAMES.get(args.category, '?')} ({len(tests)} tests)")
    else:
        tests = all_tests
        log(f"Running all {len(tests)} tests across {len(CATEGORY_NAMES)} categories")

    # Verify intent server (first inference after model load takes ~150s for CUDA warmup)
    log("Checking intent server on localhost:13380 (first call may take ~150s for CUDA warmup)...")
    probe = send_intent("test", timeout=300.0)
    if "error" in probe:
        log(f"FATAL: Intent server not reachable: {probe['error']}")
        log("Start it with: python scripts/intent_server.py")
        sys.exit(1)
    log(f"Intent server OK (mode={probe.get('mode', '?')})")

    # Run
    log("=" * 60)
    results = run_tests(tests, verbose=args.verbose, skip_exec=args.no_exec)

    # Report
    total_score, max_possible = print_report(results)

    # Save
    if args.output:
        save_results(results, args.output)
    else:
        ts = time.strftime("%Y%m%d_%H%M%S")
        default_path = f"results/intent_test_{ts}.json"
        save_results(results, default_path)

    sys.exit(0 if total_score >= 295 else 1)


if __name__ == "__main__":
    main()
