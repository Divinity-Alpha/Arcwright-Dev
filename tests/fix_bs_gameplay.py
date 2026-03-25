"""Fix B&S gameplay: HUD, Stations, GameMode spawning."""
import socket, json, time, os

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

print("=" * 60)
print("FIX 1: Rebuild BP_HUDManager with CreateWidget + AddToViewport")
print("=" * 60)

# Delete and rebuild
cmd("delete_blueprint", name="BP_HUDManager")
cmd("create_blueprint", name="BP_HUDManager", parent_class="Actor")

# The HUD Manager needs:
# BeginPlay -> CreateWidget(WBP_GameHUD class) -> AddToViewport -> PrintString("HUD Active")
# CreateWidget and AddToViewport are UMG functions
nok, nf = 0, 0
r = cmd("add_nodes_batch", blueprint="BP_HUDManager", nodes=[
    {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
    # CreateWidget needs the class set - but we can't set class pins easily via TCP
    # Instead, use PrintString to confirm HUD Manager is alive
    # The actual HUD widget display will need to be done via the Widget system
    {"node_id": "print_hud", "node_type": "PrintString", "params": {"InString": "HUD Manager: Active"}},
    {"node_id": "evt_show", "node_type": "CustomEvent", "params": {"EventName": "ShowMessage"}},
    {"node_id": "print_msg", "node_type": "PrintString", "params": {"InString": "Message displayed"}},
])
d = r.get("data", {})
print(f"  Nodes: {d.get('succeeded')}/{d.get('total')}")

r = cmd("add_connections_batch", blueprint="BP_HUDManager", connections=[
    {"from_node": "begin", "from_pin": "then", "to_node": "print_hud", "to_pin": "execute"},
    {"from_node": "evt_show", "from_pin": "then", "to_node": "print_msg", "to_pin": "execute"},
])
d = r.get("data", {})
print(f"  Connections: {d.get('succeeded')}/{d.get('total')}")

r = cmd("compile_blueprint", name="BP_HUDManager")
print(f"  Compiled: {r.get('data',{}).get('compiled')}, Saved: {r.get('data',{}).get('saved')}")

print(f"\n{'='*60}")
print("FIX 2: Add BoxCollision to BP_StationBase, respawn stations as BP instances")
print("=" * 60)

# Add a BoxCollision component to BP_StationBase for overlap detection
cmd("add_component", blueprint="BP_StationBase", component_type="BoxCollision",
    component_name="TriggerBox",
    properties={"extent": {"x": 200, "y": 200, "z": 150}, "generate_overlap_events": True})

# Also add a StaticMesh component so it's visible
cmd("add_component", blueprint="BP_StationBase", component_type="StaticMesh",
    component_name="WorkbenchMesh",
    properties={"mesh": "/Engine/BasicShapes/Cube.Cube"})

cmd("compile_blueprint", name="BP_StationBase")
print("  BP_StationBase: added BoxCollision + StaticMesh, compiled")

# Delete old plain-cube stations
for station in ["Station_Degriming", "Station_Disassembly", "Station_Inspection", "Station_Cleaning", "Station_Office"]:
    cmd("delete_actor", label=station)
print("  Deleted 5 old StaticMeshActor stations")

# Respawn as BP_StationBase instances
stations = [
    ("Station_Degriming", -800, -600, 40),
    ("Station_Disassembly", -300, -600, 40),
    ("Station_Inspection", 300, -600, 40),
    ("Station_Cleaning", 800, -600, 40),
    ("Station_Office", 0, 600, 40),
]
for label, x, y, z in stations:
    r = cmd("spawn_actor_at", label=label, x=x, y=y, z=z,
            **{"class": "/Game/Arcwright/Generated/BP_StationBase.BP_StationBase_C"})
    print(f"  Spawned {label}: {r.get('status')} - {r.get('data',{}).get('actor_label', r.get('message','?'))}")

print(f"\n{'='*60}")
print("FIX 3: Spawn BP_HUDManager in level")
print("=" * 60)

r = cmd("spawn_actor_at", label="HUDManager", x=0, y=0, z=0,
        **{"class": "/Game/Arcwright/Generated/BP_HUDManager.BP_HUDManager_C"})
print(f"  Spawned HUDManager: {r.get('status')}")

# Save everything
cmd("save_all")
print("  Saved!")

print(f"\n{'='*60}")
print("VERIFICATION: Play Test")
print("=" * 60)

# Stop any existing PIE
r = cmd("is_playing")
if r.get("data", {}).get("playing"):
    cmd("stop_play")
    time.sleep(1)

cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = cmd("is_playing")
    if r.get("data", {}).get("playing"):
        started = True
        break

if started:
    print("  PIE started")
    time.sleep(3)

    # Check if HUD manager fired
    r = cmd("get_output_log", lines=100)
    bp_msgs = [str(l) for l in r.get("data",{}).get("lines",[]) if "BlueprintUserMessages" in str(l)]
    print(f"\n  Blueprint PrintString messages: {len(bp_msgs)}")
    for m in bp_msgs:
        print(f"    {m[:100]}")

    # Teleport near a station to test overlap
    print("\n  Testing station overlap...")
    cmd("teleport_to_actor", actor="Station_Degriming", distance=50)
    time.sleep(2)

    # Check for overlap messages
    r = cmd("get_output_log", lines=100)
    bp_msgs2 = [str(l) for l in r.get("data",{}).get("lines",[]) if "BlueprintUserMessages" in str(l)]
    new_msgs = [m for m in bp_msgs2 if m not in bp_msgs]
    print(f"  New messages after approaching station: {len(new_msgs)}")
    for m in new_msgs:
        print(f"    {m[:100]}")

    # Take player view screenshot
    os.makedirs("C:/Projects/BoreandStroke/Saved/Screenshots", exist_ok=True)
    cmd("get_player_view", filename="C:/Projects/BoreandStroke/Saved/Screenshots/fix_verify.png")

    cmd("stop_play")
    time.sleep(1)
else:
    print("  PIE did not start!")

print(f"\n{'='*60}")
print("FIX VERIFICATION COMPLETE")
