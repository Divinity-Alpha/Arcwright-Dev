"""
Test script for Niagara particle commands (B25).

Tests: spawn_niagara_at_location, add_niagara_component, get_niagara_assets.

Usage:
    python scripts/mcp_client/test_niagara.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError


def run_tests(client):
    results = []
    test_bp = "BP_NiagaraTest"

    def record(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    print("=" * 60)
    print("Niagara Particle Tests (B25)")
    print("=" * 60)

    # Test 0: Health check
    print("\n[Test 0] Health check")
    try:
        resp = client.health_check()
        record("health_check", resp.get("status") == "ok",
               resp.get("data", {}).get("version", ""))
    except Exception as e:
        record("health_check", False, str(e))
        print("Cannot connect. Aborting.")
        return results

    # Test 1: get_niagara_assets (game folder)
    print("\n[Test 1] get_niagara_assets (/Game)")
    try:
        resp = client.get_niagara_assets(path="/Game")
        data = resp.get("data", {})
        record("get_niagara_game", resp.get("status") == "ok",
               f"count={data.get('count', 0)}")
    except Exception as e:
        record("get_niagara_game", False, str(e))

    # Test 2: get_niagara_assets (Niagara plugin)
    print("\n[Test 2] get_niagara_assets (/Niagara)")
    try:
        resp = client.get_niagara_assets(path="/Niagara")
        data = resp.get("data", {})
        record("get_niagara_plugin", resp.get("status") == "ok",
               f"count={data.get('count', 0)}")
    except Exception as e:
        record("get_niagara_plugin", False, str(e))

    # Test 3: Create test BP + add_niagara_component
    print("\n[Test 3] add_niagara_component")
    try:
        try:
            client.delete_blueprint(test_bp)
        except BlueprintLLMError:
            pass
        dsl_text = f"""BLUEPRINT: {test_bp}
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Niagara Test"]
EXEC n1.Then -> n2.Execute"""
        client.create_blueprint_from_dsl(dsl_text)

        resp = client.add_niagara_component(test_bp, name="FX_Particles")
        data = resp.get("data", {})
        record("add_niagara_component",
               data.get("component_name") == "FX_Particles" and data.get("compiled"),
               f"auto_activate={data.get('auto_activate')}")
    except Exception as e:
        record("add_niagara_component", False, str(e))

    # Test 4: Error — spawn_niagara_at_location with bad system
    print("\n[Test 4] Error: spawn with nonexistent system")
    try:
        client.spawn_niagara_at_location("/Game/Nonexistent/NS_Bad.NS_Bad",
                                          {"x": 0, "y": 0, "z": 0})
        record("error_bad_system", False, "Should have raised error")
    except BlueprintLLMError as e:
        record("error_bad_system", "not found" in str(e).lower(), str(e))
    except Exception as e:
        record("error_bad_system", False, str(e))

    # Test 5: Error — add_niagara_component with bad blueprint
    print("\n[Test 5] Error: add niagara to nonexistent BP")
    try:
        client.add_niagara_component("BP_DoesNotExist_XYZ", name="FX")
        record("error_bad_bp", False, "Should have raised error")
    except BlueprintLLMError as e:
        record("error_bad_bp", "not found" in str(e).lower(), str(e))
    except Exception as e:
        record("error_bad_bp", False, str(e))

    return results


def main():
    print(f"Connecting to BlueprintLLM Command Server...")
    try:
        client = ArcwrightClient(timeout=30.0)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    try:
        results = run_tests(client)
    finally:
        client.close()

    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} PASS")
    print(f"{'=' * 60}")

    report = {
        "test_suite": "niagara_commands_B25",
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "summary": {"passed": passed, "total": total},
    }
    os.makedirs("results", exist_ok=True)
    report_path = f"results/niagara_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {report_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
