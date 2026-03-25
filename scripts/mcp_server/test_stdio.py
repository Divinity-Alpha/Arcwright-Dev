"""
Test the MCP server via the actual stdio JSON-RPC protocol.
Verifies that Claude Desktop would be able to communicate with this server.

Starts the server as a subprocess, sends JSON-RPC messages over stdin,
reads responses from stdout.
"""
import subprocess
import json
import sys
import os
import threading
import time

SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "venv", "Scripts", "python.exe")


def main():
    print("MCP stdio Protocol Test")
    print("=" * 50)

    proc = subprocess.Popen(
        [PYTHON, SERVER_PATH],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    # Collect stdout lines in background thread
    stdout_lines = []
    def reader():
        for line in proc.stdout:
            stdout_lines.append(line.decode("utf-8", errors="replace").strip())
    t = threading.Thread(target=reader, daemon=True)
    t.start()

    def send(msg_dict):
        raw = json.dumps(msg_dict) + "\n"
        proc.stdin.write(raw.encode())
        proc.stdin.flush()

    def wait_for_id(req_id, timeout=10):
        deadline = time.time() + timeout
        seen = 0
        while time.time() < deadline:
            for line in stdout_lines[seen:]:
                seen += 1
                if not line:
                    continue
                data = json.loads(line)
                if data.get("id") == req_id:
                    return data
            time.sleep(0.1)
        return None

    passed = 0
    total = 0

    try:
        # 1. Initialize
        total += 1
        print("\n1. initialize...")
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        }})
        resp = wait_for_id(1)
        if resp and "result" in resp:
            info = resp["result"].get("serverInfo", {})
            print(f"   Server: {info.get('name')} v{info.get('version')}")
            caps = list(resp["result"].get("capabilities", {}).keys())
            print(f"   Capabilities: {caps}")
            assert "tools" in caps, "Missing tools capability"
            passed += 1
            print("   PASS")
        else:
            print(f"   FAIL — no response")

        # Send initialized notification
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        time.sleep(0.3)

        # 2. List tools
        total += 1
        print("\n2. tools/list...")
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        resp = wait_for_id(2)
        if resp and "result" in resp:
            tools = resp["result"].get("tools", [])
            print(f"   Tools: {len(tools)}")
            tool_names = [t["name"] for t in tools]
            expected = ["health_check", "create_blueprint_from_dsl",
                        "spawn_actor", "get_blueprint_info"]
            missing = [e for e in expected if e not in tool_names]
            if not missing:
                passed += 1
                print("   PASS")
            else:
                print(f"   FAIL — missing tools: {missing}")
        else:
            print(f"   FAIL — no response")

        # 3. Call health_check
        total += 1
        print("\n3. tools/call health_check...")
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "health_check", "arguments": {}}})
        resp = wait_for_id(3, timeout=10)
        if resp and "result" in resp:
            content = resp["result"].get("content", [])
            if content:
                inner = json.loads(content[0]["text"])
                if inner.get("status") == "ok":
                    sv = inner["data"]
                    print(f"   UE: {sv.get('server')} v{sv.get('version')}, "
                          f"engine {sv.get('engine_version', '?')[:20]}")
                    passed += 1
                    print("   PASS")
                else:
                    print(f"   FAIL — {inner}")
        else:
            print(f"   FAIL — no response")

        # 4. Call create_blueprint_from_dsl
        total += 1
        print("\n4. tools/call create_blueprint_from_dsl...")
        dsl = ("BLUEPRINT: BP_MCP_ProtocolTest\nPARENT: Actor\n\n"
               "GRAPH: EventGraph\n\n"
               "NODE n1: Event_BeginPlay\n"
               'NODE n2: PrintString [InString="Protocol test!"]\n\n'
               "EXEC n1.Then -> n2.Execute")
        send({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
              "params": {"name": "create_blueprint_from_dsl",
                         "arguments": {"dsl_text": dsl}}})
        resp = wait_for_id(4, timeout=15)
        if resp and "result" in resp:
            content = resp["result"].get("content", [])
            if content:
                inner = json.loads(content[0]["text"])
                if inner.get("status") == "ok":
                    d = inner["data"]
                    print(f"   Blueprint: {d.get('blueprint_name')}")
                    print(f"   Nodes: {d.get('nodes_created')}, "
                          f"Connections: {d.get('connections_wired')}, "
                          f"Compiled: {d.get('compiled')}")
                    passed += 1
                    print("   PASS")
                elif "error" in inner:
                    print(f"   FAIL — {inner['error']}")
        else:
            print(f"   FAIL — no response")

    except Exception as e:
        print(f"\n  EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    print(f"\n{'='*50}")
    print(f"  RESULTS: {passed}/{total} passed")
    print(f"{'='*50}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
