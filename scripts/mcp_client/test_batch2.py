#!/usr/bin/env python3
"""
Test script for Batch 2 plugin commands:
  2.1 Sequencer: create_sequence, add_sequence_track, add_keyframe, get_sequence_info, play_sequence
  2.2 Landscape/Foliage: get_landscape_info, set_landscape_material, create_foliage_type, paint_foliage, get_foliage_info

Requires UE Editor running with BlueprintLLM plugin (TCP 13377).
"""
import sys, os, json, traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError

PASS = 0
FAIL = 0
RESULTS = []

def test(name, fn):
    global PASS, FAIL
    try:
        result = fn()
        print(f"  PASS: {name}")
        PASS += 1
        RESULTS.append(("PASS", name, result))
        return result
    except Exception as e:
        print(f"  FAIL: {name} -- {e}")
        traceback.print_exc()
        FAIL += 1
        RESULTS.append(("FAIL", name, str(e)))
        return None


def main():
    global PASS, FAIL
    client = ArcwrightClient(timeout=30)
    client.health_check()
    print("Connected to BlueprintLLM Command Server\n")

    # =========================================================================
    # 2.1 SEQUENCER COMMANDS
    # =========================================================================
    print("--- 2.1 Sequencer Commands ---")

    # Test 1: Create a sequence
    def t1():
        r = client.create_sequence("LS_TestIntro", duration=5.0)
        assert r["status"] == "ok", f"Expected ok, got {r}"
        assert r["data"]["duration"] == 5.0
        return r
    test("create_sequence (5s)", t1)

    # Test 2: Spawn a cube actor to bind
    def t2():
        try:
            client.delete_actor("SeqCube")
        except BlueprintLLMError:
            pass
        r = client.spawn_actor_at("StaticMeshActor", label="SeqCube",
                                  location={"x": 0, "y": 0, "z": 100})
        assert r["status"] == "ok"
        return r
    test("spawn actor for sequencer", t2)

    # Test 3: Add transform track
    def t3():
        r = client.add_sequence_track("LS_TestIntro", "SeqCube", "Transform")
        assert r["status"] == "ok"
        return r
    test("add_sequence_track (Transform)", t3)

    # Test 4: Add keyframe at t=0
    def t4():
        r = client.add_keyframe("LS_TestIntro", "SeqCube", "Transform", 0.0,
                                 {"location": {"x": 0, "y": 0, "z": 100}})
        assert r["status"] == "ok"
        d = r.get("data", {})
        assert d.get("keys_added", 0) >= 3, f"Expected >=3 keys, got {d.get('keys_added')}"
        return r
    test("add_keyframe (t=0, location)", t4)

    # Test 5: Add keyframe at t=2.5
    def t5():
        r = client.add_keyframe("LS_TestIntro", "SeqCube", "Transform", 2.5,
                                 {"location": {"x": 500, "y": 0, "z": 300}})
        assert r["status"] == "ok"
        return r
    test("add_keyframe (t=2.5, location)", t5)

    # Test 6: Add keyframe at t=5
    def t6():
        r = client.add_keyframe("LS_TestIntro", "SeqCube", "Transform", 5.0,
                                 {"location": {"x": 0, "y": 0, "z": 100}})
        assert r["status"] == "ok"
        return r
    test("add_keyframe (t=5, location)", t6)

    # Test 7: Get sequence info
    def t7():
        r = client.get_sequence_info("LS_TestIntro")
        assert r["status"] == "ok"
        d = r.get("data", {})
        assert d.get("bound_actor_count", 0) >= 1
        assert d.get("total_tracks", 0) >= 1
        print(f"    -> duration={d.get('duration')}, tracks={d.get('total_tracks')}, actors={d.get('bound_actor_count')}")
        return r
    test("get_sequence_info", t7)

    # Test 8: play_sequence (expected to fail with limitation message)
    def t8():
        try:
            r = client.play_sequence("LS_TestIntro")
            # If it returns ok, that's fine too
            return r
        except BlueprintLLMError as e:
            if "not supported" in str(e).lower() or "PIE" in str(e):
                print(f"    -> Expected limitation: {e}")
                return {"status": "expected_limitation"}
            raise
    test("play_sequence (expected limitation)", t8)

    # Test 9: Add visibility track
    def t9():
        r = client.add_sequence_track("LS_TestIntro", "SeqCube", "Visibility")
        assert r["status"] == "ok"
        return r
    test("add_sequence_track (Visibility)", t9)

    # =========================================================================
    # 2.2 LANDSCAPE/FOLIAGE COMMANDS
    # =========================================================================
    print("\n--- 2.2 Landscape/Foliage Commands ---")

    # Test 10: Get landscape info (may or may not exist)
    def t10():
        r = client.get_landscape_info()
        assert r["status"] == "ok"
        d = r.get("data", {})
        exists = d.get("exists", False)
        print(f"    -> landscape exists: {exists}")
        if not exists:
            print(f"    -> {d.get('message', '')}")
        return r
    test("get_landscape_info", t10)

    # Test 11: Create foliage type
    def t11():
        r = client.create_foliage_type(
            "FT_TestRocks",
            mesh="/Engine/BasicShapes/Cube.Cube",
            density=50.0,
            scale_min=0.5,
            scale_max=1.5,
        )
        assert r["status"] == "ok"
        return r
    test("create_foliage_type", t11)

    # Test 12: Paint foliage
    def t12():
        r = client.paint_foliage(
            "/Game/Arcwright/Foliage/FT_TestRocks",
            center={"x": 0, "y": 0, "z": 0},
            radius=500,
            count=15,
        )
        assert r["status"] == "ok"
        d = r.get("data", {})
        print(f"    -> placed: {d.get('placed', 0)}/{d.get('requested', 0)}")
        return r
    test("paint_foliage (15 instances)", t12)

    # Test 13: Get foliage info
    def t13():
        r = client.get_foliage_info()
        assert r["status"] == "ok"
        d = r.get("data", {})
        print(f"    -> types: {d.get('foliage_type_count', 0)}, instances: {d.get('total_instances', 0)}")
        return r
    test("get_foliage_info", t13)

    # Test 14: Create second foliage type with different mesh
    def t14():
        r = client.create_foliage_type(
            "FT_TestSpheres",
            mesh="/Engine/BasicShapes/Sphere.Sphere",
            density=100.0,
            scale_min=0.3,
            scale_max=0.8,
        )
        assert r["status"] == "ok"
        return r
    test("create_foliage_type (spheres)", t14)

    # Test 15: set_landscape_material (will fail if no landscape - that's ok)
    def t15():
        try:
            r = client.set_landscape_material("/Engine/BasicShapes/BasicShapeMaterial")
            assert r["status"] == "ok"
            return r
        except BlueprintLLMError as e:
            if "no landscape" in str(e).lower():
                print(f"    -> Expected: {e}")
                return {"status": "expected_no_landscape"}
            raise
    test("set_landscape_material (may fail without landscape)", t15)

    # =========================================================================
    # CLEANUP
    # =========================================================================
    print("\n--- Cleanup ---")
    try:
        client.delete_actor("SeqCube")
    except BlueprintLLMError:
        pass
    print("  Cleanup complete")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    total = PASS + FAIL
    print(f"\n{'='*60}")
    print(f"  Batch 2 Results: {PASS}/{total} PASS, {FAIL}/{total} FAIL")
    print(f"{'='*60}")
    for status, name, _ in RESULTS:
        marker = "PASS" if status == "PASS" else "FAIL"
        print(f"  [{marker}] {name}")
    print()

    client.close()
    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
