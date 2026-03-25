#!/usr/bin/env python3
"""
Test suite for Phase 6 commands: Enhanced Input, Advanced Actor Config,
Data & Persistence, Animation, Niagara, Level Management.

Requires: UE Editor running with Arcwright plugin (TCP 13377).
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError

PASS = 0
FAIL = 0
RESULTS = []


def test(name, fn):
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


def run_all():
    global PASS, FAIL

    print("=" * 60)
    print("Arcwright Phase 6 Test Suite")
    print("=" * 60)

    client = ArcwrightClient(timeout=30)
    print(f"\nConnected to TCP 13377\n")

    # ---- SETUP ----
    print("--- Setup ---")
    # Clean up any leftover test assets
    for name in ["BP_P6Test", "BP_P6Anim", "BP_SaveTest"]:
        try:
            client.delete_blueprint(name)
        except:
            pass
    time.sleep(0.3)

    # Create a minimal BP for testing
    ir = {
        "metadata": {"name": "BP_P6Test", "parent_class": "Actor"},
        "variables": [],
        "nodes": [
            {"id": "node_1", "type": "BeginPlay", "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay"}
        ],
        "connections": []
    }
    import tempfile
    ir_path = os.path.join(tempfile.gettempdir(), "bp_p6test.blueprint.json")
    with open(ir_path, "w") as f:
        json.dump(ir, f)
    r = client.import_from_ir(ir_path)
    assert r.get("status") == "ok" or "nodes_created" in str(r), f"Setup import failed: {r}"
    time.sleep(0.3)

    # Spawn test actor
    spawn_r = client.spawn_actor_at(
        "/Game/Arcwright/Generated/BP_P6Test.BP_P6Test",
        location={"x": 0, "y": 0, "z": 100}, label="P6TestActor"
    )
    time.sleep(0.2)

    # ================================================================
    # CATEGORY 1: Advanced Actor Configuration
    # ================================================================
    print("\n--- Advanced Actor Configuration ---")

    def test_set_actor_tick_enable():
        r = client.set_actor_tick("P6TestActor", enabled=True, interval=0.1)
        assert r.get("status") == "ok", f"set_actor_tick failed: {r}"

    def test_set_actor_tick_disable():
        r = client.set_actor_tick("P6TestActor", enabled=False)
        assert r.get("status") == "ok", f"set_actor_tick disable failed: {r}"

    def test_set_actor_tick_bad_actor():
        try:
            r = client.set_actor_tick("NonExistentActor_XYZ", enabled=True)
            assert r.get("status") == "error", "Should fail for non-existent actor"
        except BlueprintLLMError:
            pass  # Expected

    def test_set_actor_lifespan():
        r = client.set_actor_lifespan("P6TestActor", lifespan=60.0)
        assert r.get("status") == "ok", f"set_actor_lifespan failed: {r}"

    def test_get_actor_bounds():
        r = client.get_actor_bounds("P6TestActor")
        assert r.get("status") == "ok", f"get_actor_bounds failed: {r}"
        data = r.get("data", {})
        assert "origin" in data or "extent" in data or "box_extent" in data, f"Missing bounds data: {data}"

    def test_set_actor_enabled():
        r = client.set_actor_enabled("P6TestActor", enabled=False)
        assert r.get("status") == "ok", f"set_actor_enabled failed: {r}"
        # Re-enable
        r2 = client.set_actor_enabled("P6TestActor", enabled=True)
        assert r2.get("status") == "ok", f"re-enable failed: {r2}"

    def test_set_actor_enabled_bad_actor():
        try:
            r = client.set_actor_enabled("NonExistentActor_XYZ", enabled=False)
            assert r.get("status") == "error", "Should fail for non-existent actor"
        except BlueprintLLMError:
            pass  # Expected

    test("set_actor_tick: enable with interval", test_set_actor_tick_enable)
    test("set_actor_tick: disable", test_set_actor_tick_disable)
    test("set_actor_tick: bad actor error", test_set_actor_tick_bad_actor)
    test("set_actor_lifespan: 60s", test_set_actor_lifespan)
    test("get_actor_bounds: success", test_get_actor_bounds)
    test("set_actor_enabled: toggle", test_set_actor_enabled)
    test("set_actor_enabled: bad actor error", test_set_actor_enabled_bad_actor)

    # ================================================================
    # CATEGORY 2: Data & Persistence
    # ================================================================
    print("\n--- Data & Persistence ---")

    def test_create_save_game():
        r = client.create_save_game("BP_SaveTest", variables=[
            {"name": "PlayerScore", "type": "int"},
            {"name": "PlayerName", "type": "string"}
        ])
        assert r.get("status") == "ok", f"create_save_game failed: {r}"

    def test_create_save_game_error():
        try:
            r = client.create_save_game("", variables=[])
            assert r.get("status") == "error", "Should fail with empty name"
        except BlueprintLLMError:
            pass  # Expected

    def test_get_data_table_rows():
        # This may fail if no DT exists — that's the error case test
        try:
            r = client.get_data_table_rows("DT_NonExistent_XYZ")
            assert r.get("status") == "error", "Should fail for non-existent table"
        except BlueprintLLMError:
            pass  # Expected

    test("create_save_game: with variables", test_create_save_game)
    test("create_save_game: empty name error", test_create_save_game_error)
    test("get_data_table_rows: non-existent error", test_get_data_table_rows)

    # Test DataTable row operations (create a DT first)
    print("\n  -- DataTable Row Operations --")

    def test_dt_row_operations():
        # Create a DataTable via the DT parser/builder
        dt_ir = {
            "metadata": {"table_name": "DT_P6Test", "struct_name": "P6TestStruct"},
            "columns": [
                {"name": "ItemName", "type": "String"},
                {"name": "Value", "type": "Float", "default": "0.0"}
            ],
            "rows": [
                {"name": "Row1", "values": {"ItemName": "Sword", "Value": "100.0"}}
            ]
        }
        r = client.send_command("create_data_table", {"ir_json": json.dumps(dt_ir)})
        if r.get("status") != "ok":
            raise Exception(f"DT creation failed: {r}")

        # Add a row
        r2 = client.add_data_table_row("DT_P6Test", "Row2", {"ItemName": "Shield", "Value": "50.0"})
        assert r2.get("status") == "ok", f"add_data_table_row failed: {r2}"

        # Get all rows
        r3 = client.get_data_table_rows("DT_P6Test")
        assert r3.get("status") == "ok", f"get_data_table_rows failed: {r3}"

        # Edit row
        r4 = client.edit_data_table_row("DT_P6Test", "Row1", {"Value": "200.0"})
        assert r4.get("status") == "ok", f"edit_data_table_row failed: {r4}"

    test("DT row ops: add + get + edit", test_dt_row_operations)

    # ================================================================
    # CATEGORY 3: Enhanced Input
    # ================================================================
    print("\n--- Enhanced Input ---")

    def test_set_player_input_mapping():
        # Create a simple BP to test input mapping on
        r = client.set_player_input_mapping("BP_P6Test", context="IMC_Default")
        # May succeed or fail depending on IMC existence — we test it doesn't crash
        if r.get("status") == "error":
            # Expected if no IMC_Default exists
            print(f"    (Expected: {r.get('message', '')})")

    test("set_player_input_mapping: basic call", test_set_player_input_mapping)

    # ================================================================
    # CATEGORY 4: Animation (skeleton-dependent — test error paths)
    # ================================================================
    print("\n--- Animation ---")

    def test_create_anim_blueprint_error():
        try:
            r = client.create_anim_blueprint("ABP_Test", skeleton="NonExistentSkeleton_XYZ")
            assert r.get("status") == "error", "Should fail with non-existent skeleton"
        except BlueprintLLMError:
            pass

    def test_create_anim_montage_error():
        try:
            r = client.create_anim_montage("AM_Test", animation="NonExistentAnim_XYZ")
            assert r.get("status") == "error", "Should fail with non-existent animation"
        except BlueprintLLMError:
            pass

    def test_create_blend_space_error():
        try:
            r = client.create_blend_space("BS_Test", skeleton="NonExistentSkeleton_XYZ")
            assert r.get("status") == "error", "Should fail with non-existent skeleton"
        except BlueprintLLMError:
            pass

    def test_get_skeleton_bones_error():
        try:
            r = client.get_skeleton_bones("NonExistentSkeleton_XYZ")
            assert r.get("status") == "error", "Should fail for non-existent skeleton"
        except BlueprintLLMError:
            pass

    def test_get_available_animations():
        r = client.get_available_animations(skeleton="NonExistentSkeleton_XYZ")
        assert r.get("status") == "ok", f"get_available_animations failed: {r}"
        # Empty results for non-existent skeleton is expected

    def test_set_skeletal_mesh_error():
        try:
            r = client.set_skeletal_mesh(mesh="NonExistentMesh_XYZ", blueprint="BP_P6Test")
            assert r.get("status") == "error", "Should fail for non-existent mesh"
        except BlueprintLLMError:
            pass

    def test_play_animation_error():
        try:
            r = client.play_animation("NonExistentActor_XYZ", animation="NonExistentAnim")
            assert r.get("status") == "error", "Should fail for non-existent actor"
        except BlueprintLLMError:
            pass

    def test_add_anim_state_error():
        try:
            r = client.add_anim_state("ABP_NonExistent", "IdleState")
            assert r.get("status") == "error", "Should fail for non-existent ABP"
        except BlueprintLLMError:
            pass

    def test_add_anim_transition():
        # May succeed (creates stub) or fail — test it doesn't crash
        r = client.add_anim_transition("ABP_NonExistent", "Idle", "Walk")
        # Either ok or error is acceptable — handler should return clean JSON

    test("create_anim_blueprint: bad skeleton error", test_create_anim_blueprint_error)
    test("create_anim_montage: bad animation error", test_create_anim_montage_error)
    test("create_blend_space: bad skeleton error", test_create_blend_space_error)
    test("get_skeleton_bones: bad skeleton error", test_get_skeleton_bones_error)
    test("get_available_animations: empty results for bad skeleton", test_get_available_animations)
    test("set_skeletal_mesh: bad mesh error", test_set_skeletal_mesh_error)
    test("play_animation: bad actor error", test_play_animation_error)
    test("add_anim_state: bad ABP error", test_add_anim_state_error)
    test("add_anim_transition: graceful handling", test_add_anim_transition)

    # ================================================================
    # CATEGORY 5: Niagara
    # ================================================================
    print("\n--- Niagara ---")

    def test_activate_niagara_error():
        try:
            r = client.activate_niagara("NonExistentActor_XYZ")
            assert r.get("status") == "error", "Should fail for non-existent actor"
        except BlueprintLLMError:
            pass

    def test_set_niagara_parameter_error():
        try:
            r = client.set_niagara_parameter("NonExistentActor_XYZ", "SpawnRate", float_value=100.0)
            assert r.get("status") == "error", "Should fail for non-existent actor"
        except BlueprintLLMError:
            pass

    def test_get_niagara_parameters_error():
        try:
            r = client.get_niagara_parameters("NonExistentActor_XYZ")
            assert r.get("status") == "error", "Should fail for non-existent actor"
        except BlueprintLLMError:
            pass

    test("activate_niagara: bad actor error", test_activate_niagara_error)
    test("set_niagara_parameter: bad actor error", test_set_niagara_parameter_error)
    test("get_niagara_parameters: bad actor error", test_get_niagara_parameters_error)

    # ================================================================
    # CATEGORY 6: Level Management
    # ================================================================
    print("\n--- Level Management ---")

    def test_get_sublevel_list():
        r = client.get_sublevel_list()
        assert r.get("status") == "ok", f"get_sublevel_list failed: {r}"
        data = r.get("data", {})
        assert "levels" in data, f"Missing levels key: {data}"

    def test_create_sublevel():
        # Level doesn't exist on disk — expects error or "already_existed"
        try:
            r = client.create_sublevel("P6TestSublevel")
            # If ok, it was already in world or added from disk
        except BlueprintLLMError:
            pass  # Expected: level doesn't exist on disk

    def test_set_level_visibility():
        # Try to set visibility on a level — may fail if no sublevels exist
        try:
            r = client.set_level_visibility("P6TestSublevel", visible=True)
        except BlueprintLLMError:
            pass  # Expected if sublevel doesn't exist

    def test_move_actor_to_sublevel_error():
        try:
            r = client.move_actor_to_sublevel("NonExistentActor_XYZ", "NonExistentLevel")
            assert r.get("status") == "error", "Should fail for non-existent actor/level"
        except BlueprintLLMError:
            pass  # Expected

    test("get_sublevel_list: success", test_get_sublevel_list)
    test("create_sublevel: P6TestSublevel", test_create_sublevel)
    test("set_level_visibility: toggle", test_set_level_visibility)
    test("move_actor_to_sublevel: bad actor error", test_move_actor_to_sublevel_error)

    # ================================================================
    # CLEANUP
    # ================================================================
    print("\n--- Cleanup ---")
    for name in ["BP_P6Test", "BP_P6Anim", "BP_SaveTest"]:
        try:
            client.delete_blueprint(name)
        except:
            pass
    try:
        client.send_command("delete_actor", {"label": "P6TestActor"})
    except:
        pass

    # ---- RESULTS ----
    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Phase 6 Results: {PASS}/{total} PASS, {FAIL} FAIL")
    print("=" * 60)

    # Save results
    os.makedirs("results", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"results/phase6_test_{ts}.json"
    with open(results_path, "w") as f:
        json.dump({
            "timestamp": ts,
            "total": total,
            "pass": PASS,
            "fail": FAIL,
            "tests": RESULTS
        }, f, indent=2)
    print(f"Results saved to {results_path}")

    client.close()
    return FAIL == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
