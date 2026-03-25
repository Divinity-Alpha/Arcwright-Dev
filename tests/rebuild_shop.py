"""Rebuild B&S shop with correct geometry, verify positions, play test."""
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
print("REBUILD SHOP GEOMETRY")
print("=" * 60)

# Delete ALL existing geometry
r = cmd("find_actors")
actors = r.get("data", {}).get("actors", [])
geo_labels = [a["label"] for a in actors if a.get("class") in ["StaticMeshActor", "PointLight"] and a.get("label")]
if geo_labels:
    cmd("batch_delete_actors", labels=geo_labels)
    print(f"  Deleted {len(geo_labels)} actors")

# Floor
print("\n  Spawning floor...")
r = cmd("spawn_actor_at", label="ShopFloor", x=0, y=0, z=-10,
        **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": 30, "scale_y": 30, "scale_z": 0.2})
print(f"    {r.get('status')}")

# Verify position
r2 = cmd("get_actor_properties", actor_label="ShopFloor")
loc = r2.get("data", {}).get("location", {})
scale = r2.get("data", {}).get("scale", {})
print(f"    Location: ({loc.get('x',0):.0f}, {loc.get('y',0):.0f}, {loc.get('z',0):.0f})")
print(f"    Scale: ({scale.get('x',1):.1f}, {scale.get('y',1):.1f}, {scale.get('z',1):.1f})")

# Material
cmd("set_actor_material", actor_label="ShopFloor", material_path="/Game/Arcwright/Materials/M_ShopFloor")

# Walls
print("\n  Spawning walls...")
walls = [
    ("Wall_North", 0, 1500, 150, 30, 0.2, 3),
    ("Wall_South", 0, -1500, 150, 30, 0.2, 3),
    ("Wall_East", 1500, 0, 150, 0.2, 30, 3),
    ("Wall_West", -1500, 0, 150, 0.2, 30, 3),
]
for label, x, y, z, sx, sy, sz in walls:
    cmd("spawn_actor_at", label=label, x=x, y=y, z=z,
        **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": sx, "scale_y": sy, "scale_z": sz})
    cmd("set_actor_material", actor_label=label, material_path="/Game/Arcwright/Materials/M_ShopWall")
    # Verify
    r = cmd("get_actor_properties", actor_label=label)
    loc = r.get("data", {}).get("location", {})
    scale = r.get("data", {}).get("scale", {})
    print(f"    {label}: loc=({loc.get('x',0):.0f},{loc.get('y',0):.0f},{loc.get('z',0):.0f}) scale=({scale.get('x',1):.1f},{scale.get('y',1):.1f},{scale.get('z',1):.1f})")

# Ceiling
print("\n  Spawning ceiling...")
cmd("spawn_actor_at", label="Ceiling", x=0, y=0, z=310,
    **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
       "scale_x": 30, "scale_y": 30, "scale_z": 0.2})
cmd("set_actor_material", actor_label="Ceiling", material_path="/Game/Arcwright/Materials/M_ShopWall")

# Stations
print("\n  Spawning stations...")
stations = [
    ("Station_Degriming", -800, -600, 40),
    ("Station_Disassembly", -300, -600, 40),
    ("Station_Inspection", 300, -600, 40),
    ("Station_Cleaning", 800, -600, 40),
    ("Station_Office", 0, 600, 40),
]
for label, x, y, z in stations:
    cmd("spawn_actor_at", label=label, x=x, y=y, z=z,
        **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": 2.0, "scale_y": 1.5, "scale_z": 1.0})
    cmd("set_actor_material", actor_label=label, material_path="/Game/Arcwright/Materials/M_Workbench")
    r = cmd("get_actor_properties", actor_label=label)
    loc = r.get("data", {}).get("location", {})
    print(f"    {label}: ({loc.get('x',0):.0f},{loc.get('y',0):.0f},{loc.get('z',0):.0f})")

# Lights
print("\n  Spawning lights...")
cmd("spawn_actor_at", label="Light_Main", x=0, y=0, z=280, **{"class": "PointLight"})
for label, x, y, z in stations:
    cmd("spawn_actor_at", label=f"Light_{label.replace('Station_','')}", x=x, y=y, z=250,
        **{"class": "PointLight"})

# PlayerStart
cmd("set_actor_transform", actor_label="PlayerStart", x=0, y=0, z=50, yaw=0)

# Game mode
cmd("set_game_mode", game_mode="BP_BoreAndStrokeGameMode")

# Save
cmd("save_all")
print("\n  Level saved!")

# Take editor screenshot
r = cmd("take_viewport_screenshot")
print(f"\n  Editor screenshot: {r.get('data',{}).get('path')}")

# Play test
print("\n" + "=" * 60)
print("PLAY TEST")
print("=" * 60)

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
    time.sleep(4)
    cmd("take_viewport_screenshot")
    r = cmd("get_output_log", lines=100)
    bp_msgs = [str(l) for l in r.get("data",{}).get("lines",[]) if "BlueprintUserMessages" in str(l)]
    print(f"  Blueprint messages: {len(bp_msgs)}")
    for m in bp_msgs:
        print(f"    {m[:100]}")
    cmd("stop_play")
    time.sleep(1)

# Analyze
ss = "C:/Users/sparu/AppData/Local/Temp/arcwright_preview.png"
if os.path.exists(ss):
    try:
        from PIL import Image
        img = Image.open(ss)
        pixels = list(img.getdata())
        brightness = sum((p[0]+p[1]+p[2])/3 for p in pixels) / len(pixels)
        print(f"\n  Screenshot brightness: {brightness:.0f}/255")
        if brightness < 80:
            print("  DARK interior — walls and ceiling visible!")
        elif brightness < 130:
            print("  MEDIUM — some enclosure visible")
        else:
            print("  BRIGHT — still open sky")
    except ImportError:
        pass

print("\nDone.")
