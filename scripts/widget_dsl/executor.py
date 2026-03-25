"""
Widget DSL v2 Executor — sends generated commands to UE via TCP.

Takes command list from command_generator, sends each via ArcwrightClient,
collects results, reports success/failure per command.
"""

import sys
import os
from typing import List, Dict, Any

# Add parent dir for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp_client"))


def execute(commands: List[dict], host: str = "localhost", port: int = 13377,
            timeout: float = 60.0, dry_run: bool = False) -> Dict[str, Any]:
    """Execute a list of TCP commands against the UE command server.

    Args:
        commands: List of {"command": "...", "params": {...}} dicts.
        host: TCP host.
        port: TCP port.
        timeout: Connection timeout.
        dry_run: If True, just print commands without sending.

    Returns:
        {"total": N, "succeeded": N, "failed": N, "results": [...]}
    """
    results = []
    succeeded = 0
    failed = 0

    if dry_run:
        for cmd in commands:
            results.append({"command": cmd["command"], "status": "dry_run", "params": cmd["params"]})
            succeeded += 1
        return {"total": len(commands), "succeeded": succeeded, "failed": 0, "results": results}

    from blueprint_client import ArcwrightClient, BlueprintLLMError

    client = ArcwrightClient(host=host, port=port, timeout=timeout)

    try:
        for cmd in commands:
            try:
                resp = client.send_command(cmd["command"], cmd["params"])
                status = resp.get("status", "unknown")
                results.append({
                    "command": cmd["command"],
                    "status": status,
                    "data": resp.get("data"),
                })
                if status == "ok":
                    succeeded += 1
                else:
                    failed += 1
            except BlueprintLLMError as e:
                results.append({
                    "command": cmd["command"],
                    "status": "error",
                    "message": str(e),
                })
                failed += 1
            except (ConnectionError, OSError) as e:
                results.append({
                    "command": cmd["command"],
                    "status": "connection_error",
                    "message": str(e),
                })
                failed += 1
                break  # connection lost, stop
    finally:
        client.close()

    return {"total": len(commands), "succeeded": succeeded, "failed": failed, "results": results}
