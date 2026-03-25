#!/usr/bin/env python3
"""
Test script for Batch 1 plugin commands:
  1.1 Spline: create_spline_actor, add_spline_point, get_spline_info
  1.2 Post-process: add_post_process_volume, set_post_process_settings
  1.3 Movement: set_movement_defaults
  1.4 Physics: add_physics_constraint, break_constraint

Requires UE Editor running with BlueprintLLM plugin (TCP 13377).
"""
import sys, os, json, time, traceback

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
    # 1.1 SPLINE COMMANDS
    # =========================================================================
    print("--- 1.1 Spline Commands ---")

    # Test 1: Create spline actor with points
    def t1():
        try:
            client.delete_blueprint("BP_TestSpline")
        except BlueprintLLMError:
            pass
        r = client.create_spline_actor(
            "BP_TestSpline",
            points=[
                {"x": 0, "y": 0, "z": 0},
                {"x": 500, "y": 0, "z": 0},
                {"x": 500, "y": 500, "z": 200},
            ],
            closed=False,
        )
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("create_spline_actor (3 points, open)", t1)

    # Test 2: Add a spline point
    def t2():
        r = client.add_spline_point("BP_TestSpline", {"x": 1000, "y": 500, "z": 0})
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("add_spline_point (append)", t2)

    # Test 3: Get spline info
    def t3():
        r = client.get_spline_info("BP_TestSpline")
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        d = r.get("data", {})
        assert d.get("point_count", 0) >= 3, f"Expected >= 3 points, got {d.get('point_count')}"
        return r
    test("get_spline_info", t3)

    # Test 4: Create closed spline
    def t4():
        try:
            client.delete_blueprint("BP_TestSplineClosed")
        except BlueprintLLMError:
            pass
        r = client.create_spline_actor(
            "BP_TestSplineClosed",
            points=[
                {"x": 0, "y": 0, "z": 0},
                {"x": 300, "y": 0, "z": 0},
                {"x": 300, "y": 300, "z": 0},
                {"x": 0, "y": 300, "z": 0},
            ],
            closed=True,
        )
        assert r["status"] == "ok"
        return r
    test("create_spline_actor (closed loop)", t4)

    # =========================================================================
    # 1.2 POST-PROCESS COMMANDS
    # =========================================================================
    print("\n--- 1.2 Post-Process Commands ---")

    # Test 5: Add post-process volume
    def t5():
        try:
            client.delete_actor("TestPPVolume")
        except BlueprintLLMError:
            pass
        r = client.add_post_process_volume(
            label="TestPPVolume",
            location={"x": 0, "y": 0, "z": 0},
            infinite_extent=True,
        )
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("add_post_process_volume (infinite)", t5)

    # Test 6: Set post-process settings
    def t6():
        r = client.set_post_process_settings("TestPPVolume", {
            "bloom_intensity": 2.5,
            "bloom_threshold": 0.5,
            "vignette_intensity": 0.6,
            "auto_exposure_min": 1.0,
            "auto_exposure_max": 3.0,
        })
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("set_post_process_settings (5 settings)", t6)

    # Test 7: Set color grading
    def t7():
        r = client.set_post_process_settings("TestPPVolume", {
            "color_saturation": {"x": 1.2, "y": 0.8, "z": 1.0, "w": 1.0},
            "color_contrast": {"x": 1.1, "y": 1.1, "z": 1.1, "w": 1.0},
        })
        assert r["status"] == "ok"
        return r
    test("set_post_process_settings (color grading)", t7)

    # =========================================================================
    # 1.3 MOVEMENT DEFAULTS
    # =========================================================================
    print("\n--- 1.3 Movement Defaults ---")

    # Test 8: Set movement on a Character-based BP
    # First create a simple BP with Character parent via DSL
    def t8():
        dsl = "BLUEPRINT: BP_TestRunner\nPARENT: Character\n\nGRAPH: EventGraph\n\nNODE n1: Event_BeginPlay\nNODE n2: PrintString [InString=\"Runner ready\"]\n\nEXEC n1.Then -> n2.Execute"
        try:
            client.delete_blueprint("BP_TestRunner")
        except BlueprintLLMError:
            pass
        client.create_blueprint_from_dsl(dsl)
        r = client.set_movement_defaults("BP_TestRunner", {
            "max_walk_speed": 1200,
            "jump_z_velocity": 800,
            "gravity_scale": 1.5,
            "air_control": 0.8,
        })
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("set_movement_defaults (Character)", t8)

    # Test 9: Set movement on a Pawn-based BP (FloatingPawnMovement)
    def t9():
        dsl = "BLUEPRINT: BP_TestFloater\nPARENT: Pawn\n\nGRAPH: EventGraph\n\nNODE n1: Event_BeginPlay\nNODE n2: PrintString [InString=\"Floater ready\"]\n\nEXEC n1.Then -> n2.Execute"
        try:
            client.delete_blueprint("BP_TestFloater")
        except BlueprintLLMError:
            pass
        client.create_blueprint_from_dsl(dsl)
        # FloatingPawnMovement might need to be added first
        try:
            client.add_component("BP_TestFloater", "FloatingPawnMovement", "FloatMove")
        except BlueprintLLMError:
            pass  # May not support this component type directly
        r = client.set_movement_defaults("BP_TestFloater", {
            "max_speed": 2000,
            "acceleration": 5000,
            "deceleration": 10000,
        })
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("set_movement_defaults (Pawn/Floating)", t9)

    # =========================================================================
    # 1.4 PHYSICS CONSTRAINTS
    # =========================================================================
    print("\n--- 1.4 Physics Constraints ---")

    # Test 10: Create two actors and constrain them
    def t10():
        # Spawn two static mesh actors
        for lbl in ["PhysBox1", "PhysBox2", "TestConstraint"]:
            try:
                client.delete_actor(lbl)
            except BlueprintLLMError:
                pass

        client.spawn_actor_at("StaticMeshActor", label="PhysBox1",
                              location={"x": 0, "y": 0, "z": 300})
        client.spawn_actor_at("StaticMeshActor", label="PhysBox2",
                              location={"x": 200, "y": 0, "z": 300})

        r = client.add_physics_constraint(
            label="TestConstraint",
            actor1="PhysBox1",
            actor2="PhysBox2",
            constraint_type="Hinge",
        )
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("add_physics_constraint (Hinge)", t10)

    # Test 11: Break constraint
    def t11():
        r = client.break_constraint("TestConstraint")
        assert r["status"] == "ok", f"Expected ok, got {r['status']}"
        return r
    test("break_constraint", t11)

    # Test 12: Fixed constraint
    def t12():
        try:
            client.delete_actor("TestConstraintFixed")
        except BlueprintLLMError:
            pass
        r = client.add_physics_constraint(
            label="TestConstraintFixed",
            actor1="PhysBox1",
            actor2="PhysBox2",
            constraint_type="Fixed",
        )
        assert r["status"] == "ok"
        return r
    test("add_physics_constraint (Fixed)", t12)

    # =========================================================================
    # CLEANUP
    # =========================================================================
    print("\n--- Cleanup ---")
    for name in ["BP_TestSpline", "BP_TestSplineClosed", "BP_TestRunner", "BP_TestFloater"]:
        try:
            client.delete_blueprint(name)
        except BlueprintLLMError:
            pass
    for label in ["TestPPVolume", "PhysBox1", "PhysBox2", "TestConstraint", "TestConstraintFixed"]:
        try:
            client.delete_actor(label)
        except BlueprintLLMError:
            pass
    print("  Cleanup complete")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    total = PASS + FAIL
    print(f"\n{'='*60}")
    print(f"  Batch 1 Results: {PASS}/{total} PASS, {FAIL}/{total} FAIL")
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
