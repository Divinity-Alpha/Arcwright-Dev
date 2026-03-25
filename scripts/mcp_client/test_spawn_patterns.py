#!/usr/bin/env python3
"""
Test suite for procedural spawn pattern commands and batch transform commands.

Tests:
  spawn_actor_grid, spawn_actor_circle, spawn_actor_line,
  batch_scale_actors, batch_move_actors

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
    print("Arcwright Procedural Spawn & Batch Transform Test Suite")
    print("=" * 60)

    client = ArcwrightClient(timeout=30)
    print(f"\nConnected to TCP 13377\n")

    # ---- SETUP: Clean up any leftover test actors ----
    print("--- Setup: cleanup ---")
    for prefix in ["Grid_", "Circle_", "Line_", "TestSP_"]:
        try:
            client.send_command("batch_delete_actors", {"name_filter": prefix})
        except: pass

    # ==================================================
    # SPAWN ACTOR GRID
    # ==================================================
    print("\n--- spawn_actor_grid ---")

    def test_grid_basic():
        # C++ params: class, rows, cols, spacing_x, spacing_y, origin, center (bool)
        r = client.send_command("spawn_actor_grid", {
            "class": "StaticMeshActor",
            "rows": 3,
            "cols": 4,
            "spacing_x": 200.0,
            "spacing_y": 200.0,
            "origin": {"x": 0, "y": 0, "z": 50},
            "center": True,
            "label_prefix": "Grid_Basic",
        })
        assert r["status"] == "ok", f"Expected ok, got {r}"
        data = r["data"]
        assert data["spawned"] == 12, f"Expected 12 actors, got {data['spawned']}"
        assert len(data["actors"]) == 12

    test("grid_basic_3x4", test_grid_basic)

    def test_grid_with_rotation_scale():
        r = client.send_command("spawn_actor_grid", {
            "class": "StaticMeshActor",
            "rows": 2,
            "cols": 2,
            "spacing_x": 300.0,
            "spacing_y": 300.0,
            "origin": {"x": 2000, "y": 0, "z": 50},
            "rotation": {"pitch": 0, "yaw": 45, "roll": 0},
            "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
            "label_prefix": "Grid_RS",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 4

    test("grid_with_rotation_scale", test_grid_with_rotation_scale)

    def test_grid_1x1():
        r = client.send_command("spawn_actor_grid", {
            "class": "StaticMeshActor",
            "rows": 1,
            "cols": 1,
            "spacing_x": 100.0,
            "origin": {"x": 4000, "y": 0, "z": 50},
            "label_prefix": "Grid_Single",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 1

    test("grid_1x1_single", test_grid_1x1)

    def test_grid_defaults():
        # All params optional except class — defaults to 3x3, 200 spacing
        r = client.send_command("spawn_actor_grid", {
            "class": "StaticMeshActor",
            "origin": {"x": 6000, "y": 0, "z": 50},
            "label_prefix": "Grid_Default",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 9  # 3x3 default

    test("grid_defaults_3x3", test_grid_defaults)

    # ==================================================
    # SPAWN ACTOR CIRCLE
    # ==================================================
    print("\n--- spawn_actor_circle ---")

    def test_circle_basic():
        r = client.send_command("spawn_actor_circle", {
            "class": "StaticMeshActor",
            "count": 8,
            "radius": 500.0,
            "center": {"x": 0, "y": 2000, "z": 50},
            "label_prefix": "Circle_Basic",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 8

    test("circle_basic_8", test_circle_basic)

    def test_circle_face_center():
        r = client.send_command("spawn_actor_circle", {
            "class": "StaticMeshActor",
            "count": 6,
            "radius": 400.0,
            "center": {"x": 2000, "y": 2000, "z": 50},
            "face_center": True,
            "label_prefix": "Circle_Face",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 6

    test("circle_face_center", test_circle_face_center)

    def test_circle_start_angle():
        r = client.send_command("spawn_actor_circle", {
            "class": "StaticMeshActor",
            "count": 4,
            "radius": 300.0,
            "center": {"x": 4000, "y": 2000, "z": 50},
            "start_angle": 45.0,
            "label_prefix": "Circle_Angle",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 4

    test("circle_start_angle", test_circle_start_angle)

    # ==================================================
    # SPAWN ACTOR LINE
    # ==================================================
    print("\n--- spawn_actor_line ---")

    def test_line_basic():
        r = client.send_command("spawn_actor_line", {
            "class": "StaticMeshActor",
            "count": 5,
            "start": {"x": 0, "y": 4000, "z": 50},
            "end": {"x": 2000, "y": 4000, "z": 50},
            "label_prefix": "Line_Basic",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 5

    test("line_basic_5", test_line_basic)

    def test_line_face_direction():
        r = client.send_command("spawn_actor_line", {
            "class": "StaticMeshActor",
            "count": 3,
            "start": {"x": 3000, "y": 4000, "z": 50},
            "end": {"x": 3000, "y": 6000, "z": 50},
            "face_direction": True,
            "label_prefix": "Line_Face",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 3

    test("line_face_direction", test_line_face_direction)

    def test_line_single():
        r = client.send_command("spawn_actor_line", {
            "class": "StaticMeshActor",
            "count": 1,
            "start": {"x": 5000, "y": 4000, "z": 50},
            "end": {"x": 6000, "y": 4000, "z": 50},
            "label_prefix": "Line_Single",
        })
        assert r["status"] == "ok"
        assert r["data"]["spawned"] == 1

    test("line_single", test_line_single)

    # ==================================================
    # BATCH SCALE ACTORS
    # ==================================================
    print("\n--- batch_scale_actors ---")

    def test_scale_by_name_filter():
        r = client.send_command("batch_scale_actors", {
            "name_filter": "Circle_Basic",
            "scale": {"x": 0.5, "y": 0.5, "z": 0.5},
            "mode": "multiply",
        })
        assert r["status"] == "ok"
        assert r["data"]["scaled"] >= 1

    test("scale_by_name_filter", test_scale_by_name_filter)

    def test_scale_absolute():
        r = client.send_command("batch_scale_actors", {
            "name_filter": "Line_Basic",
            "scale": {"x": 3.0, "y": 3.0, "z": 3.0},
            "mode": "set",
        })
        assert r["status"] == "ok"
        assert r["data"]["scaled"] >= 1

    test("scale_absolute_set", test_scale_absolute)

    def test_scale_by_labels():
        # Use actual label format: Grid_Basic_0_0, Grid_Basic_0_1
        r = client.send_command("batch_scale_actors", {
            "labels": ["Grid_Basic_0_0", "Grid_Basic_0_1", "Grid_Basic_1_0"],
            "scale": {"x": 1.5, "y": 1.5, "z": 1.5},
            "mode": "multiply",
        })
        assert r["status"] == "ok"
        assert r["data"]["scaled"] >= 1, f"Expected at least 1 scaled, got {r['data']}"

    test("scale_by_labels", test_scale_by_labels)

    def test_scale_no_match():
        # No matching actors returns error — expected behavior
        try:
            client.send_command("batch_scale_actors", {
                "name_filter": "NonExistent_ZZZZZ",
                "scale": {"x": 2.0, "y": 2.0, "z": 2.0},
            })
            assert False, "Should have raised error for no match"
        except BlueprintLLMError as e:
            assert "no matching" in str(e).lower()

    test("scale_no_match_error", test_scale_no_match)

    # ==================================================
    # BATCH MOVE ACTORS
    # ==================================================
    print("\n--- batch_move_actors ---")

    def test_move_relative():
        r = client.send_command("batch_move_actors", {
            "name_filter": "Grid_Single",
            "offset": {"x": 0, "y": 0, "z": 100},
            "mode": "relative",
        })
        assert r["status"] == "ok"
        assert r["data"]["moved"] >= 1

    test("move_relative", test_move_relative)

    def test_move_absolute():
        # C++ uses "location" (not "position") and mode="set" (not "absolute")
        r = client.send_command("batch_move_actors", {
            "name_filter": "Line_Single",
            "location": {"x": 9000, "y": 9000, "z": 200},
            "mode": "set",
        })
        assert r["status"] == "ok"
        assert r["data"]["moved"] >= 1

    test("move_absolute", test_move_absolute)

    def test_move_by_name_filter():
        r = client.send_command("batch_move_actors", {
            "name_filter": "Circle_Face",
            "offset": {"x": 500, "y": 0, "z": 0},
            "mode": "relative",
        })
        assert r["status"] == "ok"
        assert r["data"]["moved"] >= 1

    test("move_by_name_filter", test_move_by_name_filter)

    def test_move_no_match():
        try:
            client.send_command("batch_move_actors", {
                "name_filter": "NonExistent_ZZZZZ",
                "offset": {"x": 100, "y": 100, "z": 100},
            })
            assert False, "Should have raised error for no match"
        except BlueprintLLMError as e:
            assert "no matching" in str(e).lower()

    test("move_no_match_error", test_move_no_match)

    # ---- CLEANUP ----
    print("\n--- Cleanup ---")
    for prefix in ["Grid_", "Circle_", "Line_"]:
        try:
            client.send_command("batch_delete_actors", {"name_filter": prefix})
        except: pass
    print("  Cleaned up test actors")

    client.close()

    # ---- SUMMARY ----
    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} PASS / {FAIL} FAIL / {PASS + FAIL} TOTAL")
    print("=" * 60)

    # Save results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = os.path.join(os.path.dirname(__file__), "..", "..", "results",
                               f"spawn_pattern_test_{ts}.json")
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, "w") as f:
        json.dump({"timestamp": ts, "pass": PASS, "fail": FAIL, "tests": RESULTS}, f, indent=2)
    print(f"Results saved to {result_path}")

    return FAIL == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
