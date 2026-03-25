"""Dialogue DSL Executor."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_client"))

def execute(commands, host="localhost", port=13377, timeout=60.0, dry_run=False):
    results, ok, fail = [], 0, 0
    if dry_run:
        for cmd in commands:
            results.append({"command": cmd["command"], "status": "dry_run"})
            ok += 1
        return {"total": len(commands), "succeeded": ok, "failed": 0, "results": results}
    from blueprint_client import ArcwrightClient, BlueprintLLMError
    client = ArcwrightClient(host=host, port=port, timeout=timeout)
    try:
        for cmd in commands:
            try:
                resp = client.send_command(cmd["command"], cmd["params"])
                s = resp.get("status", "?")
                results.append({"command": cmd["command"], "status": s})
                if s == "ok": ok += 1
                else: fail += 1
            except Exception as e:
                results.append({"command": cmd["command"], "status": "error", "message": str(e)})
                fail += 1
    finally:
        client.close()
    return {"total": len(commands), "succeeded": ok, "failed": fail, "results": results}
