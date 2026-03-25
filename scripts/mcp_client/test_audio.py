"""
Test script for Audio commands (B24).

Tests: play_sound_at_location, add_audio_component, get_sound_assets.

Usage:
    python scripts/mcp_client/test_audio.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError


def run_tests(client):
    results = []
    test_bp = "BP_AudioTest"

    def record(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append({"test": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    print("=" * 60)
    print("Audio Command Tests (B24)")
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

    # Test 1: Create test Blueprint
    print("\n[Test 1] Create test Blueprint")
    try:
        try:
            client.delete_blueprint(test_bp)
        except BlueprintLLMError:
            pass
        dsl_text = f"""BLUEPRINT: {test_bp}
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Audio Test"]
EXEC n1.Then -> n2.Execute"""
        resp = client.create_blueprint_from_dsl(dsl_text)
        record("create_test_bp", resp.get("status") == "ok",
               resp.get("data", {}).get("blueprint_name", ""))
    except Exception as e:
        record("create_test_bp", False, str(e))

    # Test 2: get_sound_assets (game folder — may be empty)
    print("\n[Test 2] get_sound_assets (/Game)")
    try:
        resp = client.get_sound_assets(path="/Game")
        data = resp.get("data", {})
        record("get_sound_assets_game", resp.get("status") == "ok",
               f"count={data.get('count', 0)}")
    except Exception as e:
        record("get_sound_assets_game", False, str(e))

    # Test 3: get_sound_assets (engine folder)
    print("\n[Test 3] get_sound_assets (/Engine)")
    try:
        resp = client.get_sound_assets(path="/Engine")
        data = resp.get("data", {})
        record("get_sound_assets_engine", resp.get("status") == "ok",
               f"count={data.get('count', 0)}")
    except Exception as e:
        record("get_sound_assets_engine", False, str(e))

    # Test 4: add_audio_component (default)
    print("\n[Test 4] add_audio_component (default)")
    try:
        resp = client.add_audio_component(test_bp, name="AudioDefault")
        data = resp.get("data", {})
        record("add_audio_default",
               data.get("component_name") == "AudioDefault" and data.get("compiled"),
               f"auto_activate={data.get('auto_activate')}")
    except Exception as e:
        record("add_audio_default", False, str(e))

    # Test 5: add_audio_component (auto_activate=false)
    print("\n[Test 5] add_audio_component (auto_activate=false)")
    try:
        resp = client.add_audio_component(test_bp, name="AudioManual",
                                           auto_activate=False)
        data = resp.get("data", {})
        record("add_audio_no_auto",
               data.get("component_name") == "AudioManual" and not data.get("auto_activate"),
               f"auto_activate={data.get('auto_activate')}")
    except Exception as e:
        record("add_audio_no_auto", False, str(e))

    # Test 6: Error — play_sound_at_location with bad path
    print("\n[Test 6] Error: play_sound_at_location bad path")
    try:
        client.play_sound_at_location("/Game/Nonexistent/Sound.Sound",
                                       {"x": 0, "y": 0, "z": 0})
        record("error_bad_sound", False, "Should have raised error")
    except BlueprintLLMError as e:
        record("error_bad_sound", "not found" in str(e).lower(), str(e))
    except Exception as e:
        record("error_bad_sound", False, str(e))

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
        "test_suite": "audio_commands_B24",
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "summary": {"passed": passed, "total": total},
    }
    os.makedirs("results", exist_ok=True)
    report_path = f"results/audio_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {report_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
