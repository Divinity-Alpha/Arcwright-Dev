"""Arcwright QA Tour — automated level verification via PIE player control."""
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
print("ARCWRIGHT QA TOUR")
print("=" * 60)

# Ensure screenshots dir exists
ss_dir = "C:/Projects/BoreandStroke/Saved/Screenshots"
os.makedirs(ss_dir, exist_ok=True)

# Start PIE
print("\n1. Starting PIE...")
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

if not started:
    print("   PIE failed to start!")
    exit(1)

print("   PIE started")
time.sleep(2)

# 2. Check starting position
print("\n2. Player starting position")
r = cmd("get_player_location")
if r["status"] == "ok":
    d = r["data"]
    print(f"   Location: ({d.get('x',0):.0f}, {d.get('y',0):.0f}, {d.get('z',0):.0f})")
    print(f"   Rotation: pitch={d.get('pitch',0):.0f} yaw={d.get('yaw',0):.0f}")

# 3. Teleport to center, look at stations
print("\n3. Center view")
r = cmd("teleport_player", x=0, y=0, z=100)
print(f"   Teleported: {r.get('status')}")
time.sleep(0.5)

r = cmd("look_at", x=0, y=-600, z=50)
print(f"   Looking at stations: {r.get('status')}")
time.sleep(1)

r = cmd("get_player_view", filename=os.path.join(ss_dir, "qa_center.png"))
print(f"   Screenshot: {r.get('data',{}).get('path','?')}")

# 4. Visit each station
print("\n4. Station tour")
stations = ["Station_Degriming", "Station_Disassembly", "Station_Inspection",
            "Station_Cleaning", "Station_Office"]

for station in stations:
    r = cmd("teleport_to_actor", actor=station, distance=250)
    if r["status"] == "ok":
        d = r["data"]
        print(f"   {station}: teleported to ({d.get('x',0):.0f},{d.get('y',0):.0f},{d.get('z',0):.0f})")
    else:
        print(f"   {station}: {r.get('message', r.get('error', '?'))}")
        continue
    time.sleep(1)
    fname = os.path.join(ss_dir, f"qa_{station}.png")
    cmd("get_player_view", filename=fname)

# 5. Visit walls
print("\n5. Wall verification")
for wall in ["Wall_North", "Wall_South", "Wall_East", "Wall_West"]:
    r = cmd("teleport_to_actor", actor=wall, distance=300)
    if r["status"] == "ok":
        d = r["data"]
        print(f"   {wall}: at ({d.get('x',0):.0f},{d.get('y',0):.0f},{d.get('z',0):.0f}), target=({d.get('target_x',0):.0f},{d.get('target_y',0):.0f},{d.get('target_z',0):.0f})")
    else:
        print(f"   {wall}: {r.get('message', '?')}")
    time.sleep(1)
    cmd("get_player_view", filename=os.path.join(ss_dir, f"qa_{wall}.png"))

# 6. Floor check — look down
print("\n6. Floor check")
cmd("teleport_player", x=0, y=0, z=200)
r = cmd("look_at", x=0, y=0, z=-10)
print(f"   Looking down at floor: {r.get('status')}")
time.sleep(1)
cmd("get_player_view", filename=os.path.join(ss_dir, "qa_floor.png"))

# 7. Ceiling check — look up
print("\n7. Ceiling check")
r = cmd("look_at", x=0, y=0, z=310)
print(f"   Looking up at ceiling: {r.get('status')}")
time.sleep(1)
cmd("get_player_view", filename=os.path.join(ss_dir, "qa_ceiling.png"))

# 8. Check Blueprint messages
print("\n8. Blueprint log check")
r = cmd("get_output_log", lines=100)
bp_msgs = [str(l) for l in r.get("data",{}).get("lines",[]) if "BlueprintUserMessages" in str(l)]
print(f"   Blueprint messages: {len(bp_msgs)}")
for m in bp_msgs:
    print(f"     {m[:100]}")

# Stop PIE
cmd("stop_play")
time.sleep(1)

# 9. Analyze screenshots
print("\n9. Screenshot analysis")
try:
    from PIL import Image
    for f in sorted(os.listdir(ss_dir)):
        if f.startswith("qa_"):
            path = os.path.join(ss_dir, f)
            img = Image.open(path)
            pixels = list(img.getdata())
            avg = sum((p[0]+p[1]+p[2])/3 for p in pixels) / len(pixels)
            size_kb = os.path.getsize(path) // 1024
            verdict = "DARK(indoor)" if avg < 80 else ("MEDIUM" if avg < 130 else "BRIGHT(outdoor)")
            print(f"   {f}: {img.size[0]}x{img.size[1]} {size_kb}KB brightness={avg:.0f} {verdict}")
except ImportError:
    print("   PIL not available — check screenshots manually")
    for f in sorted(os.listdir(ss_dir)):
        if f.startswith("qa_"):
            size = os.path.getsize(os.path.join(ss_dir, f))
            print(f"   {f}: {size} bytes")

print("\n" + "=" * 60)
print("QA TOUR COMPLETE")
