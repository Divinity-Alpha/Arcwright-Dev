#!/usr/bin/env python3
"""Test all 4 game base modes by switching game modes via TCP.

Verifies that each game mode Blueprint exists and can be set as the active
game mode for the current level. Requires UE Editor running with TCP server
on port 13377.

Usage:
    python scripts/test_game_modes.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.mcp_client.blueprint_client import ArcwrightClient

GAME_MODES = [
    {
        "type": "fps",
        "bp_name": "BP_FirstPersonGameMode",
        "game_mode_path": "/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode.BP_FirstPersonGameMode_C",
        "description": "FPS — WASD, mouse look, jump, cursor hidden",
    },
    {
        "type": "thirdperson",
        "bp_name": "BP_ThirdPersonGameMode",
        "game_mode_path": "/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode.BP_ThirdPersonGameMode_C",
        "description": "Third Person — spring arm camera, character faces movement",
    },
    {
        "type": "topdown",
        "bp_name": "BP_TopDownGameMode",
        "game_mode_path": "/Game/TopDown/Blueprints/BP_TopDownGameMode.BP_TopDownGameMode_C",
        "description": "Top Down — overhead camera, click-to-move, visible cursor",
    },
    {
        "type": "driving",
        "bp_name": "BP_VehicleAdvGameMode",
        "game_mode_path": "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvGameMode.BP_VehicleAdvGameMode_C",
        "description": "Driving — Chaos vehicle physics, chase camera, throttle/brake/steering",
    },
]


def main():
    passed = 0
    failed = 0
    results = []

    try:
        client = ArcwrightClient()
    except Exception as e:
        print(f"FAIL: Cannot connect to UE Editor TCP server on port 13377: {e}")
        print("Make sure UE Editor is running with the Arcwright plugin.")
        sys.exit(1)

    # Health check
    try:
        health = client.health_check()
        print(f"Connected to {health.get('server', 'unknown')} v{health.get('version', '?')}")
        print(f"Engine: {health.get('engine_version', '?')}")
        print()
    except Exception as e:
        print(f"FAIL: health_check failed: {e}")
        client.close()
        sys.exit(1)

    for mode in GAME_MODES:
        test_name = f"set_game_mode({mode['bp_name']})"
        print(f"TEST: {test_name}")
        print(f"      {mode['description']}")

        try:
            result = client.set_game_mode(mode["bp_name"])
            if result.get("status") == "ok" or "game_mode" in str(result.get("data", {})).lower():
                print(f"  PASS")
                passed += 1
                results.append((test_name, "PASS", None))
            else:
                error = result.get("message", str(result))
                print(f"  FAIL: {error}")
                failed += 1
                results.append((test_name, "FAIL", error))
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1
            results.append((test_name, "FAIL", str(e)))

        time.sleep(0.5)

    # Restore to FPS as default
    print()
    print("Restoring FPS game mode as default...")
    try:
        client.set_game_mode("BP_FirstPersonGameMode")
        print("  Restored.")
    except Exception:
        print("  Warning: could not restore FPS mode.")

    client.close()

    # Summary
    print()
    print("=" * 50)
    print(f"GAME MODE TEST RESULTS: {passed}/{passed + failed} PASS")
    print("=" * 50)
    for name, status, error in results:
        marker = "PASS" if status == "PASS" else f"FAIL: {error}"
        print(f"  {marker} — {name}")

    if failed > 0:
        print(f"\n{failed} test(s) failed.")
        sys.exit(1)
    else:
        print("\nAll game modes verified.")
        sys.exit(0)


if __name__ == "__main__":
    main()
