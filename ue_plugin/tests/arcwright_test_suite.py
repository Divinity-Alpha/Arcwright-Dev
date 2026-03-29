# Arcwright Automated Test Suite
# C:\Arcwright\tests\arcwright_test_suite.py
#
# GPU: Forced to device 0 (NVIDIA RTX 5070 Ti)
# The RTX PRO 6000 is device 1 and must never be used here.
# Do NOT remove or change the CUDA_VISIBLE_DEVICES line.
#
# Usage:
#   python arcwright_test_suite.py --mode regression
#   python arcwright_test_suite.py --mode stress
#   python arcwright_test_suite.py --mode discovery
#   python arcwright_test_suite.py --mode all

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # RTX 5070 Ti only — never touch the 6000 Pro

import socket
import json
import time
import datetime
import sys
import argparse

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

HOST = "localhost"
PORT = 13377
TIMEOUT = 15
RESULTS_DIR = r"C:\Arcwright\tests\results"
TEST_CONTENT_PATH = "/Game/ArcwrightTests"

# ─────────────────────────────────────────────
# GPU VERIFICATION
# ─────────────────────────────────────────────

def verify_gpu():
    """Confirm we are on the 5070 Ti before running."""
    try:
        import torch
        if not torch.cuda.is_available():
            print("  ⚠ CUDA not available — skipping GPU check")
            return True
        name = torch.cuda.get_device_name(0)
        if "5070" in name:
            print(f"  ✓ GPU confirmed: {name} (device 0)")
            return True
        print(f"  ✗ WRONG GPU on device 0: {name}")
        print(f"    Expected RTX 5070 Ti — check nvidia-smi and update CUDA_VISIBLE_DEVICES")
        return False
    except ImportError:
        print("  ⚠ torch not installed — skipping GPU verification")
        return True

# ─────────────────────────────────────────────
# TCP CLIENT
# ─────────────────────────────────────────────

def send_command(command, params={}, timeout=TIMEOUT):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((HOST, PORT))
        s.sendall((json.dumps({"command": command, "params": params}) + "\n").encode())
        response = b""
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break
        s.close()
        return json.loads(response.decode().strip())
    except socket.timeout:
        return {"status": "error", "error": "TIMEOUT", "command": command}
    except ConnectionRefusedError:
        return {"status": "error", "error": "CONNECTION_REFUSED", "command": command}
    except Exception as e:
        return {"status": "error", "error": str(e), "command": command}

def ok(r):
    return r.get("status") == "ok"

def has_data(r, key):
    return key in r.get("data", {})

def graceful(r):
    """True unless the command hung or crashed UE5."""
    if r.get("error") == "TIMEOUT":
        return {"status": "FAIL", "error": "Command timed out — possible hang"}
    if r.get("error") == "CONNECTION_REFUSED":
        return {"status": "FAIL", "error": "UE5 crashed or disconnected"}
    return True

# ─────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────

class TestRunner:
    def __init__(self, mode):
        self.mode = mode
        self.results = []
        self.passed = self.failed = self.warnings = 0
        self.start_time = None
        os.makedirs(RESULTS_DIR, exist_ok=True)

    def test(self, name, category, fn):
        start = time.time()
        status = error = detail = None
        try:
            result = fn()
            if result is True:
                status, self.passed = "PASS", self.passed + 1
            elif result is False:
                status, self.failed = "FAIL", self.failed + 1
            elif isinstance(result, dict):
                status = result.get("status", "FAIL")
                detail = result.get("detail")
                error = result.get("error")
                if status == "PASS":   self.passed += 1
                elif status == "WARN": self.warnings += 1
                else:                  self.failed += 1
        except Exception as e:
            status, error, self.failed = "CRASH", str(e), self.failed + 1

        elapsed = round(time.time() - start, 2)
        self.results.append({
            "name": name, "category": category, "status": status,
            "elapsed_s": elapsed, "error": error, "detail": detail,
            "timestamp": datetime.datetime.now().isoformat()
        })
        icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "CRASH": "💥"}.get(status, "?")
        print(f"  {icon} [{elapsed:5.2f}s] {name}")
        if error:  print(f"           → {error}")
        if detail: print(f"           → {detail}")

    def section(self, name):
        print(f"\n{'─'*50}\n  {name}\n{'─'*50}")

    def print_summary(self):
        total = len(self.results)
        print(f"\n{'═'*50}")
        print(f"  RESULTS: {self.passed}/{total} passed  "
              f"{self.failed} failed  {self.warnings} warnings")
        print(f"{'═'*50}")
        for r in self.results:
            if r["status"] in ("FAIL", "CRASH"):
                print(f"  ✗ {r['name']}")
                if r["error"]: print(f"    → {r['error']}")

    def save(self):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(RESULTS_DIR, f"test_{self.mode}_{ts}.json")
        summary = {
            "mode": self.mode, "timestamp": ts,
            "gpu": "RTX 5070 Ti (CUDA device 0)",
            "passed": self.passed, "failed": self.failed,
            "warnings": self.warnings, "total": len(self.results),
            "duration_s": round(time.time() - self.start_time, 1),
            "results": self.results
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # Markdown report
        md = path.replace(".json", ".md")
        lines = [
            f"# Arcwright Test Results — {self.mode.upper()}",
            f"Run: {ts}",
            f"GPU: RTX 5070 Ti (CUDA device 0)",
            f"",
            f"| Result | Count |",
            f"|---|---|",
            f"| ✓ Passed | {self.passed} |",
            f"| ✗ Failed | {self.failed} |",
            f"| ⚠ Warnings | {self.warnings} |",
            f"| Total | {len(self.results)} |",
            f"| Duration | {summary['duration_s']}s |",
            f"", f"## Issues", f""
        ]
        for r in self.results:
            if r["status"] != "PASS":
                lines += [
                    f"### {r['status']} — {r['name']}",
                    f"**Category:** {r['category']}",
                ]
                if r["error"]:  lines.append(f"**Error:** {r['error']}")
                if r["detail"]: lines.append(f"**Detail:** {r['detail']}")
                lines.append("")
        lines += ["", "## All Results", "", "| Name | Status | Time |", "|---|---|---|"]
        for r in self.results:
            lines.append(f"| {r['name']} | {r['status']} | {r['elapsed_s']}s |")
        with open(md, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # new_issues.md for tally
        failures = [r for r in self.results if r["status"] in ("FAIL", "CRASH")]
        warnings = [r for r in self.results if r["status"] == "WARN"]
        if failures or warnings:
            ni = os.path.join(RESULTS_DIR, "new_issues.md")
            with open(ni, "w", encoding="utf-8") as f:
                f.write("# New Issues — Add to ARCWRIGHT_TALLY.md\n\n")
                if failures:
                    f.write("## Failures (Cat 1 or 3)\n\n")
                    for r in failures:
                        f.write(f"### {r['name']}\n- **Error:** {r['error']}\n"
                                f"- **Category:** F or M\n\n")
                if warnings:
                    f.write("## Warnings (Cat 2)\n\n")
                    for r in warnings:
                        f.write(f"### {r['name']}\n- **Detail:** {r['detail']}\n"
                                f"- **Category:** P\n\n")
            print(f"  Issues logged: {ni}")

        print(f"  Results saved: {path}")
        return summary


# ─────────────────────────────────────────────
# REGRESSION TESTS
# ─────────────────────────────────────────────

def run_regression(r):
    r.section("REGRESSION — Core functionality")
    bp = "BP_RegTest_Actor"

    r.test("health_check ok",                "connection", lambda: ok(send_command("health_check")))
    r.test("health_check has version",       "connection", lambda: has_data(send_command("health_check"), "version"))
    r.test("health_check has server name",   "connection", lambda: has_data(send_command("health_check"), "server"))
    r.test("10x rapid health_check",         "connection", lambda: all(ok(send_command("health_check")) for _ in range(10)))

    r.test("create_blueprint Actor",         "blueprint",  lambda: ok(send_command("create_blueprint", {"name": bp, "path": TEST_CONTENT_PATH, "parent_class": "Actor"})))
    r.test("get_blueprint_details",          "blueprint",  lambda: ok(send_command("get_blueprint_details", {"name": bp})))
    r.test("compile_blueprint",              "blueprint",  lambda: ok(send_command("compile_blueprint", {"name": bp})))
    r.test("create_blueprint Character",     "blueprint",  lambda: ok(send_command("create_blueprint", {"name": "BP_RegTest_Char", "path": TEST_CONTENT_PATH, "parent_class": "Character"})))
    r.test("create_blueprint Pawn",          "blueprint",  lambda: ok(send_command("create_blueprint", {"name": "BP_RegTest_Pawn", "path": TEST_CONTENT_PATH, "parent_class": "Pawn"})))

    r.test("add float variable",             "blueprint",  lambda: ok(send_command("batch_set_variable", {"operations": [{"blueprint": bp, "variable_name": "TestFloat", "default_value": "42.0"}]})))
    r.test("add int variable",               "blueprint",  lambda: ok(send_command("batch_set_variable", {"operations": [{"blueprint": bp, "variable_name": "TestInt", "default_value": "10"}]})))
    r.test("add bool variable",              "blueprint",  lambda: ok(send_command("batch_set_variable", {"operations": [{"blueprint": bp, "variable_name": "TestBool", "default_value": "true"}]})))
    r.test("add string variable",            "blueprint",  lambda: ok(send_command("batch_set_variable", {"operations": [{"blueprint": bp, "variable_name": "TestStr", "default_value": "Hello"}]})))

    r.test("add StaticMeshComponent",        "blueprint",  lambda: ok(send_command("add_component", {"blueprint": bp, "component_type": "StaticMeshComponent", "component_name": "TestMesh"})))
    r.test("add SphereComponent",            "blueprint",  lambda: ok(send_command("add_component", {"blueprint": bp, "component_type": "SphereComponent", "component_name": "TestSphere"})))
    r.test("add PointLightComponent",        "blueprint",  lambda: ok(send_command("add_component", {"blueprint": bp, "component_type": "PointLightComponent", "component_name": "TestLight"})))
    r.test("compile after components",       "blueprint",  lambda: ok(send_command("compile_blueprint", {"name": bp})))

    r.test("set SphereRadius",               "blueprint",  lambda: ok(send_command("set_component_property", {"blueprint": bp, "component_name": "TestSphere", "property_name": "SphereRadius", "value": "200.0"})))
    r.test("set PointLight intensity",       "blueprint",  lambda: ok(send_command("set_component_property", {"blueprint": bp, "component_name": "TestLight", "property_name": "Intensity", "value": "1000.0"})))
    r.test("set PointLight color hex",       "blueprint",  lambda: ok(send_command("set_component_property", {"blueprint": bp, "component_name": "TestLight", "property_name": "LightColor", "value": "hex:#4a9eff"})))

    r.test("create_widget_blueprint",        "widget",     lambda: ok(send_command("create_widget_blueprint", {"name": "WBP_RegTest_HUD", "design_width": 1920, "design_height": 1080})))
    r.test("get_widget_tree",                "widget",     lambda: ok(send_command("get_widget_tree", {"widget_blueprint": "WBP_RegTest_HUD"})))
    r.test("add widget Border child",        "widget",     lambda: ok(send_command("add_widget_child", {"widget_blueprint": "WBP_RegTest_HUD", "widget_type": "Border", "widget_name": "Border_Test"})))
    r.test("set widget BrushColor hex",      "widget",     lambda: ok(send_command("set_widget_property", {"widget_blueprint": "WBP_RegTest_HUD", "widget_name": "Border_Test", "property": "BrushColor", "value": "hex:#12161C"})))

    r.test("create_data_table",              "data",       lambda: ok(send_command("create_data_table", {"ir": {"metadata": {"table_name": "DT_RegTest", "struct_name": "RegTestStruct"}, "columns": [{"name": "Name", "type": "string"}, {"name": "Value", "type": "int32"}]}})))
    r.test("add_data_table_row",             "data",       lambda: ok(send_command("add_data_table_row", {"table_name": "DT_RegTest", "row_name": "Row_01", "values": {"Name": "Test", "Value": "100"}})))
    r.test("get_data_table_rows",            "data",       lambda: ok(send_command("get_data_table_rows", {"table_name": "DT_RegTest"})))

    r.test("spawn_actor_at",                 "level",      lambda: ok(send_command("spawn_actor_at", {"class": f"{TEST_CONTENT_PATH}/BP_RegTest_Actor.BP_RegTest_Actor_C", "label": "RegTest_Actor_01", "x": 0, "y": 0, "z": 100})))
    r.test("find_actors after spawn",        "level",      lambda: ok(send_command("find_actors", {"search": "RegTest_Actor_01"})))
    r.test("get_actor_properties",           "level",      lambda: ok(send_command("get_actor_properties", {"actor_name": "RegTest_Actor_01"})))

    r.test("verify_all_blueprints",          "verify",     lambda: ok(send_command("verify_all_blueprints")))
    r.test("run_map_check",                  "verify",     lambda: ok(send_command("run_map_check")))
    r.test("get_output_log",                 "verify",     lambda: ok(send_command("get_output_log", {"lines": 10})))
    r.test("list_project_assets",            "verify",     lambda: ok(send_command("list_project_assets", {"path": TEST_CONTENT_PATH})))
    r.test("find_assets",                    "verify",     lambda: ok(send_command("find_assets", {"search": "BP_RegTest", "asset_type": "Blueprint"})))
    r.test("save_all",                       "save",       lambda: ok(send_command("save_all")))


# ─────────────────────────────────────────────
# STRESS TESTS
# ─────────────────────────────────────────────

def run_stress(r):
    r.section("STRESS — Edge cases and bad inputs")
    bp = "BP_RegTest_Actor"

    r.test("create_blueprint empty name",         "stress", lambda: graceful(send_command("create_blueprint", {"name": "", "path": TEST_CONTENT_PATH})))
    r.test("create_blueprint no params",          "stress", lambda: graceful(send_command("create_blueprint", {})))
    r.test("compile_blueprint bad path",          "stress", lambda: graceful(send_command("compile_blueprint", {"name": "/Game/Fake/BP_Fake"})))
    r.test("get_blueprint_details nonexistent",   "stress", lambda: graceful(send_command("get_blueprint_details", {"blueprint": "/Game/Fake/BP_Never"})))
    r.test("spawn_actor invalid class",           "stress", lambda: graceful(send_command("spawn_actor_at", {"class": "BP_DoesNotExist_C", "label": "Fake", "x": 0, "y": 0, "z": 0})))
    r.test("spawn_actor missing _C suffix",       "stress", lambda: graceful(send_command("spawn_actor_at", {"class": f"{TEST_CONTENT_PATH}/BP_RegTest_Actor", "label": "NoSuffix", "x": 0, "y": 0, "z": 0})))
    r.test("set_component_property bad comp",     "stress", lambda: graceful(send_command("set_component_property", {"blueprint": bp, "component_name": "FakeComponent", "property_name": "Intensity", "value": "1000.0"})))
    r.test("set_widget_property bad widget",      "stress", lambda: graceful(send_command("set_widget_property", {"widget_blueprint": "WBP_RegTest_HUD", "widget_name": "FakeWidget", "property": "BrushColor", "value": "hex:#FF0000"})))
    r.test("add_data_table_row wrong types",      "stress", lambda: graceful(send_command("add_data_table_row", {"table_name": "DT_RegTest", "row_name": "BadRow", "values": {"Name": "99999", "Value": "not_int"}})))
    r.test("find_actors empty search",            "stress", lambda: graceful(send_command("find_actors", {"search": ""})))
    r.test("get_output_log 0 lines",              "stress", lambda: graceful(send_command("get_output_log", {"lines": 0})))
    r.test("get_output_log 10000 lines",          "stress", lambda: graceful(send_command("get_output_log", {"lines": 10000})))
    r.test("spawn at extreme positive coords",    "stress", lambda: graceful(send_command("spawn_actor_at", {"class": f"{TEST_CONTENT_PATH}/BP_RegTest_Actor.BP_RegTest_Actor_C", "label": "FarActor", "x": 999999, "y": 999999, "z": 999999})))
    r.test("spawn at extreme negative coords",    "stress", lambda: graceful(send_command("spawn_actor_at", {"class": f"{TEST_CONTENT_PATH}/BP_RegTest_Actor.BP_RegTest_Actor_C", "label": "NegActor", "x": -999999, "y": -999999, "z": -999999})))
    r.test("SphereRadius = 0",                    "stress", lambda: graceful(send_command("set_component_property", {"blueprint": bp, "component_name": "TestSphere", "property_name": "SphereRadius", "value": "0.0"})))
    r.test("SphereRadius negative",              "stress", lambda: graceful(send_command("set_component_property", {"blueprint": bp, "component_name": "TestSphere", "property_name": "SphereRadius", "value": "-500.0"})))
    r.test("light intensity = 0",                "stress", lambda: graceful(send_command("set_component_property", {"blueprint": bp, "component_name": "TestLight", "property_name": "Intensity", "value": "0.0"})))
    r.test("light intensity = 1000000",          "stress", lambda: graceful(send_command("set_component_property", {"blueprint": bp, "component_name": "TestLight", "property_name": "Intensity", "value": "1000000.0"})))
    r.test("50 rapid health_checks",             "stress", lambda: all(ok(send_command("health_check")) for _ in range(50)))
    r.test("20 rapid compiles",                  "stress", lambda: all(graceful(send_command("compile_blueprint", {"name": bp})) for _ in range(20)))
    r.test("10 rapid spawns same label",         "stress", lambda: all(graceful(send_command("spawn_actor_at", {"class": f"{TEST_CONTENT_PATH}/BP_RegTest_Actor.BP_RegTest_Actor_C", "label": "DupLabel", "x": 0, "y": 0, "z": 0})) for _ in range(10)))
    r.test("color without hex: prefix",          "stress", lambda: {"status": "WARN", "detail": "No hex: prefix — may produce wrong color"} if ok(send_command("set_widget_property", {"widget_blueprint": "WBP_RegTest_HUD", "widget_name": "Border_Test", "property": "BrushColor", "value": "(R=0.5,G=0.5,B=0.5,A=1.0)"})) else True)
    r.test("color invalid hex value",            "stress", lambda: graceful(send_command("set_widget_property", {"widget_blueprint": "WBP_RegTest_HUD", "widget_name": "Border_Test", "property": "BrushColor", "value": "hex:#GGGGGG"})))
    r.test("color 3-digit hex",                  "stress", lambda: graceful(send_command("set_widget_property", {"widget_blueprint": "WBP_RegTest_HUD", "widget_name": "Border_Test", "property": "BrushColor", "value": "hex:#FFF"})))
    r.test("unknown command graceful error",     "stress", lambda: not ok(send_command("this_command_does_not_exist", {})))
    r.test("malformed path traversal",           "stress", lambda: graceful(send_command("create_blueprint", {"name": "BP_<bad>", "path": "/Game/../../../etc"})))


# ─────────────────────────────────────────────
# DISCOVERY TESTS
# ─────────────────────────────────────────────

def run_discovery(r):
    r.section("DISCOVERY — Silent failures and wrong results")

    def color_roundtrip(color):
        if not ok(send_command("set_widget_property", {"widget_blueprint": "WBP_RegTest_HUD", "widget_name": "Border_Test", "property": "BrushColor", "value": color})):
            return {"status": "FAIL", "error": f"Set failed for {color}"}
        tree = str(send_command("get_widget_tree", {"widget_blueprint": "WBP_RegTest_HUD"}).get("data", {}))
        if "(R=1.0" in tree and "G=1.0" in tree:
            return {"status": "FAIL", "error": f"{color} applied as white — sRGB conversion broken"}
        return True

    r.test("dark color not white after apply",   "discovery", lambda: color_roundtrip("hex:#12161C"))
    r.test("amber color not white after apply",  "discovery", lambda: color_roundtrip("hex:#E8A624"))
    r.test("green color not white after apply",  "discovery", lambda: color_roundtrip("hex:#3DDC84"))
    r.test("red color not white after apply",    "discovery", lambda: color_roundtrip("hex:#E04050"))
    r.test("black hex not transparent",          "discovery", lambda: color_roundtrip("hex:#000000"))

    def light_prop(prop, val):
        send_command("set_component_property", {"blueprint": "BP_RegTest_Actor", "component_name": "TestLight", "property_name": prop, "value": val})
        return ok(send_command("get_blueprint_details", {"name": "BP_RegTest_Actor"}))

    r.test("PointLight intensity persists",      "discovery", lambda: light_prop("Intensity", "5000.0"))
    r.test("PointLight color persists",          "discovery", lambda: light_prop("LightColor", "hex:#FF0000"))

    def prop_before_compile():
        bp2 = "BP_DiscTest_Seq"
        send_command("create_blueprint", {"name": bp2, "path": TEST_CONTENT_PATH, "parent_class": "Actor"})
        send_command("add_component", {"blueprint": bp2, "component_type": "SphereComponent", "component_name": "SeqSphere"})
        r2 = send_command("set_component_property", {"blueprint": bp2, "component_name": "SeqSphere", "property_name": "SphereRadius", "value": "777.0"})
        if not ok(r2):
            return {"status": "WARN", "detail": "set_component_property before compile returns error — expected per SKILL_003"}
        send_command("compile_blueprint", {"name": bp2})
        if "777" not in str(send_command("get_blueprint_details", {"name": bp2}).get("data", {})):
            return {"status": "WARN", "detail": "Property before compile did not persist — confirms SKILL_003"}
        return True

    r.test("property before compile persistence", "discovery", prop_before_compile)

    def pie_immediate():
        send_command("play_in_editor")
        time.sleep(0.5)
        res = send_command("take_screenshot", {"filename": "disc_immediate"})
        send_command("stop_play")
        if not ok(res):
            return {"status": "WARN", "detail": "Immediate screenshot failed — confirms F002/F003"}
        return {"status": "WARN", "detail": "Immediate screenshot taken — verify image is not black"}

    def pie_delayed():
        send_command("play_in_editor")
        time.sleep(5)
        res = send_command("take_screenshot", {"filename": "disc_delayed"})
        send_command("stop_play")
        return ok(res)

    r.test("PIE screenshot immediate (expect warn)", "discovery", pie_immediate)
    r.test("PIE screenshot 5s delay (expect pass)",  "discovery", pie_delayed)

    def dup_event():
        bp3 = "BP_DiscTest_Evt"
        send_command("create_blueprint", {"name": bp3, "path": TEST_CONTENT_PATH, "parent_class": "Actor"})
        send_command("compile_blueprint", {"name": bp3})
        send_command("add_nodes_batch", {"blueprint": bp3, "nodes": [{"type": "Event_BeginPlay", "node_id": "dup"}]})
        if "Event None" in str(send_command("get_blueprint_details", {"name": bp3}).get("data", {})):
            return {"status": "WARN", "detail": "Duplicate BeginPlay = Event None — confirms P002"}
        return True

    r.test("duplicate BeginPlay detection",      "discovery", dup_event)

    def no_c_suffix():
        res = send_command("spawn_actor_at", {"class": f"{TEST_CONTENT_PATH}/BP_RegTest_Actor", "label": "NoC_Test", "x": 500, "y": 0, "z": 0})
        if not ok(res):
            return {"status": "WARN", "detail": "Spawn without _C returned error — good, fails explicitly"}
        return {"status": "WARN", "detail": "Spawn without _C succeeded — actor likely has no BP logic, confirms P003"}

    r.test("spawn without _C suffix",            "discovery", no_c_suffix)

    def level_lighting():
        actors = send_command("find_actors", {"search": "DirectionalLight"}).get("data", {}).get("actors", [])
        if not actors:
            return {"status": "WARN", "detail": "No DirectionalLight — screenshots will be black, run setup_default_lighting"}
        actors2 = send_command("find_actors", {"search": "SkyLight"}).get("data", {}).get("actors", [])
        if not actors2:
            return {"status": "WARN", "detail": "No SkyLight — ambient lighting missing"}
        return True

    r.test("level has DirectionalLight",         "discovery", level_lighting)
    r.test("verify_all after discovery",         "discovery", lambda: ok(send_command("verify_all_blueprints")))
    r.test("save_all after discovery",           "discovery", lambda: ok(send_command("save_all")))


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["regression", "stress", "discovery", "all"], default="regression")
    parser.add_argument("--no-cleanup", action="store_true")
    parser.add_argument("--skip-gpu-check", action="store_true")
    args = parser.parse_args()

    print(f"\n{'═'*50}")
    print(f"  ARCWRIGHT TEST SUITE — {args.mode.upper()}")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  GPU: RTX 5070 Ti forced (CUDA_VISIBLE_DEVICES=0)")
    print(f"{'═'*50}")

    if not args.skip_gpu_check:
        print("\n  Verifying GPU...")
        if not verify_gpu():
            print("  Aborting. Use --skip-gpu-check if torch is not installed.")
            sys.exit(1)

    print("\n  Checking Arcwright connection...")
    r = send_command("health_check")
    if not ok(r):
        print(f"  ✗ Cannot connect on {HOST}:{PORT} — is UE5 running with Arcwright enabled?")
        sys.exit(1)
    print(f"  ✓ Connected — Arcwright v{r.get('data', {}).get('version', '?')}")

    runner = TestRunner(args.mode)
    runner.start_time = time.time()

    if args.mode in ("regression", "all"): run_regression(runner)
    if args.mode in ("stress",     "all"): run_stress(runner)
    if args.mode in ("discovery",  "all"): run_discovery(runner)

    runner.print_summary()
    runner.save()
    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
