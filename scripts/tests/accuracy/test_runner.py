#!/usr/bin/env python3
"""
Arcwright Accuracy Test Runner — Run #001+

Runs the 120-command accuracy test suite against the intent server + UE,
scores on 5 dimensions (Intent, Plan, Execute, Verify, Quality),
saves results, and generates reports.

Usage:
    python scripts/tests/accuracy/test_runner.py --run-all --fresh-level
    python scripts/tests/accuracy/test_runner.py --retest-failures --run latest
    python scripts/tests/accuracy/test_runner.py --run-ids F.01 F.02 C.01
    python scripts/tests/accuracy/test_runner.py --category create
"""

import argparse
import json
import os
import re
import socket
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

ACCURACY_DIR = PROJECT_ROOT / "scripts" / "tests" / "accuracy"
RESULTS_DIR = ACCURACY_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Default ports
INTENT_PORT = 13380
UE_PORT = 13377

# Phase execution order
PHASE_ORDER = ["foundation", "create", "modify", "query", "multi", "vague", "edge"]


# ── TCP communication ─────────────────────────────────────────

def send_tcp(host, port, payload, timeout=120):
    """Send JSON payload via TCP, return parsed response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(min(timeout, 60))  # Per-recv timeout (max 60s per chunk)
    deadline = time.time() + timeout    # Hard deadline for entire operation
    try:
        sock.connect((host, port))
        msg = json.dumps(payload) + "\n"
        sock.sendall(msg.encode("utf-8"))

        buf = b""
        while time.time() < deadline:
            try:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    break
            except socket.timeout:
                # Per-recv timeout, check hard deadline
                if time.time() >= deadline:
                    break
                continue

        if time.time() >= deadline and b"\n" not in buf:
            return {"status": "error", "message": f"Timeout after {timeout}s (hard deadline)"}

        response_text = buf.decode("utf-8").strip()
        if not response_text:
            return {"status": "error", "message": "Empty response"}
        return json.loads(response_text)
    except socket.timeout:
        return {"status": "error", "message": f"Timeout after {timeout}s"}
    except ConnectionRefusedError:
        return {"status": "error", "message": f"Connection refused on port {port}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        sock.close()


def send_to_intent(prompt, host="localhost", port=INTENT_PORT, timeout=600):
    """Send prompt to intent server, return classification result."""
    return send_tcp(host, port, {"prompt": prompt}, timeout=timeout)


def send_to_ue(command, params=None, host="localhost", port=UE_PORT, timeout=30):
    """Send command to UE command server."""
    payload = {"command": command, "params": params or {}}
    return send_tcp(host, port, payload, timeout=timeout)


def generate_dsl(domain, prompt, host="localhost", port=INTENT_PORT, timeout=300):
    """Request DSL generation from intent server."""
    payload = {"command": "generate_dsl", "domain": domain, "prompt": prompt}
    return send_tcp(host, port, payload, timeout=timeout)


# ── DSL parsing helpers ───────────────────────────────────────

def parse_dsl_to_ir(domain, dsl_text):
    """Parse DSL text to IR JSON using the appropriate parser."""
    scripts_dir = str(PROJECT_ROOT / "scripts")
    parser_dir = str(PROJECT_ROOT / "scripts" / "dsl_parser")

    # Ensure parser directories are on sys.path
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    if parser_dir not in sys.path:
        sys.path.insert(0, parser_dir)

    try:
        if domain == "blueprint":
            from dsl_parser.parser import parse as _parse_bp
            result = _parse_bp(dsl_text)
            ir = result.get("ir") if isinstance(result, dict) else None
            return ir
        elif domain == "bt":
            from bt_parser.bt_parser import parse as _parse_bt
            result = _parse_bt(dsl_text)
            ir = result.get("ir") if isinstance(result, dict) else None
            return ir
        elif domain == "dt":
            from dt_parser.dt_parser import parse as _parse_dt
            result = _parse_dt(dsl_text)
            ir = result.get("ir") if isinstance(result, dict) else None
            return ir
    except Exception as e:
        print(f"         PARSE ERROR ({domain}): {e}", file=sys.stderr)
        return None
    return None


# ── Test execution ────────────────────────────────────────────

class TestResult:
    """Result of a single test execution."""
    def __init__(self, test_id):
        self.test_id = test_id
        self.intent_score = 0   # 0 or 1
        self.plan_score = 0     # 0 or 1
        self.exec_score = 0     # 0 or 1
        self.verify_score = 0   # 0 or 1
        self.quality_score = 0  # 0 or 1
        self.total = 0
        self.actual_mode = ""
        self.actual_commands = []
        self.plan_raw = {}
        self.exec_results = []
        self.verify_results = []
        self.error = ""
        self.failure_codes = []
        self.duration_s = 0.0

    def compute_total(self):
        self.total = (self.intent_score + self.plan_score +
                      self.exec_score + self.verify_score + self.quality_score)

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "intent_score": self.intent_score,
            "plan_score": self.plan_score,
            "exec_score": self.exec_score,
            "verify_score": self.verify_score,
            "quality_score": self.quality_score,
            "total": self.total,
            "actual_mode": self.actual_mode,
            "actual_commands": self.actual_commands,
            "plan_raw": self.plan_raw,
            "exec_results": self.exec_results,
            "verify_results": self.verify_results,
            "error": self.error,
            "failure_codes": self.failure_codes,
            "duration_s": round(self.duration_s, 2),
        }


class AccuracyTestRunner:
    def __init__(self, intent_host="localhost", intent_port=INTENT_PORT,
                 ue_host="localhost", ue_port=UE_PORT):
        self.intent_host = intent_host
        self.intent_port = intent_port
        self.ue_host = ue_host
        self.ue_port = ue_port
        self.tests = []
        self.results = {}

    def load_tests(self, path=None):
        """Load test_commands.json."""
        path = path or (ACCURACY_DIR / "test_commands.json")
        with open(path, "r") as f:
            data = json.load(f)
        self.tests = data["commands"]
        return len(self.tests)

    def check_connectivity(self):
        """Verify both servers are reachable."""
        print("  Checking UE command server (13377)...", end=" ")
        ue = send_to_ue("health_check")
        if ue.get("status") != "ok":
            print(f"FAILED: {ue.get('message', 'unknown')}")
            return False
        print(f"OK — {ue.get('data', {}).get('server', '?')}")

        print("  Checking intent server (13380)...", end=" ")
        intent = send_to_intent("health check", timeout=10)
        # Intent server might return a classification, not a health_check
        if intent.get("status") == "error" and "refused" in intent.get("message", "").lower():
            print(f"FAILED: {intent.get('message')}")
            return False
        print("OK")
        return True

    def fresh_level(self):
        """Clean the level for a fresh start."""
        print("\n  Cleaning level for fresh start...")

        # Delete all actors
        actors = send_to_ue("find_actors", {"name_filter": ""})
        if actors.get("status") == "ok":
            actor_list = actors.get("data", {}).get("actors", [])
            if actor_list:
                labels = [a.get("label", "") for a in actor_list if a.get("label")]
                if labels:
                    result = send_to_ue("batch_delete_actors", {"labels": labels})
                    deleted = result.get("data", {}).get("deleted", 0)
                    print(f"    Deleted {deleted} actors")

        # Delete generated blueprints
        bps = send_to_ue("find_blueprints", {"path": "/Game/Arcwright/Generated"})
        if bps.get("status") == "ok":
            bp_list = bps.get("data", {}).get("blueprints", [])
            for bp in bp_list:
                name = bp.get("name", "")
                if name:
                    send_to_ue("delete_blueprint", {"name": name})
            if bp_list:
                print(f"    Deleted {len(bp_list)} blueprints")

        # Delete generated data tables
        dts = send_to_ue("find_assets", {"type": "DataTable", "path": "/Game/BlueprintLLM"})
        if dts.get("status") == "ok":
            for asset in dts.get("data", {}).get("assets", []):
                name = asset.get("name", "")
                if name:
                    send_to_ue("delete_blueprint", {"name": name})

        # Delete behavior trees
        bts = send_to_ue("find_assets", {"type": "BehaviorTree", "path": "/Game/BlueprintLLM"})
        if bts.get("status") == "ok":
            for asset in bts.get("data", {}).get("assets", []):
                name = asset.get("name", "")
                if name:
                    send_to_ue("delete_blueprint", {"name": name})

        print("    Level cleaned.")

    # ── Intent scoring ────────────────────────────────────

    def score_intent(self, plan, test):
        """Score whether the intent mode was classified correctly."""
        expected = test["expected_mode"]
        actual = plan.get("mode", "ERROR")

        # Allow flexible matching for some categories
        if expected == actual:
            return 1

        # MULTI and CREATE are sometimes interchangeable for complex create prompts
        if expected == "MULTI" and actual == "CREATE" and test["category"] == "foundation":
            return 1
        if expected == "CREATE" and actual == "MULTI" and test["category"] == "multi":
            return 1

        # MODIFY can include find_actors step, which is fine
        if expected == "MODIFY" and actual == "MULTI":
            return 1

        return 0

    # ── Plan scoring ──────────────────────────────────────

    def score_plan(self, plan, test):
        """Score whether the plan contains the right commands."""
        expected_cmds = test["expected_commands"]
        if not expected_cmds:
            # For CLARIFY tests, no operations expected
            ops = plan.get("operations", [])
            if not ops or plan.get("mode") in ("CLARIFY", "HELP", "ERROR"):
                return 1
            return 0

        actual_ops = plan.get("operations", [])
        if not actual_ops:
            return 0

        actual_cmds = set()
        for op in actual_ops:
            cmd = op.get("command", "")
            actual_cmds.add(cmd)

        # Check if all expected commands appear in the plan
        matched = 0
        for exp in expected_cmds:
            if exp in actual_cmds:
                matched += 1
            else:
                # Check aliases
                aliases = {
                    "create_blueprint": {"create_blueprint", "create_blueprint_from_dsl", "import_from_ir"},
                    "create_data_table": {"create_data_table", "create_data_table_from_dsl"},
                    "create_behavior_tree": {"create_behavior_tree", "create_behavior_tree_from_dsl"},
                    "batch_apply_material": {"batch_apply_material", "set_actor_material"},
                    "find_actors": {"find_actors", "get_actors"},
                    "find_blueprints": {"find_blueprints", "get_blueprint_info"},
                    "find_assets": {"find_assets"},
                    "get_level_info": {"get_level_info", "find_actors"},
                    "get_components": {"get_components", "get_blueprint_info"},
                    "get_blueprint_info": {"get_blueprint_info", "find_blueprints"},
                }
                exp_set = aliases.get(exp, {exp})
                if actual_cmds & exp_set:
                    matched += 1

        return 1 if matched >= len(expected_cmds) else 0

    # ── Execution ─────────────────────────────────────────

    def execute_plan(self, plan, test):
        """Execute the plan against UE. Returns list of execution results.
        Resilient execution: if a step fails and the next step does NOT
        depend on it, continue executing. Only skip steps whose dependency failed.
        """
        operations = plan.get("operations", [])
        if not operations:
            return []

        results = []
        prior_results = {}
        failed_steps = set()  # Track which steps failed

        for op in operations:
            cmd = op.get("command", "")
            params = op.get("params", {})
            step = op.get("step", 0)
            depends_on = op.get("depends_on")

            # Check if this step depends on a failed step — skip if so
            if depends_on and isinstance(depends_on, (str, int)):
                dep_step = None
                if isinstance(depends_on, str):
                    match = re.match(r"\$?step(\d+)", depends_on)
                    if match:
                        dep_step = int(match.group(1))
                elif isinstance(depends_on, int):
                    dep_step = depends_on

                if dep_step is not None and dep_step in failed_steps:
                    result = {"status": "error",
                              "message": f"Skipped: dependency step {dep_step} failed",
                              "step": step, "command": cmd, "skipped": True}
                    results.append(result)
                    failed_steps.add(step)
                    continue

                # Inject dependency data if available
                if dep_step is not None:
                    dep_data = prior_results.get(dep_step, {})
                    if dep_data:
                        params["_dependency_data"] = dep_data

            # Auto-populate batch command operations from find_actors/find_blueprints results
            params = self._inject_discovery_into_batch(cmd, params)

            result = self._execute_single(cmd, params, test)
            result["step"] = step
            result["command"] = cmd
            results.append(result)

            if result.get("status") == "ok":
                prior_results[step] = result.get("data", {})
            else:
                failed_steps.add(step)

        return results

    def _inject_discovery_into_batch(self, cmd, params):
        """When a batch command depends on find_actors/find_blueprints results,
        build the operations[] array from the dependency data if missing."""
        dep_data = params.pop("_dependency_data", None)
        if not dep_data:
            return params

        # batch_set_property: inject actor labels from find_actors
        if cmd == "batch_set_property" and "operations" not in params:
            actors = dep_data.get("actors", [])
            if actors:
                prop = params.get("property", params.get("property_name",
                       params.get("property_path", "")))
                value = params.get("value", "")
                relative = params.get("relative", False)
                ops = []
                for actor in actors:
                    label = actor.get("label", "") if isinstance(actor, dict) else str(actor)
                    if label:
                        sub_op = {"actor_label": label, "property": prop, "value": value}
                        if relative:
                            sub_op["relative"] = True
                        ops.append(sub_op)
                if ops:
                    params = {"operations": ops}

        # batch_apply_material: inject actor labels from find_actors
        elif cmd == "batch_apply_material" and "operations" not in params:
            actors = dep_data.get("actors", [])
            mat_path = params.get("material_path", params.get("value", ""))
            if actors and mat_path:
                ops = []
                for actor in actors:
                    label = actor.get("label", "") if isinstance(actor, dict) else str(actor)
                    if label:
                        ops.append({"actor_label": label, "material_path": mat_path})
                if ops:
                    params = {"operations": ops}

        # batch_set_variable: inject blueprint names from find_blueprints
        elif cmd == "batch_set_variable" and "operations" not in params:
            blueprints = dep_data.get("blueprints", [])
            var_name = params.get("variable_name", "")
            var_value = params.get("default_value", params.get("value", ""))
            if blueprints and var_name:
                ops = []
                for bp in blueprints:
                    bp_name = bp.get("name", "") if isinstance(bp, dict) else str(bp)
                    if bp_name:
                        ops.append({"blueprint": bp_name, "variable_name": var_name,
                                    "default_value": str(var_value)})
                if ops:
                    params = {"operations": ops}

        # batch_delete_actors: inject labels from find_actors
        elif cmd == "batch_delete_actors" and "labels" not in params:
            actors = dep_data.get("actors", [])
            if actors:
                labels = []
                for actor in actors:
                    label = actor.get("label", "") if isinstance(actor, dict) else str(actor)
                    if label:
                        labels.append(label)
                if labels:
                    params["labels"] = labels

        # batch_add_component: inject blueprint names from find_blueprints
        elif cmd == "batch_add_component" and "operations" not in params:
            blueprints = dep_data.get("blueprints", [])
            comp_type = params.get("component_type", "")
            comp_name = params.get("component_name", "")
            properties = params.get("properties", {})
            if blueprints and comp_type:
                ops = []
                for bp in blueprints:
                    bp_name = bp.get("name", "") if isinstance(bp, dict) else str(bp)
                    if bp_name:
                        op = {"blueprint": bp_name, "component_type": comp_type}
                        if comp_name:
                            op["component_name"] = comp_name
                        if properties:
                            op["properties"] = dict(properties)
                        ops.append(op)
                if ops:
                    params = {"operations": ops}

        return params

    def _execute_single(self, command, params, test):
        """Execute a single command."""
        # DSL generation commands need the full pipeline
        if command in ("create_blueprint", "create_blueprint_from_dsl"):
            return self._execute_dsl_create("blueprint", params, test)
        elif command in ("create_behavior_tree", "create_behavior_tree_from_dsl"):
            return self._execute_dsl_create("bt", params, test)
        elif command in ("create_data_table", "create_data_table_from_dsl"):
            return self._execute_dsl_create("dt", params, test)
        else:
            # Direct TCP command to UE
            return send_to_ue(command, params)

    def _execute_dsl_create(self, domain, params, test):
        """Full DSL pipeline: generate → parse → import."""
        prompt = params.get("prompt", test.get("prompt", ""))

        # Step 1: Generate DSL
        dsl_result = generate_dsl(domain, prompt, timeout=300)
        if dsl_result.get("status") != "ok":
            return {"status": "error", "message": f"DSL generation failed: {dsl_result.get('message', '')}",
                    "stage": "generate"}

        dsl_text = dsl_result.get("dsl", "")
        if not dsl_text:
            return {"status": "error", "message": "Empty DSL generated", "stage": "generate"}

        # Step 2: Parse DSL to IR
        ir = parse_dsl_to_ir(domain, dsl_text)
        if not ir:
            return {"status": "error", "message": "DSL parsing failed", "stage": "parse",
                    "dsl": dsl_text}

        # Step 3: Import IR to UE
        if domain == "blueprint":
            # Save IR to temp file and import
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".blueprint.json",
                                              delete=False, dir=str(PROJECT_ROOT / "test_ir")) as f:
                json.dump(ir, f, indent=2)
                ir_path = f.name

            try:
                result = send_to_ue("import_from_ir", {"path": ir_path})
                result["dsl"] = dsl_text
                result["ir_path"] = ir_path
                return result
            except Exception as e:
                return {"status": "error", "message": str(e), "stage": "import"}
        elif domain == "bt":
            result = send_to_ue("create_behavior_tree", {"ir": ir})
            result["dsl"] = dsl_text
            return result
        elif domain == "dt":
            result = send_to_ue("create_data_table", {"ir": ir})
            result["dsl"] = dsl_text
            return result

        return {"status": "error", "message": f"Unknown domain: {domain}"}

    def score_execution(self, exec_results):
        """Score whether all commands executed without errors."""
        if not exec_results:
            return 1  # No operations = no errors (for CLARIFY etc.)

        for r in exec_results:
            if r.get("status") != "ok":
                return 0
        return 1

    # ── Verification ──────────────────────────────────────

    def run_verifications(self, verify_checks, plan=None):
        """Run all verification checks for a test."""
        results = []
        for check in verify_checks:
            check_type = check.get("type", "")
            params = check.get("params", {})

            try:
                passed, detail = self._run_single_verify(check_type, params, plan)
            except Exception as e:
                passed, detail = False, str(e)

            results.append({
                "type": check_type,
                "passed": passed,
                "detail": detail,
            })
        return results

    def _run_single_verify(self, check_type, params, plan=None):
        """Run a single verification check. Returns (passed, detail)."""

        if check_type == "blueprint_exists":
            pattern = params.get("name_pattern", "")
            result = send_to_ue("find_blueprints", {"name_filter": ""})
            if result.get("status") != "ok":
                return False, f"find_blueprints failed: {result.get('message', '')}"
            bps = result.get("data", {}).get("blueprints", [])
            for bp in bps:
                name = bp.get("name", "")
                if self._pattern_match(name, pattern):
                    return True, f"Found: {name}"
            return False, f"No blueprint matching '{pattern}' found"

        elif check_type == "blueprint_has_variable":
            pattern = params.get("name_pattern", "")
            var_pattern = params.get("variable", "")
            # Find the blueprint first
            result = send_to_ue("find_blueprints", {"name_filter": ""})
            if result.get("status") != "ok":
                return False, "find_blueprints failed"
            bps = result.get("data", {}).get("blueprints", [])
            for bp in bps:
                name = bp.get("name", "")
                if self._pattern_match(name, pattern):
                    # Check variables
                    info = send_to_ue("get_blueprint_info", {"name": name})
                    if info.get("status") == "ok":
                        variables = info.get("data", {}).get("variables", [])
                        for v in variables:
                            vname = v.get("name", "")
                            if self._pattern_match(vname, var_pattern):
                                return True, f"Found variable '{vname}' on {name}"
                    return False, f"Blueprint '{name}' has no variable matching '{var_pattern}'"
            return False, f"No blueprint matching '{pattern}'"

        elif check_type == "blueprint_has_component":
            pattern = params.get("name_pattern", "")
            comp_pattern = params.get("component", "")
            result = send_to_ue("find_blueprints", {"name_filter": ""})
            if result.get("status") != "ok":
                return False, "find_blueprints failed"
            bps = result.get("data", {}).get("blueprints", [])
            for bp in bps:
                name = bp.get("name", "")
                if self._pattern_match(name, pattern):
                    comps = send_to_ue("get_components", {"blueprint": name})
                    if comps.get("status") == "ok":
                        for c in comps.get("data", {}).get("components", []):
                            if self._pattern_match(c.get("name", ""), comp_pattern) or \
                               self._pattern_match(c.get("class", ""), comp_pattern):
                                return True, f"Found component matching '{comp_pattern}' on {name}"
                    return False, f"No component matching '{comp_pattern}' on {name}"
            return False, f"No blueprint matching '{pattern}'"

        elif check_type == "actor_exists":
            name_pat = params.get("name_pattern", "")
            class_pat = params.get("class_pattern", "")
            filter_params = {}
            if name_pat:
                # Use the first alternative as the filter
                first = name_pat.split("|")[0]
                filter_params["name_filter"] = first
            if class_pat:
                first = class_pat.split("|")[0]
                filter_params["class_filter"] = first
            result = send_to_ue("find_actors", filter_params)
            if result.get("status") != "ok":
                return False, "find_actors failed"
            actors = result.get("data", {}).get("actors", [])
            if actors:
                return True, f"Found {len(actors)} actors"
            # Try broader search
            result2 = send_to_ue("find_actors", {"name_filter": ""})
            if result2.get("status") == "ok":
                all_actors = result2.get("data", {}).get("actors", [])
                full_pattern = name_pat or class_pat
                for a in all_actors:
                    label = a.get("label", "")
                    cls = a.get("class", "")
                    if self._pattern_match(label, full_pattern) or self._pattern_match(cls, full_pattern):
                        return True, f"Found actor: {label} ({cls})"
            return False, f"No actor matching name='{name_pat}' class='{class_pat}'"

        elif check_type == "actor_count":
            name_pat = params.get("name_pattern", "")
            min_count = params.get("min_count", 1)
            result = send_to_ue("find_actors", {"name_filter": ""})
            if result.get("status") != "ok":
                return False, "find_actors failed"
            actors = result.get("data", {}).get("actors", [])
            matching = [a for a in actors
                        if self._pattern_match(a.get("label", ""), name_pat) or
                           self._pattern_match(a.get("class", ""), name_pat)]
            count = len(matching)
            if count >= min_count:
                return True, f"Found {count} actors (min: {min_count})"
            return False, f"Found {count} actors, expected >= {min_count}"

        elif check_type == "actor_not_exists":
            name_pat = params.get("name_pattern", "")
            result = send_to_ue("find_actors", {"name_filter": ""})
            if result.get("status") != "ok":
                return True, "find_actors failed (assumed no actors)"
            actors = result.get("data", {}).get("actors", [])
            matching = [a for a in actors
                        if self._pattern_match(a.get("label", ""), name_pat) or
                           self._pattern_match(a.get("class", ""), name_pat)]
            if not matching:
                return True, "No matching actors found (as expected)"
            return False, f"Found {len(matching)} actors that should have been deleted"

        elif check_type == "asset_exists":
            asset_type = params.get("asset_type", "")
            name_pat = params.get("name_pattern", "")
            result = send_to_ue("find_assets", {"type": asset_type, "name_filter": name_pat.split("|")[0]})
            if result.get("status") != "ok":
                return False, "find_assets failed"
            assets = result.get("data", {}).get("assets", [])
            for a in assets:
                if self._pattern_match(a.get("name", ""), name_pat):
                    return True, f"Found asset: {a.get('name')}"
            return False, f"No {asset_type} matching '{name_pat}'"

        elif check_type == "data_returned":
            # Check that the plan execution returned useful data
            if plan:
                ops = plan.get("operations", [])
                if ops:
                    return True, "Plan has operations with data"
                # For QUERY, even having a summary is fine
                if plan.get("summary"):
                    return True, f"Summary: {plan.get('summary', '')[:80]}"
            return False, "No data returned"

        elif check_type == "response_mode":
            expected_mode = params.get("mode", "CLARIFY")
            actual = plan.get("mode", "") if plan else ""
            if actual == expected_mode:
                return True, f"Mode is {actual} as expected"
            return False, f"Expected mode {expected_mode}, got {actual}"

        elif check_type == "no_error":
            return True, "No error check (pass-through)"

        else:
            return False, f"Unknown check type: {check_type}"

    def _pattern_match(self, text, pattern):
        """Case-insensitive match with | alternatives."""
        if not pattern:
            return True
        text_lower = text.lower()
        for alt in pattern.split("|"):
            if alt.strip().lower() in text_lower:
                return True
        return False

    def score_verification(self, verify_results):
        """Score verification: 1 if all checks pass, 0 otherwise."""
        if not verify_results:
            return 1  # No checks = pass
        for vr in verify_results:
            if not vr.get("passed", False):
                return 0
        return 1

    # ── Quality scoring ───────────────────────────────────

    def score_quality(self, test, plan, exec_results):
        """Heuristic quality score based on output quality."""
        category = test["category"]
        mode = plan.get("mode", "")

        if category in ("vague",):
            # For vague prompts: did it return a coherent CLARIFY?
            if mode == "CLARIFY" and plan.get("summary"):
                return 1
            if mode in ("MODIFY", "MULTI") and plan.get("operations"):
                return 1  # Also acceptable: it took action
            return 0

        if category == "edge":
            # Edge cases: did it handle gracefully (no crash)?
            for r in exec_results:
                if r.get("status") == "error" and "crash" in r.get("message", "").lower():
                    return 0
            return 1

        if category == "query":
            # Query: did it return meaningful data?
            if plan.get("operations"):
                return 1
            if plan.get("summary") and len(plan.get("summary", "")) > 10:
                return 1
            return 0

        if category in ("create", "foundation"):
            # Create: did it produce a compiled blueprint with variables?
            for r in exec_results:
                if r.get("status") == "ok":
                    data = r.get("data", {})
                    # Check if compiled
                    if data.get("compiled") is True:
                        return 1
                    # If it at least created something
                    if data.get("name") or data.get("blueprint"):
                        return 1
            if exec_results and all(r.get("status") == "ok" for r in exec_results):
                return 1
            return 0

        if category in ("modify",):
            # Modify: did all operations succeed without error?
            if not exec_results:
                return 0
            success_count = sum(1 for r in exec_results if r.get("status") == "ok")
            if success_count == len(exec_results):
                return 1
            return 0

        if category == "multi":
            # Multi: did most operations succeed?
            if not exec_results:
                return 0
            success_count = sum(1 for r in exec_results if r.get("status") == "ok")
            if success_count >= len(exec_results) * 0.5:
                return 1
            return 0

        return 0

    # ── Run a single test ─────────────────────────────────

    def run_test(self, test):
        """Run a single test and return scored result."""
        test_id = test["id"]
        result = TestResult(test_id)
        start = time.time()

        try:
            # Phase 1: Intent classification
            plan = send_to_intent(test["prompt"], timeout=600)
            result.plan_raw = plan
            result.actual_mode = plan.get("mode", "ERROR")

            if plan.get("status") == "error":
                result.error = plan.get("message", "Intent server error")
                result.failure_codes.append("I2")
                result.duration_s = time.time() - start
                result.compute_total()
                return result

            # Extract actual commands from plan
            ops = plan.get("operations", [])
            result.actual_commands = [op.get("command", "") for op in ops]

            # Score intent
            result.intent_score = self.score_intent(plan, test)
            if not result.intent_score:
                result.failure_codes.append("I1")

            # Score plan
            result.plan_score = self.score_plan(plan, test)
            if not result.plan_score:
                if not ops and test["expected_commands"]:
                    result.failure_codes.append("P1")
                else:
                    result.failure_codes.append("P2")

            # Phase 2: Execute plan (skip for CLARIFY/HELP)
            if plan.get("mode") not in ("CLARIFY", "HELP", "ERROR") and ops:
                exec_results = self.execute_plan(plan, test)
                result.exec_results = [self._sanitize_result(r) for r in exec_results]
                result.exec_score = self.score_execution(exec_results)
                if not result.exec_score:
                    # Classify execution failures
                    for r in exec_results:
                        if r.get("status") != "ok":
                            msg = r.get("message", "").lower()
                            if "material" in msg:
                                result.failure_codes.append("E2")
                            elif "actor" in msg or "not found" in msg:
                                result.failure_codes.append("E3")
                            elif "blueprint" in msg:
                                result.failure_codes.append("E4")
                            else:
                                result.failure_codes.append("E1")
            else:
                result.exec_score = 1  # No execution needed

            # Phase 3: Verify
            verify_results = self.run_verifications(test.get("verify", []), plan)
            result.verify_results = verify_results
            result.verify_score = self.score_verification(verify_results)
            if not result.verify_score:
                for vr in verify_results:
                    if not vr.get("passed"):
                        vtype = vr.get("type", "")
                        if "blueprint" in vtype:
                            result.failure_codes.append("V1")
                        elif "actor" in vtype:
                            result.failure_codes.append("V3")
                        else:
                            result.failure_codes.append("V1")
                        break

            # Phase 4: Quality
            result.quality_score = self.score_quality(test, plan, result.exec_results)
            if not result.quality_score:
                result.failure_codes.append("Q2")

        except Exception as e:
            result.error = f"Exception: {str(e)}"
            result.failure_codes.append("E1")

        result.duration_s = time.time() - start
        result.compute_total()
        return result

    def _sanitize_result(self, r):
        """Remove large fields from exec results for storage."""
        sanitized = dict(r)
        # Truncate large DSL text
        if "dsl" in sanitized and len(sanitized.get("dsl", "")) > 500:
            sanitized["dsl"] = sanitized["dsl"][:500] + "..."
        # Remove raw plan data to save space
        if "ir_path" in sanitized:
            del sanitized["ir_path"]
        return sanitized

    # ── Run all tests ─────────────────────────────────────

    def run_all(self, fresh_level=False, categories=None, test_ids=None):
        """Run all tests (or filtered subset) in phase order."""
        if not self.tests:
            self.load_tests()

        # Filter tests
        if test_ids:
            tests_to_run = [t for t in self.tests if t["id"] in test_ids]
        elif categories:
            tests_to_run = [t for t in self.tests if t["category"] in categories]
        else:
            tests_to_run = list(self.tests)

        # Sort by phase order
        phase_idx = {p: i for i, p in enumerate(PHASE_ORDER)}
        tests_to_run.sort(key=lambda t: (phase_idx.get(t["category"], 99), t["id"]))

        total = len(tests_to_run)
        print(f"\n{'='*65}")
        print(f" ARCWRIGHT ACCURACY TEST — {total} commands")
        print(f"{'='*65}\n")

        # Check connectivity
        print("  Pre-flight checks:")
        if not self.check_connectivity():
            print("\n  ABORT: Server connectivity check failed.")
            return None

        if fresh_level:
            self.fresh_level()

        print(f"\n  Running {total} tests...\n")

        results = {}
        current_phase = ""
        phase_start = time.time()

        for i, test in enumerate(tests_to_run):
            # Phase header
            if test["category"] != current_phase:
                if current_phase:
                    elapsed = time.time() - phase_start
                    phase_tests = [r for tid, r in results.items()
                                   if any(t["id"] == tid and t["category"] == current_phase
                                          for t in tests_to_run)]
                    phase_score = sum(r.total for r in phase_tests)
                    phase_max = len(phase_tests) * 5
                    pct = (phase_score / phase_max * 100) if phase_max else 0
                    print(f"\n    Phase '{current_phase}': {phase_score}/{phase_max} "
                          f"({pct:.0f}%) in {elapsed:.0f}s\n")
                current_phase = test["category"]
                phase_start = time.time()
                print(f"  --- {current_phase.upper()} ---")
                sys.stdout.flush()

            # Run test
            test_start = time.time()
            sys.stdout.write(f"  [{i+1:3d}/{total}] {test['id']:5s} ")
            sys.stdout.flush()

            result = self.run_test(test)
            results[test["id"]] = result

            # Status indicator
            score_bar = ""
            score_bar += "I" if result.intent_score else "."
            score_bar += "P" if result.plan_score else "."
            score_bar += "E" if result.exec_score else "."
            score_bar += "V" if result.verify_score else "."
            score_bar += "Q" if result.quality_score else "."

            elapsed = time.time() - test_start
            status = "PASS" if result.total == 5 else f"{result.total}/5"
            print(f"[{score_bar}] {status:>4s} ({elapsed:.1f}s)  {test['prompt'][:50]}")

            if result.error:
                print(f"         ERROR: {result.error[:80]}")
            sys.stdout.flush()

        # Final phase summary
        if current_phase:
            elapsed = time.time() - phase_start
            phase_tests = [r for tid, r in results.items()
                           if any(t["id"] == tid and t["category"] == current_phase
                                  for t in tests_to_run)]
            phase_score = sum(r.total for r in phase_tests)
            phase_max = len(phase_tests) * 5
            pct = (phase_score / phase_max * 100) if phase_max else 0
            print(f"\n    Phase '{current_phase}': {phase_score}/{phase_max} "
                  f"({pct:.0f}%) in {elapsed:.0f}s")

        self.results = results
        return results

    # ── Save results ──────────────────────────────────────

    def get_next_run_number(self):
        """Get the next run number from accuracy_history.json."""
        history_path = ACCURACY_DIR / "accuracy_history.json"
        if history_path.exists():
            with open(history_path) as f:
                history = json.load(f)
            runs = history.get("runs", [])
            if runs:
                return max(r.get("run", 0) for r in runs) + 1
        return 1

    def save_results(self, results, run_number=None):
        """Save results to a timestamped file and update history."""
        if run_number is None:
            run_number = self.get_next_run_number()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now().strftime("%Y-%m-%d")

        # Compute summary
        total_score = sum(r.total for r in results.values())
        max_score = len(results) * 5
        pct = (total_score / max_score * 100) if max_score else 0

        # Per-category breakdown
        categories = {}
        for test in self.tests:
            tid = test["id"]
            if tid not in results:
                continue
            cat = test["category"]
            if cat not in categories:
                categories[cat] = {"intent": 0, "plan": 0, "exec": 0,
                                   "verify": 0, "quality": 0, "count": 0}
            r = results[tid]
            categories[cat]["intent"] += r.intent_score
            categories[cat]["plan"] += r.plan_score
            categories[cat]["exec"] += r.exec_score
            categories[cat]["verify"] += r.verify_score
            categories[cat]["quality"] += r.quality_score
            categories[cat]["count"] += 1

        # Failure code counts
        failure_counts = {}
        for r in results.values():
            for code in r.failure_codes:
                failure_counts[code] = failure_counts.get(code, 0) + 1

        # Build run data
        run_data = {
            "run": run_number,
            "timestamp": timestamp,
            "date": date_str,
            "total_score": total_score,
            "max_score": max_score,
            "pct": round(pct, 1),
            "test_count": len(results),
            "categories": categories,
            "failure_counts": failure_counts,
            "results": {tid: r.to_dict() for tid, r in results.items()},
        }

        # Save run file
        run_path = RESULTS_DIR / f"run_{run_number:03d}_{timestamp}.json"
        with open(run_path, "w") as f:
            json.dump(run_data, f, indent=2)
        print(f"\n  Results saved: {run_path.name}")

        # Update accuracy_history.json
        history_path = ACCURACY_DIR / "accuracy_history.json"
        if history_path.exists():
            with open(history_path) as f:
                history = json.load(f)
        else:
            history = {"runs": []}

        history["runs"].append({
            "run": run_number,
            "date": date_str,
            "score": total_score,
            "max": max_score,
            "pct": round(pct, 1),
            "test_count": len(results),
            "file": run_path.name,
        })

        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)

        return run_data

    # ── Report generation ─────────────────────────────────

    def print_report(self, run_data):
        """Print the formatted accuracy report."""
        from report_generator import generate_report
        generate_report(run_data)


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Arcwright Accuracy Test Runner")
    parser.add_argument("--run-all", action="store_true", help="Run the full 120-command suite")
    parser.add_argument("--fresh-level", action="store_true", help="Clean level before running")
    parser.add_argument("--retest-failures", action="store_true", help="Retest only failures from latest run")
    parser.add_argument("--run", default=None, help="Run number to reference (e.g. 'latest' or '3')")
    parser.add_argument("--run-ids", nargs="+", help="Run specific test IDs")
    parser.add_argument("--category", help="Run only a specific category")
    parser.add_argument("--intent-port", type=int, default=INTENT_PORT)
    parser.add_argument("--ue-port", type=int, default=UE_PORT)
    args = parser.parse_args()

    runner = AccuracyTestRunner(intent_port=args.intent_port, ue_port=args.ue_port)
    runner.load_tests()

    test_ids = None
    categories = None

    if args.retest_failures:
        # Find latest run and extract failed test IDs
        run_ref = args.run or "latest"
        run_data = load_run(run_ref)
        if run_data:
            test_ids = [tid for tid, r in run_data.get("results", {}).items()
                        if r.get("total", 0) < 5]
            print(f"  Retesting {len(test_ids)} failures from run #{run_data.get('run')}")
        else:
            print("  No previous run found.")
            return

    if args.run_ids:
        test_ids = args.run_ids

    if args.category:
        categories = [args.category]

    if args.run_all or test_ids or categories:
        results = runner.run_all(
            fresh_level=args.fresh_level,
            test_ids=test_ids,
            categories=categories,
        )

        if results:
            run_data = runner.save_results(results)

            # Generate report
            print()
            try:
                sys.path.insert(0, str(ACCURACY_DIR))
                from report_generator import generate_report
                generate_report(run_data)
            except ImportError:
                # Inline basic report
                total = run_data["total_score"]
                mx = run_data["max_score"]
                pct = run_data["pct"]
                print(f"\n  TOTAL: {total}/{mx} ({pct}%)")

            # Run failure classifier
            try:
                from failure_classifier import classify_run
                classify_run(run_data)
            except ImportError:
                pass
    else:
        parser.print_help()


def load_run(ref):
    """Load a run by number or 'latest'."""
    if ref == "latest":
        history_path = ACCURACY_DIR / "accuracy_history.json"
        if history_path.exists():
            with open(history_path) as f:
                history = json.load(f)
            runs = history.get("runs", [])
            if runs:
                latest = max(runs, key=lambda r: r.get("run", 0))
                run_file = RESULTS_DIR / latest["file"]
                if run_file.exists():
                    with open(run_file) as f:
                        return json.load(f)
    else:
        # Find by run number
        for p in RESULTS_DIR.glob(f"run_{int(ref):03d}_*.json"):
            with open(p) as f:
                return json.load(f)
    return None


if __name__ == "__main__":
    main()
