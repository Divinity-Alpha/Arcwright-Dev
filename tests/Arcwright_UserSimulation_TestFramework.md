# Arcwright — User Simulation Test Framework

> **Purpose:** Test the Arcwright plugin exactly as a real user would use it.
> NOT through TCP commands or MCP tools directly.
> ALL requests go through the intent server (port 13380) → plan → execute.
> This catches the gap between "commands work" and "user experience works."

---

## ARCHITECTURE

```
test_user_simulation.py
    │
    ├── Sends plain English to intent server (port 13380)
    │   (exactly like the Generator Panel does)
    │
    ├── Receives plan JSON
    │
    ├── Executes plan against UE (port 13377)
    │   (exactly like the Generator Panel does)
    │
    ├── Verifies results by querying UE state
    │
    └── Scores: intent / plan / execution / verification
```

**Key difference from existing tests:** This does NOT call TCP commands directly.
Everything goes through the intent system first, same as a real user typing in the panel.

---

## SETUP INSTRUCTIONS FOR CLAUDE CODE

### Step 1: Create a fresh UE project for testing

```
Create a new UE5 project:
  Name: ArcwrightTestBed
  Location: C:\Junk\ArcwrightTestBed
  Template: Blank
  
Copy the Arcwright plugin into the project:
  Copy C:\BlueprintLLM\Plugins\ → C:\Junk\ArcwrightTestBed\Plugins\

Build the project:
  & "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" ArcwrightTestBedEditor Win64 Development "C:\Junk\ArcwrightTestBed\ArcwrightTestBed.uproject"

Launch the editor:
  & "C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe" "C:\Junk\ArcwrightTestBed\ArcwrightTestBed.uproject" -skipcompile -nosplash -unattended -nopause

Kill crash reporter in background loop:
  powershell -Command "while ($true) { Get-Process -Name 'CrashReportClient*' -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 10 }" &

Verify TCP 13377 responds to health_check.
Start intent server on 13380:
  python scripts/intent_server.py
```

### Step 2: Create the test runner

Create `scripts/tests/test_user_simulation.py` with the full test suite below.

### Step 3: Create the manual test log

Every command sent gets logged to `C:\BlueprintLLM\tests\manual_test_log.txt` so the user can replay them by hand.

---

## THE TEST RUNNER

```python
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

INTENT_HOST = "127.0.0.1"
INTENT_PORT = 13380
UE_HOST = "127.0.0.1"
UE_PORT = 13377
LOG_FILE = r"C:\BlueprintLLM\tests\manual_test_log.txt"
RESULTS_DIR = r"C:\BlueprintLLM\tests\results"

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
        print(f"  {line}")
    
    def send_to_intent(self, prompt):
        """Send a plain English prompt to the intent server.
        This is exactly what the Generator Panel does."""
        self.log(f'USER TYPES: "{prompt}"')
        
        request = json.dumps({
            "prompt": prompt,
            "context": {}  # Panel sends context when available
        })
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((INTENT_HOST, INTENT_PORT))
            sock.sendall(request.encode('utf-8'))
            
            response = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            sock.close()
            
            plan = json.loads(response.decode('utf-8'))
            self.log(f"INTENT RETURNS: mode={plan.get('mode', '?')}, "
                    f"ops={len(plan.get('operations', []))}, "
                    f"summary={plan.get('summary', '?')[:80]}")
            return plan
            
        except Exception as e:
            self.log(f"INTENT ERROR: {e}")
            return {"mode": "ERROR", "error": str(e), "operations": []}
    
    def send_to_ue(self, command, params=None):
        """Send a TCP command to UE. Used for verification, not for the test itself."""
        if params is None:
            params = {}
        
        request = json.dumps({"command": command, **params})
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((UE_HOST, UE_PORT))
            sock.sendall((request + "\n").encode('utf-8'))
            
            response = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            sock.close()
            
            return json.loads(response.decode('utf-8'))
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_plan(self, plan):
        """Execute a plan from the intent server against UE.
        This is exactly what the Generator Panel does after confirmation."""
        results = []
        
        for op in plan.get("operations", []):
            cmd = op.get("command", "")
            params = op.get("params", {})
            
            self.log(f"EXECUTE: {cmd} {json.dumps(params)[:150]}")
            
            result = self.send_to_ue(cmd, params)
            success = result.get("success", False)
            
            self.log(f"RESULT: {'OK' if success else 'FAIL'} — {json.dumps(result)[:150]}")
            results.append({"command": cmd, "success": success, "result": result})
        
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
                result = self.send_to_ue("find_actors", {"class_name": check.get("class", ""), "name_pattern": check.get("pattern", "")})
                actors = result.get("actors", [])
                passed = len(actors) > 0
                verifications.append({"check": f"Actor matching '{check.get('pattern', check.get('class', ''))}' exists", "passed": passed, "found": len(actors)})
                
            elif check_type == "actor_count":
                result = self.send_to_ue("find_actors", {"class_name": check.get("class", ""), "name_pattern": check.get("pattern", "")})
                actors = result.get("actors", [])
                expected = check["count"]
                passed = len(actors) == expected
                verifications.append({"check": f"Actor count = {expected}", "passed": passed, "found": len(actors)})
                
            elif check_type == "actor_not_exists":
                result = self.send_to_ue("find_actors", {"class_name": check.get("class", ""), "name_pattern": check.get("pattern", "")})
                actors = result.get("actors", [])
                passed = len(actors) == 0
                verifications.append({"check": f"No actors matching '{check.get('pattern', check.get('class', ''))}'", "passed": passed, "found": len(actors)})
                
            elif check_type == "variable_value":
                result = self.send_to_ue("get_blueprint_info", {"name": check["blueprint"]})
                variables = result.get("variables", [])
                found_var = None
                for v in variables:
                    if v.get("name", "").lower() == check["variable"].lower():
                        found_var = v
                        break
                if found_var:
                    passed = str(found_var.get("default", "")) == str(check["expected"])
                    verifications.append({"check": f"{check['blueprint']}.{check['variable']} == {check['expected']}", "passed": passed, "actual": found_var.get("default", "?")})
                else:
                    verifications.append({"check": f"{check['blueprint']}.{check['variable']} exists", "passed": False, "actual": "NOT FOUND"})
                    
            elif check_type == "material_applied":
                result = self.send_to_ue("find_actors", {"name_pattern": check.get("actor_pattern", "")})
                # Check material on found actors
                passed = result.get("success", False)  # Basic check
                verifications.append({"check": f"Material on '{check.get('actor_pattern', '')}'", "passed": passed})
                
            elif check_type == "level_has_actors":
                result = self.send_to_ue("get_level_info", {})
                count = result.get("actor_count", 0)
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
        intent_ok = mode.upper() in [m.upper() for m in (expected_mode if isinstance(expected_mode, list) else [expected_mode])]
        
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
        
        icon = "✅" if score == 4 else "⚠️" if score >= 2 else "❌"
        self.log(f"SCORE: {score}/4 {icon} (intent={intent_ok}, plan={plan_ok}, exec={exec_ok}, verify={verify_ok})")
        
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


# ═══════════════════════════════════════════════════════════════════
# TEST DEFINITIONS
# ═══════════════════════════════════════════════════════════════════

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
        "verify": [{"type": "actor_exists", "pattern": "*nemy*"}]
    },
    {
        "id": "S.07",
        "name": "Setup: Spawn coins",
        "prompt": "Place 5 gold coins around the level",
        "expected_mode": ["CREATE", "MULTI"],
        "verify": [{"type": "actor_exists", "pattern": "*oin*"}]
    },
    {
        "id": "S.08",
        "name": "Setup: Spawn torches",
        "prompt": "Put 4 torches in the level",
        "expected_mode": ["CREATE", "MULTI"],
        "verify": [{"type": "actor_exists", "pattern": "*orch*"}]
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
        "verify": [{"type": "actor_not_exists", "pattern": "*oin*"}]
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
        "verify": [{"type": "actor_not_exists", "pattern": "*orch*"}]
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
        print("  ❌ UE editor not responding on TCP 13377")
        return
    print("  ✅ UE editor connected")
    
    intent_check = sim.send_to_intent("health check")
    if intent_check.get("mode") == "ERROR":
        print("  ❌ Intent server not responding on TCP 13380")
        return
    print("  ✅ Intent server connected")
    
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
    print(f"  {'─'*18} {'─'*6} {'─'*10} {'─'*6}")
    print(f"  {'TOTAL':<18} {len(sim.test_results):>6} {total_score:>4}/{max_score:<4} {pct_total:>5.1f}%")
    
    # Failures
    failures = [r for r in sim.test_results if r["score"] < 3]
    if failures:
        print(f"\n  FAILURES (score < 3):")
        for r in failures:
            print(f"    {r['test_id']}: \"{r['prompt'][:50]}\" → mode={r['actual_mode']} "
                  f"(intent={'✓' if r['intent_ok'] else '✗'} plan={'✓' if r['plan_ok'] else '✗'} "
                  f"exec={'✓' if r['exec_ok'] else '✗'} verify={'✓' if r['verify_ok'] else '✗'})")
    
    perfect = sum(1 for r in sim.test_results if r["score"] == 4)
    print(f"\n  Perfect 4/4: {perfect}/{len(sim.test_results)}")
    print(f"  Grade: {'A — Production Ready' if pct_total >= 95 else 'B — Minor Fixes' if pct_total >= 85 else 'C — Significant Gaps' if pct_total >= 70 else 'D — Major Rework'}")
    
    sim.save_results()


if __name__ == "__main__":
    main()
```

---

## MANUAL REPLAY LOG FORMAT

The log file at `C:\BlueprintLLM\tests\manual_test_log.txt` looks like:

```
# Arcwright Manual Test Log
# Generated: 20260311_120000
# Replay these prompts in the Arcwright Generator Panel

[12:00:01] ============================================================
[12:00:01] TEST S.01: Setup: Create enemy blueprint
[12:00:01] ============================================================
[12:00:01] USER TYPES: "Create an enemy with 100 health, 15 damage, and 300 speed"
[12:00:03] INTENT RETURNS: mode=CREATE, ops=1, summary=Create enemy Blueprint with Health, Damage, Speed
[12:00:03] EXECUTE: create_blueprint {"domain": "blueprint", "prompt": "Create an enemy..."}
[12:00:06] RESULT: OK — {"success": true, "name": "BP_Enemy", "nodes": 5}
[12:00:06] SCORE: 4/4 ✅ (intent=True, plan=True, exec=True, verify=True)

[12:00:08] ============================================================
[12:00:08] TEST M.01: Change enemy health
[12:00:08] ============================================================
[12:00:08] USER TYPES: "Set health to 200 on all enemies"
...
```

You can then open the Generator Panel and type each "USER TYPES" prompt 
manually to confirm it works the same way.

---

## RUNNING

```powershell
# Full suite
python scripts/tests/test_user_simulation.py --category all

# Just modify tests
python scripts/tests/test_user_simulation.py --category modify

# Single test
python scripts/tests/test_user_simulation.py --test M.05

# Setup only (creates the known state)
python scripts/tests/test_user_simulation.py --category setup
```
