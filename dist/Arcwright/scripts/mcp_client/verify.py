"""
Quick verification script for the BlueprintLLM Command Server.

Tests:
1. TCP connection
2. health_check command
3. import_from_ir with T1_01 HelloWorld
4. get_blueprint_info on the created Blueprint
5. delete_blueprint cleanup

Usage:
    python scripts/mcp_client/verify.py
"""

import sys
import os
import json
import time

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blueprint_client import ArcwrightClient, BlueprintLLMError

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEST_IR_DIR = os.path.join(PROJECT_ROOT, "test_ir")


def main():
    passed = 0
    failed = 0

    # Test 1: Connect
    print("=" * 60)
    print("BlueprintLLM Command Server — Verification")
    print("=" * 60)

    print("\n[1] Connecting to localhost:13377...", end=" ")
    try:
        client = ArcwrightClient(timeout=10)
        print("OK")
        passed += 1
    except Exception as e:
        print(f"FAIL — {e}")
        print("\nIs UE5 Editor running with the BlueprintLLM plugin?")
        return 1

    # Test 2: health_check
    print("[2] health_check...", end=" ")
    try:
        result = client.health_check()
        data = result.get("data", {})
        server = data.get("server", "")
        version = data.get("version", "")
        print(f"OK — {server} v{version}")
        passed += 1
    except Exception as e:
        print(f"FAIL — {e}")
        failed += 1

    # Test 3: import_from_ir
    test_file = os.path.join(TEST_IR_DIR, "T1_01_HelloWorld.blueprint.json")
    print(f"[3] import_from_ir ({os.path.basename(test_file)})...", end=" ")
    if not os.path.exists(test_file):
        print(f"SKIP — file not found: {test_file}")
    else:
        try:
            result = client.import_from_ir(test_file)
            data = result.get("data", {})
            bp_name = data.get("blueprint_name", "?")
            nodes = data.get("nodes_created", 0)
            nodes_exp = data.get("nodes_expected", 0)
            conns = data.get("connections_wired", 0)
            conns_exp = data.get("connections_expected", 0)
            compiled = data.get("compiled", False)
            print(f"OK — {bp_name}: {nodes}/{nodes_exp} nodes, "
                  f"{conns}/{conns_exp} connections, compiled={compiled}")
            passed += 1
        except Exception as e:
            print(f"FAIL — {e}")
            failed += 1

    # Test 4: get_blueprint_info
    print("[4] get_blueprint_info (BP_HelloWorld)...", end=" ")
    try:
        result = client.get_blueprint_info("BP_HelloWorld")
        data = result.get("data", {})
        node_count = len(data.get("nodes", []))
        conn_count = len(data.get("connections", []))
        compiled = data.get("compiled", False)
        print(f"OK — {node_count} nodes, {conn_count} connections, compiled={compiled}")
        passed += 1
    except BlueprintLLMError as e:
        # May not exist if import was skipped
        print(f"FAIL — {e}")
        failed += 1
    except Exception as e:
        print(f"FAIL — {e}")
        failed += 1

    # Test 5: delete_blueprint
    print("[5] delete_blueprint (BP_HelloWorld)...", end=" ")
    try:
        result = client.delete_blueprint("BP_HelloWorld")
        data = result.get("data", {})
        deleted = data.get("deleted", False)
        print(f"OK — deleted={deleted}")
        passed += 1
    except Exception as e:
        print(f"FAIL — {e}")
        failed += 1

    client.close()

    # Summary
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed", end="")
    if failed > 0:
        print(f", {failed} failed")
    else:
        print(" — All tests passed!")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
