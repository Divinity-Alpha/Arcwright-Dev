"""Test BehaviorTree creation via TCP command server."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from blueprint_client import ArcwrightClient

TEST_DSL = """
BEHAVIORTREE: BT_TestPatrol
BLACKBOARD: BB_TestPatrol

KEY TargetActor: Object
KEY PatrolLocation: Vector

TREE:

SELECTOR: Root
  SEQUENCE: Chase
    DECORATOR: BlackboardBased [Key=TargetActor, Condition=IsSet, AbortMode=LowerPriority]
    TASK: MoveTo [Key=TargetActor, AcceptableRadius=200]
  SEQUENCE: Patrol
    TASK: MoveTo [Key=PatrolLocation, AcceptableRadius=50]
    TASK: Wait [Duration=3.0]
"""

def main():
    c = ArcwrightClient()
    c.sock.settimeout(30)

    # Health check
    r = c.health_check()
    print(f"Server: {r['status']}")

    # Test 1: Create BehaviorTree from DSL
    print("\n=== Test 1: Create BehaviorTree from DSL ===")
    try:
        r = c.create_behavior_tree_from_dsl(TEST_DSL)
        print(f"  Status: {r.get('status')}")
        data = r.get('data', {})
        print(f"  Tree path: {data.get('tree_asset_path')}")
        print(f"  Blackboard path: {data.get('blackboard_asset_path')}")
        print(f"  Composites: {data.get('composite_count')}")
        print(f"  Tasks: {data.get('task_count')}")
        print(f"  Decorators: {data.get('decorator_count')}")
        print(f"  Services: {data.get('service_count')}")
        print(f"  Total nodes: {data.get('total_node_count')}")

        parser = r.get('parser_result', {})
        if parser.get('errors'):
            print(f"  Parser errors: {parser['errors']}")
        if parser.get('warnings'):
            print(f"  Parser warnings: {parser['warnings']}")
        stats = parser.get('stats', {})
        print(f"  Parser stats: {stats.get('total_nodes')} nodes, {stats.get('blackboard_keys')} BB keys")

        test1_pass = r.get('status') == 'ok'
        print(f"  RESULT: {'PASS' if test1_pass else 'FAIL'}")
    except Exception as e:
        print(f"  RESULT: FAIL - {e}")
        test1_pass = False

    # Test 2: Query the created BehaviorTree
    print("\n=== Test 2: Get BehaviorTree Info ===")
    try:
        r = c.get_behavior_tree_info("BT_TestPatrol")
        print(f"  Status: {r.get('status')}")
        data = r.get('data', {})
        print(f"  Name: {data.get('name')}")
        print(f"  Blackboard: {data.get('blackboard_name')}")
        print(f"  BB keys: {data.get('blackboard_key_count')}")
        print(f"  Composites: {data.get('composite_count')}")
        print(f"  Tasks: {data.get('task_count')}")
        print(f"  Decorators: {data.get('decorator_count')}")
        print(f"  Services: {data.get('service_count')}")
        print(f"  Total: {data.get('total_node_count')}")
        print(f"  Has root: {data.get('has_root')}")

        # Print BB keys
        keys = data.get('blackboard_keys', [])
        for k in keys:
            print(f"    Key: {k.get('name')} ({k.get('type')})")

        test2_pass = (r.get('status') == 'ok' and
                      data.get('has_root') == True and
                      data.get('composite_count', 0) >= 3)
        print(f"  RESULT: {'PASS' if test2_pass else 'FAIL'}")
    except Exception as e:
        print(f"  RESULT: FAIL - {e}")
        test2_pass = False

    # Test 3: Query non-existent BT (error handling)
    print("\n=== Test 3: Get non-existent BT ===")
    try:
        r = c.get_behavior_tree_info("BT_DoesNotExist")
        print(f"  RESULT: FAIL - should have raised error")
        test3_pass = False
    except Exception as e:
        print(f"  Error (expected): {e}")
        test3_pass = "not found" in str(e).lower()
        print(f"  RESULT: {'PASS' if test3_pass else 'FAIL'}")

    c.close()

    # Summary
    results = [test1_pass, test2_pass, test3_pass]
    passed = sum(results)
    total = len(results)
    print(f"\n=== RESULTS: {passed}/{total} PASS ===")
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
