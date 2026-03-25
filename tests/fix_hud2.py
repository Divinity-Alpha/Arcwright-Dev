"""Rebuild WBP_GameHUD with correct param names + verify in PIE."""
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

# Stop PIE
r = cmd("is_playing")
if r.get("data", {}).get("playing"):
    cmd("stop_play")
    time.sleep(1)

print("=" * 60)
print("STEP 1: Rebuild WBP_GameHUD")
print("=" * 60)

cmd("delete_blueprint", name="WBP_GameHUD")
time.sleep(0.5)
r = cmd("create_widget_blueprint", name="WBP_GameHUD")
print(f"  Created: {r.get('status')}")

# Root canvas panel
cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="CanvasPanel", widget_name="HUDPanel")

# Day counter (top-left)
cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="DayLabel", parent_name="HUDPanel")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="text", value="DAY 1")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="font_size", value="28")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="color", value="#FFFFFF")
cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", preset="TopLeft")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="position", value={"x": 30, "y": 20})
print("  DayLabel: ok")

# Cash (top-right)
cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="CashLabel", parent_name="HUDPanel")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="text", value="Cash: 5000")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="font_size", value="24")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="color", value="#33D166")
cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", preset="TopRight")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="position", value={"x": -200, "y": 20})
print("  CashLabel: ok")

# Time bar (top-center)
cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="ProgressBar", widget_name="TimeBar", parent_name="HUDPanel")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="percent", value="0.75")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="fill_color", value="#4A9EFF")
cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", preset="TopCenter")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="position", value={"x": -150, "y": 15})
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="size", value={"x": 300, "y": 25})
print("  TimeBar: ok")

# Time label
cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TimeLabel", parent_name="HUDPanel")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeLabel", property="text", value="8:00 AM")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeLabel", property="font_size", value="16")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeLabel", property="color", value="#CCCCCC")
cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="TimeLabel", preset="TopCenter")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeLabel", property="position", value={"x": -40, "y": 45})
print("  TimeLabel: ok")

# Reputation (bottom-left)
cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="RepLabel", parent_name="HUDPanel")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", property="text", value="REP: 50")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", property="font_size", value="18")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", property="color", value="#FFC733")
cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", preset="BottomLeft")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", property="position", value={"x": 30, "y": -60})
print("  RepLabel: ok")

# Station prompt (bottom-center)
cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="StationPrompt", parent_name="HUDPanel")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="text", value="[E] Interact")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="font_size", value="20")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="color", value="#FFFFFF")
cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", preset="BottomCenter")
cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="position", value={"x": -60, "y": -80})
print("  StationPrompt: ok")

# Verify
r = cmd("get_widget_tree", widget_blueprint="WBP_GameHUD")
d = r.get("data", {})
print(f"  Total widgets: {d.get('total_widgets', 0)}")

cmd("save_all")

print()
print("=" * 60)
print("STEP 2: Update BP_HUDManager WidgetType pin")
print("=" * 60)

r = cmd("set_node_param", blueprint="BP_HUDManager", node_id="create_widget",
        pin_name="WidgetType", value="/Game/UI/WBP_GameHUD.WBP_GameHUD_C")
print(f"  WidgetType pin: {r.get('status')}")

r = cmd("compile_blueprint", name="BP_HUDManager")
print(f"  Compiled: {r.get('data',{}).get('compiled')}")

# Respawn
cmd("delete_actor", label="HUDManager")
cmd("spawn_actor_at", label="HUDManager", x=0, y=0, z=0,
    **{"class": "/Game/Arcwright/Generated/BP_HUDManager.BP_HUDManager_C"})
cmd("save_all")
print("  Respawned + saved")

print()
print("=" * 60)
print("STEP 3: PIE Verification")
print("=" * 60)

cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = cmd("is_playing")
    if r.get("data", {}).get("playing"):
        started = True
        break

if started:
    print("  PIE running")
    time.sleep(4)

    r = cmd("get_output_log", lines=100)
    lines = r.get("data", {}).get("lines", [])
    errors = [str(l) for l in lines if "Error" in str(l) and "Blueprint" in str(l)]
    hud_msgs = [str(l) for l in lines if "HUD" in str(l)]

    print(f"  Blueprint errors: {len(errors)}")
    for e in errors[:5]:
        print(f"    {e[:140]}")
    print(f"  HUD messages: {len(hud_msgs)}")
    for m in hud_msgs[:5]:
        print(f"    {m[:140]}")

    os.makedirs("C:/Arcwright/screenshots", exist_ok=True)
    cmd("get_player_view", filename="C:/Arcwright/screenshots/hud_final2.png")
    print("  Screenshot: hud_final2.png")

    cmd("stop_play")
    time.sleep(1)
else:
    print("  PIE did not start!")

print()
print("DONE")
