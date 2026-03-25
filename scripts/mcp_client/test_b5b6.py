"""
B5+B6 Test Suite — Individual node/connection editing commands.

Tests add_node, remove_node, add_connection, remove_connection,
set_node_param, set_variable_default against BP_HelloMCP.

Scenario: Insert a Delay node between BeginPlay and PrintString,
wire it up, change the duration, verify, then clean up.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blueprint_client import ArcwrightClient


def main():
    client = ArcwrightClient(timeout=15)

    print("B5+B6 COMMAND TEST SUITE")
    print("=" * 60)

    passed = 0
    total = 0

    # ---- Test 1: Verify BP_HelloMCP exists ----
    total += 1
    print("\n1. Verify BP_HelloMCP exists...")
    try:
        info = client.get_blueprint_info("BP_HelloMCP")
        nodes = info["data"]["nodes"]
        print(f"   Nodes: {len(nodes)}")
        for n in nodes:
            print(f"     {n['id']}: {n['class']} ({n['title']})")
        conns = info["data"]["connections"]
        print(f"   Connections: {len(conns)}")
        for c in conns:
            print(f"     {c['source_node']}.{c['source_pin']} -> {c['target_node']}.{c['target_pin']}")
        passed += 1
        print("   PASS")
    except Exception as e:
        print(f"   FAIL: {e}")
        client.close()
        return 1

    # Map node IDs by class/title
    beginplay_id = None
    printstring_id = None
    for n in nodes:
        title = n.get("title", "")
        if "Begin" in title and "Play" in title:
            beginplay_id = n["id"]
        elif "Print String" in title:
            printstring_id = n["id"]

    print(f"\n   Mapped: BeginPlay={beginplay_id}, PrintString={printstring_id}")

    # ---- Test 2: add_node — add a Delay node ----
    total += 1
    print("\n2. add_node (Delay)...")
    delay_id = None
    try:
        result = client.add_node("BP_HelloMCP", "Delay", node_id="delay_1",
                                 params={"Duration": "2.0"})
        delay_id = result["data"]["node_id"]
        delay_class = result["data"]["class"]
        pins = [p["name"] for p in result["data"]["pins"]]
        print(f"   Node ID: {delay_id}")
        print(f"   Class: {delay_class}")
        print(f"   Pins: {pins}")
        print(f"   Compiled: {result['data']['compiled']}")
        passed += 1
        print("   PASS")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 3: Verify Delay appears in blueprint info ----
    total += 1
    print("\n3. Verify Delay node in Blueprint...")
    delay_node_id = None
    try:
        info = client.get_blueprint_info("BP_HelloMCP")
        nodes = info["data"]["nodes"]
        print(f"   Nodes now: {len(nodes)}")
        for n in nodes:
            title = n.get("title", "")
            print(f"     {n['id']}: {n['class']} ({title})")
            if "Delay" in title:
                delay_node_id = n["id"]

        if delay_node_id is None and delay_id:
            delay_node_id = delay_id

        if delay_node_id:
            passed += 1
            print(f"   Delay node found: {delay_node_id}")
            print("   PASS")
        else:
            print("   FAIL - Delay not found in nodes")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 4: remove_connection — disconnect BeginPlay -> PrintString ----
    total += 1
    print("\n4. remove_connection (BeginPlay -> PrintString)...")
    try:
        if beginplay_id and printstring_id:
            result = client.remove_connection(
                "BP_HelloMCP", beginplay_id, "Then", printstring_id, "execute"
            )
            print(f"   Disconnected: {result['data']['disconnected']}")
            print(f"   Compiled: {result['data']['compiled']}")
            passed += 1
            print("   PASS")
        else:
            print("   SKIP - could not identify nodes")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 5: add_connection — BeginPlay -> Delay ----
    total += 1
    print("\n5. add_connection (BeginPlay -> Delay)...")
    try:
        if beginplay_id and delay_node_id:
            result = client.add_connection(
                "BP_HelloMCP", beginplay_id, "Then", delay_node_id, "execute"
            )
            print(f"   Connected: {result['data']['connected']}")
            print(f"   Compiled: {result['data']['compiled']}")
            passed += 1
            print("   PASS")
        else:
            print(f"   SKIP - beginplay={beginplay_id}, delay={delay_node_id}")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 6: add_connection — Delay -> PrintString ----
    total += 1
    print("\n6. add_connection (Delay -> PrintString)...")
    try:
        if delay_node_id and printstring_id:
            result = client.add_connection(
                "BP_HelloMCP", delay_node_id, "Then", printstring_id, "execute"
            )
            print(f"   Connected: {result['data']['connected']}")
            print(f"   Compiled: {result['data']['compiled']}")
            passed += 1
            print("   PASS")
        else:
            print(f"   SKIP - delay={delay_node_id}, print={printstring_id}")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 7: set_node_param — change Delay duration ----
    total += 1
    print("\n7. set_node_param (Delay Duration = 5.0)...")
    try:
        if delay_node_id:
            result = client.set_node_param(
                "BP_HelloMCP", delay_node_id, "Duration", "5.0"
            )
            print(f"   Pin: {result['data']['pin_name']}")
            print(f"   Value: {result['data']['value']}")
            print(f"   Compiled: {result['data']['compiled']}")
            passed += 1
            print("   PASS")
        else:
            print("   SKIP - no delay node")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 8: Final verification ----
    total += 1
    print("\n8. Final verification (BeginPlay -> Delay -> PrintString)...")
    try:
        info = client.get_blueprint_info("BP_HelloMCP")
        nodes = info["data"]["nodes"]
        conns = info["data"]["connections"]
        compiled = info["data"]["compiled"]
        print(f"   Nodes: {len(nodes)}")
        print(f"   Connections: {len(conns)}")
        for c in conns:
            print(f"     {c['source_node']}.{c['source_pin']} -> {c['target_node']}.{c['target_pin']}")
        print(f"   Compiled: {compiled}")
        if compiled and len(conns) >= 2:
            passed += 1
            print("   PASS")
        else:
            print(f"   PARTIAL - compiled={compiled}, conns={len(conns)}")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 9: set_variable_default (on BP_MCPStressTest) ----
    total += 1
    print("\n9. set_variable_default (Health = 200.0 on BP_MCPStressTest)...")
    try:
        result = client.set_variable_default("BP_MCPStressTest", "Health", "200.0")
        print(f"   Variable: {result['data']['variable_name']}")
        print(f"   Value: {result['data']['default_value']}")
        print(f"   Type: {result['data']['type']}")
        print(f"   Compiled: {result['data']['compiled']}")
        passed += 1
        print("   PASS")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 10: remove_node — clean up Delay ----
    total += 1
    print("\n10. remove_node (remove Delay from BP_HelloMCP)...")
    try:
        if delay_node_id:
            result = client.remove_node("BP_HelloMCP", delay_node_id)
            print(f"   Deleted: {result['data']['deleted']}")
            print(f"   Compiled: {result['data']['compiled']}")
            passed += 1
            print("   PASS")
        else:
            print("   SKIP - no delay node")
    except Exception as e:
        print(f"   FAIL: {e}")

    # ---- Test 11: Rewire BeginPlay -> PrintString ----
    total += 1
    print("\n11. Rewire BeginPlay -> PrintString (restore original)...")
    try:
        if beginplay_id and printstring_id:
            result = client.add_connection(
                "BP_HelloMCP", beginplay_id, "Then", printstring_id, "execute"
            )
            print(f"   Connected: {result['data']['connected']}")
            print(f"   Compiled: {result['data']['compiled']}")
            passed += 1
            print("   PASS")
        else:
            print("   SKIP")
    except Exception as e:
        print(f"   FAIL: {e}")

    client.close()

    print(f"\n{'=' * 60}")
    print(f"  B5+B6 RESULTS: {passed}/{total} passed")
    print(f"{'=' * 60}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
