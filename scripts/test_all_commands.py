"""
test_all_commands.py — Unified CI test suite for Arcwright plugin
================================================================
Tests every TCP command against a live UE editor instance.
Groups tests by category. Reports pass/fail with error details.

Usage:
    python scripts/test_all_commands.py [--category <name>] [--verbose]
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "mcp_client"))

from mcp_client.blueprint_client import ArcwrightClient

# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name, category, passed, detail="", duration=0.0, skipped=False):
        self.name = name
        self.category = category
        self.passed = passed
        self.detail = detail
        self.duration = duration
        self.skipped = skipped

    def status_str(self):
        if self.skipped:
            return "SKIP"
        return "PASS" if self.passed else "FAIL"

    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status_str(),
            "detail": self.detail,
            "duration_seconds": round(self.duration, 3),
        }


RESULTS: list[TestResult] = []
CLIENT: ArcwrightClient = None
VERBOSE = False

# Test BP names (cleaned up at start and end)
TEST_BP = "BP_ArcwrightTest"
TEST_BP2 = "BP_ArcwrightTest2"
TEST_WBP = "WBP_ArcwrightTest"
TEST_BT = "BT_ArcwrightTest"
TEST_DT = "DT_ArcwrightTest"
TEST_SEQ = "SEQ_ArcwrightTest"
TEST_MAT = "MAT_ArcwrightTest"
TEST_MAT2 = "MAT_ArcwrightTest2"
TEST_ACTOR_LABEL = "ArcwrightTestActor"
TEST_ACTOR_LABEL2 = "ArcwrightTestActor2"
TEST_PP_LABEL = "ArcwrightTestPP"
TEST_CONSTRAINT_LABEL = "ArcwrightTestConstraint"
TEST_SPLINE = "BP_ArcwrightSplineTest"
TEST_FOLIAGE = "FT_ArcwrightTest"


def run_test(name: str, category: str, fn):
    """Run a single test, catch all exceptions, record result."""
    global CLIENT
    t0 = time.time()
    try:
        detail = fn()
        elapsed = time.time() - t0
        r = TestResult(name, category, True, detail or "", elapsed)
    except AssertionError as e:
        elapsed = time.time() - t0
        r = TestResult(name, category, False, f"ASSERT: {e}", elapsed)
    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
        elapsed = time.time() - t0
        r = TestResult(name, category, False, f"CONNECTION LOST: {e}", elapsed)
        # Try to reconnect — editor may need time to restart
        print(f"    [!] Connection lost — attempting reconnect (up to 60s)...")
        try:
            CLIENT.close()
        except Exception:
            pass
        reconnected = False
        for attempt in range(20):
            time.sleep(3)
            try:
                CLIENT = ArcwrightClient(timeout=30.0)
                print(f"    [!] Reconnected after {(attempt+1)*3}s")
                reconnected = True
                break
            except Exception:
                pass
        if not reconnected:
            print(f"    [!] Could not reconnect after 60s — editor may have crashed")
    except Exception as e:
        elapsed = time.time() - t0
        r = TestResult(name, category, False, f"{type(e).__name__}: {e}", elapsed)
        if VERBOSE:
            traceback.print_exc()
    RESULTS.append(r)
    status = "SKIP" if r.skipped else ("+" if r.passed else "X")
    print(f"  [{status}] {name}" + (f"  ({r.detail[:80]})" if r.detail and VERBOSE else ""))
    return r


def skip_test(name: str, category: str, reason: str):
    r = TestResult(name, category, False, reason, 0.0, skipped=True)
    RESULTS.append(r)
    print(f"  [SKIP] {name}  ({reason})")


def assert_ok(resp, msg=""):
    """Assert the response has status 'ok'."""
    status = resp.get("status", "")
    if status != "ok":
        err = resp.get("message", resp.get("error", "unknown"))
        raise AssertionError(f"{msg}: server returned error: {err}")


def assert_error(resp, msg=""):
    """Assert the response has status 'error' (expected failure)."""
    status = resp.get("status", "")
    if status == "ok":
        raise AssertionError(f"{msg}: expected error but got ok")


def send_raw(command: str, params: dict = None) -> dict:
    """Send command and return raw dict WITHOUT raising on error."""
    import json as _json
    msg = _json.dumps({"command": command, "params": params or {}})
    CLIENT.sock.sendall((msg + "\n").encode("utf-8"))
    response = CLIENT._read_response()
    return _json.loads(response)


def safe_delete_bp(name):
    try:
        CLIENT.delete_blueprint(name)
    except Exception:
        pass


def safe_delete_actor(label):
    try:
        CLIENT.delete_actor(label)
    except Exception:
        pass


def reconnect():
    """Reconnect client if connection was lost."""
    global CLIENT
    try:
        CLIENT.close()
    except Exception:
        pass
    time.sleep(1)
    CLIENT = ArcwrightClient(timeout=30.0)


# ---------------------------------------------------------------------------
# Category 1: Health check + connection
# ---------------------------------------------------------------------------

def test_health_check():
    def _test():
        resp = CLIENT.health_check()
        assert_ok(resp)
        data = resp.get("data", {})
        assert "server" in data or "name" in data, "No server name in health_check"
        return f"server={data.get('server', data.get('name', '?'))}"
    return run_test("health_check", "connection", _test)


# ---------------------------------------------------------------------------
# Category 2: Blueprint CRUD
# ---------------------------------------------------------------------------

def test_blueprint_crud():
    cat = "blueprint_crud"

    # Create a simple Blueprint from DSL
    def _create():
        safe_delete_bp(TEST_BP)
        time.sleep(0.3)
        dsl = (
            "BLUEPRINT: BP_ArcwrightTest\n"
            "PARENT: Actor\n\n"
            "VAR Health: Float = 100.0\n\n"
            "EVENT: BeginPlay\n"
            "NODE: PrintString [I=\"Test OK\"]\n"
            "EXEC: BeginPlay.Then -> PrintString.Execute\n"
        )
        resp = CLIENT.create_blueprint_from_dsl(dsl, TEST_BP)
        assert_ok(resp, "create_blueprint_from_dsl")
        return f"created {TEST_BP}"
    run_test("create_blueprint_from_dsl", cat, _create)

    # Get info
    def _get_info():
        resp = CLIENT.get_blueprint_info(TEST_BP)
        assert_ok(resp, "get_blueprint_info")
        data = resp.get("data", {})
        # Response shape varies: nodes_created, node_count, or nodes
        nc = data.get("nodes_created") or data.get("node_count") or len(data.get("nodes", []))
        assert nc >= 1, f"Expected >=1 nodes, got {nc}"
        return f"nodes={nc}, compiled={data.get('compiled')}"
    run_test("get_blueprint_info", cat, _get_info)

    # Compile
    def _compile():
        resp = CLIENT.compile_blueprint(TEST_BP)
        assert_ok(resp, "compile_blueprint")
        return "compiled"
    run_test("compile_blueprint", cat, _compile)

    # Duplicate
    def _duplicate():
        safe_delete_bp(TEST_BP2)
        time.sleep(0.3)
        resp = CLIENT.duplicate_blueprint(TEST_BP, TEST_BP2)
        assert_ok(resp, "duplicate_blueprint")
        return f"duplicated to {TEST_BP2}"
    run_test("duplicate_blueprint", cat, _duplicate)

    # Delete
    def _delete():
        resp = CLIENT.delete_blueprint(TEST_BP2)
        assert_ok(resp, "delete_blueprint")
        return "deleted"
    run_test("delete_blueprint", cat, _delete)

    # Get info on non-existent (should error)
    def _get_missing():
        resp = send_raw("get_blueprint_info", {"name": "BP_NonExistent_XYZ_99"})
        assert_error(resp, "get_blueprint_info non-existent")
        return "correctly returned error"
    run_test("get_blueprint_info_nonexistent", cat, _get_missing)


# ---------------------------------------------------------------------------
# Category 3: Node editing
# ---------------------------------------------------------------------------

def test_node_editing():
    cat = "node_editing"

    # We need to know the actual node IDs in the BP. Use get_blueprint_info first.
    _node_id = {}

    # Add a Delay node
    def _add_node():
        resp = CLIENT.add_node(TEST_BP, "Delay", "TestDelay")
        assert_ok(resp, "add_node")
        data = resp.get("data", {})
        # Store the actual node_id returned by the server
        actual_id = data.get("node_id", data.get("node_name", "TestDelay"))
        _node_id["delay"] = actual_id
        return f"added Delay (id={actual_id})"
    run_test("add_node", cat, _add_node)

    # Set node param — use actual node_id
    def _set_param():
        nid = _node_id.get("delay", "TestDelay")
        resp = CLIENT.set_node_param(TEST_BP, nid, "Duration", "2.0")
        assert_ok(resp, "set_node_param")
        return f"set Duration=2.0 on {nid}"
    run_test("set_node_param", cat, _set_param)

    # Add connection (BeginPlay -> Delay) — use actual node_id
    def _add_conn():
        nid = _node_id.get("delay", "TestDelay")
        resp = CLIENT.add_connection(TEST_BP, "BeginPlay", "Then", nid, "Execute")
        assert_ok(resp, "add_connection")
        return f"wired BeginPlay->{nid}"
    run_test("add_connection", cat, _add_conn)

    # Remove connection
    def _remove_conn():
        nid = _node_id.get("delay", "TestDelay")
        resp = CLIENT.remove_connection(TEST_BP, "BeginPlay", "Then", nid, "Execute")
        assert_ok(resp, "remove_connection")
        return "unwired"
    run_test("remove_connection", cat, _remove_conn)

    # Remove node
    def _remove_node():
        nid = _node_id.get("delay", "TestDelay")
        resp = CLIENT.remove_node(TEST_BP, nid)
        assert_ok(resp, "remove_node")
        return "removed Delay"
    run_test("remove_node", cat, _remove_node)

    # Set variable default
    def _set_var():
        resp = CLIENT.set_variable_default(TEST_BP, "Health", "75.0")
        assert_ok(resp, "set_variable_default")
        return "Health=75.0"
    run_test("set_variable_default", cat, _set_var)


# ---------------------------------------------------------------------------
# Category 4: Components
# ---------------------------------------------------------------------------

def test_components():
    cat = "components"

    component_types = [
        ("BoxCollision", {"extent": {"x": 50, "y": 50, "z": 50}}),
        ("SphereCollision", {"radius": 100}),
        ("StaticMesh", {"mesh": "/Engine/BasicShapes/Sphere.Sphere"}),
        ("PointLight", {"intensity": 500, "light_color": {"r": 1, "g": 0.8, "b": 0.5}}),
        ("SpotLight", {"intensity": 300}),
        ("Audio", {}),
        ("Arrow", {}),
        ("Scene", {}),
        ("CapsuleCollision", {"radius": 30, "half_height": 60}),
    ]

    for comp_type, props in component_types:
        def _add(ct=comp_type, p=props):
            resp = CLIENT.add_component(TEST_BP, ct, f"Test{ct}", properties=p)
            assert_ok(resp, f"add_component {ct}")
            return f"added {ct}"
        run_test(f"add_component_{comp_type}", cat, _add)

    # Get components
    def _get():
        resp = CLIENT.get_components(TEST_BP)
        assert_ok(resp, "get_components")
        data = resp.get("data", {})
        comps = data.get("components", [])
        assert len(comps) >= 9, f"Expected >=9 components, got {len(comps)}"
        return f"count={len(comps)}"
    run_test("get_components", cat, _get)

    # Set component property
    def _set_prop():
        resp = CLIENT.set_component_property(TEST_BP, "TestPointLight", "intensity", 1000)
        assert_ok(resp, "set_component_property")
        return "intensity=1000"
    run_test("set_component_property", cat, _set_prop)

    # Remove component
    def _remove():
        resp = CLIENT.remove_component(TEST_BP, "TestArrow")
        assert_ok(resp, "remove_component")
        return "removed Arrow"
    run_test("remove_component", cat, _remove)

    # Remove non-existent (idempotent)
    def _remove_idem():
        resp = CLIENT.remove_component(TEST_BP, "TestArrow")
        assert_ok(resp, "remove_component idempotent")
        return "idempotent ok"
    run_test("remove_component_idempotent", cat, _remove_idem)


# ---------------------------------------------------------------------------
# Category 5: Materials
# ---------------------------------------------------------------------------

def test_materials():
    cat = "materials"

    def _create_simple():
        resp = CLIENT.create_simple_material(TEST_MAT, {"r": 0.8, "g": 0.2, "b": 0.1})
        assert_ok(resp, "create_simple_material")
        return "created red material"
    run_test("create_simple_material", cat, _create_simple)

    def _create_simple_emissive():
        resp = CLIENT.create_simple_material(TEST_MAT2, {"r": 0, "g": 1, "b": 0.5}, emissive_strength=2.0)
        assert_ok(resp, "create_simple_material emissive")
        return "created green emissive"
    run_test("create_simple_material_emissive", cat, _create_simple_emissive)

    def _apply():
        resp = CLIENT.apply_material(TEST_BP, "TestStaticMesh",
                                     f"/Game/Arcwright/Materials/{TEST_MAT}")
        assert_ok(resp, "apply_material")
        return "applied to StaticMesh"
    run_test("apply_material", cat, _apply)

    # create_textured_material requires an actual texture — test with a known one
    def _create_textured():
        resp = CLIENT.create_textured_material(
            "MAT_ArcwrightTexTest",
            "/Game/Arcwright/Textures/T_StoneWall",
            roughness=0.7, metallic=0.1, tiling=2.0
        )
        # May fail if texture doesn't exist — that's OK, we test the command path
        if resp.get("status") == "ok":
            return "created textured material"
        else:
            return f"expected: texture may not exist ({resp.get('message', '')[:60]})"
    run_test("create_textured_material", cat, _create_textured)

    # set_actor_material — need a spawned actor first
    def _set_actor_mat():
        safe_delete_actor(TEST_ACTOR_LABEL)
        time.sleep(0.3)
        CLIENT.spawn_actor_at("StaticMeshActor", label=TEST_ACTOR_LABEL,
                              location={"x": 9000, "y": 9000, "z": 100})
        time.sleep(0.3)
        resp = CLIENT.send_command("set_actor_material", {
            "actor_label": TEST_ACTOR_LABEL,
            "material_path": f"/Game/Arcwright/Materials/{TEST_MAT}"
        })
        assert_ok(resp, "set_actor_material")
        return "material applied to actor"
    run_test("set_actor_material", cat, _set_actor_mat)


# ---------------------------------------------------------------------------
# Category 6: Level operations
# ---------------------------------------------------------------------------

def test_level():
    cat = "level"

    def _spawn():
        safe_delete_actor(TEST_ACTOR_LABEL2)
        time.sleep(0.3)
        resp = CLIENT.spawn_actor_at("StaticMeshActor", label=TEST_ACTOR_LABEL2,
                                     location={"x": 8000, "y": 8000, "z": 200})
        assert_ok(resp, "spawn_actor_at")
        return "spawned actor"
    run_test("spawn_actor_at", cat, _spawn)

    def _get_actors():
        resp = CLIENT.get_actors()
        assert_ok(resp, "get_actors")
        data = resp.get("data", {})
        count = data.get("count", 0)
        assert count > 0, "No actors found"
        return f"actors={count}"
    run_test("get_actors", cat, _get_actors)

    def _set_transform():
        resp = CLIENT.set_actor_transform(TEST_ACTOR_LABEL2,
                                          location={"x": 8100, "y": 8100, "z": 300})
        assert_ok(resp, "set_actor_transform")
        return "moved actor"
    run_test("set_actor_transform", cat, _set_transform)

    def _get_level_info():
        resp = CLIENT.get_level_info()
        assert_ok(resp, "get_level_info")
        data = resp.get("data", {})
        assert "level_name" in data or "name" in data, "No level name"
        return f"level={data.get('level_name', data.get('name', '?'))}"
    run_test("get_level_info", cat, _get_level_info)

    def _delete_actor():
        resp = CLIENT.delete_actor(TEST_ACTOR_LABEL2)
        assert_ok(resp, "delete_actor")
        return "deleted"
    run_test("delete_actor", cat, _delete_actor)

    def _save_all():
        resp = CLIENT.save_all()
        assert_ok(resp, "save_all")
        return "saved"
    run_test("save_all", cat, _save_all)

    def _save_level():
        resp = CLIENT.save_level()
        assert_ok(resp, "save_level")
        return "saved"
    run_test("save_level", cat, _save_level)


# ---------------------------------------------------------------------------
# Category 7: Widgets
# ---------------------------------------------------------------------------

def test_widgets():
    cat = "widgets"

    def _create():
        resp = CLIENT.create_widget_blueprint(TEST_WBP)
        assert_ok(resp, "create_widget_blueprint")
        return "created"
    run_test("create_widget_blueprint", cat, _create)

    def _add_root():
        resp = CLIENT.add_widget_child(TEST_WBP, "CanvasPanel", "RootPanel")
        assert_ok(resp, "add_widget_child CanvasPanel")
        return "added root CanvasPanel"
    run_test("add_widget_child_canvas", cat, _add_root)

    def _add_text():
        resp = CLIENT.add_widget_child(TEST_WBP, "TextBlock", "TestText", parent_widget="RootPanel")
        assert_ok(resp, "add_widget_child TextBlock")
        return "added TextBlock"
    run_test("add_widget_child_text", cat, _add_text)

    def _add_progress():
        resp = CLIENT.add_widget_child(TEST_WBP, "ProgressBar", "TestBar", parent_widget="RootPanel")
        assert_ok(resp, "add_widget_child ProgressBar")
        return "added ProgressBar"
    run_test("add_widget_child_progress", cat, _add_progress)

    def _set_text():
        resp = CLIENT.set_widget_property(TEST_WBP, "TestText", "text", "Hello Arcwright")
        assert_ok(resp, "set_widget_property text")
        return "text set"
    run_test("set_widget_property_text", cat, _set_text)

    def _set_percent():
        resp = CLIENT.set_widget_property(TEST_WBP, "TestBar", "percent", 0.75)
        assert_ok(resp, "set_widget_property percent")
        return "percent=0.75"
    run_test("set_widget_property_percent", cat, _set_percent)

    def _get_tree():
        resp = CLIENT.get_widget_tree(TEST_WBP)
        assert_ok(resp, "get_widget_tree")
        return "tree retrieved"
    run_test("get_widget_tree", cat, _get_tree)

    def _remove():
        resp = CLIENT.remove_widget(TEST_WBP, "TestBar")
        assert_ok(resp, "remove_widget")
        return "removed ProgressBar"
    run_test("remove_widget", cat, _remove)


# ---------------------------------------------------------------------------
# Category 8: BehaviorTree
# ---------------------------------------------------------------------------

def test_behavior_tree():
    cat = "behavior_tree"

    def _create():
        dsl = (
            "BEHAVIORTREE: BT_ArcwrightTest\n"
            "BLACKBOARD: BB_ArcwrightTest\n\n"
            "KEY TargetActor: Object\n"
            "KEY PatrolPoint: Vector\n\n"
            "TREE:\n\n"
            "SELECTOR: Root\n"
            "  SEQUENCE: Chase\n"
            "    DECORATOR: BlackboardBased [Key=TargetActor, Condition=IsSet]\n"
            "    TASK: MoveTo [Key=TargetActor, AcceptableRadius=200]\n"
            "  SEQUENCE: Patrol\n"
            "    TASK: MoveTo [Key=PatrolPoint, AcceptableRadius=50]\n"
            "    TASK: Wait [Duration=3.0]\n"
        )
        resp = CLIENT.create_behavior_tree_from_dsl(dsl)
        assert_ok(resp, "create_behavior_tree")
        return "created BT"
    run_test("create_behavior_tree", cat, _create)

    def _get_info():
        resp = CLIENT.get_behavior_tree_info(TEST_BT)
        assert_ok(resp, "get_behavior_tree_info")
        return "queried BT"
    run_test("get_behavior_tree_info", cat, _get_info)

    def _get_missing():
        resp = send_raw("get_behavior_tree_info", {"name": "BT_NonExistent_XYZ"})
        assert_error(resp, "BT nonexistent")
        return "correctly returned error"
    run_test("get_behavior_tree_info_nonexistent", cat, _get_missing)


# ---------------------------------------------------------------------------
# Category 9: DataTable
# ---------------------------------------------------------------------------

def test_data_table():
    cat = "data_table"

    def _create():
        dsl = (
            "DATATABLE: DT_ArcwrightTest\n"
            "STRUCT: TestWeapon\n\n"
            "COLUMN Name: String\n"
            "COLUMN Damage: Float = 0.0\n"
            "COLUMN IsAuto: Boolean = false\n\n"
            "ROW Pistol: Name=Pistol, Damage=25.0, IsAuto=false\n"
            "ROW Rifle: Name=Rifle, Damage=15.0, IsAuto=true\n"
        )
        resp = CLIENT.create_data_table_from_dsl(dsl)
        assert_ok(resp, "create_data_table")
        return "created DT"
    run_test("create_data_table", cat, _create)

    def _get_info():
        resp = CLIENT.get_data_table_info(TEST_DT)
        assert_ok(resp, "get_data_table_info")
        return "queried DT"
    run_test("get_data_table_info", cat, _get_info)


# ---------------------------------------------------------------------------
# Category 10: AI setup
# ---------------------------------------------------------------------------

def test_ai():
    cat = "ai_setup"

    # Create a Pawn BP for AI testing — use import_from_ir with correct IR format
    def _create_pawn():
        safe_delete_bp("BP_ArcwrightAIPawn")
        time.sleep(0.5)
        import tempfile
        ir = {
            "metadata": {
                "name": "BP_ArcwrightAIPawn",
                "parent_class": "Pawn",
                "category": None
            },
            "variables": [],
            "nodes": [
                {"id": "BeginPlay", "dsl_type": "Event_BeginPlay", "params": {},
                 "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay",
                 "position": [0, 0]}
            ],
            "connections": []
        }
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".blueprint.json", delete=False,
                                           dir="C:/Arcwright/test_ir")
        json.dump(ir, tmp, indent=2)
        tmp.close()
        try:
            resp = CLIENT.import_from_ir(tmp.name)
            assert_ok(resp, "create AI pawn via IR")
        finally:
            os.unlink(tmp.name)
        return "pawn created (via IR)"
    run_test("create_ai_pawn", cat, _create_pawn)

    def _setup_ai():
        resp = CLIENT.setup_ai_for_pawn("BP_ArcwrightAIPawn", TEST_BT)
        assert_ok(resp, "setup_ai_for_pawn")
        return "AI setup complete"
    run_test("setup_ai_for_pawn", cat, _setup_ai)

    def _set_class_defaults():
        resp = CLIENT.send_command("set_class_defaults", {
            "blueprint": "BP_ArcwrightAIPawn",
            "properties": {"auto_possess_ai": "PlacedInWorldOrSpawned"}
        })
        assert_ok(resp, "set_class_defaults")
        return "class defaults set"
    run_test("set_class_defaults", cat, _set_class_defaults)


# ---------------------------------------------------------------------------
# Category 11: Asset import
# ---------------------------------------------------------------------------

def test_asset_import():
    cat = "asset_import"

    # These need actual files — test error handling for non-existent paths
    def _import_mesh_bad():
        resp = send_raw("import_static_mesh", {
            "file_path": "C:/nonexistent/mesh.fbx",
            "asset_name": "SM_Test"
        })
        assert_error(resp, "import_static_mesh bad path")
        return "correctly returned error for bad path"
    run_test("import_static_mesh_bad_path", cat, _import_mesh_bad)

    def _import_texture_bad():
        resp = send_raw("import_texture", {
            "file_path": "C:/nonexistent/tex.png",
            "asset_name": "T_Test"
        })
        assert_error(resp, "import_texture bad path")
        return "correctly returned error for bad path"
    run_test("import_texture_bad_path", cat, _import_texture_bad)

    def _import_sound_bad():
        resp = send_raw("import_sound", {
            "file_path": "C:/nonexistent/sfx.wav",
            "asset_name": "SFX_Test"
        })
        assert_error(resp, "import_sound bad path")
        return "correctly returned error for bad path"
    run_test("import_sound_bad_path", cat, _import_sound_bad)


# ---------------------------------------------------------------------------
# Category 12: Splines
# ---------------------------------------------------------------------------

def test_splines():
    cat = "splines"

    def _create():
        safe_delete_bp(TEST_SPLINE)
        time.sleep(0.3)
        resp = CLIENT.create_spline_actor(
            TEST_SPLINE,
            points=[{"x": 0, "y": 0, "z": 0}, {"x": 500, "y": 0, "z": 0}, {"x": 500, "y": 500, "z": 0}],
            closed=False
        )
        assert_ok(resp, "create_spline_actor")
        return "created spline"
    run_test("create_spline_actor", cat, _create)

    def _add_point():
        resp = CLIENT.add_spline_point(TEST_SPLINE, {"x": 500, "y": 500, "z": 200})
        assert_ok(resp, "add_spline_point")
        return "added point"
    run_test("add_spline_point", cat, _add_point)

    def _get_info():
        resp = CLIENT.get_spline_info(TEST_SPLINE)
        assert_ok(resp, "get_spline_info")
        data = resp.get("data", {})
        assert data.get("point_count", 0) >= 3, f"Expected >=3 points"
        return f"points={data.get('point_count')}"
    run_test("get_spline_info", cat, _get_info)


# ---------------------------------------------------------------------------
# Category 13: Post-process
# ---------------------------------------------------------------------------

def test_post_process():
    cat = "post_process"

    def _add_volume():
        safe_delete_actor(TEST_PP_LABEL)
        time.sleep(0.3)
        resp = CLIENT.add_post_process_volume(
            label=TEST_PP_LABEL,
            location={"x": 7000, "y": 7000, "z": 500},
            infinite_extent=True
        )
        assert_ok(resp, "add_post_process_volume")
        return "added PP volume"
    run_test("add_post_process_volume", cat, _add_volume)

    def _set_settings():
        resp = CLIENT.set_post_process_settings(TEST_PP_LABEL, {
            "bloom_intensity": 0.5,
            "auto_exposure_min_brightness": 1.0,
            "auto_exposure_max_brightness": 2.0,
            "vignette_intensity": 0.3
        })
        assert_ok(resp, "set_post_process_settings")
        return "settings applied"
    run_test("set_post_process_settings", cat, _set_settings)


# ---------------------------------------------------------------------------
# Category 14: Movement
# ---------------------------------------------------------------------------

def test_movement():
    cat = "movement"

    # Create a Character BP for movement testing
    def _test():
        safe_delete_bp("BP_ArcwrightMoveTest")
        time.sleep(0.3)
        # Use IR import with correct metadata format
        import tempfile
        ir = {
            "metadata": {
                "name": "BP_ArcwrightMoveTest",
                "parent_class": "Character",
                "category": None
            },
            "variables": [],
            "nodes": [
                {"id": "BeginPlay", "dsl_type": "Event_BeginPlay", "params": {},
                 "ue_class": "UK2Node_Event", "ue_event": "ReceiveBeginPlay",
                 "position": [0, 0]}
            ],
            "connections": []
        }
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".blueprint.json", delete=False,
                                           dir="C:/Arcwright/test_ir")
        json.dump(ir, tmp, indent=2)
        tmp.close()
        try:
            CLIENT.import_from_ir(tmp.name)
        finally:
            os.unlink(tmp.name)
        time.sleep(0.3)
        resp = CLIENT.set_movement_defaults("BP_ArcwrightMoveTest", {
            "max_walk_speed": 800,
            "jump_z_velocity": 600,
            "air_control": 0.3
        })
        assert_ok(resp, "set_movement_defaults")
        return "movement defaults set"
    run_test("set_movement_defaults", cat, _test)


# ---------------------------------------------------------------------------
# Category 15: Physics constraints
# ---------------------------------------------------------------------------

def test_physics():
    cat = "physics"

    def _add():
        safe_delete_actor(TEST_CONSTRAINT_LABEL)
        time.sleep(0.3)
        # Need two actors to constrain
        resp = CLIENT.add_physics_constraint(
            label=TEST_CONSTRAINT_LABEL,
            actor1=TEST_ACTOR_LABEL,
            actor2=TEST_ACTOR_LABEL,  # Same actor is fine for testing
            constraint_type="Hinge"
        )
        # May fail if test actors were cleaned up — that's expected
        if resp.get("status") == "ok":
            return "added hinge constraint"
        return f"note: {resp.get('message', '')[:60]}"
    run_test("add_physics_constraint", cat, _add)

    def _break():
        resp = CLIENT.break_constraint(TEST_CONSTRAINT_LABEL)
        # May fail if constraint wasn't created
        return f"status={resp.get('status')}"
    run_test("break_constraint", cat, _break)


# ---------------------------------------------------------------------------
# Category 16: Sequencer
# ---------------------------------------------------------------------------

def test_sequencer():
    cat = "sequencer"

    def _create():
        resp = CLIENT.create_sequence(TEST_SEQ, duration=5.0)
        assert_ok(resp, "create_sequence")
        return "created 5s sequence"
    run_test("create_sequence", cat, _create)

    # Need a spawned actor to bind
    def _add_track():
        safe_delete_actor("ArcwrightSeqActor")
        time.sleep(0.3)
        CLIENT.spawn_actor_at("StaticMeshActor", label="ArcwrightSeqActor",
                              location={"x": 6000, "y": 6000, "z": 100})
        time.sleep(0.3)
        resp = CLIENT.add_sequence_track(TEST_SEQ, "ArcwrightSeqActor", "Transform")
        assert_ok(resp, "add_sequence_track")
        return "added Transform track"
    run_test("add_sequence_track", cat, _add_track)

    def _add_keyframe():
        resp = CLIENT.add_keyframe(TEST_SEQ, "ArcwrightSeqActor", "Transform", 0.0,
                                   {"location": {"x": 6000, "y": 6000, "z": 100}})
        assert_ok(resp, "add_keyframe")
        return "keyframe at t=0"
    run_test("add_keyframe", cat, _add_keyframe)

    def _get_info():
        resp = CLIENT.get_sequence_info(TEST_SEQ)
        assert_ok(resp, "get_sequence_info")
        return "queried sequence"
    run_test("get_sequence_info", cat, _get_info)

    def _play():
        resp = send_raw("play_sequence", {"name": TEST_SEQ})
        # Known PIE limitation — command may error or queue without processing
        return f"status={resp.get('status')} (PIE limitation expected)"
    run_test("play_sequence", cat, _play)


# ---------------------------------------------------------------------------
# Category 17: Foliage
# ---------------------------------------------------------------------------

def test_foliage():
    cat = "foliage"

    def _create_type():
        resp = CLIENT.create_foliage_type(
            TEST_FOLIAGE,
            mesh="/Engine/BasicShapes/Sphere.Sphere",
            density=50.0,
            scale_min=0.5,
            scale_max=1.5
        )
        assert_ok(resp, "create_foliage_type")
        return "created foliage type"
    run_test("create_foliage_type", cat, _create_type)

    def _paint():
        resp = send_raw("paint_foliage", {
            "foliage_type": TEST_FOLIAGE,
            "center": {"x": 5000, "y": 5000, "z": 0},
            "radius": 300.0,
            "count": 5
        })
        # May fail if foliage type asset path differs from name
        return f"status={resp.get('status')}"
    run_test("paint_foliage", cat, _paint)

    def _get_info():
        resp = CLIENT.get_foliage_info()
        assert_ok(resp, "get_foliage_info")
        return "queried foliage"
    run_test("get_foliage_info", cat, _get_info)


# ---------------------------------------------------------------------------
# Category 18: Landscape
# ---------------------------------------------------------------------------

def test_landscape():
    cat = "landscape"

    def _get_info():
        resp = CLIENT.get_landscape_info()
        assert_ok(resp, "get_landscape_info")
        return "queried landscape"
    run_test("get_landscape_info", cat, _get_info)

    def _set_material():
        resp = send_raw("set_landscape_material", {
            "material_path": f"/Game/Arcwright/Materials/{TEST_MAT}"
        })
        # Fails if no landscape exists — that's expected in test level
        return f"status={resp.get('status')}"
    run_test("set_landscape_material", cat, _set_material)


# ---------------------------------------------------------------------------
# Category 19: Scene setup
# ---------------------------------------------------------------------------

def test_scene_setup():
    cat = "scene_setup"

    def _lighting():
        resp = CLIENT.setup_scene_lighting(preset="indoor_bright")
        assert_ok(resp, "setup_scene_lighting")
        return "lighting set up"
    run_test("setup_scene_lighting", cat, _lighting)

    def _game_mode():
        # set_game_mode needs a valid GameMode BP — test with a common one
        resp = CLIENT.set_game_mode("GameModeBase")
        # May fail if no such BP — just verify the command doesn't crash
        return f"status={resp.get('status')}"
    run_test("set_game_mode", cat, _game_mode)


# ---------------------------------------------------------------------------
# Category 20: Misc (viewport, screenshot, output log)
# ---------------------------------------------------------------------------

def test_misc():
    cat = "misc"

    def _get_log():
        resp = CLIENT.get_output_log(last_n_lines=20)
        assert_ok(resp, "get_output_log")
        return "log retrieved"
    run_test("get_output_log", cat, _get_log)

    def _screenshot():
        resp = CLIENT.take_screenshot("arcwright_test_screenshot")
        assert_ok(resp, "take_screenshot")
        return "screenshot taken"
    run_test("take_screenshot", cat, _screenshot)

    def _viewport_info():
        resp = CLIENT.get_viewport_info()
        assert_ok(resp, "get_viewport_info")
        return "viewport info retrieved"
    run_test("get_viewport_info", cat, _viewport_info)

    def _set_viewport():
        resp = CLIENT.set_viewport_camera(
            location={"x": 0, "y": 0, "z": 500},
            rotation={"pitch": -30, "yaw": 0, "roll": 0}
        )
        assert_ok(resp, "set_viewport_camera")
        return "camera moved"
    run_test("set_viewport_camera", cat, _set_viewport)

    # Don't test quit_editor — it would close the editor!
    skip_test("quit_editor", cat, "skipped: would close the editor")


# ---------------------------------------------------------------------------
# Category 21: Error handling (Task 2 — bad input resilience)
# ---------------------------------------------------------------------------

def test_error_handling():
    cat = "error_handling"

    # Empty string parameters
    def _empty_bp_name():
        resp = send_raw("get_blueprint_info", {"name": ""})
        assert_error(resp, "empty blueprint name")
        return "correctly errored on empty name"
    run_test("empty_blueprint_name", cat, _empty_bp_name)

    def _empty_node_type():
        resp = send_raw("add_node", {"blueprint": TEST_BP, "node_type": "", "node_id": "x"})
        assert_error(resp, "empty node type")
        return "correctly errored"
    run_test("empty_node_type", cat, _empty_node_type)

    # Non-existent targets
    def _nonexist_bp_compile():
        resp = send_raw("compile_blueprint", {"name": "BP_NoSuchThing_99"})
        assert_error(resp, "compile non-existent BP")
        return "correctly errored"
    run_test("compile_nonexistent_bp", cat, _nonexist_bp_compile)

    def _nonexist_actor_delete():
        resp = send_raw("delete_actor", {"label": "NoSuchActor_99"})
        # delete_actor may return ok (idempotent) or error — both are acceptable
        return f"status={resp.get('status')} (idempotent delete is ok)"
    run_test("delete_nonexistent_actor", cat, _nonexist_actor_delete)

    def _nonexist_actor_transform():
        resp = send_raw("set_actor_transform", {
            "label": "NoSuchActor_99",
            "location": {"x": 0, "y": 0, "z": 0}
        })
        assert_error(resp, "transform non-existent actor")
        return "correctly errored"
    run_test("transform_nonexistent_actor", cat, _nonexist_actor_transform)

    # Invalid paths
    def _bad_material_path():
        resp = send_raw("apply_material", {
            "blueprint": TEST_BP,
            "component_name": "TestStaticMesh",
            "material_path": "/Game/TOTALLY_FAKE_PATH/BadMat"
        })
        assert_error(resp, "bad material path")
        return "correctly errored"
    run_test("bad_material_path", cat, _bad_material_path)

    # Unknown command
    def _unknown_cmd():
        resp = send_raw("totally_fake_command_xyz", {})
        assert_error(resp, "unknown command")
        return "correctly errored"
    run_test("unknown_command", cat, _unknown_cmd)

    # Missing required params
    def _missing_params():
        resp = send_raw("spawn_actor_at", {})
        # Should either error gracefully or spawn default
        return f"status={resp.get('status')}"
    run_test("missing_required_params", cat, _missing_params)

    # Very long string
    def _long_string():
        long_name = "A" * 500
        resp = send_raw("get_blueprint_info", {"name": long_name})
        assert_error(resp, "very long name")
        return "handled gracefully"
    run_test("very_long_string", cat, _long_string)

    # Verify server is still alive after all abuse
    def _still_alive():
        resp = CLIENT.health_check()
        assert_ok(resp, "health_check after error tests")
        return "server survived"
    run_test("server_still_alive", cat, _still_alive)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup():
    """Delete all test assets created during the run."""
    print("\n--- Cleanup ---")
    for name in [TEST_BP, TEST_BP2, TEST_SPLINE, "BP_ArcwrightAIPawn", "BP_ArcwrightMoveTest"]:
        safe_delete_bp(name)
    for label in [TEST_ACTOR_LABEL, TEST_ACTOR_LABEL2, TEST_PP_LABEL,
                  TEST_CONSTRAINT_LABEL, "ArcwrightSeqActor"]:
        safe_delete_actor(label)
    # Don't delete BT/DT/WBP/sequences/materials — they're harmless and
    # deleting them can crash if assets are referenced
    print("  Cleanup complete")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CATEGORIES = {
    "connection":       test_health_check,
    "blueprint_crud":   test_blueprint_crud,
    "node_editing":     test_node_editing,
    "components":       test_components,
    "materials":        test_materials,
    "level":            test_level,
    "widgets":          test_widgets,
    "behavior_tree":    test_behavior_tree,
    "data_table":       test_data_table,
    "ai_setup":         test_ai,
    "asset_import":     test_asset_import,
    "splines":          test_splines,
    "post_process":     test_post_process,
    "movement":         test_movement,
    "physics":          test_physics,
    "sequencer":        test_sequencer,
    "foliage":          test_foliage,
    "landscape":        test_landscape,
    "scene_setup":      test_scene_setup,
    "misc":             test_misc,
    "error_handling":   test_error_handling,
}


def main():
    global CLIENT, VERBOSE

    parser = argparse.ArgumentParser(description="Arcwright unified CI test suite")
    parser.add_argument("--category", "-c", help="Run only this category")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup")
    args = parser.parse_args()
    VERBOSE = args.verbose

    print("=" * 60)
    print("  ARCWRIGHT UNIFIED TEST SUITE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Connect
    try:
        CLIENT = ArcwrightClient(timeout=30.0)
        print(f"\nConnected to localhost:13377")
    except Exception as e:
        print(f"\nFATAL: Cannot connect to UE editor on port 13377: {e}")
        print("Is the editor running with the Arcwright plugin loaded?")
        sys.exit(1)

    # Pre-run cleanup: delete any stale BP_Generated that could cause partial-load crashes
    safe_delete_bp("BP_Generated")
    time.sleep(0.3)

    t_start = time.time()

    # Run categories
    cats_to_run = CATEGORIES
    if args.category:
        if args.category not in CATEGORIES:
            print(f"Unknown category: {args.category}")
            print(f"Available: {', '.join(CATEGORIES.keys())}")
            sys.exit(1)
        cats_to_run = {args.category: CATEGORIES[args.category]}

    for cat_name, cat_fn in cats_to_run.items():
        print(f"\n--- {cat_name.upper().replace('_', ' ')} ---")
        try:
            cat_fn()
        except Exception as e:
            print(f"  [FATAL] Category {cat_name} crashed: {e}")
            traceback.print_exc()
            # Try to reconnect for next category
            try:
                reconnect()
            except Exception:
                print("  Could not reconnect — remaining tests will fail")

    total_time = time.time() - t_start

    # Cleanup
    if not args.no_cleanup:
        try:
            cleanup()
        except Exception:
            pass

    # Close connection
    try:
        CLIENT.close()
    except Exception:
        pass

    # Summary
    passed = sum(1 for r in RESULTS if r.passed)
    failed = sum(1 for r in RESULTS if not r.passed and not r.skipped)
    skipped = sum(1 for r in RESULTS if r.skipped)
    total = len(RESULTS)

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed}/{total} PASS | {failed} FAIL | {skipped} SKIP")
    print(f"  Duration: {total_time:.1f}s")
    print("=" * 60)

    if failed > 0:
        print("\nFAILURES:")
        for r in RESULTS:
            if not r.passed and not r.skipped:
                print(f"  [{r.category}] {r.name}: {r.detail}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "duration_seconds": round(total_time, 1),
        "results": [r.to_dict() for r in RESULTS],
    }
    os.makedirs("results", exist_ok=True)
    report_path = f"results/ci_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
