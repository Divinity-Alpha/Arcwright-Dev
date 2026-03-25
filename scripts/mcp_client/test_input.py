"""
Test script for Enhanced Input commands (B29).

Tests: setup_input_context, add_input_action, add_input_mapping, get_input_actions.

Usage:
    python scripts/mcp_client/test_input.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError


def run_tests(client):
    results = []

    def record(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    print("=" * 60)
    print("Enhanced Input Tests (B29)")
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

    # Test 1: setup_input_context
    print("\n[Test 1] setup_input_context")
    try:
        resp = client.setup_input_context("IMC_Test")
        data = resp.get("data", {})
        record("setup_input_context", data.get("name") == "IMC_Test",
               f"path={data.get('asset_path', '')}")
    except Exception as e:
        record("setup_input_context", False, str(e))

    # Test 2: add_input_action (bool)
    print("\n[Test 2] add_input_action (bool)")
    try:
        resp = client.add_input_action("IA_Jump", "bool")
        data = resp.get("data", {})
        record("add_input_action_bool", data.get("name") == "IA_Jump",
               f"type={data.get('value_type', '')}")
    except Exception as e:
        record("add_input_action_bool", False, str(e))

    # Test 3: add_input_action (axis2d)
    print("\n[Test 3] add_input_action (axis2d)")
    try:
        resp = client.add_input_action("IA_Move", "axis2d")
        data = resp.get("data", {})
        record("add_input_action_axis2d", data.get("name") == "IA_Move",
               f"type={data.get('value_type', '')}")
    except Exception as e:
        record("add_input_action_axis2d", False, str(e))

    # Test 4: add_input_mapping (Jump -> SpaceBar)
    print("\n[Test 4] add_input_mapping (IA_Jump -> SpaceBar)")
    try:
        resp = client.add_input_mapping("IMC_Test", "IA_Jump", "SpaceBar")
        data = resp.get("data", {})
        record("add_input_mapping_jump",
               data.get("key") == "SpaceBar" and data.get("mapping_count", 0) >= 1,
               f"mappings={data.get('mapping_count', 0)}")
    except Exception as e:
        record("add_input_mapping_jump", False, str(e))

    # Test 5: add_input_mapping (Move -> W)
    print("\n[Test 5] add_input_mapping (IA_Move -> W)")
    try:
        resp = client.add_input_mapping("IMC_Test", "IA_Move", "W")
        data = resp.get("data", {})
        record("add_input_mapping_move",
               data.get("key") == "W" and data.get("mapping_count", 0) >= 2,
               f"mappings={data.get('mapping_count', 0)}")
    except Exception as e:
        record("add_input_mapping_move", False, str(e))

    # Test 6: get_input_actions
    print("\n[Test 6] get_input_actions")
    try:
        resp = client.get_input_actions()
        data = resp.get("data", {})
        actions = data.get("actions", [])
        names = [a["name"] for a in actions]
        has_jump = "IA_Jump" in names
        has_move = "IA_Move" in names
        record("get_input_actions", has_jump and has_move,
               f"count={data.get('count', 0)}, found: {names}")
    except Exception as e:
        record("get_input_actions", False, str(e))

    # Test 7: Error case — add_input_mapping with nonexistent context
    print("\n[Test 7] Error: mapping with bad context")
    try:
        client.add_input_mapping("IMC_NonExistent", "IA_Jump", "SpaceBar")
        record("error_bad_context", False, "Should have raised error")
    except BlueprintLLMError as e:
        record("error_bad_context", "not found" in str(e).lower(), str(e))
    except Exception as e:
        record("error_bad_context", False, str(e))

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

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} PASS")
    print(f"{'=' * 60}")

    # Save report
    report = {
        "test_suite": "input_commands_B29",
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "summary": {"passed": passed, "total": total},
    }
    os.makedirs("results", exist_ok=True)
    report_path = f"results/input_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {report_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
