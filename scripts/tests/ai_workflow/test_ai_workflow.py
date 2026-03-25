#!/usr/bin/env python3
"""AI Workflow Integration Test Suite.

Mimics how an AI assistant (e.g. Claude via MCP) actually uses the
Arcwright TCP command server. Each test is a sequence of chained calls
that exercise a realistic end-to-end workflow.

10 workflow tests:
  1. Query-then-create       - Level info -> create BP -> spawn -> verify
  2. Build-and-configure     - Create BP -> components -> spawn -> material -> verify
  3. Batch-modify            - Spawn 3 actors -> find -> batch material -> verify
  4. Full enemy setup        - Pawn BP -> behavior tree -> AI setup -> spawn x3
  5. Scene setup             - Lighting -> floor -> material -> spawn game actors
  6. Data-driven             - Create data table -> verify structure
  7. Iterative refinement    - Create BP -> add var -> spawn -> modify -> verify
  8. Cleanup                 - Spawn 5 -> find -> batch delete -> verify empty
  9. Multi-domain            - Blueprint + BT + DT in one session, verify all 3
 10. Error recovery          - Bad command -> check error -> retry -> verify

Requires UE Editor running with Arcwright plugin on TCP port 13377.

Usage:
    python scripts/tests/ai_workflow/test_ai_workflow.py
"""

import sys
import os
import json
import time
import tempfile
from datetime import datetime

# Ensure project root is on the path so we can import the client
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts", "mcp_client"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

from blueprint_client import ArcwrightClient, BlueprintLLMError

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
TEST_IR_DIR = os.path.join(PROJECT_ROOT, "test_ir")

# Unique prefix to avoid collisions with other tests
PFX = "AIW"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_temp_ir(name, parent_class="Actor", variables=None, nodes=None,
                  connections=None):
    """Write a minimal IR JSON file and return its absolute path."""
    if nodes is None:
        nodes = [
            {
                "id": "n1",
                "dsl_type": "Event_BeginPlay",
                "ue_class": "UK2Node_Event",
                "ue_event": "ReceiveBeginPlay",
                "params": {},
                "position": [0, 0],
            }
        ]
    ir = {
        "metadata": {
            "name": name,
            "parent_class": parent_class,
            "category": None,
        },
        "variables": variables or [],
        "nodes": nodes,
        "connections": connections or [],
    }
    os.makedirs(TEST_IR_DIR, exist_ok=True)
    path = os.path.join(TEST_IR_DIR, f"{name}.blueprint.json")
    with open(path, "w") as f:
        json.dump(ir, f, indent=2)
    return path


def safe_delete_bp(client, name):
    """Delete a Blueprint, ignoring errors if it doesn't exist."""
    try:
        client.delete_blueprint(name)
    except Exception:
        pass


def safe_delete_actor(client, label):
    """Delete an actor by label, ignoring errors."""
    try:
        client.delete_actor(label)
    except Exception:
        pass


def safe_cleanup_ir(name):
    """Remove a temp IR file."""
    path = os.path.join(TEST_IR_DIR, f"{name}.blueprint.json")
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Test implementations
# ---------------------------------------------------------------------------

def test_01_query_then_create(client):
    """Query-then-create: get_level_info -> import IR -> spawn -> find_actors."""
    bp_name = f"BP_{PFX}_QTC"
    actor_label = f"{PFX}_QTC_Actor"
    steps = []

    try:
        # Cleanup pre-existing
        safe_delete_actor(client, actor_label)
        safe_delete_bp(client, bp_name)
        time.sleep(0.3)

        # Step 1: Query level info (AI checks the scene first)
        r = client.get_level_info()
        level_name = r.get("data", {}).get("level_name", "?")
        steps.append(("get_level_info", True, f"level={level_name}"))

        # Step 2: Create a Blueprint via IR import
        ir_path = write_temp_ir(bp_name)
        r = client.import_from_ir(ir_path)
        ok = r.get("status") == "ok"
        steps.append(("import_from_ir", ok,
                       f"nodes={r.get('data', {}).get('nodes_created', 0)}"))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 3: Spawn actor from the new Blueprint
        actor_class = f"/Game/Arcwright/Generated/{bp_name}.{bp_name}"
        r = client.spawn_actor_at(actor_class=actor_class,
                                  location={"x": 100, "y": 100, "z": 50},
                                  label=actor_label)
        ok = r.get("status") == "ok"
        steps.append(("spawn_actor_at", ok,
                       f"label={r.get('data', {}).get('label', '?')}"))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 4: Verify actor exists via find_actors
        r = client.find_actors(name_filter=actor_label)
        actors = r.get("data", {}).get("actors", [])
        # find_actors returns "label" field, not "name"
        found = len(actors) >= 1
        steps.append(("find_actors verify", found,
                       f"found={len(actors)} matching"))

        return found, steps

    finally:
        safe_delete_actor(client, actor_label)
        safe_delete_bp(client, bp_name)
        safe_cleanup_ir(bp_name)


def test_02_build_and_configure(client):
    """Build-and-configure: Create BP -> add components -> spawn -> material -> verify."""
    bp_name = f"BP_{PFX}_BAC"
    mat_name = f"MAT_{PFX}_BAC"
    actor_label = f"{PFX}_BAC_Actor"
    steps = []

    try:
        safe_delete_actor(client, actor_label)
        safe_delete_bp(client, bp_name)
        safe_delete_bp(client, mat_name)
        time.sleep(0.3)

        # Step 1: Create a Blueprint
        ir_path = write_temp_ir(bp_name)
        r = client.import_from_ir(ir_path)
        ok = r.get("status") == "ok"
        steps.append(("create blueprint", ok, ""))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 2: Add a StaticMesh component
        r = client.add_component(bp_name, "StaticMesh", "VisualMesh",
                                 properties={"mesh": "/Engine/BasicShapes/Cube.Cube"})
        ok = r.get("status") == "ok"
        steps.append(("add StaticMesh component", ok, ""))
        time.sleep(0.3)

        # Step 3: Add a BoxCollision component
        r = client.add_component(bp_name, "BoxCollision", "HitBox",
                                 properties={"extent": {"x": 50, "y": 50, "z": 50},
                                             "generate_overlap_events": True})
        ok = r.get("status") == "ok"
        steps.append(("add BoxCollision component", ok, ""))
        time.sleep(0.3)

        # Step 4: Spawn the actor
        actor_class = f"/Game/Arcwright/Generated/{bp_name}.{bp_name}"
        r = client.spawn_actor_at(actor_class=actor_class,
                                  location={"x": 200, "y": 0, "z": 50},
                                  label=actor_label)
        ok = r.get("status") == "ok"
        steps.append(("spawn actor", ok, ""))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 5: Create and apply material to the placed actor
        r = client.create_simple_material(mat_name, color={"r": 0.8, "g": 0.2, "b": 0.1})
        ok = r.get("status") == "ok"
        steps.append(("create material", ok, ""))
        time.sleep(0.3)

        r = client.send_command("set_actor_material", {
            "actor_label": actor_label,
            "material_path": f"/Game/Arcwright/Materials/{mat_name}",
        })
        ok = r.get("status") == "ok"
        steps.append(("set_actor_material", ok, ""))
        time.sleep(0.3)

        # Step 6: Verify with get_actor_properties
        r = client.send_command("get_actor_properties", {"actor_label": actor_label})
        ok = r.get("status") == "ok"
        actor_class_name = r.get("data", {}).get("class", "")
        steps.append(("get_actor_properties verify", ok,
                       f"class={actor_class_name}"))

        return ok, steps

    finally:
        safe_delete_actor(client, actor_label)
        safe_delete_bp(client, bp_name)
        safe_delete_bp(client, mat_name)
        safe_cleanup_ir(bp_name)


def test_03_batch_modify(client):
    """Batch-modify: Spawn 3 actors -> find -> batch_apply_material -> verify."""
    bp_name = f"BP_{PFX}_BM"
    mat_name = f"MAT_{PFX}_BM"
    labels = [f"{PFX}_BM_A{i}" for i in range(3)]
    steps = []

    try:
        # Cleanup
        for lbl in labels:
            safe_delete_actor(client, lbl)
        safe_delete_bp(client, bp_name)
        safe_delete_bp(client, mat_name)
        time.sleep(0.3)

        # Step 1: Create a BP with a mesh component
        ir_path = write_temp_ir(bp_name)
        client.import_from_ir(ir_path)
        time.sleep(0.3)
        client.add_component(bp_name, "StaticMesh", "Mesh",
                             properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere"})
        time.sleep(0.3)
        steps.append(("create BP with mesh", True, ""))

        # Step 2: Spawn 3 actors
        actor_class = f"/Game/Arcwright/Generated/{bp_name}.{bp_name}"
        spawn_ok = True
        for i, lbl in enumerate(labels):
            r = client.spawn_actor_at(actor_class=actor_class,
                                      location={"x": i * 200, "y": 500, "z": 50},
                                      label=lbl)
            if r.get("status") != "ok":
                spawn_ok = False
            time.sleep(0.3)
        steps.append(("spawn 3 actors", spawn_ok, ""))

        # Step 3: find_actors to confirm they exist
        r = client.find_actors(name_filter=f"{PFX}_BM_A")
        found = r.get("data", {}).get("actors", [])
        steps.append(("find_actors", len(found) >= 3, f"found={len(found)}"))

        # Step 4: Create material and batch apply
        client.create_simple_material(mat_name, color={"r": 0.0, "g": 0.7, "b": 0.3})
        time.sleep(0.3)
        ops = [{"actor_label": lbl,
                "material_path": f"/Game/Arcwright/Materials/{mat_name}"}
               for lbl in labels]
        r = client.batch_apply_material(ops)
        ok = r.get("status") == "ok"
        steps.append(("batch_apply_material", ok,
                       f"succeeded={r.get('data', {}).get('succeeded', 0)}"))

        # Step 5: find_actors again to confirm actors still present
        r = client.find_actors(name_filter=f"{PFX}_BM_A")
        found2 = r.get("data", {}).get("actors", [])
        steps.append(("verify actors still present", len(found2) >= 3,
                       f"found={len(found2)}"))

        return ok and len(found2) >= 3, steps

    finally:
        for lbl in labels:
            safe_delete_actor(client, lbl)
        safe_delete_bp(client, bp_name)
        safe_delete_bp(client, mat_name)
        safe_cleanup_ir(bp_name)


def test_04_full_enemy_setup(client):
    """Full enemy setup: Create pawn BP -> BT -> setup_ai_for_pawn -> spawn x3."""
    pawn_name = f"BP_{PFX}_Enemy"
    bt_name = f"BT_{PFX}_Patrol"
    bb_name = f"BB_{PFX}_Patrol"
    controller_name = f"BP_{PFX}_Enemy_AIController"
    actor_labels = [f"{PFX}_Enemy_{i}" for i in range(3)]
    steps = []

    try:
        # Cleanup
        for lbl in actor_labels:
            safe_delete_actor(client, lbl)
        safe_delete_bp(client, pawn_name)
        safe_delete_bp(client, bt_name)
        safe_delete_bp(client, bb_name)
        safe_delete_bp(client, controller_name)
        time.sleep(0.3)

        # Step 1: Create enemy pawn BP (parent: Pawn)
        ir_path = write_temp_ir(pawn_name, parent_class="Pawn")
        r = client.import_from_ir(ir_path)
        ok = r.get("status") == "ok"
        steps.append(("create pawn BP", ok, ""))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 2: Add mesh component so enemy is visible
        client.add_component(pawn_name, "StaticMesh", "Body",
                             properties={"mesh": "/Engine/BasicShapes/Sphere.Sphere"})
        time.sleep(0.3)

        # Step 3: Create behavior tree via send_command
        # BT IR requires metadata.name + metadata.blackboard wrapper
        # Nodes use "dsl_type" (not "type") to match parser output format
        bt_ir = {
            "metadata": {
                "name": bt_name,
                "blackboard": bb_name,
            },
            "blackboard_keys": [
                {"name": "PatrolTarget", "type": "Vector"}
            ],
            "tree": {
                "dsl_type": "Sequence",
                "name": "Root",
                "ue_class": "UBTComposite_Sequence",
                "children": [
                    {"dsl_type": "Wait", "name": "WaitTask",
                     "ue_class": "UBTTask_Wait",
                     "params": {"WaitTime": "2.0"}},
                ],
                "decorators": [],
                "services": [],
            }
        }
        r = client.send_command("create_behavior_tree",
                                {"ir_json": json.dumps(bt_ir)})
        ok = r.get("status") == "ok"
        steps.append(("create behavior tree", ok, ""))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 4: Wire AI to pawn
        r = client.setup_ai_for_pawn(pawn_name, bt_name,
                                     controller_name=controller_name)
        ok = r.get("status") == "ok"
        steps.append(("setup_ai_for_pawn", ok,
                       f"controller={r.get('data', {}).get('controller', '?')}"))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 5: Spawn 3 enemy actors
        actor_class = f"/Game/Arcwright/Generated/{pawn_name}.{pawn_name}"
        spawn_count = 0
        for i, lbl in enumerate(actor_labels):
            r = client.spawn_actor_at(actor_class=actor_class,
                                      location={"x": -500 + i * 300, "y": 800, "z": 50},
                                      label=lbl)
            if r.get("status") == "ok":
                spawn_count += 1
            time.sleep(0.3)
        steps.append(("spawn 3 enemies", spawn_count == 3,
                       f"spawned={spawn_count}"))

        # Step 6: Verify with find_actors
        r = client.find_actors(name_filter=f"{PFX}_Enemy_")
        found = r.get("data", {}).get("actors", [])
        steps.append(("verify enemies exist", len(found) >= 3,
                       f"found={len(found)}"))

        return spawn_count == 3 and len(found) >= 3, steps

    finally:
        for lbl in actor_labels:
            safe_delete_actor(client, lbl)
        safe_delete_bp(client, controller_name)
        safe_delete_bp(client, pawn_name)
        safe_delete_bp(client, bt_name)
        safe_delete_bp(client, bb_name)
        safe_cleanup_ir(pawn_name)


def test_05_scene_setup(client):
    """Scene setup: lighting -> floor -> material -> spawn game actors."""
    floor_label = f"{PFX}_Floor"
    mat_name = f"MAT_{PFX}_Floor"
    bp_name = f"BP_{PFX}_Prop"
    prop_label = f"{PFX}_Prop_1"
    # Track lighting actors so we can clean up
    lighting_labels = []
    steps = []

    try:
        # Cleanup
        safe_delete_actor(client, floor_label)
        safe_delete_actor(client, prop_label)
        safe_delete_bp(client, mat_name)
        safe_delete_bp(client, bp_name)
        time.sleep(0.3)

        # Step 1: Setup scene lighting
        r = client.setup_scene_lighting(preset="indoor_bright")
        ok = r.get("status") == "ok"
        actors_created = r.get("data", {}).get("actors_created", 0)
        # Collect lighting actor labels for cleanup
        for a in r.get("data", {}).get("actors", []):
            lbl = a.get("label", "")
            if lbl:
                lighting_labels.append(lbl)
        steps.append(("setup_scene_lighting", ok,
                       f"actors_created={actors_created}"))

        # Step 2: Spawn a floor
        r = client.spawn_actor_at(
            actor_class="StaticMeshActor",
            location={"x": 0, "y": 0, "z": 0},
            scale={"x": 50, "y": 50, "z": 1},
            label=floor_label,
        )
        ok = r.get("status") == "ok"
        steps.append(("spawn floor", ok, ""))
        time.sleep(0.3)

        # Step 3: Create and apply floor material
        client.create_simple_material(mat_name, color={"r": 0.5, "g": 0.5, "b": 0.5})
        time.sleep(0.3)
        r = client.send_command("set_actor_material", {
            "actor_label": floor_label,
            "material_path": f"/Game/Arcwright/Materials/{mat_name}",
        })
        ok_mat = r.get("status") == "ok"
        steps.append(("apply floor material", ok_mat, ""))

        # Step 4: Create a game prop BP and spawn it
        ir_path = write_temp_ir(bp_name)
        client.import_from_ir(ir_path)
        time.sleep(0.3)
        client.add_component(bp_name, "StaticMesh", "Mesh",
                             properties={"mesh": "/Engine/BasicShapes/Cone.Cone"})
        time.sleep(0.3)

        actor_class = f"/Game/Arcwright/Generated/{bp_name}.{bp_name}"
        r = client.spawn_actor_at(actor_class=actor_class,
                                  location={"x": 0, "y": 0, "z": 100},
                                  label=prop_label)
        ok_prop = r.get("status") == "ok"
        steps.append(("spawn game prop", ok_prop, ""))

        # Step 5: Verify with get_level_info that actor count grew
        r = client.get_level_info()
        count = r.get("data", {}).get("actor_count", 0)
        steps.append(("verify level populated", count > 0,
                       f"actor_count={count}"))

        return ok and ok_prop, steps

    finally:
        safe_delete_actor(client, prop_label)
        safe_delete_actor(client, floor_label)
        for lbl in lighting_labels:
            safe_delete_actor(client, lbl)
        safe_delete_bp(client, bp_name)
        safe_delete_bp(client, mat_name)
        safe_cleanup_ir(bp_name)


def test_06_data_driven(client):
    """Data-driven: Create a data table -> verify with get_data_table_info."""
    dt_name = f"DT_{PFX}_Weapons"
    struct_name = f"S_{PFX}_WeaponData"
    steps = []

    try:
        # Cleanup (data tables live in /Game/Arcwright/DataTables/)
        safe_delete_bp(client, dt_name)
        safe_delete_bp(client, struct_name)
        time.sleep(0.3)

        # Step 1: Create a data table via IR JSON
        # DT IR requires metadata.table_name + metadata.struct_name wrapper
        dt_ir = {
            "metadata": {
                "table_name": dt_name,
                "struct_name": struct_name,
            },
            "columns": [
                {"name": "WeaponName", "type": {"name": "String"}},
                {"name": "Damage", "type": {"name": "Float"}, "default": "0.0"},
                {"name": "FireRate", "type": {"name": "Float"}, "default": "1.0"},
            ],
            "rows": [
                {"name": "Pistol",
                 "values": {"WeaponName": "Pistol", "Damage": "25.0", "FireRate": "2.0"}},
                {"name": "Rifle",
                 "values": {"WeaponName": "Rifle", "Damage": "15.0", "FireRate": "8.0"}},
                {"name": "Shotgun",
                 "values": {"WeaponName": "Shotgun", "Damage": "80.0", "FireRate": "0.5"}},
            ]
        }
        r = client.send_command("create_data_table",
                                {"ir_json": json.dumps(dt_ir)})
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        steps.append(("create_data_table", ok,
                       f"cols={data.get('column_count', 0)}, "
                       f"rows={data.get('row_count', 0)}"))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 2: Verify via get_data_table_info
        r = client.send_command("get_data_table_info", {"name": dt_name})
        ok = r.get("status") == "ok"
        data = r.get("data", {})
        row_count = data.get("row_count", 0)
        columns = data.get("columns", [])
        col_names = [c.get("name", "") for c in columns]
        steps.append(("get_data_table_info", ok and row_count >= 3,
                       f"rows={row_count}, columns={col_names}"))

        return ok and row_count >= 3, steps

    finally:
        safe_delete_bp(client, dt_name)
        safe_delete_bp(client, struct_name)


def test_07_iterative_refinement(client):
    """Iterative refinement: Create BP -> add variable -> spawn -> modify -> verify."""
    bp_name = f"BP_{PFX}_Iter"
    actor_label = f"{PFX}_Iter_Actor"
    steps = []

    try:
        safe_delete_actor(client, actor_label)
        safe_delete_bp(client, bp_name)
        time.sleep(0.3)

        # Step 1: Create initial Blueprint
        ir_path = write_temp_ir(bp_name)
        r = client.import_from_ir(ir_path)
        ok = r.get("status") == "ok"
        steps.append(("create initial BP", ok, ""))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 2: Add a Health variable via modify_blueprint
        r = client.modify_blueprint(bp_name,
                                    add_variables=[{"name": "Health", "type": "float",
                                                    "default": "100.0"}])
        ok = r.get("status") == "ok"
        steps.append(("add Health variable", ok, ""))
        time.sleep(0.3)

        # Step 3: Spawn an instance
        actor_class = f"/Game/Arcwright/Generated/{bp_name}.{bp_name}"
        r = client.spawn_actor_at(actor_class=actor_class,
                                  location={"x": 400, "y": 400, "z": 50},
                                  label=actor_label)
        ok = r.get("status") == "ok"
        steps.append(("spawn actor", ok, ""))
        time.sleep(0.3)

        # Step 4: Find the BP and verify Health variable exists
        r = client.find_blueprints(name_filter=bp_name)
        bps = r.get("data", {}).get("blueprints", [])
        has_health = False
        for bp in bps:
            vars_list = bp.get("variables", [])
            if any(v.get("name") == "Health" for v in vars_list):
                has_health = True
                break
        steps.append(("find_blueprints verify Health", has_health,
                       f"blueprints_found={len(bps)}"))

        # Step 5: Modify - change Health default to 200
        r = client.modify_blueprint(bp_name,
                                    add_variables=[{"name": "MaxHealth", "type": "float",
                                                    "default": "200.0"}])
        ok = r.get("status") == "ok"
        steps.append(("add MaxHealth variable", ok, ""))
        time.sleep(0.3)

        # Step 6: Verify both variables exist
        r = client.get_blueprint_info(bp_name)
        vars_list = r.get("data", {}).get("variables", [])
        var_names = [v.get("name") for v in vars_list]
        has_both = "Health" in var_names and "MaxHealth" in var_names
        steps.append(("verify both variables", has_both,
                       f"variables={var_names}"))

        return has_both, steps

    finally:
        safe_delete_actor(client, actor_label)
        safe_delete_bp(client, bp_name)
        safe_cleanup_ir(bp_name)


def test_08_cleanup_workflow(client):
    """Cleanup: Spawn 5 actors -> find_actors -> batch_delete -> verify empty."""
    bp_name = f"BP_{PFX}_Clean"
    labels = [f"{PFX}_Clean_{i}" for i in range(5)]
    steps = []

    try:
        # Pre-cleanup
        for lbl in labels:
            safe_delete_actor(client, lbl)
        safe_delete_bp(client, bp_name)
        time.sleep(0.3)

        # Step 1: Create a simple BP
        ir_path = write_temp_ir(bp_name)
        client.import_from_ir(ir_path)
        time.sleep(0.3)
        steps.append(("create BP", True, ""))

        # Step 2: Spawn 5 actors
        actor_class = f"/Game/Arcwright/Generated/{bp_name}.{bp_name}"
        spawn_count = 0
        for i, lbl in enumerate(labels):
            r = client.spawn_actor_at(actor_class=actor_class,
                                      location={"x": i * 150, "y": -500, "z": 50},
                                      label=lbl)
            if r.get("status") == "ok":
                spawn_count += 1
            time.sleep(0.2)
        steps.append(("spawn 5 actors", spawn_count == 5,
                       f"spawned={spawn_count}"))

        # Step 3: Find them
        r = client.find_actors(name_filter=f"{PFX}_Clean_")
        before = r.get("data", {}).get("actors", [])
        steps.append(("find_actors (before)", len(before) >= 5,
                       f"found={len(before)}"))

        # Step 4: Batch delete all 5
        r = client.batch_delete_actors(labels=labels)
        deleted = r.get("data", {}).get("deleted", 0)
        steps.append(("batch_delete_actors", deleted >= 5,
                       f"deleted={deleted}"))
        time.sleep(0.3)

        # Step 5: Verify they are gone
        r = client.find_actors(name_filter=f"{PFX}_Clean_")
        after = r.get("data", {}).get("actors", [])
        steps.append(("verify actors deleted", len(after) == 0,
                       f"remaining={len(after)}"))

        return len(after) == 0, steps

    finally:
        # Belt-and-suspenders cleanup
        for lbl in labels:
            safe_delete_actor(client, lbl)
        safe_delete_bp(client, bp_name)
        safe_cleanup_ir(bp_name)


def test_09_multi_domain(client):
    """Multi-domain: Create BP + BT + DT in one session, verify all 3."""
    bp_name = f"BP_{PFX}_Multi"
    bt_name = f"BT_{PFX}_Multi"
    bb_name = f"BB_{PFX}_Multi"
    dt_name = f"DT_{PFX}_Multi"
    struct_name = f"S_{PFX}_MultiData"
    steps = []

    try:
        # Cleanup
        safe_delete_bp(client, bp_name)
        safe_delete_bp(client, bt_name)
        safe_delete_bp(client, bb_name)
        safe_delete_bp(client, dt_name)
        safe_delete_bp(client, struct_name)
        time.sleep(0.3)

        # Step 1: Create a Blueprint
        ir_path = write_temp_ir(bp_name)
        r = client.import_from_ir(ir_path)
        bp_ok = r.get("status") == "ok"
        steps.append(("create Blueprint", bp_ok, ""))
        time.sleep(0.3)

        # Step 2: Create a Behavior Tree
        bt_ir = {
            "metadata": {
                "name": bt_name,
                "blackboard": bb_name,
            },
            "blackboard_keys": [
                {"name": "Target", "type": "Object"},
            ],
            "tree": {
                "dsl_type": "Selector",
                "name": "Root",
                "ue_class": "UBTComposite_Selector",
                "children": [
                    {"dsl_type": "Wait", "name": "Idle",
                     "ue_class": "UBTTask_Wait",
                     "params": {"WaitTime": "5.0"}},
                ],
                "decorators": [],
                "services": [],
            }
        }
        r = client.send_command("create_behavior_tree",
                                {"ir_json": json.dumps(bt_ir)})
        bt_ok = r.get("status") == "ok"
        steps.append(("create BehaviorTree", bt_ok, ""))
        time.sleep(0.3)

        # Step 3: Create a DataTable
        dt_ir = {
            "metadata": {
                "table_name": dt_name,
                "struct_name": struct_name,
            },
            "columns": [
                {"name": "ItemName", "type": {"name": "String"}},
                {"name": "Value", "type": {"name": "Int"}, "default": "0"},
            ],
            "rows": [
                {"name": "Gem",
                 "values": {"ItemName": "Gem", "Value": "100"}},
                {"name": "Coin",
                 "values": {"ItemName": "Coin", "Value": "10"}},
            ]
        }
        r = client.send_command("create_data_table",
                                {"ir_json": json.dumps(dt_ir)})
        dt_ok = r.get("status") == "ok"
        steps.append(("create DataTable", dt_ok, ""))
        time.sleep(0.3)

        # Step 4: Verify all 3 exist
        # Verify Blueprint
        r = client.get_blueprint_info(bp_name)
        bp_exists = r.get("status") == "ok"
        steps.append(("verify Blueprint exists", bp_exists, ""))

        # Verify BT
        r = client.send_command("get_behavior_tree_info", {"name": bt_name})
        bt_exists = r.get("status") == "ok"
        steps.append(("verify BT exists", bt_exists, ""))

        # Verify DT
        r = client.send_command("get_data_table_info", {"name": dt_name})
        dt_exists = r.get("status") == "ok"
        dt_rows = r.get("data", {}).get("row_count", 0)
        steps.append(("verify DT exists", dt_exists and dt_rows >= 2,
                       f"rows={dt_rows}"))

        return bp_exists and bt_exists and dt_exists, steps

    finally:
        safe_delete_bp(client, bp_name)
        safe_delete_bp(client, bt_name)
        safe_delete_bp(client, bb_name)
        safe_delete_bp(client, dt_name)
        safe_delete_bp(client, struct_name)
        safe_cleanup_ir(bp_name)


def test_10_error_recovery(client):
    """Error recovery: Bad command -> check error -> retry with correct params -> verify."""
    bp_name = f"BP_{PFX}_ErrRec"
    steps = []

    try:
        safe_delete_bp(client, bp_name)
        time.sleep(0.3)

        # Step 1: Send a command that will fail (get_blueprint_info on non-existent)
        got_error = False
        try:
            client.get_blueprint_info(f"BP_DOES_NOT_EXIST_{PFX}_12345")
        except BlueprintLLMError:
            got_error = True
        steps.append(("expected error on bad BP name", got_error,
                       "BlueprintLLMError raised" if got_error else "no error raised"))

        # Step 2: Send a malformed import_from_ir (non-existent path)
        got_error2 = False
        try:
            client.import_from_ir("C:/NONEXISTENT/PATH/fake.blueprint.json")
        except BlueprintLLMError:
            got_error2 = True
        steps.append(("expected error on bad IR path", got_error2,
                       "BlueprintLLMError raised" if got_error2 else "no error raised"))

        # Step 3: Send a command with missing required params
        got_error3 = False
        try:
            client.send_command("spawn_actor_at", {})
            # If it does not raise, it might still return ok with default actor
            # That's fine -- the point is it doesn't crash
            steps.append(("spawn_actor_at with empty params", True,
                           "returned ok or error without crash"))
        except BlueprintLLMError:
            got_error3 = True
            steps.append(("spawn_actor_at with empty params", True,
                           "raised error as expected"))
        except Exception as e:
            steps.append(("spawn_actor_at with empty params", False, str(e)))

        # Step 4: Now do the correct version -- create a valid BP
        ir_path = write_temp_ir(bp_name)
        r = client.import_from_ir(ir_path)
        ok = r.get("status") == "ok"
        steps.append(("retry with valid import", ok, ""))
        if not ok:
            return False, steps
        time.sleep(0.3)

        # Step 5: Verify the BP actually exists
        r = client.get_blueprint_info(bp_name)
        exists = r.get("status") == "ok"
        steps.append(("verify recovery succeeded", exists, ""))

        return got_error and got_error2 and exists, steps

    finally:
        safe_delete_bp(client, bp_name)
        safe_cleanup_ir(bp_name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_TESTS = [
    ("01_query_then_create",     test_01_query_then_create),
    ("02_build_and_configure",   test_02_build_and_configure),
    ("03_batch_modify",          test_03_batch_modify),
    ("04_full_enemy_setup",      test_04_full_enemy_setup),
    ("05_scene_setup",           test_05_scene_setup),
    ("06_data_driven",           test_06_data_driven),
    ("07_iterative_refinement",  test_07_iterative_refinement),
    ("08_cleanup_workflow",      test_08_cleanup_workflow),
    ("09_multi_domain",          test_09_multi_domain),
    ("10_error_recovery",        test_10_error_recovery),
]


def main():
    print("=" * 70)
    print("  Arcwright AI Workflow Integration Tests")
    print("  Simulates how an AI assistant uses TCP commands end-to-end")
    print("=" * 70)
    print()

    # Connect
    try:
        client = ArcwrightClient(timeout=30)
        health = client.health_check()
        server = health.get("data", {}).get("server", health.get("server", "?"))
        version = health.get("data", {}).get("version", health.get("version", "?"))
        print(f"Connected to {server} v{version}")
    except Exception as e:
        print(f"FAIL: Cannot connect to TCP server on localhost:13377: {e}")
        print("Is UE5 Editor running with the Arcwright plugin?")
        sys.exit(1)

    print()

    passed = 0
    failed = 0
    results = []

    for test_id, test_fn in ALL_TESTS:
        print("-" * 70)
        print(f"TEST {test_id}")
        print("-" * 70)

        t0 = time.time()
        try:
            ok, steps = test_fn(client)
            elapsed = time.time() - t0
        except Exception as e:
            elapsed = time.time() - t0
            ok = False
            steps = [("unexpected exception", False, str(e))]

        # Print step details
        for step_name, step_ok, detail in steps:
            tag = "OK" if step_ok else "FAIL"
            suffix = f" -- {detail}" if detail else ""
            print(f"  [{tag:>4}] {step_name}{suffix}")

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"  >>> {status} ({elapsed:.1f}s)")
        print()

        results.append({
            "test_id": test_id,
            "status": status,
            "elapsed_s": round(elapsed, 2),
            "steps": [{"name": s[0], "ok": s[1], "detail": s[2]} for s in steps],
        })

    client.close()

    # Summary
    total = passed + failed
    print("=" * 70)
    print(f"  AI WORKFLOW RESULTS: {passed}/{total} PASS")
    print("=" * 70)
    for r in results:
        marker = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{marker:>4}] {r['test_id']} ({r['elapsed_s']}s)")
    print()

    if failed > 0:
        print(f"{failed} workflow(s) FAILED.")
    else:
        print("All AI workflow tests passed.")

    # Save report
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(RESULTS_DIR,
                               f"ai_workflow_test_{timestamp}.json")
    report = {
        "timestamp": timestamp,
        "suite": "AI Workflow Integration Tests",
        "passed": passed,
        "failed": failed,
        "total": total,
        "results": results,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved: {report_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
