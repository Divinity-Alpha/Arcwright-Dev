"""
MCP Server integration test.

Tests the full chain:
  MCP Client -> MCP Server (in-process) -> TCP -> UE Command Server

Runs 5 verification steps:
  1. health_check — server connectivity
  2. create_blueprint_from_dsl — Hello World Blueprint
  3. get_blueprint_info — verify created Blueprint
  4. spawn_actor — place the Blueprint in the level
  5. get_actors — verify actor appears

Usage:
    python scripts/mcp_server/test_mcp.py
"""
import sys
import os
import json

# Set up paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_client"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dsl_parser"))

# Import the MCP tool functions directly (bypass MCP protocol for testing)
from server import (
    health_check, create_blueprint_from_dsl, get_blueprint_info,
    spawn_actor, get_actors, delete_actor, move_actor,
    import_blueprint_ir, create_blueprint,
)


def run_test(name, fn, expect_error=False):
    """Run a test step and print results."""
    print(f"\n{'='*50}")
    print(f"  Step: {name}")
    print(f"{'='*50}")
    try:
        result_str = fn()
        result = json.loads(result_str)
        has_error = "error" in result

        if expect_error:
            if has_error:
                print(f"  Result: Expected error received")
                print(f"  Message: {result['error'][:100]}")
                return True
            else:
                print(f"  Result: UNEXPECTED SUCCESS (expected error)")
                return False

        if has_error:
            print(f"  Result: ERROR")
            print(f"  Message: {result['error']}")
            return False

        print(f"  Result: OK")
        # Print key fields
        if "data" in result:
            data = result["data"]
            for key in ["server", "version", "engine_version",
                        "blueprint_name", "nodes_created", "connections_wired",
                        "compiled", "asset_path", "label", "class", "count"]:
                if key in data:
                    print(f"  {key}: {data[key]}")
        if "parser_result" in result:
            pr = result["parser_result"]
            stats = pr.get("stats", {})
            print(f"  Parser: {stats.get('nodes', '?')} nodes, "
                  f"{stats.get('connections', '?')} connections, "
                  f"{stats.get('mapped', '?')} mapped")
            if pr.get("errors"):
                print(f"  Parser errors: {pr['errors']}")
        return True
    except Exception as e:
        print(f"  EXCEPTION: {e}")
        return False


def main():
    print("=" * 50)
    print("  Arcwright MCP Server Integration Test")
    print("=" * 50)

    passed = 0
    total = 0

    # 1. Health check
    total += 1
    if run_test("health_check", health_check):
        passed += 1

    # 2. Create Blueprint from DSL
    hello_dsl = """BLUEPRINT: BP_MCP_HelloWorld
PARENT: Actor

GRAPH: EventGraph

NODE n1: Event_BeginPlay
NODE n2: PrintString [InString="Hello from MCP!"]

EXEC n1.Then -> n2.Execute"""

    total += 1
    if run_test("create_blueprint_from_dsl (Hello World)",
                lambda: create_blueprint_from_dsl(hello_dsl)):
        passed += 1

    # 3. Query the created Blueprint
    total += 1
    if run_test("get_blueprint_info (BP_MCP_HelloWorld)",
                lambda: get_blueprint_info("BP_MCP_HelloWorld")):
        passed += 1

    # 4. Spawn the Blueprint as an actor in the level
    total += 1
    if run_test("spawn_actor (BP_MCP_HelloWorld)",
                lambda: spawn_actor(
                    actor_class="/Game/Arcwright/Generated/BP_MCP_HelloWorld",
                    x=100.0, y=200.0, z=50.0,
                    label="MCP_TestActor"
                )):
        passed += 1

    # 5. List actors to verify
    total += 1
    if run_test("get_actors (verify spawn)",
                lambda: get_actors(class_filter="MCP")):
        passed += 1

    # 6. Move the actor
    total += 1
    if run_test("move_actor (MCP_TestActor)",
                lambda: move_actor(label="MCP_TestActor", z=300.0)):
        passed += 1

    # 7. Delete the actor
    total += 1
    if run_test("delete_actor (MCP_TestActor)",
                lambda: delete_actor(label="MCP_TestActor")):
        passed += 1

    # 8. Test create_blueprint (natural language — should return not-implemented error)
    total += 1
    if run_test("create_blueprint (natural language — expect error)",
                lambda: create_blueprint("A cube that spins"),
                expect_error=True):
        passed += 1

    # 9. Import IR file
    ir_path = os.path.join(os.path.dirname(__file__), "..", "..",
                           "test_ir", "T1_01_HelloWorld.blueprint.json")
    ir_path = os.path.abspath(ir_path)
    total += 1
    if run_test("import_blueprint_ir (T1_01_HelloWorld)",
                lambda: import_blueprint_ir(ir_path)):
        passed += 1

    # Summary
    print(f"\n{'='*50}")
    print(f"  RESULTS: {passed}/{total} passed")
    print(f"{'='*50}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
