import socket, json

def cmd(command, **params):
    s = socket.socket(); s.settimeout(15)
    s.connect(('localhost', 13377))
    s.sendall(json.dumps({"command": command, "params": params}).encode() + b'\n')
    data = b''
    while b'\n' not in data:
        chunk = s.recv(65536)
        if not chunk: break
        data += chunk
    s.close()
    return json.loads(data.decode().strip())

for bp_name in ["BP_TimeManager", "BP_HeatManager"]:
    print(f"\n{'='*60}")
    print(f"DIAGNOSIS: {bp_name}")
    print(f"{'='*60}")

    r = cmd("compile_blueprint", name=bp_name)
    d = r.get("data", {})
    print(f"Compiled: {d.get('compiled')}")
    print(f"Nodes: {d.get('node_count')}, Connections: {d.get('connection_count')}")
    msgs = d.get("messages", [])
    print(f"Messages ({len(msgs)}):")
    for m in msgs:
        print(f"  [{m.get('severity')}] {m.get('node_title','?')}: {m.get('message','?')}")

    if not msgs:
        print("  No compile messages. compiled=False may mean warnings treated as errors.")

# Check all 5
print(f"\n{'='*60}")
print("ALL BLUEPRINTS STATUS")
print(f"{'='*60}")
for bp in ["BP_TimeManager", "BP_EconomyManager", "BP_StationBase", "BP_HeatManager", "BP_BoreAndStrokeGameMode"]:
    r = cmd("compile_blueprint", name=bp)
    d = r.get("data", {})
    compiled = d.get("compiled", False)
    nodes = d.get("node_count", 0)
    conns = d.get("connection_count", 0)
    msgs = len(d.get("messages", []))
    print(f"  {bp}: compiled={compiled} nodes={nodes} conns={conns} msgs={msgs}")
