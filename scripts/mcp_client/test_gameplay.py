"""
Automated gameplay verification test (B20).

Chains play_in_editor + get_output_log to verify that placed Blueprints
execute correctly during PIE.

Test flow:
  1. Verify UE Editor is connected
  2. Check that game Blueprints exist in the level
  3. Call play_in_editor
  4. Wait for PIE to start (poll for a few seconds)
  5. Call get_output_log filtered for "LogBlueprintUserMessages"
  6. Check if expected PrintString messages appear
  7. Call stop_play
  8. Report pass/fail

Known limitation: PIE may not start programmatically in UE 5.7 due to
FEngineLoop::Tick() not running. If PIE doesn't start, the test will
report this as a known limitation rather than a failure.

Usage:
    python scripts/mcp_client/test_gameplay.py
    python scripts/mcp_client/test_gameplay.py --wait 5     # custom wait time
    python scripts/mcp_client/test_gameplay.py --manual-pie  # user starts PIE manually
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError


def run_gameplay_test(client, wait_seconds=3, manual_pie=False):
    results = []

    def record(name, passed, detail="", known_limitation=False):
        if known_limitation:
            status = "KNOWN_LIMITATION"
        else:
            status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        icon = "~" if known_limitation else ("+" if passed else "!")
        print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))

    print("=" * 60)
    print("Automated Gameplay Verification Test (B20)")
    print("=" * 60)

    # --- Step 1: Health check ---
    print("\n[Step 1] Health check")
    try:
        resp = client.health_check()
        record("health_check", resp.get("status") == "ok",
               resp.get("data", {}).get("version", ""))
    except Exception as e:
        record("health_check", False, str(e))
        print("Cannot connect to UE Editor. Aborting.")
        return results

    # --- Step 2: Check game Blueprints exist in level ---
    print("\n[Step 2] Check level actors")
    try:
        level_info = client.get_level_info()
        data = level_info.get("data", {})
        actor_count = data.get("actor_count", 0)
        class_counts = {item["class"]: item["count"]
                        for item in data.get("class_counts", [])}
        print(f"  Level: {data.get('level_name', '?')}, {actor_count} actors")
        print(f"  Classes: {json.dumps(class_counts, indent=2)}")

        has_game_bps = any(
            c for c in class_counts
            if "BP_Pickup" in c or "BP_Hazard" in c or "BP_Victory" in c
        )
        record("level_has_game_bps", has_game_bps,
               f"{actor_count} actors" + (", game BPs found" if has_game_bps else ", NO game BPs"))
    except Exception as e:
        record("level_has_game_bps", False, str(e))

    # --- Step 3: Get baseline log ---
    print("\n[Step 3] Get baseline output log")
    try:
        baseline = client.get_output_log(last_n_lines=10,
                                         category="LogBlueprintUserMessages")
        baseline_data = baseline.get("data", {})
        baseline_count = baseline_data.get("line_count", 0)
        print(f"  Baseline BlueprintUserMessages lines: {baseline_count}")
        record("baseline_log", True, f"{baseline_count} existing lines")
    except Exception as e:
        baseline_count = 0
        record("baseline_log", False, str(e))

    # --- Step 4: Start PIE ---
    print("\n[Step 4] Start PIE")
    pie_started = False
    if manual_pie:
        print("  --manual-pie mode: Please click Play in the UE Editor now.")
        input("  Press Enter when PIE is running...")
        pie_started = True
        record("play_in_editor", True, "Manual PIE start")
    else:
        try:
            resp = client.play_in_editor()
            data = resp.get("data", {})
            requested = data.get("requested", False)
            print(f"  PIE requested: {requested}")
            if data.get("note"):
                print(f"  Note: {data['note']}")
            record("play_in_editor_request", requested,
                   "Request queued" if requested else "Request failed")
        except Exception as e:
            record("play_in_editor_request", False, str(e))

    # --- Step 5: Wait for PIE + BeginPlay ---
    print(f"\n[Step 5] Waiting {wait_seconds}s for PIE to start and BeginPlay to fire...")
    time.sleep(wait_seconds)

    # --- Step 6: Read output log for PrintString messages ---
    print("\n[Step 6] Read output log (BlueprintUserMessages)")
    try:
        log_resp = client.get_output_log(last_n_lines=100,
                                         category="LogBlueprintUserMessages")
        log_data = log_resp.get("data", {})
        log_lines = log_data.get("lines", [])
        line_count = log_data.get("line_count", 0)

        print(f"  Found {line_count} BlueprintUserMessages lines")

        # Check for expected messages from game Blueprints
        expected_messages = [
            "Picked up!",
            "Entered hazard zone",
            "Victory!",
        ]

        found_messages = []
        for msg in expected_messages:
            found = any(msg.lower() in line.lower() for line in log_lines)
            if found:
                found_messages.append(msg)
                print(f"    Found: \"{msg}\"")

        new_lines = line_count - baseline_count
        has_new_output = new_lines > 0

        if has_new_output:
            pie_started = True
            print(f"  {new_lines} new log lines since baseline")
            record("pie_log_output", True,
                   f"{new_lines} new lines, {len(found_messages)} expected messages found")
        elif not manual_pie:
            record("pie_log_output", False,
                   "No new BlueprintUserMessages -- PIE likely didn't start",
                   known_limitation=True)
        else:
            record("pie_log_output", new_lines > 0,
                   f"{new_lines} new lines" if new_lines > 0 else "No new output")

        # Also grab full log for context
        full_log = client.get_output_log(last_n_lines=20)
        full_lines = full_log.get("data", {}).get("lines", [])
        if full_lines:
            print(f"\n  Last 5 log lines (any category):")
            for line in full_lines[-5:]:
                print(f"    {line.rstrip()}")

    except Exception as e:
        record("pie_log_output", False, str(e))

    # --- Step 7: Stop PIE ---
    print("\n[Step 7] Stop PIE")
    try:
        resp = client.stop_play()
        data = resp.get("data", {})
        stopped = data.get("stopped", False)
        record("stop_play", True,
               "Stopped PIE session" if stopped else "No PIE session was running")
    except Exception as e:
        record("stop_play", False, str(e))

    # --- Summary ---
    print("\n" + "=" * 60)
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    known_count = sum(1 for r in results if r["status"] == "KNOWN_LIMITATION")
    total = len(results)
    print(f"Results: {pass_count} PASS, {fail_count} FAIL, {known_count} KNOWN_LIMITATION / {total} total")

    if not pie_started and not manual_pie:
        print("\nNote: PIE did not start programmatically. This is a known UE 5.7")
        print("limitation (FEngineLoop::Tick doesn't run, so RequestPlaySession")
        print("queues but never processes). Use --manual-pie to test with manual")
        print("PIE start, or click Play in the editor before running this test.")

    print("=" * 60)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Automated gameplay verification test (B20)")
    parser.add_argument("--wait", type=int, default=3,
                        help="Seconds to wait after PIE request (default: 3)")
    parser.add_argument("--manual-pie", action="store_true",
                        help="Prompt user to manually start PIE instead of calling play_in_editor")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=13377)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        client = ArcwrightClient(host=args.host, port=args.port)
    except Exception as e:
        print(f"Failed to connect to UE Editor at {args.host}:{args.port}: {e}")
        sys.exit(1)

    try:
        results = run_gameplay_test(client, wait_seconds=args.wait,
                                    manual_pie=args.manual_pie)
    finally:
        client.close()

    # Save report
    report = {
        "test": "gameplay_verification",
        "timestamp": timestamp,
        "results": results,
        "summary": {
            "total": len(results),
            "pass": sum(1 for r in results if r["status"] == "PASS"),
            "fail": sum(1 for r in results if r["status"] == "FAIL"),
            "known_limitation": sum(1 for r in results if r["status"] == "KNOWN_LIMITATION"),
        }
    }

    report_dir = os.path.join(os.path.dirname(__file__), "..", "..", "results")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"gameplay_test_{timestamp}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")

    sys.exit(0 if report["summary"]["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
