"""
Test script for component management commands (add_component, get_components, remove_component).

Tests CRUD operations on Blueprint SCS components, then optionally
adds collision to game Blueprints (BP_Pickup, BP_HazardZone, BP_VictoryZone).

Usage:
    python scripts/mcp_client/test_components.py
    python scripts/mcp_client/test_components.py --game-bps   # also add collision to game BPs
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError


def run_tests(client, add_game_bps=False):
    results = []
    test_bp = "BP_ComponentTest"

    def record(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    print("=" * 60)
    print("Component Management Tests")
    print("=" * 60)

    # --- Test 0: Health check ---
    print("\n[Test 0] Health check")
    try:
        resp = client.health_check()
        record("health_check", resp.get("status") == "ok",
               resp.get("data", {}).get("version", ""))
    except Exception as e:
        record("health_check", False, str(e))
        print("Cannot connect. Aborting.")
        return results

    # --- Test 1: Create a test Blueprint via IR for component testing ---
    print("\n[Test 1] Create test Blueprint")
    try:
        # Delete if exists from previous run
        try:
            client.delete_blueprint(test_bp)
        except BlueprintLLMError:
            pass

        # Create a minimal BP via DSL
        dsl_text = f"""BLUEPRINT: {test_bp}
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Component test"]
EXEC n1.Then -> n2.Execute
"""
        resp = client.create_blueprint_from_dsl(dsl_text, name=test_bp)
        record("create_test_bp", resp.get("status") == "ok",
               f"nodes={resp.get('data', {}).get('nodes_created', '?')}")
    except Exception as e:
        record("create_test_bp", False, str(e))
        print("Cannot create test BP. Aborting remaining tests.")
        return results

    # --- Test 2: Add BoxCollision component ---
    print("\n[Test 2] Add BoxCollision component")
    try:
        resp = client.add_component(
            test_bp, "BoxCollision", "CollisionBox",
            properties={
                "extent": {"x": 50, "y": 50, "z": 50},
                "generate_overlap_events": True,
            }
        )
        data = resp.get("data", {})
        record("add_box_collision", resp.get("status") == "ok" and data.get("compiled"),
               f"class={data.get('component_class')}, parent={data.get('parent')}")
    except Exception as e:
        record("add_box_collision", False, str(e))

    # --- Test 3: Add SphereCollision component ---
    print("\n[Test 3] Add SphereCollision component")
    try:
        resp = client.add_component(
            test_bp, "SphereCollision", "CollisionSphere",
            properties={"radius": 100.0, "generate_overlap_events": True}
        )
        data = resp.get("data", {})
        record("add_sphere_collision", resp.get("status") == "ok" and data.get("compiled"),
               f"class={data.get('component_class')}")
    except Exception as e:
        record("add_sphere_collision", False, str(e))

    # --- Test 4: Add PointLight component ---
    print("\n[Test 4] Add PointLight component")
    try:
        resp = client.add_component(
            test_bp, "PointLight", "MyLight",
            properties={
                "intensity": 5000.0,
                "attenuation_radius": 500.0,
                "location": {"x": 0, "y": 0, "z": 100},
            }
        )
        data = resp.get("data", {})
        record("add_point_light", resp.get("status") == "ok" and data.get("compiled"),
               f"class={data.get('component_class')}")
    except Exception as e:
        record("add_point_light", False, str(e))

    # --- Test 5: Get components — verify all 3 present ---
    print("\n[Test 5] Get components")
    try:
        resp = client.get_components(test_bp)
        data = resp.get("data", {})
        count = data.get("count", 0)
        names = [c.get("name") for c in data.get("components", [])]
        has_all = all(n in names for n in ["CollisionBox", "CollisionSphere", "MyLight"])
        record("get_components", has_all and count >= 3,
               f"count={count}, names={names}")
    except Exception as e:
        record("get_components", False, str(e))

    # --- Test 6: Duplicate name error ---
    print("\n[Test 6] Duplicate component name (should error)")
    try:
        resp = client.add_component(test_bp, "BoxCollision", "CollisionBox")
        record("duplicate_name_error", False, "Expected error but got success")
    except BlueprintLLMError as e:
        record("duplicate_name_error", "already exists" in str(e).lower(),
               str(e))
    except Exception as e:
        record("duplicate_name_error", False, str(e))

    # --- Test 7: Remove component ---
    print("\n[Test 7] Remove component")
    try:
        resp = client.remove_component(test_bp, "MyLight")
        data = resp.get("data", {})
        record("remove_component", data.get("deleted") is True and data.get("compiled"),
               f"deleted={data.get('deleted')}")
    except Exception as e:
        record("remove_component", False, str(e))

    # --- Test 8: Idempotent remove (nonexistent) ---
    print("\n[Test 8] Remove nonexistent component (idempotent)")
    try:
        resp = client.remove_component(test_bp, "DoesNotExist")
        data = resp.get("data", {})
        record("remove_nonexistent", resp.get("status") == "ok" and data.get("deleted") is False,
               f"deleted={data.get('deleted')}")
    except Exception as e:
        record("remove_nonexistent", False, str(e))

    # --- Test 9: Verify count after removal ---
    print("\n[Test 9] Verify component count after removal")
    try:
        resp = client.get_components(test_bp)
        data = resp.get("data", {})
        count = data.get("count", 0)
        names = [c.get("name") for c in data.get("components", [])]
        record("count_after_remove", count == 2 and "MyLight" not in names,
               f"count={count}, names={names}")
    except Exception as e:
        record("count_after_remove", False, str(e))

    # --- Test 10: Unknown component type ---
    print("\n[Test 10] Unknown component type (should error)")
    try:
        resp = client.add_component(test_bp, "FakeComponent", "BadComp")
        record("unknown_type_error", False, "Expected error but got success")
    except BlueprintLLMError as e:
        record("unknown_type_error", "unknown component type" in str(e).lower(),
               str(e)[:80])
    except Exception as e:
        record("unknown_type_error", False, str(e))

    # --- Cleanup test BP ---
    print("\n[Cleanup] Deleting test Blueprint")
    try:
        client.delete_blueprint(test_bp)
        print("  Deleted BP_ComponentTest")
    except Exception:
        print("  Warning: could not delete test BP")

    # --- Game Blueprint collision (optional) ---
    if add_game_bps:
        print("\n" + "=" * 60)
        print("Adding Collision to Game Blueprints")
        print("=" * 60)

        game_configs = [
            {
                "bp": "BP_Pickup",
                "name": "CollisionBox",
                "extent": {"x": 50, "y": 50, "z": 50},
            },
            {
                "bp": "BP_HazardZone",
                "name": "CollisionBox",
                "extent": {"x": 200, "y": 200, "z": 100},
            },
            {
                "bp": "BP_VictoryZone",
                "name": "CollisionBox",
                "extent": {"x": 200, "y": 200, "z": 200},
            },
        ]

        for cfg in game_configs:
            bp = cfg["bp"]
            print(f"\n  Adding BoxCollision to {bp}...")
            try:
                resp = client.add_component(
                    bp, "BoxCollision", cfg["name"],
                    properties={
                        "extent": cfg["extent"],
                        "generate_overlap_events": True,
                        "collision_profile": "OverlapAllDynamic",
                    }
                )
                data = resp.get("data", {})
                record(f"game_{bp}_collision",
                       resp.get("status") == "ok" and data.get("compiled"),
                       f"extent={cfg['extent']}")
            except BlueprintLLMError as e:
                if "already exists" in str(e).lower():
                    record(f"game_{bp}_collision", True,
                           "Already has collision (idempotent)")
                else:
                    record(f"game_{bp}_collision", False, str(e))
            except Exception as e:
                record(f"game_{bp}_collision", False, str(e))

    # --- Summary ---
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"Results: {passed} PASS, {failed} FAIL out of {len(results)} tests")
    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="Test component management commands")
    parser.add_argument("--game-bps", action="store_true",
                        help="Also add collision to game Blueprints")
    args = parser.parse_args()

    try:
        client = ArcwrightClient(timeout=60)
    except (ConnectionRefusedError, OSError) as e:
        print(f"ERROR: Cannot connect to UE command server: {e}")
        print("Is Unreal Editor running with the BlueprintLLM plugin?")
        sys.exit(1)

    try:
        results = run_tests(client, add_game_bps=args.game_bps)
    finally:
        client.close()

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "results",
        f"component_test_{timestamp}.json"
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "tests": results,
            "passed": sum(1 for r in results if r["status"] == "PASS"),
            "failed": sum(1 for r in results if r["status"] == "FAIL"),
        }, f, indent=2)
    print(f"\nReport saved: {report_path}")

    failed = sum(1 for r in results if r["status"] == "FAIL")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
