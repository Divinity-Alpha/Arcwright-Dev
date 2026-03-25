#!/usr/bin/env python3
"""
Test script for the setup_ai_for_pawn command.
Creates a Pawn Blueprint and BehaviorTree, then tests the one-command AI setup.

Requires UE Editor running with BlueprintLLM plugin (TCP 13377).
"""
import sys, os, traceback

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
    # SETUP: Create a test Pawn Blueprint via IR
    # =========================================================================
    print("--- Setup: Create test Pawn ---")

    # Create a minimal Pawn Blueprint via create_blueprint_from_dsl
    def setup_pawn():
        # Delete existing first
        try: client.delete_blueprint("BP_TestAIPawn")
        except BlueprintLLMError: pass

        dsl = """BLUEPRINT: BP_TestAIPawn
PARENT: Pawn
GRAPH: EventGraph
NODE N1: Event_BeginPlay
NODE N2: PrintString [I="AI Pawn Ready"]
EXEC N1.Then -> N2.Execute"""
        r = client.create_blueprint_from_dsl(dsl)
        assert r["status"] == "ok", f"Expected ok, got {r}"
        return r
    test("create test Pawn BP", setup_pawn)

    # Create a minimal BehaviorTree via create_behavior_tree
    def setup_bt():
        bt_dsl = """BEHAVIORTREE: BT_TestSetup
BLACKBOARD: BB_TestSetup

KEY PatrolPoint: Vector

TREE:

SEQUENCE: Main
  TASK: PrintString [Message="AI Running"]
  TASK: Wait [Duration=2.0]"""
        r = client.create_behavior_tree_from_dsl(bt_dsl)
        assert r["status"] == "ok", f"Expected ok, got {r}"
        return r
    test("create test BehaviorTree", setup_bt)

    # =========================================================================
    # TEST 1: Basic setup_ai_for_pawn
    # =========================================================================
    print("\n--- setup_ai_for_pawn Tests ---")

    def t1():
        r = client.setup_ai_for_pawn("BP_TestAIPawn", "BT_TestSetup")
        assert r["status"] == "ok", f"Expected ok, got {r}"
        d = r.get("data", {})
        assert d.get("pawn") == "BP_TestAIPawn"
        assert d.get("behavior_tree") == "BT_TestSetup"
        assert d.get("controller_created") == True
        assert d.get("auto_possess") == "PlacedInWorldOrSpawned"
        controller_name = d.get("controller")
        print(f"    -> controller: {controller_name}")
        print(f"    -> controller_created: {d.get('controller_created')}")
        return r
    test("setup_ai_for_pawn (default controller name)", t1)

    # TEST 2: Verify the controller Blueprint was created
    def t2():
        r = client.send_command("get_blueprint_info", {"name": "BP_TestAIPawn_AIController"})
        assert r["status"] == "ok", f"Expected ok, got {r}"
        d = r.get("data", {})
        compiled = d.get("compiled", False)
        # node_count may be in different field names depending on version
        nodes = d.get("node_count") or d.get("nodes") or len(d.get("node_list", []))
        print(f"    -> compiled: {compiled}, data keys: {list(d.keys())}")
        assert compiled == True
        return r
    test("verify controller Blueprint exists + compiled", t2)

    # TEST 3: Call again — should reuse existing controller (not create new)
    def t3():
        r = client.setup_ai_for_pawn("BP_TestAIPawn", "BT_TestSetup")
        assert r["status"] == "ok"
        d = r.get("data", {})
        assert d.get("controller_created") == False, "Expected controller_created=False (reuse)"
        print(f"    -> controller_created: {d.get('controller_created')} (reused)")
        return r
    test("setup_ai_for_pawn (reuse existing controller)", t3)

    # TEST 4: Custom controller name
    def t4():
        try: client.delete_blueprint("BP_CustomAICtrl")
        except BlueprintLLMError: pass
        r = client.setup_ai_for_pawn("BP_TestAIPawn", "BT_TestSetup",
                                      controller_name="BP_CustomAICtrl")
        assert r["status"] == "ok"
        d = r.get("data", {})
        assert d.get("controller") == "BP_CustomAICtrl"
        assert d.get("controller_created") == True
        print(f"    -> controller: {d.get('controller')}")
        return r
    test("setup_ai_for_pawn (custom controller name)", t4)

    # TEST 5: Error — non-existent pawn
    def t5():
        try:
            client.setup_ai_for_pawn("BP_NonExistent", "BT_TestSetup")
            assert False, "Should have raised BlueprintLLMError"
        except BlueprintLLMError as e:
            assert "not found" in str(e).lower()
            print(f"    -> Expected error: {e}")
            return {"status": "expected_error"}
    test("error: non-existent pawn", t5)

    # TEST 6: Error — non-existent behavior tree
    def t6():
        try:
            client.setup_ai_for_pawn("BP_TestAIPawn", "BT_NonExistent")
            assert False, "Should have raised BlueprintLLMError"
        except BlueprintLLMError as e:
            assert "not found" in str(e).lower()
            print(f"    -> Expected error: {e}")
            return {"status": "expected_error"}
    test("error: non-existent behavior tree", t6)

    # =========================================================================
    # CLEANUP
    # =========================================================================
    print("\n--- Cleanup ---")
    for bp in ["BP_TestAIPawn", "BP_TestAIPawn_AIController", "BP_CustomAICtrl"]:
        try: client.delete_blueprint(bp)
        except BlueprintLLMError: pass
    print("  Cleanup complete")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    total = PASS + FAIL
    print(f"\n{'='*60}")
    print(f"  setup_ai_for_pawn Results: {PASS}/{total} PASS, {FAIL}/{total} FAIL")
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
