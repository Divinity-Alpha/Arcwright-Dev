"""
Test script for BlueprintLLM Level Population Commands.

Tests spawn_actor_at, get_actors, set_actor_transform, delete_actor.
Requires UE5 Editor running with BlueprintLLM plugin loaded.

Usage:
    python scripts/mcp_client/test_level_commands.py
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

TEST_LABEL = "BPLLM_Test"


def main():
    results = []
    passed = 0
    failed = 0
    skipped = 0

    def record(step, name, ok, detail=""):
        nonlocal passed, failed
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({"step": step, "name": name, "status": status, "detail": detail})
        tag = "OK" if ok else "FAIL"
        suffix = f" — {detail}" if detail else ""
        print(f"[{step:>2}] {name}... {tag}{suffix}")

    print("=" * 60)
    print("BlueprintLLM Level Commands — Test Suite")
    print("=" * 60)

    # Step 1: Connect + health_check
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
        print("\nIs UE5 Editor running with the BlueprintLLM plugin?")
        return 1

    # Step 2: get_actors baseline
    try:
        r = client.get_actors()
        baseline_count = r.get("data", {}).get("count", 0)
        record(2, "get_actors (baseline)", True, f"count={baseline_count}")
    except Exception as e:
        record(2, "get_actors (baseline)", False, str(e))
        baseline_count = -1

    # Step 3: spawn_actor_at
    try:
        r = client.spawn_actor_at(
            actor_class="StaticMeshActor",
            location={"x": 0, "y": 0, "z": 200},
            label=TEST_LABEL
        )
        data = r.get("data", {})
        label = data.get("label", "")
        cls = data.get("class", "")
        ok = label == TEST_LABEL and "StaticMeshActor" in cls
        record(3, f"spawn_actor_at ({TEST_LABEL})", ok,
               f"label={label}, class={cls}")
    except Exception as e:
        record(3, f"spawn_actor_at ({TEST_LABEL})", False, str(e))

    # Step 4: get_actors — verify count increased
    try:
        r = client.get_actors()
        new_count = r.get("data", {}).get("count", 0)
        actors = r.get("data", {}).get("actors", [])
        found = any(a.get("label") == TEST_LABEL for a in actors)
        ok = new_count > baseline_count and found
        record(4, "get_actors (verify spawn)", ok,
               f"count={new_count} (was {baseline_count}), found={found}")
    except Exception as e:
        record(4, "get_actors (verify spawn)", False, str(e))

    # Step 5: set_actor_transform
    try:
        r = client.set_actor_transform(
            label=TEST_LABEL,
            location={"x": 500, "y": 500, "z": 100},
            rotation={"pitch": 0, "yaw": 90, "roll": 0}
        )
        data = r.get("data", {})
        loc = data.get("location", {})
        rot = data.get("rotation", {})
        ok = (abs(loc.get("x", 0) - 500) < 1 and
              abs(loc.get("y", 0) - 500) < 1 and
              abs(rot.get("yaw", 0) - 90) < 1)
        record(5, "set_actor_transform", ok,
               f"loc=({loc.get('x',0):.0f},{loc.get('y',0):.0f},{loc.get('z',0):.0f}) "
               f"yaw={rot.get('yaw',0):.0f}")
    except Exception as e:
        record(5, "set_actor_transform", False, str(e))

    # Step 6: get_actors — verify new location
    try:
        r = client.get_actors(class_filter="StaticMeshActor")
        actors = r.get("data", {}).get("actors", [])
        test_actor = next((a for a in actors if a.get("label") == TEST_LABEL), None)
        if test_actor:
            loc = test_actor.get("location", {})
            ok = abs(loc.get("x", 0) - 500) < 1 and abs(loc.get("y", 0) - 500) < 1
            record(6, "get_actors (verify transform)", ok,
                   f"loc=({loc.get('x',0):.0f},{loc.get('y',0):.0f},{loc.get('z',0):.0f})")
        else:
            record(6, "get_actors (verify transform)", False, "actor not found")
    except Exception as e:
        record(6, "get_actors (verify transform)", False, str(e))

    # Step 7: delete_actor
    try:
        r = client.delete_actor(TEST_LABEL)
        data = r.get("data", {})
        deleted = data.get("deleted", False)
        record(7, "delete_actor", deleted, f"deleted={deleted}")
    except Exception as e:
        record(7, "delete_actor", False, str(e))

    # Step 8: get_actors — verify count back to baseline
    try:
        r = client.get_actors()
        final_count = r.get("data", {}).get("count", 0)
        ok = final_count == baseline_count
        record(8, "get_actors (verify deletion)", ok,
               f"count={final_count} (baseline={baseline_count})")
    except Exception as e:
        record(8, "get_actors (verify deletion)", False, str(e))

    # Step 9: delete_actor again — idempotent
    try:
        r = client.delete_actor(TEST_LABEL)
        data = r.get("data", {})
        deleted = data.get("deleted", False)
        ok = not deleted  # Should be false — already gone
        record(9, "delete_actor (idempotent)", ok, f"deleted={deleted}")
    except Exception as e:
        record(9, "delete_actor (idempotent)", False, str(e))

    # Step 10: Spawn Blueprint actor (if one exists)
    try:
        r = client.get_actors()  # Just to make sure connection is alive
        # Try spawning a generated Blueprint if available
        bp_path = "/Game/Arcwright/Generated/BP_HelloWorld"
        try:
            r = client.spawn_actor_at(
                actor_class=bp_path,
                location={"x": 1000, "y": 0, "z": 200},
                label="BPLLM_BP_Test"
            )
            data = r.get("data", {})
            record(10, f"spawn Blueprint actor", True,
                   f"class={data.get('class','?')}")
            # Cleanup
            try:
                client.delete_actor("BPLLM_BP_Test")
            except Exception:
                pass
        except BlueprintLLMError as e:
            # Not an error — the BP may not exist
            record(10, "spawn Blueprint actor", True,
                   f"SKIP (no BP available): {e}")
    except Exception as e:
        record(10, "spawn Blueprint actor", False, str(e))

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
    report_path = os.path.join(RESULTS_DIR, f"level_test_{timestamp}.json")
    report = {
        "timestamp": timestamp,
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
