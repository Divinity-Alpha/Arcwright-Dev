"""
intent_test_setup.py
--------------------
Creates the known level state required by the Arcwright Intent Test Suite.

1. Creates 5 Blueprints: BP_WallSegment, BP_EnemyGuard, BP_GoldCoin, BP_Torch, BP_HealthPotion
2. BP_EnemyGuard vars: Health(Float=100), Damage(Float=15), Speed(Float=300)
3. BP_GoldCoin vars: Value(Int=10)
4. BP_Torch vars: Intensity(Float=5000)
5. Spawns: 8 walls, 3 enemies, 5 coins, 4 torches, 2 health potions
6. Creates + applies MI_Stone to walls, MI_GoldMetal to coins

Usage:
    python scripts/tests/intent_test_setup.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.mcp_client.blueprint_client import ArcwrightClient, BlueprintLLMError


def log(msg):
    ts = time.strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}")
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii', errors='replace').decode()}")
    sys.stdout.flush()


def setup_level():
    log("Connecting to UE Command Server on localhost:13377...")
    client = ArcwrightClient(timeout=60.0)
    info = client.health_check()
    log(f"Connected: {info.get('data', {}).get('server', 'unknown')}")

    # ── 1. Create Blueprints with variables ──────────────────────
    blueprints = {
        "BP_WallSegment": [],
        "BP_EnemyGuard": [
            {"name": "Health", "type": "Float", "default": "100"},
            {"name": "Damage", "type": "Float", "default": "15"},
            {"name": "Speed", "type": "Float", "default": "300"},
        ],
        "BP_GoldCoin": [
            {"name": "Value", "type": "Int", "default": "10"},
        ],
        "BP_Torch": [
            {"name": "Intensity", "type": "Float", "default": "5000"},
        ],
        "BP_HealthPotion": [],
    }

    for bp_name, variables in blueprints.items():
        # Delete existing
        try:
            client.delete_blueprint(bp_name)
            log(f"  Deleted existing {bp_name}")
        except BlueprintLLMError:
            pass

        # Create via DSL (reliable path for new BPs with variables)
        try:
            dsl = f"BLUEPRINT: {bp_name}\nCLASS: Actor\n"
            for v in variables:
                dsl += f"VAR {v['name']}: {v['type']} = {v['default']}\n"
            client.create_blueprint_from_dsl(dsl, bp_name)
            log(f"  Created {bp_name}" + (f" with {len(variables)} vars" if variables else ""))
        except BlueprintLLMError as e:
            log(f"  FAILED to create {bp_name}: {e}")

    time.sleep(1.0)

    # ── 2. Create materials ──────────────────────────────────────
    materials = {
        "MI_Stone": {"r": 0.4, "g": 0.38, "b": 0.35},
        "MI_GoldMetal": {"r": 1.0, "g": 0.84, "b": 0.0},
    }

    for mat_name, color in materials.items():
        try:
            client.create_simple_material(mat_name, color)
            log(f"  Created material {mat_name}")
        except BlueprintLLMError as e:
            log(f"  Material {mat_name}: {e}")
    time.sleep(0.5)

    # ── 3. Spawn actors ──────────────────────────────────────────
    spawn_config = [
        ("BP_WallSegment", 8, [
            {"x": -500, "y": i * 250, "z": 50} for i in range(8)
        ]),
        ("BP_EnemyGuard", 3, [
            {"x": 500, "y": i * 400, "z": 50} for i in range(3)
        ]),
        ("BP_GoldCoin", 5, [
            {"x": 0, "y": i * 300, "z": 50} for i in range(5)
        ]),
        ("BP_Torch", 4, [
            {"x": -300, "y": i * 300, "z": 100} for i in range(4)
        ]),
        ("BP_HealthPotion", 2, [
            {"x": 300, "y": i * 400, "z": 50} for i in range(2)
        ]),
    ]

    actor_labels = {}  # bp_name -> [labels]
    for bp_name, count, positions in spawn_config:
        labels = []
        bp_class = f"/Game/Arcwright/Generated/{bp_name}.{bp_name}"
        for i, pos in enumerate(positions):
            label = f"{bp_name}_{i}"
            try:
                result = client.spawn_actor_at(
                    actor_class=bp_class,
                    location=pos,
                    label=label,
                )
                actual_label = result.get("data", {}).get("label", label)
                labels.append(actual_label)
            except BlueprintLLMError as e:
                log(f"  WARN: spawn {bp_name}_{i}: {e}")
                labels.append(label)
        actor_labels[bp_name] = labels
        log(f"  Spawned {count}x {bp_name}")

    time.sleep(1.0)

    # ── 4. Apply materials to actors ─────────────────────────────
    mat_assignments = {
        "BP_WallSegment": "/Game/Arcwright/Materials/MI_Stone",
        "BP_GoldCoin": "/Game/Arcwright/Materials/MI_GoldMetal",
    }

    for bp_name, mat_path in mat_assignments.items():
        for label in actor_labels.get(bp_name, []):
            try:
                client.send_command("set_actor_material", {
                    "actor_label": label,
                    "material_path": mat_path,
                })
            except BlueprintLLMError:
                pass
        log(f"  Applied material to {bp_name} actors")

    # ── 5. Save ──────────────────────────────────────────────────
    try:
        client.save_all()
        log("  Saved all")
    except BlueprintLLMError as e:
        log(f"  Save warning: {e}")

    # ── 6. Verify ────────────────────────────────────────────────
    try:
        level = client.get_level_info()
        actor_count = level.get("data", {}).get("actor_count", "?")
        log(f"Level state: {actor_count} actors")
    except BlueprintLLMError:
        pass

    # Verify BPs exist
    for bp_name in blueprints:
        try:
            info = client.get_blueprint_info(bp_name)
            vars_found = len(info.get("data", {}).get("variables", []))
            log(f"  OK {bp_name} -- {vars_found} variables")
        except BlueprintLLMError:
            log(f"  MISSING {bp_name}")

    client.close()
    log("Setup complete.")


if __name__ == "__main__":
    setup_level()
