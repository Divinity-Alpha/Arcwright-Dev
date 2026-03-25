"""
Test script for the create_blueprint_from_dsl single command (B8).

Tests raw DSL text -> verified Blueprint in one call, no intermediate files.
Three test cases of increasing complexity:
  1. Simple: BeginPlay -> PrintString
  2. Medium: Branch on a bool variable
  3. Complex: Health system with AnyDamage, subtraction, comparison

Requires UE5 Editor running with BlueprintLLM plugin loaded.

Usage:
    python scripts/mcp_client/test_dsl_command.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blueprint_client import ArcwrightClient, BlueprintLLMError

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

# ---------------------------------------------------------------------------
# DSL test inputs
# ---------------------------------------------------------------------------

DSL_SIMPLE = """\
BLUEPRINT: BP_DSL_SimpleHello
PARENT: Actor
GRAPH: EventGraph
NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Hello from DSL!"]
EXEC n1.Then -> n2.Execute
"""

DSL_MEDIUM = """\
BLUEPRINT: BP_DSL_BranchTest
PARENT: Actor
GRAPH: EventGraph
VAR IsActive: bool = true
NODE n1: Event_BeginPlay
NODE n2: VariableGet [VarName=IsActive]
NODE n3: Branch
NODE n4: PrintString [InString="Active!"]
NODE n5: PrintString [InString="Inactive!"]
EXEC n1.Then -> n3.Execute
DATA n2.Value -> n3.C [bool]
EXEC n3.True -> n4.Execute
EXEC n3.False -> n5.Execute
"""

DSL_COMPLEX = """\
BLUEPRINT: BP_DSL_ComplexFlow
PARENT: Actor
GRAPH: EventGraph
VAR Score: int = 0
NODE n1: Event_BeginPlay
NODE n2: Sequence
NODE n3: VariableGet [VarName=Score]
NODE n4: GreaterThan_IntInt
NODE n5: Branch
NODE n6: PrintString [InString="High score!"]
NODE n7: PrintString [InString="Low score"]
NODE n8: PrintString [InString="Sequence path B"]
EXEC n1.Then -> n2.Execute
EXEC n2.A -> n5.Execute
EXEC n2.B -> n8.Execute
DATA n3.Value -> n4.A [int]
DATA_LITERAL "50" -> n4.B [int]
DATA n4.ReturnValue -> n5.C [bool]
EXEC n5.True -> n6.Execute
EXEC n5.False -> n7.Execute
"""

TEST_CASES = [
    {
        "name": "Simple (BeginPlay -> PrintString)",
        "dsl": DSL_SIMPLE,
        "bp_name": "BP_DSL_SimpleHello",
        "min_nodes": 2,
        "min_connections": 1,
    },
    {
        "name": "Medium (Branch + Variable)",
        "dsl": DSL_MEDIUM,
        "bp_name": "BP_DSL_BranchTest",
        "min_nodes": 4,
        "min_connections": 4,
    },
    {
        "name": "Complex (Sequence + Branch + Variable)",
        "dsl": DSL_COMPLEX,
        "bp_name": "BP_DSL_ComplexFlow",
        "min_nodes": 6,
        "min_connections": 5,
    },
]


def main():
    results = []
    passed = 0
    failed = 0
    step = 0

    def record(name, ok, detail=""):
        nonlocal passed, failed, step
        step += 1
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        results.append({"step": step, "name": name, "status": status, "detail": detail})
        tag = "OK" if ok else "FAIL"
        suffix = f" -- {detail}" if detail else ""
        print(f"[{step:>2}] {name}... {tag}{suffix}")

    print("=" * 60)
    print("BlueprintLLM DSL-to-Blueprint -- Test Suite (B8)")
    print("=" * 60)

    # Step 1: Connect
    print(f"\n[ 1] Connecting to localhost:13377...", end=" ")
    try:
        client = ArcwrightClient(timeout=30)
        r = client.health_check()
        server = r.get("data", {}).get("server", "")
        print(f"OK -- {server}")
        step = 1
        passed += 1
        results.append({"step": 1, "name": "connect", "status": "PASS", "detail": server})
    except Exception as e:
        print(f"FAIL -- {e}")
        print("\nIs UE5 Editor running with the BlueprintLLM plugin?")
        return 1

    # Run each DSL test case
    for tc in TEST_CASES:
        tc_name = tc["name"]
        bp_name = tc["bp_name"]

        # Create from DSL
        try:
            r = client.create_blueprint_from_dsl(tc["dsl"])
            data = r.get("data", {})
            parser = r.get("parser_result", {})
            nodes = data.get("nodes_created", 0)
            nodes_exp = data.get("nodes_expected", 0)
            conns = data.get("connections_wired", 0)
            conns_exp = data.get("connections_expected", 0)
            compiled = data.get("compiled", False)
            errors = parser.get("errors", [])
            warnings = parser.get("warnings", [])

            ok = (compiled and
                  nodes >= tc["min_nodes"] and
                  conns >= tc["min_connections"] and
                  len(errors) == 0)

            detail = (f"{nodes}/{nodes_exp} nodes, {conns}/{conns_exp} conns, "
                      f"compiled={compiled}")
            if errors:
                detail += f", parser_errors={errors}"
            if warnings:
                detail += f", warnings={len(warnings)}"

            record(f"create_blueprint_from_dsl: {tc_name}", ok, detail)
        except Exception as e:
            record(f"create_blueprint_from_dsl: {tc_name}", False, str(e))

        # Verify via get_blueprint_info
        try:
            r = client.get_blueprint_info(bp_name)
            info = r.get("data", {})
            info_nodes = len(info.get("nodes", []))
            info_conns = len(info.get("connections", []))
            info_compiled = info.get("compiled", False)
            ok = info_compiled and info_nodes >= tc["min_nodes"]
            record(f"verify {bp_name}", ok,
                   f"{info_nodes} nodes, {info_conns} conns, compiled={info_compiled}")
        except Exception as e:
            record(f"verify {bp_name}", False, str(e))

    # Cleanup all test Blueprints
    print()
    for tc in TEST_CASES:
        bp_name = tc["bp_name"]
        try:
            r = client.delete_blueprint(bp_name)
            deleted = r.get("data", {}).get("deleted", False)
            record(f"cleanup {bp_name}", deleted, f"deleted={deleted}")
        except Exception as e:
            record(f"cleanup {bp_name}", False, str(e))

    client.close()

    # Summary
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed", end="")
    if failed > 0:
        print(f", {failed} FAILED")
    else:
        print(" -- All tests passed!")
    print("=" * 60)

    # Save report
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(RESULTS_DIR, f"dsl_command_test_{timestamp}.json")
    report = {
        "timestamp": timestamp,
        "passed": passed,
        "failed": failed,
        "total": total,
        "results": results,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved: {report_path}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
