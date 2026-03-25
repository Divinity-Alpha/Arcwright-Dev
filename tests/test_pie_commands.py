"""Test PIE verification commands."""
import socket, json, time

def cmd(command, **params):
    s = socket.socket(); s.settimeout(30)
    s.connect(('localhost', 13377))
    s.sendall(json.dumps({"command": command, "params": params}).encode() + b'\n')
    data = b''
    while b'\n' not in data:
        chunk = s.recv(65536)
        if not chunk: break
        data += chunk
    s.close()
    return json.loads(data.decode().strip())

print("=" * 60)
print("PIE VERIFICATION COMMANDS TEST")
print("=" * 60)

# 1. is_playing
print("\n1. is_playing")
r = cmd("is_playing")
print(f"   Status: {r['status']}, playing: {r.get('data',{}).get('playing')}")

# 2. verify_all_blueprints
print("\n2. verify_all_blueprints")
r = cmd("verify_all_blueprints")
if r["status"] == "ok":
    d = r["data"]
    print(f"   Total: {d.get('total')}, Pass: {d.get('pass')}, Fail: {d.get('fail')}")
    for bp in d.get("results", []):
        name = bp.get("name", "?")
        compiles = bp.get("compiles", False)
        nodes = bp.get("node_count", 0)
        conns = bp.get("connection_count", 0)
        status = "PASS" if compiles else "FAIL"
        print(f"     {status}: {name} ({nodes} nodes, {conns} conns)")
        if not compiles:
            for err in bp.get("errors", []):
                print(f"       Error: {err[:80]}")
else:
    print(f"   Error: {r.get('message','?')}")

# 3. play_and_capture
print("\n3. play_and_capture (5 seconds)")
cmd("save_all")
r = cmd("play_and_capture", duration=5)
if r["status"] == "ok":
    d = r["data"]
    print(f"   Started: {d.get('started')}")
    print(f"   Crashed: {d.get('crashed')}")
    print(f"   Duration: {d.get('duration_seconds')}s")
    print(f"   Screenshot: {d.get('screenshot','?')}")
    log_lines = d.get("log_lines", [])
    print(f"   Log lines: {len(log_lines)}")
    for line in log_lines[:15]:
        print(f"     {line[:100]}")
else:
    print(f"   Error: {r.get('message', r.get('error','?'))}")

# 4. is_playing (should be false after play_and_capture)
print("\n4. is_playing (post-capture)")
r = cmd("is_playing")
print(f"   playing: {r.get('data',{}).get('playing')}")

print("\n" + "=" * 60)
print("PIE COMMANDS TEST COMPLETE")
