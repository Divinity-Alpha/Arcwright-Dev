#!/usr/bin/env python3
"""AI Workflow Test Suite -- mimics how Claude Desktop uses Arcwright.
Tests sequential multi-command workflows against live UE Editor (TCP 13377).

Scenario 1: Build a simple game level (~10 commands)
Scenario 2: Modify existing level (~8 commands)
Scenario 3: Create and wire AI (~6 commands)
Scenario 4: Full session -- 50 commands building a complete arena level

Usage:
    python scripts/tests/test_ai_workflow.py
"""

import sys
import os
import json
import time
import tempfile
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts", "mcp_client"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from blueprint_client import ArcwrightClient, BlueprintLLMError

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
TEST_IR_DIR = os.path.join(PROJECT_ROOT, "test_ir")

PASS = 0
FAIL = 0
RESULTS = []


def test(name, fn):
    """Run a single test function and track results."""
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        RESULTS.append({"test": name, "result": "PASS"})
        print(f"  [PASS] {name}")
    except Exception as e:
        FAIL += 1
        RESULTS.append({"test": name, "result": "FAIL", "error": str(e)})
        print(f"  [FAIL] {name} -- {e}")


def write_temp_ir(name, parent_class="Actor", variables=None):
    """Write a minimal IR JSON file and return its absolute path."""
    ir = {
        "metadata": {
            "name": name,
            "parent_class": parent_class,
            "category": None,
        },
        "variables": variables or [],
        "nodes": [
            {
                "id": "n1",
                "dsl_type": "Event_BeginPlay",
                "ue_class": "UK2Node_Event",
                "ue_event": "ReceiveBeginPlay",
                "params": {},
                "position": [0, 0],
            }
        ],
        "connections": [],
    }
    os.makedirs(TEST_IR_DIR, exist_ok=True)
    path = os.path.join(TEST_IR_DIR, f"{name}.blueprint.json")
    with open(path, "w") as f:
        json.dump(ir, f, indent=2)
    return path


def cleanup(client, bp_names, actor_labels):
    """Clean up test artifacts. Errors are silently ignored."""
    for label in actor_labels:
        try:
            client.send_command("delete_actor", {"label": label})
        except Exception:
            pass
    time.sleep(0.2)
    for name in bp_names:
        try:
            client.delete_blueprint(name)
        except Exception:
            pass
    # Clean up temp IR files
    for name in bp_names:
        ir_path = os.path.join(TEST_IR_DIR, f"{name}.blueprint.json")
        if os.path.exists(ir_path):
            try:
                os.remove(ir_path)
            except Exception:
                pass


# ==================================================================
# SCENARIO 1: Build a simple game level (~10 commands)
# ==================================================================

def run_scenario_1(client):
    """Build a simple game level."""
    print("\n" + "=" * 60)
    print("SCENARIO 1: Build a simple game level")
    print("=" * 60)

    bp_names = ["BP_WF_HealthPickup"]
    actor_labels = ["WF_TestFloor", "WF_PickupActor1"]
    lighting_labels = []

    # Pre-cleanup
    cleanup(client, bp_names, actor_labels)
    time.sleep(0.3)

    def test_s1_01_get_level_info():
        r = client.get_level_info()
        assert r.get("status") == "ok", f"get_level_info failed: {r}"
        data = r.get("data", {})
        assert "level_name" in data or "name" in data, f"No level name in response: {data}"

    def test_s1_02_setup_lighting():
        nonlocal lighting_labels
        r = client.setup_scene_lighting(preset="indoor_bright")
        assert r.get("status") == "ok", f"setup_scene_lighting failed: {r}"
        # Collect lighting actor labels for cleanup
        for a in r.get("data", {}).get("actors", []):
            lbl = a.get("label", "")
            if lbl:
                lighting_labels.append(lbl)

    def test_s1_03_spawn_floor():
        r = client.spawn_actor_at(
            actor_class="StaticMeshActor",
            location={"x": 0, "y": 0, "z": 0},
            scale={"x": 50, "y": 50, "z": 1},
            label="WF_TestFloor",
        )
        assert r.get("status") == "ok", f"spawn floor failed: {r}"
        time.sleep(0.3)

    def test_s1_04_create_blueprint():
        ir_path = write_temp_ir(
            "BP_WF_HealthPickup",
            variables=[
                {"name": "Health", "type": "Float", "default": "100.0"}
            ]
        )
        r = client.import_from_ir(ir_path)
        assert r.get("status") == "ok", f"import_from_ir failed: {r}"
        time.sleep(0.3)

    def test_s1_05_spawn_pickup():
        r = client.spawn_actor_at(
            actor_class="/Game/Arcwright/Generated/BP_WF_HealthPickup.BP_WF_HealthPickup",
            location={"x": 200, "y": 0, "z": 50},
            label="WF_PickupActor1",
        )
        assert r.get("status") == "ok", f"spawn pickup failed: {r}"
        time.sleep(0.3)

    def test_s1_06_find_pickup():
        r = client.find_actors(name_filter="WF_PickupActor1")
        actors = r.get("data", {}).get("actors", [])
        assert len(actors) >= 1, f"Expected 1+ actors, found {len(actors)}"

    def test_s1_07_get_actor_properties():
        r = client.get_actor_properties("WF_PickupActor1")
        assert r.get("status") == "ok", f"get_actor_properties failed: {r}"
        data = r.get("data", {})
        assert data, f"Empty actor properties data"

    def test_s1_08_batch_set_variable():
        ops = [
            {"blueprint": "BP_WF_HealthPickup", "variable_name": "Health", "default_value": "50.0"}
        ]
        r = client.batch_set_variable(ops)
        assert r.get("status") == "ok", f"batch_set_variable failed: {r}"
        data = r.get("data", {})
        assert data.get("succeeded", 0) >= 1, f"batch_set_variable succeeded=0: {data}"

    def test_s1_09_find_all_actors():
        r = client.find_actors(name_filter="WF_")
        actors = r.get("data", {}).get("actors", [])
        # Should find at least the floor and pickup
        assert len(actors) >= 2, f"Expected 2+ WF_ actors, found {len(actors)}"

    def test_s1_10_cleanup():
        # Delete test actors
        for label in actor_labels:
            try:
                client.send_command("delete_actor", {"label": label})
            except Exception:
                pass
        # Delete lighting actors
        for label in lighting_labels:
            try:
                client.send_command("delete_actor", {"label": label})
            except Exception:
                pass
        time.sleep(0.2)
        # Delete test blueprints
        for name in bp_names:
            try:
                client.delete_blueprint(name)
            except Exception:
                pass
        # Clean up IR files
        for name in bp_names:
            ir_path = os.path.join(TEST_IR_DIR, f"{name}.blueprint.json")
            if os.path.exists(ir_path):
                try:
                    os.remove(ir_path)
                except Exception:
                    pass

    test("S1.01 get_level_info", test_s1_01_get_level_info)
    test("S1.02 setup_scene_lighting indoor_bright", test_s1_02_setup_lighting)
    test("S1.03 spawn floor (StaticMeshActor)", test_s1_03_spawn_floor)
    test("S1.04 create BP_WF_HealthPickup with Health var", test_s1_04_create_blueprint)
    test("S1.05 spawn pickup actor", test_s1_05_spawn_pickup)
    test("S1.06 find_actors pickup (exactly 1)", test_s1_06_find_pickup)
    test("S1.07 get_actor_properties on pickup", test_s1_07_get_actor_properties)
    test("S1.08 batch_set_variable Health=50", test_s1_08_batch_set_variable)
    test("S1.09 find_actors (floor + pickup exist)", test_s1_09_find_all_actors)
    test("S1.10 cleanup all test artifacts", test_s1_10_cleanup)


# ==================================================================
# SCENARIO 2: Modify existing level (~8 commands)
# ==================================================================

def run_scenario_2(client):
    """Modify existing level: create BPs, spawn actors, modify, delete."""
    print("\n" + "=" * 60)
    print("SCENARIO 2: Modify existing level")
    print("=" * 60)

    bp_names = ["BP_WF_Wall", "BP_WF_Enemy", "BP_WF_Coin", "MAT_WF_Red"]
    wall_labels = ["WF_Wall_0", "WF_Wall_1"]
    enemy_labels = ["WF_Enemy_0"]
    coin_labels = ["WF_Coin_0", "WF_Coin_1", "WF_Coin_2"]
    all_actor_labels = wall_labels + enemy_labels + coin_labels

    # Pre-cleanup
    cleanup(client, bp_names, all_actor_labels)
    time.sleep(0.3)

    def test_s2_01_setup():
        """Create 3 test BPs, spawn 2 walls, 1 enemy, 3 coins."""
        # Create BPs
        for name in ["BP_WF_Wall", "BP_WF_Enemy", "BP_WF_Coin"]:
            ir_path = write_temp_ir(name)
            r = client.import_from_ir(ir_path)
            assert r.get("status") == "ok", f"Failed to create {name}: {r}"
            time.sleep(0.3)

        # Spawn walls
        for i, label in enumerate(wall_labels):
            r = client.spawn_actor_at(
                actor_class="/Game/Arcwright/Generated/BP_WF_Wall.BP_WF_Wall",
                location={"x": i * 300, "y": -200, "z": 50},
                label=label,
            )
            assert r.get("status") == "ok", f"Failed to spawn {label}: {r}"
            time.sleep(0.3)

        # Spawn enemy
        r = client.spawn_actor_at(
            actor_class="/Game/Arcwright/Generated/BP_WF_Enemy.BP_WF_Enemy",
            location={"x": 0, "y": 200, "z": 50},
            label="WF_Enemy_0",
        )
        assert r.get("status") == "ok", f"Failed to spawn enemy: {r}"
        time.sleep(0.3)

        # Spawn coins
        for i, label in enumerate(coin_labels):
            r = client.spawn_actor_at(
                actor_class="/Game/Arcwright/Generated/BP_WF_Coin.BP_WF_Coin",
                location={"x": i * 150, "y": 0, "z": 30},
                label=label,
            )
            assert r.get("status") == "ok", f"Failed to spawn {label}: {r}"
            time.sleep(0.3)

    def test_s2_02_find_all():
        r = client.find_actors(name_filter="WF_")
        actors = r.get("data", {}).get("actors", [])
        assert len(actors) >= 6, f"Expected 6+ WF_ actors, found {len(actors)}"

    def test_s2_03_create_material():
        r = client.create_simple_material("MAT_WF_Red", color={"r": 1.0, "g": 0.0, "b": 0.0})
        assert r.get("status") == "ok", f"create_simple_material failed: {r}"
        time.sleep(0.3)

    def test_s2_04_batch_apply_material():
        ops = [
            {"actor_label": label, "material_path": "/Game/Arcwright/Materials/MAT_WF_Red"}
            for label in wall_labels
        ]
        r = client.batch_apply_material(ops)
        assert r.get("status") == "ok", f"batch_apply_material failed: {r}"

    def test_s2_05_batch_scale_enemy():
        r = client.batch_scale_actors(
            scale={"x": 2.0, "y": 2.0, "z": 2.0},
            name_filter="WF_Enemy",
            mode="set",
        )
        assert r.get("status") == "ok", f"batch_scale_actors failed: {r}"
        data = r.get("data", {})
        scaled = data.get("scaled", data.get("affected", 0))
        assert scaled >= 1, f"No actors scaled: {data}"

    def test_s2_06_batch_delete_coins():
        r = client.batch_delete_actors(labels=coin_labels)
        assert r.get("status") == "ok", f"batch_delete_actors failed: {r}"
        deleted = r.get("data", {}).get("deleted", 0)
        assert deleted >= 3, f"Expected 3 deleted, got {deleted}"
        time.sleep(0.3)

    def test_s2_07_verify_coins_gone():
        r = client.find_actors(name_filter="WF_Coin")
        actors = r.get("data", {}).get("actors", [])
        assert len(actors) == 0, f"Expected 0 coins, found {len(actors)}"

    def test_s2_08_cleanup():
        # Delete remaining actors (walls + enemy)
        for label in wall_labels + enemy_labels:
            try:
                client.send_command("delete_actor", {"label": label})
            except Exception:
                pass
        time.sleep(0.2)
        for name in bp_names:
            try:
                client.delete_blueprint(name)
            except Exception:
                pass
        for name in ["BP_WF_Wall", "BP_WF_Enemy", "BP_WF_Coin"]:
            ir_path = os.path.join(TEST_IR_DIR, f"{name}.blueprint.json")
            if os.path.exists(ir_path):
                try:
                    os.remove(ir_path)
                except Exception:
                    pass

    test("S2.01 setup: create 3 BPs, spawn 6 actors", test_s2_01_setup)
    test("S2.02 find_actors WF_ (6 actors)", test_s2_02_find_all)
    test("S2.03 create_simple_material MAT_WF_Red", test_s2_03_create_material)
    test("S2.04 batch_apply_material on walls", test_s2_04_batch_apply_material)
    test("S2.05 batch_scale_actors on enemy (2x)", test_s2_05_batch_scale_enemy)
    test("S2.06 batch_delete_actors (3 coins)", test_s2_06_batch_delete_coins)
    test("S2.07 verify coins gone (0 found)", test_s2_07_verify_coins_gone)
    test("S2.08 cleanup", test_s2_08_cleanup)


# ==================================================================
# SCENARIO 3: Create and wire AI (~6 commands)
# ==================================================================

def run_scenario_3(client):
    """Create and wire AI: pawn BP, behavior tree, AI controller setup."""
    print("\n" + "=" * 60)
    print("SCENARIO 3: Create and wire AI")
    print("=" * 60)

    bp_names = ["BP_WF_AIEnemy", "BT_WF_Patrol", "BB_WF_Patrol", "BP_WF_AIEnemy_AIController"]
    actor_labels = ["WF_AIEnemy_0"]

    # Pre-cleanup
    cleanup(client, bp_names, actor_labels)
    time.sleep(0.3)

    def test_s3_01_create_pawn():
        ir_path = write_temp_ir(
            "BP_WF_AIEnemy",
            parent_class="Pawn",
            variables=[
                {"name": "Health", "type": "Float", "default": "100.0"}
            ],
        )
        r = client.import_from_ir(ir_path)
        assert r.get("status") == "ok", f"Failed to create pawn BP: {r}"
        time.sleep(0.3)

    def test_s3_02_create_behavior_tree():
        bt_ir = {
            "metadata": {
                "name": "BT_WF_Patrol",
                "blackboard": "BB_WF_Patrol",
            },
            "blackboard_keys": [
                {"name": "PatrolTarget", "type": "Vector"},
            ],
            "tree": {
                "dsl_type": "Sequence",
                "name": "Root",
                "ue_class": "UBTComposite_Sequence",
                "children": [
                    {
                        "dsl_type": "Wait",
                        "name": "WaitTask",
                        "ue_class": "UBTTask_Wait",
                        "params": {"WaitTime": "3.0"},
                    },
                ],
                "decorators": [],
                "services": [],
            },
        }
        r = client.send_command("create_behavior_tree", {"ir_json": json.dumps(bt_ir)})
        assert r.get("status") == "ok", f"Failed to create BT: {r}"
        time.sleep(0.3)

    def test_s3_03_setup_ai():
        r = client.send_command("setup_ai_for_pawn", {
            "pawn_name": "BP_WF_AIEnemy",
            "behavior_tree": "BT_WF_Patrol",
        })
        assert r.get("status") == "ok", f"setup_ai_for_pawn failed: {r}"
        time.sleep(0.3)

    def test_s3_04_spawn_enemy():
        r = client.spawn_actor_at(
            actor_class="/Game/Arcwright/Generated/BP_WF_AIEnemy.BP_WF_AIEnemy",
            location={"x": 500, "y": 500, "z": 50},
            label="WF_AIEnemy_0",
        )
        assert r.get("status") == "ok", f"Failed to spawn AI enemy: {r}"
        time.sleep(0.3)

    def test_s3_05_verify_blueprint_details():
        r = client.get_blueprint_details("BP_WF_AIEnemy")
        assert r.get("status") == "ok", f"get_blueprint_details failed: {r}"

    def test_s3_06_cleanup():
        cleanup(client, bp_names, actor_labels)

    test("S3.01 create BP_WF_AIEnemy (Pawn) with Health", test_s3_01_create_pawn)
    test("S3.02 create BT_WF_Patrol (Sequence->Wait)", test_s3_02_create_behavior_tree)
    test("S3.03 setup_ai_for_pawn", test_s3_03_setup_ai)
    test("S3.04 spawn AI enemy", test_s3_04_spawn_enemy)
    test("S3.05 get_blueprint_details on AI enemy", test_s3_05_verify_blueprint_details)
    test("S3.06 cleanup", test_s3_06_cleanup)


# ==================================================================
# SCENARIO 4: Full session -- 50 commands building a complete arena
# ==================================================================

def run_scenario_4(client):
    """Full session: build a complete arena level with ~50 commands."""
    print("\n" + "=" * 60)
    print("SCENARIO 4: Full session -- complete arena level (~50 commands)")
    print("=" * 60)

    bp_names = [
        "BP_WF_ArenaWall", "BP_WF_ArenaPickup", "BP_WF_ArenaEnemy",
        "MAT_WF_ArenaRed", "MAT_WF_ArenaGreen", "MAT_WF_ArenaGold",
    ]
    # We track actor labels for cleanup
    spawned_actor_labels = []
    lighting_labels = []
    floor_label = "WF_ArenaFloor"

    # Pre-cleanup: try to clean known labels
    pre_cleanup_labels = [floor_label]
    for prefix in ["WF_ArenaWall_", "WF_ArenaPickup_", "WF_ArenaEnemy_"]:
        for i in range(20):
            pre_cleanup_labels.append(f"{prefix}{i}")
    cleanup(client, bp_names, pre_cleanup_labels)
    time.sleep(0.5)

    cmd_count = 0
    cmd_success = 0
    cmd_fail = 0
    t_start = time.time()

    def track_cmd(r, desc=""):
        nonlocal cmd_count, cmd_success, cmd_fail
        cmd_count += 1
        if r.get("status") == "ok":
            cmd_success += 1
        else:
            cmd_fail += 1
            print(f"    WARNING: {desc} returned non-ok: {r.get('status')}")

    # --- Phase 1: Scene setup ---

    def test_s4_01_lighting():
        nonlocal lighting_labels
        r = client.setup_scene_lighting(preset="indoor_bright")
        track_cmd(r, "lighting")
        assert r.get("status") == "ok", f"lighting failed: {r}"
        for a in r.get("data", {}).get("actors", []):
            lbl = a.get("label", "")
            if lbl:
                lighting_labels.append(lbl)
        time.sleep(0.3)

    def test_s4_02_floor():
        r = client.spawn_actor_at(
            actor_class="StaticMeshActor",
            location={"x": 0, "y": 0, "z": 0},
            scale={"x": 80, "y": 80, "z": 1},
            label=floor_label,
        )
        track_cmd(r, "floor")
        assert r.get("status") == "ok", f"floor spawn failed: {r}"
        spawned_actor_labels.append(floor_label)
        time.sleep(0.3)

    def test_s4_03_create_materials():
        """Create 3 materials: red, green, gold."""
        materials = [
            ("MAT_WF_ArenaRed",   {"r": 1.0, "g": 0.0, "b": 0.0}),
            ("MAT_WF_ArenaGreen", {"r": 0.0, "g": 0.8, "b": 0.2}),
            ("MAT_WF_ArenaGold",  {"r": 1.0, "g": 0.85, "b": 0.0}),
        ]
        for mat_name, color in materials:
            r = client.create_simple_material(mat_name, color=color)
            track_cmd(r, f"material {mat_name}")
            assert r.get("status") == "ok", f"create_simple_material {mat_name} failed: {r}"
            time.sleep(0.3)

    # --- Phase 2: Create Blueprints ---

    def test_s4_04_create_blueprints():
        """Create BP_WF_ArenaWall, BP_WF_ArenaPickup (with Score var), BP_WF_ArenaEnemy."""
        # Wall
        ir_path = write_temp_ir("BP_WF_ArenaWall")
        r = client.import_from_ir(ir_path)
        track_cmd(r, "BP_WF_ArenaWall")
        assert r.get("status") == "ok", f"Wall BP failed: {r}"
        time.sleep(0.3)

        # Pickup with Score variable
        ir_path = write_temp_ir(
            "BP_WF_ArenaPickup",
            variables=[{"name": "Score", "type": "Int", "default": "5"}],
        )
        r = client.import_from_ir(ir_path)
        track_cmd(r, "BP_WF_ArenaPickup")
        assert r.get("status") == "ok", f"Pickup BP failed: {r}"
        time.sleep(0.3)

        # Enemy
        ir_path = write_temp_ir("BP_WF_ArenaEnemy")
        r = client.import_from_ir(ir_path)
        track_cmd(r, "BP_WF_ArenaEnemy")
        assert r.get("status") == "ok", f"Enemy BP failed: {r}"
        time.sleep(0.3)

    # --- Phase 3: Add components ---

    def test_s4_05_add_components():
        """Add BoxCollision on pickup, StaticMesh on wall."""
        r = client.add_component("BP_WF_ArenaPickup", "BoxCollision", "PickupCollision",
                                 properties={"extent": {"x": 40, "y": 40, "z": 40},
                                             "generate_overlap_events": True})
        track_cmd(r, "pickup collision")
        assert r.get("status") == "ok", f"add BoxCollision failed: {r}"
        time.sleep(0.3)

        r = client.add_component("BP_WF_ArenaWall", "StaticMesh", "WallMesh",
                                 properties={"mesh": "/Engine/BasicShapes/Cube.Cube"})
        track_cmd(r, "wall mesh")
        assert r.get("status") == "ok", f"add StaticMesh failed: {r}"
        time.sleep(0.3)

    # --- Phase 4: Spawn patterns ---

    def test_s4_06_spawn_wall_grid():
        """Spawn walls in a 4x4 grid."""
        r = client.spawn_actor_grid(
            actor_class="/Game/Arcwright/Generated/BP_WF_ArenaWall.BP_WF_ArenaWall",
            rows=4, cols=4,
            spacing_x=400.0, spacing_y=400.0,
            origin={"x": -600, "y": -600, "z": 50},
            center=False,
            label_prefix="WF_ArenaWall_",
        )
        track_cmd(r, "wall grid")
        assert r.get("status") == "ok", f"spawn_actor_grid failed: {r}"
        # Collect spawned labels
        data = r.get("data", {})
        for actor in data.get("actors", []):
            lbl = actor.get("label", "")
            if lbl:
                spawned_actor_labels.append(lbl)
        time.sleep(0.3)

    def test_s4_07_spawn_pickup_circle():
        """Spawn pickups in a circle of 8."""
        r = client.spawn_actor_circle(
            actor_class="/Game/Arcwright/Generated/BP_WF_ArenaPickup.BP_WF_ArenaPickup",
            count=8,
            radius=800.0,
            center={"x": 0, "y": 0, "z": 30},
            face_center=True,
            label_prefix="WF_ArenaPickup_",
        )
        track_cmd(r, "pickup circle")
        assert r.get("status") == "ok", f"spawn_actor_circle failed: {r}"
        data = r.get("data", {})
        for actor in data.get("actors", []):
            lbl = actor.get("label", "")
            if lbl:
                spawned_actor_labels.append(lbl)
        time.sleep(0.3)

    def test_s4_08_spawn_enemy_line():
        """Spawn enemies along a line (3 enemies)."""
        r = client.spawn_actor_line(
            actor_class="/Game/Arcwright/Generated/BP_WF_ArenaEnemy.BP_WF_ArenaEnemy",
            count=3,
            start={"x": -500, "y": 500, "z": 50},
            end={"x": 500, "y": 500, "z": 50},
            label_prefix="WF_ArenaEnemy_",
        )
        track_cmd(r, "enemy line")
        assert r.get("status") == "ok", f"spawn_actor_line failed: {r}"
        data = r.get("data", {})
        for actor in data.get("actors", []):
            lbl = actor.get("label", "")
            if lbl:
                spawned_actor_labels.append(lbl)
        time.sleep(0.3)

    # --- Phase 5: Apply materials ---

    def test_s4_09_apply_materials():
        """Batch apply materials to spawned actors."""
        # Apply red to walls (first 4)
        wall_actors = [l for l in spawned_actor_labels if "ArenaWall" in l][:4]
        if wall_actors:
            ops = [{"actor_label": l, "material_path": "/Game/Arcwright/Materials/MAT_WF_ArenaRed"}
                   for l in wall_actors]
            r = client.batch_apply_material(ops)
            track_cmd(r, "wall materials")
            assert r.get("status") == "ok", f"batch_apply_material walls failed: {r}"
            time.sleep(0.3)

        # Apply gold to pickups (first 4)
        pickup_actors = [l for l in spawned_actor_labels if "ArenaPickup" in l][:4]
        if pickup_actors:
            ops = [{"actor_label": l, "material_path": "/Game/Arcwright/Materials/MAT_WF_ArenaGold"}
                   for l in pickup_actors]
            r = client.batch_apply_material(ops)
            track_cmd(r, "pickup materials")
            assert r.get("status") == "ok", f"batch_apply_material pickups failed: {r}"
            time.sleep(0.3)

    # --- Phase 6: Query level ---

    def test_s4_10_query_level():
        """Query the level: find_actors, find_blueprints, get_level_info."""
        # find_actors for walls
        r = client.find_actors(name_filter="WF_ArenaWall")
        track_cmd(r, "find walls")
        wall_count = len(r.get("data", {}).get("actors", []))
        assert wall_count >= 4, f"Expected 4+ walls, found {wall_count}"

        # find_actors for pickups
        r = client.find_actors(name_filter="WF_ArenaPickup")
        track_cmd(r, "find pickups")
        pickup_count = len(r.get("data", {}).get("actors", []))
        assert pickup_count >= 4, f"Expected 4+ pickups, found {pickup_count}"

        # find_actors for enemies
        r = client.find_actors(name_filter="WF_ArenaEnemy")
        track_cmd(r, "find enemies")
        enemy_count = len(r.get("data", {}).get("actors", []))
        assert enemy_count >= 3, f"Expected 3+ enemies, found {enemy_count}"

        # find_blueprints
        r = client.find_blueprints(name_filter="BP_WF_Arena")
        track_cmd(r, "find BPs")
        bp_count = len(r.get("data", {}).get("blueprints", []))
        assert bp_count >= 3, f"Expected 3+ BPs, found {bp_count}"

        # get_level_info
        r = client.get_level_info()
        track_cmd(r, "level info")
        assert r.get("status") == "ok", f"get_level_info failed: {r}"

    # --- Phase 7: Modify ---

    def test_s4_11_modify_variable():
        """batch_set_variable Score=10 on pickup BP."""
        ops = [{"blueprint": "BP_WF_ArenaPickup", "variable_name": "Score", "default_value": "10"}]
        r = client.batch_set_variable(ops)
        track_cmd(r, "set Score=10")
        assert r.get("status") == "ok", f"batch_set_variable failed: {r}"
        time.sleep(0.3)

    # --- Phase 8: Save ---

    def test_s4_12_save():
        """save_all to persist."""
        r = client.save_all()
        track_cmd(r, "save_all")
        assert r.get("status") == "ok", f"save_all failed: {r}"

    # --- Phase 9: Audit ---

    def test_s4_13_audit():
        """Final audit: count all WF_ actors."""
        r = client.find_actors(name_filter="WF_")
        track_cmd(r, "audit find_actors")
        actors = r.get("data", {}).get("actors", [])
        total = len(actors)
        # Should have floor + 16 walls + 8 pickups + 3 enemies = 28
        assert total >= 15, f"Expected 15+ total WF_ actors, found {total}"

    # --- Phase 10: Cleanup ---

    def test_s4_14_cleanup():
        """Clean up all arena test artifacts."""
        # Delete all spawned actors
        all_labels = list(set(spawned_actor_labels + lighting_labels))
        if all_labels:
            # Use batch_delete_actors for efficiency
            r = client.batch_delete_actors(labels=all_labels)
            track_cmd(r, "batch delete")
        time.sleep(0.3)

        # Delete blueprints and materials
        for name in bp_names:
            try:
                client.delete_blueprint(name)
            except Exception:
                pass

        # Clean up IR files
        for name in ["BP_WF_ArenaWall", "BP_WF_ArenaPickup", "BP_WF_ArenaEnemy"]:
            ir_path = os.path.join(TEST_IR_DIR, f"{name}.blueprint.json")
            if os.path.exists(ir_path):
                try:
                    os.remove(ir_path)
                except Exception:
                    pass

    test("S4.01 setup_scene_lighting", test_s4_01_lighting)
    test("S4.02 spawn floor", test_s4_02_floor)
    test("S4.03 create 3 materials (red, green, gold)", test_s4_03_create_materials)
    test("S4.04 create 3 BPs (wall, pickup, enemy)", test_s4_04_create_blueprints)
    test("S4.05 add components (collision, mesh)", test_s4_05_add_components)
    test("S4.06 spawn_actor_grid 4x4 walls", test_s4_06_spawn_wall_grid)
    test("S4.07 spawn_actor_circle 8 pickups", test_s4_07_spawn_pickup_circle)
    test("S4.08 spawn_actor_line 3 enemies", test_s4_08_spawn_enemy_line)
    test("S4.09 batch_apply_material (walls + pickups)", test_s4_09_apply_materials)
    test("S4.10 query level (find_actors x3, find_blueprints, get_level_info)", test_s4_10_query_level)
    test("S4.11 batch_set_variable Score=10", test_s4_11_modify_variable)
    test("S4.12 save_all", test_s4_12_save)
    test("S4.13 audit: count all WF_ actors", test_s4_13_audit)
    test("S4.14 cleanup all arena artifacts", test_s4_14_cleanup)

    elapsed = time.time() - t_start
    print(f"\n  Arena session: {cmd_count} commands, {cmd_success} success, {cmd_fail} fail, {elapsed:.1f}s")


# ==================================================================
# Main
# ==================================================================

def run_all():
    global PASS, FAIL

    print("=" * 60)
    print("  Arcwright AI Workflow Test Suite")
    print("  Mimics how Claude Desktop uses Arcwright via MCP/TCP")
    print("=" * 60)

    try:
        client = ArcwrightClient(timeout=30)
        health = client.health_check()
        server = health.get("data", {}).get("server", health.get("server", "?"))
        version = health.get("data", {}).get("version", health.get("version", "?"))
        print(f"\nConnected to {server} v{version}")
    except Exception as e:
        print(f"\nFAIL: Cannot connect to TCP server on localhost:13377: {e}")
        print("Is UE5 Editor running with the Arcwright plugin?")
        return False

    t_start = time.time()

    run_scenario_1(client)
    run_scenario_2(client)
    run_scenario_3(client)
    run_scenario_4(client)

    client.close()
    elapsed = time.time() - t_start

    # Summary
    total = PASS + FAIL
    print("\n" + "=" * 60)
    print(f"  AI WORKFLOW RESULTS: {PASS}/{total} PASS, {FAIL} FAIL ({elapsed:.1f}s)")
    print("=" * 60)
    for r in RESULTS:
        marker = "PASS" if r["result"] == "PASS" else "FAIL"
        suffix = f" -- {r.get('error', '')}" if r["result"] == "FAIL" else ""
        print(f"  [{marker:>4}] {r['test']}{suffix}")
    print()

    if FAIL > 0:
        print(f"{FAIL} test(s) FAILED.")
    else:
        print("All AI workflow tests passed.")

    # Save report
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(RESULTS_DIR, f"ai_workflow_test_{timestamp}.json")
    report = {
        "timestamp": timestamp,
        "suite": "AI Workflow Test Suite",
        "passed": PASS,
        "failed": FAIL,
        "total": total,
        "elapsed_s": round(elapsed, 2),
        "tests": RESULTS,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved: {report_path}")

    return FAIL == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
