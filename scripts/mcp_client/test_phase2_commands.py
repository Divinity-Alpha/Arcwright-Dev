"""
Test script for Phase 2 + Phase 4 TCP commands (v8.2).

Phase 2 (10 commands):
  set_collision_preset, get_blueprint_details, set_camera_properties,
  create_input_action, bind_input_to_blueprint, set_collision_shape,
  create_nav_mesh_bounds, set_audio_properties, set_actor_tags,
  get_actor_properties

Phase 4 (3 commands):
  list_available_materials, list_available_blueprints, get_last_error

Requires UE5 Editor running with Arcwright plugin loaded.

Usage:
    python scripts/mcp_client/test_phase2_commands.py
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blueprint_client import ArcwrightClient, BlueprintLLMError

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

TEST_BP_NAME = "BP_Phase2Test"
TEST_ACTOR_LABEL = "Phase2TestActor"


def main():
    results = []
    passed = 0
    failed = 0

    def record(step, name, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({"step": step, "name": name, "status": "PASS" if ok else "FAIL",
                         "detail": detail})
        tag = "OK" if ok else "FAIL"
        suffix = f" — {detail}" if detail else ""
        print(f"[{step:>2}] {name}... {tag}{suffix}")

    print("=" * 60)
    print("Arcwright Phase 2 + Phase 4 Commands — Test Suite")
    print("=" * 60)

    # Step 1: Connect
    print(f"\n[ 1] Connecting to localhost:13377...", end=" ")
    try:
        client = ArcwrightClient(timeout=15)
        result = client.health_check()
        server = result.get("data", {}).get("server", "")
        print(f"OK — {server}")
        passed += 1
        results.append({"step": 1, "name": "connect + health_check", "status": "PASS",
                         "detail": server})
    except Exception as e:
        print(f"FAIL — {e}")
        print("\nIs UE5 Editor running with the Arcwright plugin?")
        return 1

    # --- Setup: Create a test Blueprint via temp IR file ---
    print("\n--- Setup: Creating test Blueprint ---")
    try:
        client.delete_blueprint(TEST_BP_NAME)
    except Exception:
        pass

    try:
        import json as _json
        import tempfile
        ir = {
            "metadata": {
                "name": TEST_BP_NAME,
                "parent_class": "Actor",
                "category": None
            },
            "variables": [],
            "nodes": [
                {"id": "n1", "dsl_type": "Event_BeginPlay",
                 "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay",
                 "params": {}, "position": [0, 0]}
            ],
            "connections": []
        }
        # Write to temp file and import via file path (avoids inline JSON TCP issues)
        ir_path = os.path.join(PROJECT_ROOT, "test_ir", f"{TEST_BP_NAME}.blueprint.json")
        with open(ir_path, "w") as f:
            _json.dump(ir, f, indent=2)
        r = client.import_from_ir(ir_path)
        setup_ok = r.get("status") == "ok"
        print(f"  Setup BP: {'OK' if setup_ok else 'FAIL'}")
    except Exception as e:
        print(f"  Setup BP: FAIL — {e}")
        setup_ok = False

    # Also add a component for collision/camera tests
    if setup_ok:
        try:
            client.add_component(TEST_BP_NAME, "BoxCollision", "TestBox",
                                 properties={"extent": {"x": 100, "y": 100, "z": 100}})
            client.add_component(TEST_BP_NAME, "StaticMesh", "TestMesh")
        except Exception:
            pass

    # ============================================================
    # Phase 4: Discovery commands (test first — no side effects)
    # ============================================================
    print("\n--- Phase 4: Discovery Commands ---")

    # Step 2: list_available_materials
    try:
        r = client.send_command("list_available_materials", {"name_filter": "", "max_results": 10})
        data = r.get("data", {})
        count = data.get("count", 0)
        materials = data.get("materials", [])
        ok = r.get("status") == "ok" and count >= 0
        record(2, "list_available_materials", ok,
               f"found {count} materials" + (f", first: {materials[0].get('name','?')}" if materials else ""))
    except Exception as e:
        record(2, "list_available_materials", False, str(e))

    # Step 3: list_available_materials with filter
    try:
        r = client.send_command("list_available_materials", {"name_filter": "Basic"})
        data = r.get("data", {})
        count = data.get("count", 0)
        ok = r.get("status") == "ok"
        record(3, "list_available_materials (filtered)", ok, f"found {count} matching 'Basic'")
    except Exception as e:
        record(3, "list_available_materials (filtered)", False, str(e))

    # Step 4: list_available_blueprints
    try:
        r = client.send_command("list_available_blueprints", {"name_filter": ""})
        data = r.get("data", {})
        count = data.get("count", 0)
        bps = data.get("blueprints", [])
        ok = r.get("status") == "ok" and count >= 0
        record(4, "list_available_blueprints", ok,
               f"found {count} blueprints" + (f", first: {bps[0].get('name','?')}" if bps else ""))
    except Exception as e:
        record(4, "list_available_blueprints", False, str(e))

    # Step 5: list_available_blueprints with filter
    try:
        r = client.send_command("list_available_blueprints", {"name_filter": TEST_BP_NAME})
        data = r.get("data", {})
        count = data.get("count", 0)
        ok = r.get("status") == "ok" and count >= 1
        record(5, "list_available_blueprints (filtered)", ok,
               f"found {count} matching '{TEST_BP_NAME}'")
    except Exception as e:
        record(5, "list_available_blueprints (filtered)", False, str(e))

    # Step 6: get_last_error (should be empty or have a previous error)
    try:
        r = client.send_command("get_last_error", {})
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        has_error = data.get("has_error", False)
        record(6, "get_last_error", ok,
               f"has_error={has_error}" + (f", cmd={data.get('command','')}" if has_error else ""))
    except Exception as e:
        record(6, "get_last_error", False, str(e))

    # Step 7: Trigger an error then verify get_last_error captures it
    try:
        try:
            client.send_command("get_blueprint_info", {"name": "NONEXISTENT_BP_12345"})
        except Exception:
            pass
        r = client.send_command("get_last_error", {})
        data = r.get("data", {})
        has_error = data.get("has_error", False)
        ok = r.get("status") == "ok" and has_error
        record(7, "get_last_error (after error)", ok,
               f"message={data.get('message','')[:80]}")
    except Exception as e:
        record(7, "get_last_error (after error)", False, str(e))

    # ============================================================
    # Phase 2: New commands
    # ============================================================
    print("\n--- Phase 2: New Commands ---")

    # Step 8: get_blueprint_details
    try:
        r = client.send_command("get_blueprint_details", {"name": TEST_BP_NAME})
        data = r.get("data", {})
        ok = r.get("status") == "ok"
        bp_name = data.get("name", "")
        parent = data.get("parent_class", "")
        components = data.get("components", [])
        record(8, "get_blueprint_details", ok,
               f"name={bp_name}, parent={parent}, components={len(components)}")
    except Exception as e:
        record(8, "get_blueprint_details", False, str(e))

    # Step 9: get_blueprint_details — error case
    try:
        r = client.send_command("get_blueprint_details", {"name": "NONEXISTENT_BP_99999"})
        ok = r.get("status") == "error"
        record(9, "get_blueprint_details (not found)", ok,
               f"got expected error: {r.get('message','')[:60]}")
    except BlueprintLLMError as e:
        record(9, "get_blueprint_details (not found)", True, f"got expected error: {str(e)[:60]}")
    except Exception as e:
        record(9, "get_blueprint_details (not found)", False, str(e))

    # Step 10: set_collision_preset on Blueprint component
    try:
        r = client.send_command("set_collision_preset", {
            "preset_name": "OverlapAllDynamic",
            "blueprint": TEST_BP_NAME,
            "component_name": "TestBox"
        })
        ok = r.get("status") == "ok"
        record(10, "set_collision_preset (BP component)", ok,
               f"preset=OverlapAllDynamic")
    except Exception as e:
        record(10, "set_collision_preset (BP component)", False, str(e))

    # Step 11: set_collision_shape
    try:
        r = client.send_command("set_collision_shape", {
            "blueprint": TEST_BP_NAME,
            "component_name": "TestBox",
            "extents": {"x": 200, "y": 200, "z": 50}
        })
        ok = r.get("status") == "ok"
        record(11, "set_collision_shape", ok, "extents=200x200x50")
    except Exception as e:
        record(11, "set_collision_shape", False, str(e))

    # Step 12: set_camera_properties — need actual camera component
    try:
        # Add a real CameraComponent (not Scene)
        try:
            client.send_command("add_component", {
                "blueprint": TEST_BP_NAME,
                "component_type": "Camera",
                "component_name": "TestCamera"
            })
        except Exception:
            pass
        r = client.send_command("set_camera_properties", {
            "blueprint": TEST_BP_NAME,
            "fov": 90.0,
            "use_pawn_control_rotation": True
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        record(12, "set_camera_properties", ok,
               f"fov=90, applied={data.get('properties_set', 0)} props")
    except Exception as e:
        record(12, "set_camera_properties", False, str(e))

    # Step 13: create_input_action
    try:
        r = client.send_command("create_input_action", {
            "name": "IA_Phase2Test",
            "value_type": "bool"
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        record(13, "create_input_action", ok,
               f"path={data.get('path', '?')}")
    except Exception as e:
        record(13, "create_input_action", False, str(e))

    # Step 14: bind_input_to_blueprint
    try:
        r = client.send_command("bind_input_to_blueprint", {
            "blueprint": TEST_BP_NAME,
            "action": "IA_Phase2Test",
            "trigger": "Pressed"
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        record(14, "bind_input_to_blueprint", ok,
               f"node_id={data.get('node_id', '?')}")
    except Exception as e:
        record(14, "bind_input_to_blueprint", False, str(e))

    # Step 15: Spawn a test actor for actor-level commands
    try:
        try:
            client.delete_actor(TEST_ACTOR_LABEL)
        except Exception:
            pass
        r = client.spawn_actor_at(
            actor_class="StaticMeshActor",
            location={"x": 0, "y": 0, "z": 200},
            label=TEST_ACTOR_LABEL
        )
        ok = r.get("data", {}).get("label") == TEST_ACTOR_LABEL
        record(15, "spawn test actor", ok, f"label={TEST_ACTOR_LABEL}")
    except Exception as e:
        record(15, "spawn test actor", False, str(e))

    # Step 16: set_actor_tags
    try:
        r = client.send_command("set_actor_tags", {
            "actor_label": TEST_ACTOR_LABEL,
            "tags": ["TestTag1", "TestTag2", "Interactable"]
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        record(16, "set_actor_tags", ok,
               f"tag_count={data.get('tag_count', '?')}")
    except Exception as e:
        record(16, "set_actor_tags", False, str(e))

    # Step 17: get_actor_properties
    try:
        r = client.send_command("get_actor_properties", {
            "actor_label": TEST_ACTOR_LABEL
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        tags = data.get("tags", [])
        has_tags = "TestTag1" in tags and "TestTag2" in tags
        record(17, "get_actor_properties", ok and has_tags,
               f"tags={tags}, has_expected={has_tags}")
    except Exception as e:
        record(17, "get_actor_properties", False, str(e))

    # Step 18: set_collision_preset on actor
    try:
        r = client.send_command("set_collision_preset", {
            "preset_name": "BlockAll",
            "actor_label": TEST_ACTOR_LABEL
        })
        ok = r.get("status") == "ok"
        record(18, "set_collision_preset (actor)", ok, "preset=BlockAll")
    except Exception as e:
        record(18, "set_collision_preset (actor)", False, str(e))

    # Step 19: set_audio_properties — add audio component to BP first
    try:
        try:
            client.add_component(TEST_BP_NAME, "Audio", "TestAudio")
        except Exception:
            pass
        r = client.send_command("set_audio_properties", {
            "blueprint": TEST_BP_NAME,
            "component_name": "TestAudio",
            "volume_multiplier": 0.5,
            "pitch_multiplier": 1.2,
            "auto_activate": False
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        record(19, "set_audio_properties", ok,
               f"applied={data.get('properties_set', 0)} props")
    except Exception as e:
        record(19, "set_audio_properties", False, str(e))

    # Step 20: create_nav_mesh_bounds
    try:
        r = client.send_command("create_nav_mesh_bounds", {
            "x": 0, "y": 0, "z": 0,
            "extent_x": 2000, "extent_y": 2000, "extent_z": 500,
            "label": "Phase2TestNavMesh"
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        record(20, "create_nav_mesh_bounds", ok,
               f"label={data.get('label', '?')}")
    except Exception as e:
        record(20, "create_nav_mesh_bounds", False, str(e))

    # Step 21: get_actor_properties on nav mesh
    try:
        r = client.send_command("get_actor_properties", {
            "actor_label": "Phase2TestNavMesh"
        })
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        cls = data.get("class", "")
        record(21, "get_actor_properties (nav mesh)", ok,
               f"class={cls}")
    except Exception as e:
        record(21, "get_actor_properties (nav mesh)", False, str(e))

    # --- Cleanup ---
    print("\n--- Cleanup ---")
    try:
        client.delete_actor(TEST_ACTOR_LABEL)
        print(f"  Deleted actor: {TEST_ACTOR_LABEL}")
    except Exception:
        pass
    try:
        client.delete_actor("Phase2TestNavMesh")
        print(f"  Deleted actor: Phase2TestNavMesh")
    except Exception:
        pass
    try:
        client.delete_blueprint(TEST_BP_NAME)
        print(f"  Deleted blueprint: {TEST_BP_NAME}")
    except Exception:
        pass
    try:
        # Clean up the input action asset
        client.delete_blueprint("IA_Phase2Test")
        print(f"  Deleted input action: IA_Phase2Test")
    except Exception:
        pass
    # Clean up temp IR file
    ir_path = os.path.join(PROJECT_ROOT, "test_ir", f"{TEST_BP_NAME}.blueprint.json")
    if os.path.exists(ir_path):
        os.remove(ir_path)
        print(f"  Deleted temp IR: {ir_path}")

    client.close()

    # Summary
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed", end="")
    if failed > 0:
        print(f", {failed} FAILED")
    else:
        print(" — All tests passed!")
    print("=" * 60)

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(RESULTS_DIR, f"phase2_test_{timestamp}.json")
    report = {
        "timestamp": timestamp,
        "suite": "Phase 2 + Phase 4 Commands",
        "passed": passed,
        "failed": failed,
        "total": total,
        "results": results
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
