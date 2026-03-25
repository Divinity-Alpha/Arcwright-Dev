"""
Automated Test Runner for BlueprintLLM Command Server.

Takes a directory of IR files, imports each one via the command server,
queries the result, compares to expected values, produces a report.

Usage:
    python scripts/mcp_client/test_runner.py
    python scripts/mcp_client/test_runner.py --ir-dir C:/BlueprintLLM/test_ir
    python scripts/mcp_client/test_runner.py --ir-dir test_ir --output results/plugin_test.json
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blueprint_client import ArcwrightClient, BlueprintLLMError

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def parse_ir_expectations(ir_path: str) -> dict:
    """Parse an IR file and extract expected counts."""
    with open(ir_path, "r", encoding="utf-8") as f:
        ir = json.load(f)

    name = ir.get("metadata", {}).get("name", "Unknown")
    nodes_expected = len(ir.get("nodes", []))
    # Don't count data_literal connections — the server reports those as default values, not wired connections
    connections_expected = sum(1 for c in ir.get("connections", []) if c.get("type") != "data_literal")
    variables_expected = len(ir.get("variables", []))

    return {
        "name": name,
        "nodes_expected": nodes_expected,
        "connections_expected": connections_expected,
        "variables_expected": variables_expected,
    }


def run_single_test(client: ArcwrightClient, ir_path: str) -> dict:
    """Run a single import test and return results."""
    filename = os.path.basename(ir_path)
    result = {
        "file": filename,
        "ir_path": ir_path,
        "status": "FAIL",
        "details": {},
        "errors": [],
    }

    # Parse expectations from IR
    try:
        expectations = parse_ir_expectations(ir_path)
        result["blueprint_name"] = expectations["name"]
        result["details"]["nodes_expected"] = expectations["nodes_expected"]
        result["details"]["connections_expected"] = expectations["connections_expected"]
        result["details"]["variables_expected"] = expectations["variables_expected"]
    except Exception as e:
        result["errors"].append(f"Failed to parse IR: {e}")
        return result

    # Step 1: Delete existing Blueprint (clean slate)
    try:
        client.delete_blueprint(expectations["name"])
    except BlueprintLLMError:
        pass  # OK if it doesn't exist
    except (ConnectionError, ConnectionResetError, OSError):
        raise  # Propagate connection errors for outer handler

    # Step 2: Import
    try:
        import_result = client.import_from_ir(ir_path)
        data = import_result.get("data", {})
        result["details"]["nodes_created"] = data.get("nodes_created", 0)
        result["details"]["connections_wired"] = data.get("connections_wired", 0)
        result["details"]["variables_created"] = data.get("variables_created", 0)
        result["details"]["compiled"] = data.get("compiled", False)
        result["details"]["compile_errors"] = data.get("compile_errors", [])
        result["details"]["asset_path"] = data.get("asset_path", "")
    except BlueprintLLMError as e:
        result["errors"].append(f"Import failed: {e}")
        return result
    except Exception as e:
        result["errors"].append(f"Connection error during import: {e}")
        return result

    # Step 3: Query the created Blueprint
    try:
        info_result = client.get_blueprint_info(expectations["name"])
        info_data = info_result.get("data", {})
        result["details"]["query_nodes"] = len(info_data.get("nodes", []))
        result["details"]["query_connections"] = len(info_data.get("connections", []))
        result["details"]["query_variables"] = len(info_data.get("variables", []))
        result["details"]["query_compiled"] = info_data.get("compiled", False)
    except BlueprintLLMError as e:
        result["errors"].append(f"Query failed: {e}")
    except Exception as e:
        result["errors"].append(f"Connection error during query: {e}")

    # Step 4: Evaluate
    d = result["details"]
    nodes_ok = d.get("nodes_created", 0) >= d.get("nodes_expected", 0)
    # Connection count may differ due to default pins, so use >= expected
    conns_ok = d.get("connections_wired", 0) >= d.get("connections_expected", 0)
    compiled = d.get("compiled", False)

    if nodes_ok and conns_ok and compiled:
        result["status"] = "PASS"
    elif nodes_ok and compiled:
        result["status"] = "PARTIAL"
    else:
        result["status"] = "FAIL"

    if not nodes_ok:
        result["errors"].append(
            f"Nodes: {d.get('nodes_created', 0)}/{d.get('nodes_expected', 0)}"
        )
    if not conns_ok:
        result["errors"].append(
            f"Connections: {d.get('connections_wired', 0)}/{d.get('connections_expected', 0)}"
        )
    if not compiled:
        result["errors"].append("Compilation failed")

    return result


def print_summary_table(results: list):
    """Print a formatted summary table."""
    # Header
    print(f"\n{'Test':<20} | {'Nodes':<12} | {'Connections':<14} | {'Compiled':<10} | {'Status'}")
    print("-" * 80)

    for r in results:
        d = r.get("details", {})
        name = r.get("file", "?")[:18]

        nodes_str = f"{d.get('nodes_created', '?')}/{d.get('nodes_expected', '?')}"
        conns_str = f"{d.get('connections_wired', '?')}/{d.get('connections_expected', '?')}"
        compiled_str = "Yes" if d.get("compiled") else "No"
        status = r.get("status", "?")

        # Status indicator
        if status == "PASS":
            status_str = "PASS"
        elif status == "PARTIAL":
            status_str = "PARTIAL"
        else:
            status_str = "FAIL"

        print(f"{name:<20} | {nodes_str:<12} | {conns_str:<14} | {compiled_str:<10} | {status_str}")

    # Totals
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    partial = sum(1 for r in results if r["status"] == "PARTIAL")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print("-" * 80)
    print(f"Total: {total} | Passed: {passed} | Partial: {partial} | Failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description="BlueprintLLM Plugin Test Runner")
    parser.add_argument("--ir-dir", default=str(PROJECT_ROOT / "test_ir"),
                        help="Directory containing .blueprint.json IR files")
    parser.add_argument("--output", default=None,
                        help="Output JSON report path")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=13377)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    ir_dir = Path(args.ir_dir)
    if not ir_dir.exists():
        print(f"IR directory not found: {ir_dir}")
        return 1

    ir_files = sorted(ir_dir.glob("*.blueprint.json"))
    if not ir_files:
        print(f"No .blueprint.json files found in {ir_dir}")
        return 1

    print("=" * 60)
    print("BlueprintLLM Plugin Test Runner")
    print(f"IR directory: {ir_dir}")
    print(f"Test files: {len(ir_files)}")
    print("=" * 60)

    # Connect
    print(f"\nConnecting to {args.host}:{args.port}...", end=" ")
    try:
        client = ArcwrightClient(host=args.host, port=args.port, timeout=args.timeout)
        health = client.health_check()
        server_version = health.get("data", {}).get("version", "?")
        print(f"OK (server v{server_version})")
    except Exception as e:
        print(f"FAIL — {e}")
        print("Is UE5 Editor running with the BlueprintLLM plugin?")
        return 1

    # Run tests
    results = []
    start_time = time.time()

    for i, ir_file in enumerate(ir_files, 1):
        print(f"\n[{i}/{len(ir_files)}] Testing {ir_file.name}...")
        # Small delay between tests to avoid overwhelming the editor renderer
        if i > 1:
            time.sleep(1.5)
        test_start = time.time()
        try:
            result = run_single_test(client, str(ir_file))
        except (ConnectionError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
            # Server/editor likely crashed — try to reconnect
            result = {
                "file": ir_file.name,
                "ir_path": str(ir_file),
                "status": "FAIL",
                "details": {},
                "errors": [f"Connection lost: {e}"],
            }
            print(f"  CONNECTION LOST — attempting reconnect...")
            try:
                client.close()
            except Exception:
                pass
            # Wait for editor to potentially recover
            time.sleep(2)
            try:
                client = ArcwrightClient(host=args.host, port=args.port, timeout=args.timeout)
                health = client.health_check()
                print(f"  Reconnected OK (v{health.get('data', {}).get('version', '?')})")
            except Exception:
                print(f"  Reconnect FAILED — editor crashed. Marking remaining tests as SKIP.")
                result["errors"].append("Editor crashed")
                results.append(result)
                # Mark remaining tests
                for j, remaining_file in enumerate(ir_files[i:], i + 1):
                    results.append({
                        "file": remaining_file.name,
                        "ir_path": str(remaining_file),
                        "status": "FAIL",
                        "details": {},
                        "errors": ["SKIPPED — editor not running"],
                    })
                break
        result["duration_seconds"] = round(time.time() - test_start, 2)
        results.append(result)

        if result.get("errors"):
            for err in result["errors"]:
                print(f"  Warning: {err}")

    try:
        client.close()
    except Exception:
        pass

    total_duration = round(time.time() - start_time, 2)

    # Summary table
    print_summary_table(results)
    print(f"\nTotal time: {total_duration}s")

    # Save report
    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = PROJECT_ROOT / "results" / f"plugin_test_{ts}.json"
    else:
        output_path = Path(args.output)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "server_version": server_version,
        "ir_directory": str(ir_dir),
        "total_tests": len(results),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "partial": sum(1 for r in results if r["status"] == "PARTIAL"),
        "failed": sum(1 for r in results if r["status"] == "FAIL"),
        "total_duration_seconds": total_duration,
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {output_path}")

    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
