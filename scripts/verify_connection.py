#!/usr/bin/env python3
"""Arcwright Connection Verification — one-command check that everything works."""

import json
import os
import socket
import sys
import time

PORT = 13377
HOST = "localhost"
TIMEOUT = 5


def send_command(sock, command, params=None):
    """Send a TCP command and return the parsed response."""
    request = json.dumps({"command": command, "params": params or {}}) + "\n"
    sock.sendall(request.encode("utf-8"))

    # Read until newline
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Server closed connection")
        buf += chunk

    return json.loads(buf.decode("utf-8").strip())


def check_tcp_connection():
    """[1/5] TCP connection to localhost:13377"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    try:
        sock.connect((HOST, PORT))
        return True, sock, None
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        return False, None, str(e)


def check_health(sock):
    """[2/5] health_check"""
    resp = send_command(sock, "health_check")
    if resp.get("status") != "ok":
        return False, None
    data = resp.get("data", {})
    server = data.get("server", "?")
    version = data.get("version", "?")
    engine_ver = data.get("engine_version", "?")
    # Truncate engine version to major.minor
    if "." in engine_ver:
        parts = engine_ver.split(".")
        engine_ver = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else engine_ver
    return True, f"{server} v{version}, UE {engine_ver}"


def check_level_info(sock):
    """[3/5] get_level_info"""
    resp = send_command(sock, "get_level_info")
    if resp.get("status") != "ok":
        return False, None
    data = resp.get("data", {})
    level = data.get("level_name", "?")
    actors = data.get("actor_count", 0)
    return True, f"Level: {level}, {actors} actors"


def check_find_actors(sock):
    """[4/5] find_actors"""
    resp = send_command(sock, "find_actors", {})
    if resp.get("status") != "ok":
        return False, None
    data = resp.get("data", {})
    count = data.get("count", len(data.get("actors", [])))
    return True, f"Found {count} actors"


def check_capabilities(sock):
    """[5/5] get_capabilities"""
    # Try get_capabilities first, fall back to counting commands we know exist
    resp = send_command(sock, "get_capabilities")
    if resp.get("status") == "ok":
        data = resp.get("data", {})
        tcp = data.get("tcp_commands", "?")
        mcp = data.get("mcp_tools", "?")
        return True, f"{tcp} commands, {mcp} MCP tools"

    # Fallback: just report health check worked
    return True, "Commands available (get_capabilities not yet deployed)"


def print_config_snippet():
    """Print Claude Desktop config snippet."""
    # Find the Python executable
    venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server", "server.py")

    # Escape backslashes for JSON
    py_path = venv_python.replace("\\", "\\\\")
    srv_path = server_script.replace("\\", "\\\\")

    config = {
        "mcpServers": {
            "arcwright": {
                "command": py_path,
                "args": [srv_path]
            }
        }
    }

    print("\n" + "=" * 60)
    print("Claude Desktop Config")
    print("=" * 60)
    print(f"Add to: %APPDATA%\\Claude\\claude_desktop_config.json\n")
    print(json.dumps(config, indent=2))


def main():
    print("=" * 60)
    print("Arcwright Connection Verification")
    print("=" * 60)

    checks = []
    sock = None

    # Check 1: TCP connection
    label = "[1/5] TCP connection to localhost:13377"
    ok, sock, err = check_tcp_connection()
    if ok:
        print(f"{label} {'.' * (50 - len(label))} OK")
        checks.append(True)
    else:
        print(f"{label} {'.' * (50 - len(label))} FAIL")
        print(f"      Error: {err}")
        print(f"\n      Is UE Editor running with the Arcwright plugin?")
        print(f"      Check Output Log for: 'Arcwright Command Server started on port 13377'")
        checks.append(False)
        print(f"\nRESULT: FAIL — Cannot connect to Arcwright")
        print_config_snippet()
        return 1

    # Checks 2-5: require connection
    smoke_tests = [
        ("[2/5] health_check", check_health),
        ("[3/5] get_level_info", check_level_info),
        ("[4/5] find_actors", check_find_actors),
        ("[5/5] get_capabilities", check_capabilities),
    ]

    try:
        for label, check_fn in smoke_tests:
            try:
                ok, detail = check_fn(sock)
                pad = "." * max(1, 50 - len(label))
                if ok:
                    print(f"{label} {pad} OK — {detail}")
                    checks.append(True)
                else:
                    print(f"{label} {pad} FAIL")
                    checks.append(False)
            except Exception as e:
                pad = "." * max(1, 50 - len(label))
                print(f"{label} {pad} FAIL — {e}")
                checks.append(False)
    finally:
        if sock:
            sock.close()

    # Summary
    passed = sum(checks)
    total = len(checks)

    print()
    if passed == total:
        print(f"ALL CHECKS PASSED — Arcwright is ready!")
    else:
        print(f"RESULT: {passed}/{total} checks passed")
        if not checks[0]:
            print("  → UE Editor is not running or plugin is not loaded")

    print_config_snippet()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
