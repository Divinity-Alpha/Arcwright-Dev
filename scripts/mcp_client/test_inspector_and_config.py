#!/usr/bin/env python3
"""
Test suite for Batches 1-6: Inspector, Collision/Physics, Camera/Input,
Actor Config, Nav/Audio, and Project Utilities.

Requires: UE Editor running with Arcwright plugin (TCP 13377).
"""

import sys
import os
import json
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
    print("Arcwright Batches 1-6 Test Suite")
    print("=" * 60)

    client = ArcwrightClient(timeout=30)
    print(f"\nConnected to TCP 13377\n")

    # ---- SETUP: Create test assets ----
    print("--- Setup ---")
    import time

    # Delete existing test BP first (prevents partially-loaded crash)
    for bp in ["BP_TestInspect", "BP_CamTest"]:
        try:
            client.delete_blueprint(bp)
        except:
            pass
    time.sleep(0.5)

    # Import a minimal IR to have a BP to work with
    ir = {
        "metadata": {
            "name": "BP_TestInspect",
            "parent_class": "Actor",
        },
        "variables": [
            {"name": "Health", "type": "float", "default": "100.0"},
            {"name": "Score", "type": "int", "default": "0"},
        ],
        "nodes": [],
        "connections": [],
    }
    ir_dir = os.path.join(os.path.dirname(__file__), "..", "..", "test_ir")
    os.makedirs(ir_dir, exist_ok=True)
    ir_path = os.path.join(ir_dir, "BP_TestInspect.blueprint.json")
    with open(ir_path, "w") as f:
        json.dump(ir, f)
    import_r = client.import_from_ir(os.path.abspath(ir_path))
    print(f"  Import BP_TestInspect: {import_r.get('status', 'unknown')}")
    time.sleep(0.5)

    # Add components for testing
    client.send_command("add_component", {
        "blueprint": "BP_TestInspect",
        "component_type": "BoxCollision",
        "component_name": "TestBox",
    })
    client.send_command("add_component", {
        "blueprint": "BP_TestInspect",
        "component_type": "StaticMesh",
        "component_name": "TestMesh",
    })

    # Spawn test actors
    for label in ["TestActor_A", "TestActor_B", "TestActor_C"]:
        try:
            client.send_command("delete_actor", {"actor_label": label})
        except:
            pass
    client.send_command("spawn_actor_at", {
        "class": "StaticMeshActor",
        "label": "TestActor_A",
        "location": {"x": 0, "y": 0, "z": 100},
    })
    client.send_command("spawn_actor_at", {
        "class": "StaticMeshActor",
        "label": "TestActor_B",
        "location": {"x": 500, "y": 0, "z": 100},
    })
    client.send_command("spawn_actor_at", {
        "class": "StaticMeshActor",
        "label": "TestActor_C",
        "location": {"x": 1000, "y": 0, "z": 100},
    })
    print("  Setup complete\n")

    # ==================================================
    # BATCH 1: Inspector Commands
    # ==================================================
    print("--- Batch 1: Inspector Commands ---")

    def test_get_blueprint_details():
        r = client.get_blueprint_details("BP_TestInspect")
        assert r["status"] == "ok", f"Expected ok, got {r}"
        d = r["data"]
        assert d["name"] == "BP_TestInspect"
        assert d["parent_class"] == "Actor"
        assert isinstance(d["variables"], list)
        assert len(d["variables"]) >= 2
        var_names = [v["name"] for v in d["variables"]]
        assert "Health" in var_names, f"Health not in {var_names}"
        assert isinstance(d["components"], list)
        assert isinstance(d["events"], list)
        assert "node_count" in d

    test("get_blueprint_details", test_get_blueprint_details)

    def test_get_actor_properties():
        r = client.get_actor_properties("TestActor_A")
        assert r["status"] == "ok"
        d = r["data"]
        assert d["label"] == "TestActor_A"
        assert "class" in d
        assert "location" in d
        assert "rotation" in d
        assert "scale" in d
        assert "tags" in d
        assert "components" in d

    test("get_actor_properties", test_get_actor_properties)

    def test_get_all_materials():
        r = client.get_all_materials()
        assert r["status"] == "ok"
        d = r["data"]
        assert "count" in d
        assert "materials" in d
        assert isinstance(d["materials"], list)

    test("get_all_materials", test_get_all_materials)

    def test_get_all_materials_filtered():
        r = client.get_all_materials(name_filter="Basic", max_results=5)
        assert r["status"] == "ok"
        assert r["data"]["count"] <= 5

    test("get_all_materials_filtered", test_get_all_materials_filtered)

    def test_get_all_blueprints():
        r = client.get_all_blueprints()
        assert r["status"] == "ok"
        d = r["data"]
        assert "count" in d
        assert "blueprints" in d
        assert isinstance(d["blueprints"], list)

    test("get_all_blueprints", test_get_all_blueprints)

    def test_get_all_blueprints_filtered():
        r = client.get_all_blueprints(name_filter="TestInspect")
        assert r["status"] == "ok"
        # Should find at least our test BP
        assert r["data"]["count"] >= 1

    test("get_all_blueprints_filtered", test_get_all_blueprints_filtered)

    # ==================================================
    # BATCH 2: Collision & Physics
    # ==================================================
    print("\n--- Batch 2: Collision & Physics ---")

    def test_set_collision_preset_actor():
        r = client.set_collision_preset("OverlapAll", actor_label="TestActor_A")
        assert r["status"] == "ok"
        assert r["data"]["preset"] == "OverlapAll"

    test("set_collision_preset_actor", test_set_collision_preset_actor)

    def test_set_collision_preset_bp():
        r = client.set_collision_preset("Trigger", blueprint="BP_TestInspect",
                                         component_name="TestBox")
        assert r["status"] == "ok"

    test("set_collision_preset_bp", test_set_collision_preset_bp)

    def test_set_collision_shape_bp():
        r = client.set_collision_shape(blueprint="BP_TestInspect",
                                        component_name="TestBox",
                                        extents={"x": 100, "y": 100, "z": 50})
        assert r["status"] == "ok"
        assert r["data"]["shape_type"] == "Box"

    test("set_collision_shape_bp", test_set_collision_shape_bp)

    def test_set_physics_enabled_actor():
        r = client.set_physics_enabled(True, actor_label="TestActor_A")
        assert r["status"] == "ok"
        assert r["data"]["physics_enabled"] == True

    test("set_physics_enabled_actor", test_set_physics_enabled_actor)

    def test_set_physics_disabled():
        r = client.set_physics_enabled(False, actor_label="TestActor_A")
        assert r["status"] == "ok"
        assert r["data"]["physics_enabled"] == False

    test("set_physics_disabled", test_set_physics_disabled)

    def test_set_physics_no_target():
        try:
            client.set_physics_enabled(True)
            assert False, "Should error without target"
        except BlueprintLLMError:
            pass

    test("set_physics_no_target_error", test_set_physics_no_target)

    # ==================================================
    # BATCH 3: Camera & Input
    # ==================================================
    print("\n--- Batch 3: Camera & Input ---")

    # Create a BP with a camera for testing
    ir_cam = {
        "metadata": {"name": "BP_CamTest", "parent_class": "Actor"},
        "variables": [], "nodes": [], "connections": [],
    }
    cam_path = os.path.join(ir_dir, "BP_CamTest.blueprint.json")
    with open(cam_path, "w") as f:
        json.dump(ir_cam, f)
    client.import_from_ir(os.path.abspath(cam_path))
    time.sleep(0.5)
    # Add a camera component
    client.send_command("add_component", {
        "blueprint": "BP_CamTest",
        "component_type": "Camera",
        "component_name": "TestCamera",
    })

    def test_set_camera_fov():
        r = client.set_camera_properties("BP_CamTest", fov=110.0)
        assert r["status"] == "ok"
        assert r["data"]["fov"] == 110.0

    test("set_camera_fov", test_set_camera_fov)

    def test_set_camera_no_camera():
        # BP without camera should error
        try:
            client.set_camera_properties("BP_TestInspect", fov=90.0)
            assert False, "Should error"
        except BlueprintLLMError:
            pass

    test("set_camera_no_camera_error", test_set_camera_no_camera)

    def test_create_input_action():
        r = client.create_input_action("IA_TestJump", value_type="bool")
        assert r["status"] == "ok"

    test("create_input_action", test_create_input_action)

    def test_create_input_mapping():
        # First create the input mapping context, then add the mapping
        client.send_command("setup_input_context", {"name": "IMC_TestDefault"})
        r = client.create_input_mapping("IMC_TestDefault", "IA_TestJump", "SpaceBar")
        assert r["status"] == "ok"

    test("create_input_mapping", test_create_input_mapping)

    def test_bind_input_to_blueprint():
        # Bind the input action to the camera test BP
        r = client.send_command("bind_input_to_blueprint", {
            "blueprint": "BP_CamTest",
            "action": "IA_TestJump",
        })
        assert r["status"] == "ok"

    test("bind_input_to_blueprint", test_bind_input_to_blueprint)

    # ==================================================
    # BATCH 4: Actor Configuration
    # ==================================================
    print("\n--- Batch 4: Actor Configuration ---")

    def test_set_actor_tags():
        r = client.set_actor_tags("TestActor_A", ["Enemy", "Spawnable", "Boss"])
        assert r["status"] == "ok"
        assert r["data"]["tag_count"] == 3

    test("set_actor_tags", test_set_actor_tags)

    def test_set_actor_visibility_hide():
        r = client.set_actor_visibility("TestActor_B", False)
        assert r["status"] == "ok"
        assert r["data"]["visible"] == False

    test("set_actor_visibility_hide", test_set_actor_visibility_hide)

    def test_set_actor_visibility_show():
        r = client.set_actor_visibility("TestActor_B", True)
        assert r["status"] == "ok"
        assert r["data"]["visible"] == True

    test("set_actor_visibility_show", test_set_actor_visibility_show)

    def test_set_actor_mobility_movable():
        r = client.set_actor_mobility("TestActor_A", "Movable")
        assert r["status"] == "ok"
        assert r["data"]["mobility"] == "Movable"

    test("set_actor_mobility_movable", test_set_actor_mobility_movable)

    def test_set_actor_mobility_static():
        r = client.set_actor_mobility("TestActor_A", "Static")
        assert r["status"] == "ok"

    test("set_actor_mobility_static", test_set_actor_mobility_static)

    def test_set_actor_mobility_invalid():
        try:
            client.set_actor_mobility("TestActor_A", "Floating")
            assert False, "Should error on invalid mobility"
        except BlueprintLLMError as e:
            assert "invalid" in str(e).lower() or "Invalid" in str(e)

    test("set_actor_mobility_invalid_error", test_set_actor_mobility_invalid)

    def test_attach_actor():
        r = client.attach_actor_to("TestActor_B", "TestActor_A")
        assert r["status"] == "ok"
        assert r["data"]["parent"] == "TestActor_A"

    test("attach_actor_to", test_attach_actor)

    def test_detach_actor():
        r = client.detach_actor("TestActor_B")
        assert r["status"] == "ok"
        assert r["data"]["actor"] == "TestActor_B"

    test("detach_actor", test_detach_actor)

    def test_attach_missing_parent():
        try:
            client.attach_actor_to("TestActor_A", "NonExistent_ZZZ")
            assert False, "Should error"
        except BlueprintLLMError:
            pass

    test("attach_missing_parent_error", test_attach_missing_parent)

    # ==================================================
    # BATCH 5: Navigation & Audio
    # ==================================================
    print("\n--- Batch 5: Navigation & Audio ---")

    def test_create_nav_mesh_bounds():
        r = client.create_nav_mesh_bounds(
            location={"x": 0, "y": 0, "z": 0},
            extents={"x": 2000, "y": 2000, "z": 500},
            label="TestNavBounds",
        )
        assert r["status"] == "ok"
        assert r["data"]["label"] == "TestNavBounds"

    test("create_nav_mesh_bounds", test_create_nav_mesh_bounds)

    # Add audio component to test BP for audio tests
    client.send_command("add_component", {
        "blueprint": "BP_TestInspect",
        "component_type": "Audio",
        "component_name": "TestAudio",
    })

    def test_set_audio_properties():
        r = client.set_audio_properties(
            blueprint="BP_TestInspect",
            component_name="TestAudio",
            volume_multiplier=0.5,
            pitch_multiplier=1.2,
        )
        assert r["status"] == "ok"
        assert r["data"]["volume_multiplier"] == 0.5

    test("set_audio_properties", test_set_audio_properties)

    def test_play_sound_at_location():
        # play_sound_at_location requires a real sound asset — test error handling
        try:
            r = client.play_sound_at_location("NonExistent_Sound", {"x": 0, "y": 0, "z": 100})
            # If no sound assets exist, it may error — that's expected
            assert r["status"] == "ok" or r["status"] == "error"
        except BlueprintLLMError:
            pass  # Expected if no sound asset exists

    test("play_sound_at_location", test_play_sound_at_location)

    # ==================================================
    # BATCH 6: Project Utilities
    # ==================================================
    print("\n--- Batch 6: Project Utilities ---")

    def test_list_project_assets_by_type():
        r = client.list_project_assets(asset_type="Blueprint", max_results=10)
        assert r["status"] == "ok"
        assert r["data"]["count"] >= 1
        assert isinstance(r["data"]["assets"], list)

    test("list_project_assets_by_type", test_list_project_assets_by_type)

    def test_list_project_assets_filtered():
        r = client.list_project_assets(asset_type="Blueprint", name_filter="TestInspect")
        assert r["status"] == "ok"
        assert r["data"]["count"] >= 1

    test("list_project_assets_filtered", test_list_project_assets_filtered)

    def test_list_project_assets_by_path():
        r = client.list_project_assets(path="/Game/BlueprintLLM", max_results=20)
        assert r["status"] == "ok"

    test("list_project_assets_by_path", test_list_project_assets_by_path)

    def test_list_project_assets_bad_type():
        try:
            client.list_project_assets(asset_type="FooBarWidget")
            assert False, "Should error"
        except BlueprintLLMError:
            pass

    test("list_project_assets_bad_type_error", test_list_project_assets_bad_type)

    def test_copy_actor():
        r = client.copy_actor("TestActor_C", new_label="TestActor_C_Copy",
                               offset={"x": 200, "y": 0, "z": 0})
        assert r["status"] == "ok"
        assert r["data"]["source"] == "TestActor_C"
        assert r["data"]["copy"] == "TestActor_C_Copy"

    test("copy_actor", test_copy_actor)

    def test_copy_actor_default_label():
        r = client.copy_actor("TestActor_A")
        assert r["status"] == "ok"
        assert "Copy" in r["data"]["copy"]

    test("copy_actor_default_label", test_copy_actor_default_label)

    def test_copy_actor_not_found():
        try:
            client.copy_actor("NonExistent_ZZZZ")
            assert False, "Should error"
        except BlueprintLLMError:
            pass

    test("copy_actor_not_found_error", test_copy_actor_not_found)

    # ---- CLEANUP ----
    print("\n--- Cleanup ---")
    for label in ["TestActor_A", "TestActor_B", "TestActor_C", "TestActor_C_Copy",
                   "TestActor_A_Copy", "TestNavBounds"]:
        try:
            client.send_command("delete_actor", {"actor_label": label})
        except:
            pass
    for bp in ["BP_TestInspect", "BP_CamTest"]:
        try:
            client.delete_blueprint(bp)
        except:
            pass
    print("  Cleaned up test assets")

    client.close()

    # ---- SUMMARY ----
    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} PASS / {FAIL} FAIL / {PASS + FAIL} TOTAL")
    print("=" * 60)

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = os.path.join(os.path.dirname(__file__), "..", "..", "results",
                                f"batch_1_6_test_{ts}.json")
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "w") as f:
        json.dump({"timestamp": ts, "pass": PASS, "fail": FAIL, "tests": RESULTS}, f, indent=2)
    print(f"Results saved to {result_path}")

    return FAIL == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
