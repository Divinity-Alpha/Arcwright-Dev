"""
Arcwright User Simulation Test Runner

Simulates a real user typing into the Arcwright Generator Panel.
All requests go through the intent server, not direct TCP commands.
"""

import socket
import json
import time
import datetime
import os
import sys
import tempfile

# Add project scripts to path for parser imports
PROJECT_ROOT = r"C:\BlueprintLLM"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
# dsl_parser submodules use bare imports (e.g. "from node_map import resolve")
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts", "dsl_parser"))
# NOTE: Do NOT add bt_parser/ or dt_parser/ directly — they're packages under scripts/
# and adding them shadows the package import (e.g. "from bt_parser.bt_parser import parse" breaks)

INTENT_HOST = "127.0.0.1"
INTENT_PORT = 13380
UE_HOST = "127.0.0.1"
UE_PORT = 13377
LOG_FILE = os.path.join(PROJECT_ROOT, "tests", "manual_test_log.txt")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "tests", "results")

# Commands that require DSL generation pipeline (Fix 1)
DSL_COMMANDS = {"create_blueprint": "blueprint", "create_behavior_tree": "bt", "create_data_table": "dt"}

# Commands that need operations[] array (Fix 3)
BATCH_COMMANDS = {"batch_set_variable", "batch_add_component", "batch_apply_material",
                  "batch_set_property", "batch_delete_actors"}

class UserSimulator:
    """Simulates a user interacting with the Arcwright Generator Panel."""

    def __init__(self):
        self.log_lines = []
        self.test_results = []
        os.makedirs(RESULTS_DIR, exist_ok=True)

    def log(self, msg):
        """Log for manual replay."""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        try:
            print(f"  {line}")
        except UnicodeEncodeError:
            print(f"  {line.encode('ascii', errors='replace').decode()}")

    def send_to_intent(self, prompt):
        """Send a plain English prompt to the intent server.
        This is exactly what the Generator Panel does."""
        self.log(f'USER TYPES: "{prompt}"')

        # The intent server expects newline-delimited JSON
        request = json.dumps({"prompt": prompt}) + "\n"

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(300)  # LLM inference: 20-90s classify + 60-120s refine
            sock.connect((INTENT_HOST, INTENT_PORT))
            sock.sendall(request.encode('utf-8'))

            # Read response until connection closes
            response = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    # Check if we got a complete JSON (newline-terminated)
                    if b'\n' in response:
                        break
                except socket.timeout:
                    break
            sock.close()

            # Parse first complete JSON line
            resp_text = response.decode('utf-8').strip()
            if not resp_text:
                self.log("INTENT ERROR: Empty response")
                return {"mode": "ERROR", "error": "Empty response", "operations": []}

            plan = json.loads(resp_text)
            self.log(f"INTENT RETURNS: mode={plan.get('mode', '?')}, "
                    f"ops={len(plan.get('operations', []))}, "
                    f"summary={plan.get('summary', '?')[:80]}")
            return plan

        except Exception as e:
            self.log(f"INTENT ERROR: {e}")
            return {"mode": "ERROR", "error": str(e), "operations": []}

    def send_to_ue(self, command, params=None):
        """Send a TCP command to UE. Used for BOTH execution and verification.
        Protocol: {"command": "...", "params": {...}}\n"""
        if params is None:
            params = {}

        # UE command server expects: {"command": "name", "params": {"key": "val", ...}}
        request = {"command": command, "params": params}
        payload = json.dumps(request) + "\n"

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((UE_HOST, UE_PORT))
            sock.sendall(payload.encode('utf-8'))

            response = b""
            while True:
                try:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    response += chunk
                    if b'\n' in response:
                        break
                except socket.timeout:
                    break
            sock.close()

            resp_text = response.decode('utf-8').strip()
            if not resp_text:
                return {"status": "error", "message": "Empty response"}

            result = json.loads(resp_text)
            # Normalize: UE returns {"status": "ok/error", "data": {...}}
            # or {"status": "error", "message": "..."}
            success = result.get("status") == "ok"
            return {"success": success, **result}
        except Exception as e:
            return {"success": False, "status": "error", "message": str(e)}

    # ── Fix 1: DSL Generation Pipeline ───────────────────────

    def generate_dsl(self, domain, prompt):
        """Call intent server's generate_dsl endpoint to create DSL from natural language."""
        request = json.dumps({
            "command": "generate_dsl",
            "domain": domain,
            "prompt": prompt,
        }) + "\n"

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(300)  # DSL generation can take 2-5 min for 70B
            sock.connect((INTENT_HOST, INTENT_PORT))
            sock.sendall(request.encode("utf-8"))

            response = b""
            while True:
                try:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    response += chunk
                    if b"\n" in response:
                        break
                except socket.timeout:
                    break
            sock.close()

            resp_text = response.decode("utf-8").strip()
            if not resp_text:
                self.log("DSL GENERATE: Empty response from intent server")
                return None

            result = json.loads(resp_text)
            if result.get("status") == "ok":
                dsl = result.get("dsl", "")
                self.log(f"DSL GENERATE: Got {len(dsl)} chars of {domain} DSL")
                return dsl
            else:
                self.log(f"DSL GENERATE: Error - {result.get('message', 'unknown')}")
                return None
        except Exception as e:
            self.log(f"DSL GENERATE: Exception - {e}")
            return None

    def parse_dsl_to_ir(self, domain, dsl_text):
        """Parse DSL text to IR JSON using the appropriate domain parser."""
        try:
            if domain == "blueprint":
                from dsl_parser.parser import parse as bp_parse
                result = bp_parse(dsl_text)
            elif domain == "bt":
                from bt_parser.bt_parser import parse as bt_parse
                result = bt_parse(dsl_text)
            elif domain == "dt":
                from dt_parser.dt_parser import parse as dt_parse
                result = dt_parse(dsl_text)
            else:
                self.log(f"PARSE: Unknown domain '{domain}'")
                return None

            ir = result.get("ir")
            errors = result.get("errors", [])
            if errors:
                self.log(f"PARSE: {len(errors)} errors: {errors[:3]}")
            if ir:
                self.log(f"PARSE: IR generated for {domain}")
            return ir
        except Exception as e:
            self.log(f"PARSE: Exception - {e}")
            return None

    def execute_dsl_create(self, domain, prompt):
        """Full CREATE pipeline: generate DSL → parse to IR → send to UE."""
        # Step 1: Generate DSL via LoRA model
        dsl = self.generate_dsl(domain, prompt)
        if not dsl:
            return {"success": False, "status": "error", "message": "DSL generation failed"}

        # Step 2: Parse DSL to IR
        ir = self.parse_dsl_to_ir(domain, dsl)
        if not ir:
            return {"success": False, "status": "error", "message": "DSL parsing failed"}

        # Step 3: Send IR to UE
        if domain == "blueprint":
            # Blueprint uses import_from_ir with a temp file
            ir_dir = os.path.join(PROJECT_ROOT, "test_ir")
            os.makedirs(ir_dir, exist_ok=True)
            bp_name = ir.get("metadata", {}).get("name", "BP_Generated")
            ir_path = os.path.join(ir_dir, f"{bp_name}.blueprint.json")
            with open(ir_path, "w", encoding="utf-8") as f:
                json.dump(ir, f, indent=2)
            self.log(f"IMPORT: Saved IR to {ir_path}")
            return self.send_to_ue("import_from_ir", {"path": ir_path.replace("\\", "/")})
        elif domain == "bt":
            ir_json = json.dumps(ir)
            return self.send_to_ue("create_behavior_tree", {"ir_json": ir_json})
        elif domain == "dt":
            ir_json = json.dumps(ir)
            return self.send_to_ue("create_data_table", {"ir_json": ir_json})
        else:
            return {"success": False, "status": "error", "message": f"Unknown domain: {domain}"}

    # ── Fix 3: Parameter Schema Validation ────────────────

    def reshape_batch_params(self, cmd, params, prior_results):
        """Reshape flat params into the operations[] format batch commands expect."""
        # Extract actors/blueprints from prior find_* results
        found_actors = []
        found_blueprints = []
        for pr in prior_results:
            data = pr.get("result", {}).get("data", {})
            if "actors" in data:
                found_actors = [a.get("label", "") for a in data["actors"]
                               if a.get("class", "") not in ("WorldDataLayers", "WorldPartitionMiniMap")]
            if "blueprints" in data:
                found_blueprints = [b.get("name", "") for b in data["blueprints"]]

        if cmd == "batch_set_variable":
            # Flat: {variable_name, default_value} → {operations: [{blueprint, variable_name, default_value}]}
            var_name = params.get("variable_name", params.get("variable", ""))
            value = params.get("default_value", params.get("value", ""))
            if found_blueprints and var_name:
                ops = [{"blueprint": bp, "variable_name": var_name, "default_value": str(value)}
                       for bp in found_blueprints]
                return {"operations": ops}

        elif cmd == "batch_add_component":
            # Flat: {component_name/type, properties} → {operations: [{blueprint, component_type, ...}]}
            comp_type = params.get("component_type", params.get("component_name", "PointLight"))
            props = params.get("properties", {})
            if found_blueprints:
                ops = [{"blueprint": bp, "component_type": comp_type,
                        "component_name": f"{comp_type}_{i}", "properties": props}
                       for i, bp in enumerate(found_blueprints)]
                return {"operations": ops}

        elif cmd == "batch_apply_material":
            # Flat: {material_name/path} → {operations: [{actor_label, material_path}]}
            mat = params.get("material_path", params.get("material_name", ""))
            if not mat.startswith("/Game/"):
                mat = f"/Game/Arcwright/Materials/{mat}"
            if found_actors:
                ops = [{"actor_label": actor, "material_path": mat} for actor in found_actors[:50]]
                return {"operations": ops}

        elif cmd == "batch_set_property":
            # Flat: {property_name, value} → {operations: [{actor_label, property, value}]}
            prop = params.get("property", params.get("property_name", ""))
            value = params.get("value", "")
            if found_actors and prop:
                ops = [{"actor_label": actor, "property": prop, "value": value}
                       for actor in found_actors[:50]]
                return {"operations": ops}

        elif cmd == "batch_delete_actors":
            # Empty params → {labels: [...]} from prior find results
            if not params.get("labels") and found_actors:
                return {"labels": found_actors[:100]}

        elif cmd == "rename_asset":
            # Fix param names: asset_name → old_name
            if "asset_name" in params and "old_name" not in params:
                params["old_name"] = params.pop("asset_name")
            if "new_name" not in params and "name" in params:
                params["new_name"] = params.pop("name")
            return params

        elif cmd == "batch_replace_material":
            # Fix param names
            if "old_material" not in params:
                params["old_material"] = params.get("material_filter", params.get("old", ""))
            if "new_material" not in params:
                params["new_material"] = params.get("new", params.get("replacement", ""))
            return params

        return params  # Return as-is if no reshape needed

    # ── Execute Plan (with Fix 1 + Fix 3 translation) ──────

    def execute_plan(self, plan):
        """Execute a plan from the intent server against UE.
        Translates high-level commands into actual executable sequences."""
        results = []
        prior_results = []  # Track results from prior steps for dependency resolution

        for op in plan.get("operations", []):
            cmd = op.get("command", "")
            params = op.get("params", {})

            # Fix 1: Command translation for CREATE commands
            if cmd in DSL_COMMANDS:
                domain = DSL_COMMANDS[cmd]
                prompt = params.get("prompt", params.get("description", ""))
                self.log(f"EXECUTE: {cmd} → DSL pipeline ({domain}): \"{prompt[:80]}\"")

                result = self.execute_dsl_create(domain, prompt)
                success = result.get("success", False)

                result_str = json.dumps(result)
                if len(result_str) > 150:
                    result_str = result_str[:150] + "..."
                self.log(f"RESULT: {'OK' if success else 'FAIL'} -- {result_str}")
                results.append({"command": cmd, "success": success, "result": result})
                prior_results.append({"command": cmd, "success": success, "result": result})
                continue

            # Fix 3: Reshape batch command params
            if cmd in BATCH_COMMANDS or cmd in ("rename_asset", "batch_replace_material"):
                params = self.reshape_batch_params(cmd, params, prior_results)

            param_str = json.dumps(params)
            if len(param_str) > 150:
                param_str = param_str[:150] + "..."
            self.log(f"EXECUTE: {cmd} {param_str}")

            result = self.send_to_ue(cmd, params)
            success = result.get("success", False)

            result_str = json.dumps(result)
            if len(result_str) > 150:
                result_str = result_str[:150] + "..."
            self.log(f"RESULT: {'OK' if success else 'FAIL'} -- {result_str}")
            results.append({"command": cmd, "success": success, "result": result})
            prior_results.append({"command": cmd, "success": success, "result": result})

        return results

    def verify_state(self, checks):
        """Verify the UE state after a test by running query commands."""
        verifications = []

        for check in checks:
            check_type = check["type"]

            if check_type == "blueprint_exists":
                result = self.send_to_ue("get_blueprint_info", {"name": check["name"]})
                passed = result.get("success", False)
                verifications.append({"check": f"BP '{check['name']}' exists", "passed": passed})

            elif check_type == "actor_exists":
                result = self.send_to_ue("find_actors", {
                    "name_filter": check.get("pattern", check.get("class", ""))
                })
                data = result.get("data", {})
                actors = data.get("actors", [])
                passed = len(actors) > 0
                verifications.append({
                    "check": f"Actor matching '{check.get('pattern', check.get('class', ''))}' exists",
                    "passed": passed,
                    "found": len(actors)
                })

            elif check_type == "actor_count":
                result = self.send_to_ue("find_actors", {
                    "name_filter": check.get("pattern", check.get("class", ""))
                })
                data = result.get("data", {})
                actors = data.get("actors", [])
                expected = check["count"]
                passed = len(actors) == expected
                verifications.append({
                    "check": f"Actor count = {expected}",
                    "passed": passed,
                    "found": len(actors)
                })

            elif check_type == "actor_not_exists":
                result = self.send_to_ue("find_actors", {
                    "name_filter": check.get("pattern", check.get("class", ""))
                })
                data = result.get("data", {})
                actors = data.get("actors", [])
                passed = len(actors) == 0
                verifications.append({
                    "check": f"No actors matching '{check.get('pattern', check.get('class', ''))}'",
                    "passed": passed,
                    "found": len(actors)
                })

            elif check_type == "variable_value":
                result = self.send_to_ue("get_blueprint_info", {"name": check["blueprint"]})
                data = result.get("data", {})
                variables = data.get("variables", [])
                found_var = None
                for v in variables:
                    if v.get("name", "").lower() == check["variable"].lower():
                        found_var = v
                        break
                if found_var:
                    passed = str(found_var.get("default", "")) == str(check["expected"])
                    verifications.append({
                        "check": f"{check['blueprint']}.{check['variable']} == {check['expected']}",
                        "passed": passed,
                        "actual": found_var.get("default", "?")
                    })
                else:
                    verifications.append({
                        "check": f"{check['blueprint']}.{check['variable']} exists",
                        "passed": False,
                        "actual": "NOT FOUND"
                    })

            elif check_type == "material_applied":
                result = self.send_to_ue("find_actors", {
                    "name_filter": check.get("actor_pattern", "")
                })
                passed = result.get("success", False)
                verifications.append({
                    "check": f"Material on '{check.get('actor_pattern', '')}'",
                    "passed": passed
                })

            elif check_type == "level_has_actors":
                result = self.send_to_ue("get_level_info", {})
                data = result.get("data", {})
                count = data.get("actor_count", 0)
                passed = count > 0
                verifications.append({"check": "Level has actors", "passed": passed, "count": count})

        return verifications

    def run_test(self, test):
        """Run a single user simulation test."""
        test_id = test["id"]
        prompt = test["prompt"]
        expected_mode = test["expected_mode"]
        checks = test.get("verify", [])

        self.log(f"\n{'='*60}")
        self.log(f"TEST {test_id}: {test.get('name', '')}")
        self.log(f"{'='*60}")

        # Phase 1: Send to intent server
        plan = self.send_to_intent(prompt)

        mode = plan.get("mode", "ERROR")
        ops = plan.get("operations", [])

        # Score: Intent correct?
        expected_modes = expected_mode if isinstance(expected_mode, list) else [expected_mode]
        intent_ok = mode.upper() in [m.upper() for m in expected_modes]

        # Score: Plan has operations?
        plan_ok = len(ops) > 0 or mode in ["CLARIFY", "HELP"]

        # Phase 2: Execute plan (if not CLARIFY/ERROR)
        exec_results = []
        exec_ok = False
        if mode not in ["CLARIFY", "HELP", "ERROR"] and len(ops) > 0:
            exec_results = self.execute_plan(plan)
            exec_ok = all(r["success"] for r in exec_results) if exec_results else False
        elif mode in ["CLARIFY", "HELP"]:
            exec_ok = True  # Clarify doesn't execute, that's correct

        # Phase 3: Verify state
        verify_results = []
        verify_ok = True
        if checks and exec_ok:
            time.sleep(1)  # Give UE a moment to process
            verify_results = self.verify_state(checks)
            verify_ok = all(v["passed"] for v in verify_results) if verify_results else True
        elif checks and not exec_ok:
            # Execution failed, so verification also fails
            verify_ok = False

        # Calculate score
        score = 0
        if intent_ok: score += 1
        if plan_ok: score += 1
        if exec_ok: score += 1
        if verify_ok: score += 1

        result = {
            "test_id": test_id,
            "name": test.get("name", ""),
            "prompt": prompt,
            "expected_mode": expected_mode,
            "actual_mode": mode,
            "intent_ok": intent_ok,
            "plan_ok": plan_ok,
            "plan_ops": len(ops),
            "exec_ok": exec_ok,
            "exec_results": exec_results,
            "verify_ok": verify_ok,
            "verify_results": verify_results,
            "score": score,
            "max_score": 4,
        }

        self.test_results.append(result)

        status = "PASS" if score == 4 else "WARN" if score >= 2 else "FAIL"
        self.log(f"SCORE: {score}/4 {status} (intent={intent_ok}, plan={plan_ok}, exec={exec_ok}, verify={verify_ok})")

        return result

    def save_results(self):
        """Save all results to files."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed JSON
        results_file = os.path.join(RESULTS_DIR, f"user_sim_{ts}.json")
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": ts,
                "total_tests": len(self.test_results),
                "total_score": sum(r["score"] for r in self.test_results),
                "max_score": sum(r["max_score"] for r in self.test_results),
                "results": self.test_results,
            }, f, indent=2)

        # Save manual replay log
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("# Arcwright Manual Test Log\n")
            f.write(f"# Generated: {ts}\n")
            f.write(f"# Replay these prompts in the Arcwright Generator Panel\n\n")
            for line in self.log_lines:
                f.write(line + "\n")

        print(f"\n  Results: {results_file}")
        print(f"  Manual log: {LOG_FILE}")


# ===================================================================
# TEST DEFINITIONS
# ===================================================================

SETUP_TESTS = [
    # These run first to create a known state
    {
        "id": "S.01",
        "name": "Setup: Create enemy blueprint",
        "prompt": "Create an enemy with 100 health, 15 damage, and 300 speed",
        "expected_mode": "CREATE",
        "verify": [{"type": "blueprint_exists", "name": "BP_Enemy"}]
    },
    {
        "id": "S.02",
        "name": "Setup: Create health pickup",
        "prompt": "Create a health pickup that heals 25 HP when touched and destroys itself",
        "expected_mode": "CREATE",
        "verify": [{"type": "blueprint_exists", "name": "BP_HealthPickup"}]
    },
    {
        "id": "S.03",
        "name": "Setup: Create coin",
        "prompt": "Create a gold coin pickup worth 10 points that destroys on collection",
        "expected_mode": "CREATE",
        "verify": [{"type": "blueprint_exists", "name": "BP_GoldCoin"}]
    },
    {
        "id": "S.04",
        "name": "Setup: Create torch",
        "prompt": "Create a torch with a point light intensity of 5000",
        "expected_mode": "CREATE",
        "verify": [{"type": "blueprint_exists", "name": "BP_Torch"}]
    },
    {
        "id": "S.05",
        "name": "Setup: Add lighting",
        "prompt": "Set up dark indoor lighting for the level",
        "expected_mode": "CREATE",
        "verify": [{"type": "level_has_actors"}]
    },
    {
        "id": "S.06",
        "name": "Setup: Spawn enemies",
        "prompt": "Spawn 3 enemies in the level",
        "expected_mode": ["CREATE", "MULTI"],
        "verify": [{"type": "actor_exists", "pattern": "nemy"}]
    },
    {
        "id": "S.07",
        "name": "Setup: Spawn coins",
        "prompt": "Place 5 gold coins around the level",
        "expected_mode": ["CREATE", "MULTI"],
        "verify": [{"type": "actor_exists", "pattern": "oin"}]
    },
    {
        "id": "S.08",
        "name": "Setup: Spawn torches",
        "prompt": "Put 4 torches in the level",
        "expected_mode": ["CREATE", "MULTI"],
        "verify": [{"type": "actor_exists", "pattern": "orch"}]
    },
]

CREATE_TESTS = [
    {
        "id": "C.01",
        "name": "Create simple pickup",
        "prompt": "Create a key pickup that sets HasKey to true when collected",
        "expected_mode": "CREATE",
        "verify": [{"type": "blueprint_exists", "name": "BP_KeyPickup"}]
    },
    {
        "id": "C.02",
        "name": "Create door with logic",
        "prompt": "Make a door that checks if the player has a key before opening",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.03",
        "name": "Create timer-based hazard",
        "prompt": "Build a damage zone that hurts the player 10 HP per second while they stand on it",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.04",
        "name": "Create score manager",
        "prompt": "I need a score manager that tracks points and prints New High Score when the record is beaten",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.05",
        "name": "Create wave spawner",
        "prompt": "Create a wave spawner that sends enemies every 15 seconds with increasing counts",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.06",
        "name": "Create behavior tree",
        "prompt": "Make a patrol AI that walks between two points and chases the player when spotted",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.07",
        "name": "Create data table",
        "prompt": "I need a weapons table with name, damage, fire rate, and ammo count",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.08",
        "name": "Create with casual language",
        "prompt": "Can you make me a treasure chest that gives random gold between 10 and 50",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.09",
        "name": "Create checkpoint",
        "prompt": "I want a checkpoint that saves the player position when they touch it",
        "expected_mode": "CREATE",
        "verify": []
    },
    {
        "id": "C.10",
        "name": "Create spinning actor",
        "prompt": "Make something that spins on its Z axis",
        "expected_mode": "CREATE",
        "verify": []
    },
]

MODIFY_TESTS = [
    {
        "id": "M.01",
        "name": "Change enemy health",
        "prompt": "Set health to 200 on all enemies",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.02",
        "name": "Make enemies faster",
        "prompt": "Make the enemies faster",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.03",
        "name": "Change coin value",
        "prompt": "Gold coins should be worth 50 each",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.04",
        "name": "Scale enemies up",
        "prompt": "Scale all enemies up by 1.5",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.05",
        "name": "Delete coins",
        "prompt": "Delete all the gold coins",
        "expected_mode": "MODIFY",
        "verify": [{"type": "actor_not_exists", "pattern": "oin"}]
    },
    {
        "id": "M.06",
        "name": "Hide torches",
        "prompt": "Hide all the torches",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.07",
        "name": "Change material with exact name",
        "prompt": "Change the material on all enemies to MI_Stone",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.08",
        "name": "Change material with fuzzy name",
        "prompt": "Make the torches look like gold",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.09",
        "name": "Multiple variable changes",
        "prompt": "All enemies need 500 HP and 40 damage",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.10",
        "name": "Add component to all",
        "prompt": "Add a point light to every torch",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.11",
        "name": "Rename blueprint",
        "prompt": "Rename BP_GoldCoin to BP_TreasureCoin",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.12",
        "name": "Conversational modify",
        "prompt": "The enemies are too weak, buff them",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.13",
        "name": "Replace material globally",
        "prompt": "Replace every stone material with brick",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.14",
        "name": "Move actors",
        "prompt": "Move all coins up by 50 units",
        "expected_mode": "MODIFY",
        "verify": []
    },
    {
        "id": "M.15",
        "name": "Remove all of a type",
        "prompt": "Clear out all the torches",
        "expected_mode": "MODIFY",
        "verify": [{"type": "actor_not_exists", "pattern": "orch"}]
    },
]

QUERY_TESTS = [
    {
        "id": "Q.01",
        "name": "Count enemies",
        "prompt": "How many enemies are in the level?",
        "expected_mode": "QUERY",
        "verify": []
    },
    {
        "id": "Q.02",
        "name": "List blueprints",
        "prompt": "Show me all the blueprints in the project",
        "expected_mode": "QUERY",
        "verify": []
    },
    {
        "id": "Q.03",
        "name": "List actors",
        "prompt": "What's in the level right now?",
        "expected_mode": "QUERY",
        "verify": []
    },
    {
        "id": "Q.04",
        "name": "Find specific type",
        "prompt": "Which blueprints have a Health variable?",
        "expected_mode": "QUERY",
        "verify": []
    },
    {
        "id": "Q.05",
        "name": "Count specific actors",
        "prompt": "How many coins did I place?",
        "expected_mode": "QUERY",
        "verify": []
    },
]

MULTI_TESTS = [
    {
        "id": "X.01",
        "name": "Create and spawn",
        "prompt": "Create a health potion and spawn 3 of them in the level",
        "expected_mode": "MULTI",
        "verify": []
    },
    {
        "id": "X.02",
        "name": "Full scene setup",
        "prompt": "Set up FPS controls and add dark lighting to the level",
        "expected_mode": ["MULTI", "CREATE"],
        "verify": []
    },
    {
        "id": "X.03",
        "name": "Delete and replace",
        "prompt": "Delete all coins and replace them with gems worth 100 each",
        "expected_mode": "MULTI",
        "verify": []
    },
    {
        "id": "X.04",
        "name": "Modify multiple properties",
        "prompt": "Make all enemies tougher and change the lighting to outdoor daytime",
        "expected_mode": "MULTI",
        "verify": []
    },
    {
        "id": "X.05",
        "name": "Complex build request",
        "prompt": "Build a boss room with one powerful enemy, health pickups around the edges, and dramatic dark lighting",
        "expected_mode": "MULTI",
        "verify": []
    },
]

CONVERSATIONAL_TESTS = [
    {
        "id": "V.01",
        "name": "Vague complaint",
        "prompt": "The level feels empty",
        "expected_mode": ["MULTI", "CLARIFY"],
        "verify": []
    },
    {
        "id": "V.02",
        "name": "Very vague",
        "prompt": "Make it better",
        "expected_mode": "CLARIFY",
        "verify": []
    },
    {
        "id": "V.03",
        "name": "Aesthetic complaint",
        "prompt": "Everything looks too plain",
        "expected_mode": ["MODIFY", "CLARIFY"],
        "verify": []
    },
    {
        "id": "V.04",
        "name": "Difficulty complaint",
        "prompt": "The game is too easy",
        "expected_mode": ["MODIFY", "CLARIFY"],
        "verify": []
    },
    {
        "id": "V.05",
        "name": "Help request",
        "prompt": "I'm stuck, can you help me set up the level?",
        "expected_mode": ["CLARIFY", "HELP"],
        "verify": []
    },
]

ALL_TESTS = SETUP_TESTS + CREATE_TESTS + MODIFY_TESTS + QUERY_TESTS + MULTI_TESTS + CONVERSATIONAL_TESTS


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", choices=["setup", "create", "modify", "query", "multi", "conversational", "all"], default="all")
    ap.add_argument("--test", help="Run specific test by ID, e.g. M.05")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    test_map = {
        "setup": SETUP_TESTS,
        "create": CREATE_TESTS,
        "modify": MODIFY_TESTS,
        "query": QUERY_TESTS,
        "multi": MULTI_TESTS,
        "conversational": CONVERSATIONAL_TESTS,
        "all": ALL_TESTS,
    }

    if args.test:
        tests = [t for t in ALL_TESTS if t["id"] == args.test]
        if not tests:
            print(f"Test {args.test} not found")
            return
    else:
        tests = test_map[args.category]

    sim = UserSimulator()

    # Verify connections
    print("\n  Checking connections...")
    ue_check = sim.send_to_ue("health_check")
    if not ue_check.get("success"):
        print("  FAIL: UE editor not responding on TCP 13377")
        return
    print("  OK: UE editor connected")

    intent_check = sim.send_to_intent("health check")
    if intent_check.get("mode") == "ERROR":
        print("  FAIL: Intent server not responding on TCP 13380")
        return
    print("  OK: Intent server connected")

    # Run tests
    print(f"\n  Running {len(tests)} user simulation tests...\n")

    for test in tests:
        sim.run_test(test)
        time.sleep(2)  # Give UE time between operations

    # Summary
    print(f"\n{'='*60}")
    print(f"  USER SIMULATION RESULTS")
    print(f"{'='*60}")

    total_score = sum(r["score"] for r in sim.test_results)
    max_score = sum(r["max_score"] for r in sim.test_results)

    # Category breakdown
    categories = {}
    for r in sim.test_results:
        cat = r["test_id"].split(".")[0]
        if cat not in categories:
            categories[cat] = {"tests": 0, "score": 0, "max": 0}
        categories[cat]["tests"] += 1
        categories[cat]["score"] += r["score"]
        categories[cat]["max"] += r["max_score"]

    cat_names = {"S": "Setup", "C": "Create", "M": "Modify", "Q": "Query", "X": "Multi-Step", "V": "Conversational"}

    print(f"\n  {'Category':<18} {'Tests':>6} {'Score':>10} {'Pct':>6}")
    print(f"  {'-'*18} {'-'*6} {'-'*10} {'-'*6}")
    for cat in ["S", "C", "M", "Q", "X", "V"]:
        if cat in categories:
            c = categories[cat]
            pct = c['score'] / c['max'] * 100 if c['max'] > 0 else 0
            name = cat_names.get(cat, cat)
            print(f"  {name:<18} {c['tests']:>6} {c['score']:>4}/{c['max']:<4} {pct:>5.0f}%")

    pct_total = total_score / max_score * 100 if max_score > 0 else 0
    print(f"  {'='*18} {'='*6} {'='*10} {'='*6}")
    print(f"  {'TOTAL':<18} {len(sim.test_results):>6} {total_score:>4}/{max_score:<4} {pct_total:>5.1f}%")

    # Failures
    failures = [r for r in sim.test_results if r["score"] < 3]
    if failures:
        print(f"\n  FAILURES (score < 3):")
        for r in failures:
            print(f"    {r['test_id']}: \"{r['prompt'][:50]}\" -> mode={r['actual_mode']} "
                  f"(intent={'Y' if r['intent_ok'] else 'N'} plan={'Y' if r['plan_ok'] else 'N'} "
                  f"exec={'Y' if r['exec_ok'] else 'N'} verify={'Y' if r['verify_ok'] else 'N'})")

    perfect = sum(1 for r in sim.test_results if r["score"] == 4)
    print(f"\n  Perfect 4/4: {perfect}/{len(sim.test_results)}")
    print(f"  Grade: {'A -- Production Ready' if pct_total >= 95 else 'B -- Minor Fixes' if pct_total >= 85 else 'C -- Significant Gaps' if pct_total >= 70 else 'D -- Major Rework'}")

    sim.save_results()


if __name__ == "__main__":
    main()
