"""Fix HUD: Create WBP_GameHUD widget + rebuild BP_HUDManager with CreateWidget + AddToViewport."""
import socket, json, time

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
print("STEP 1: Create WBP_GameHUD Widget")
print("=" * 60)

r = cmd("create_widget_blueprint", name="WBP_GameHUD")
print(f"  Created WBP_GameHUD: {r.get('status')}")

r = cmd("add_widget_child", widget_name="WBP_GameHUD", type="CanvasPanel", name="Root")
print(f"  Root CanvasPanel: {r.get('status')}")

# Day counter (top-left)
cmd("add_widget_child", widget_name="WBP_GameHUD", type="TextBlock", name="DayLabel", parent="Root")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="DayLabel", property="Text", value="DAY 1")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="DayLabel", property="FontSize", value="28")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="DayLabel", property="Color", value="#FFFFFF")
cmd("set_widget_anchor", widget_name="WBP_GameHUD", target="DayLabel", preset="TopLeft")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="DayLabel", property="position", value={"x": 30, "y": 20})
print("  DayLabel: ok")

# Cash display (top-right)
cmd("add_widget_child", widget_name="WBP_GameHUD", type="TextBlock", name="CashLabel", parent="Root")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="CashLabel", property="Text", value="$5,000")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="CashLabel", property="FontSize", value="24")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="CashLabel", property="Color", value="#33D166")
cmd("set_widget_anchor", widget_name="WBP_GameHUD", target="CashLabel", preset="TopRight")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="CashLabel", property="position", value={"x": -200, "y": 20})
print("  CashLabel: ok")

# Time bar (top-center)
cmd("add_widget_child", widget_name="WBP_GameHUD", type="ProgressBar", name="TimeBar", parent="Root")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeBar", property="Percent", value="0.75")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeBar", property="FillColor", value="#4A9EFF")
cmd("set_widget_anchor", widget_name="WBP_GameHUD", target="TimeBar", preset="TopCenter")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeBar", property="position", value={"x": -150, "y": 15})
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeBar", property="size", value={"x": 300, "y": 25})
print("  TimeBar: ok")

# Time label
cmd("add_widget_child", widget_name="WBP_GameHUD", type="TextBlock", name="TimeLabel", parent="Root")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeLabel", property="Text", value="8:00 AM")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeLabel", property="FontSize", value="16")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeLabel", property="Color", value="#CCCCCC")
cmd("set_widget_anchor", widget_name="WBP_GameHUD", target="TimeLabel", preset="TopCenter")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="TimeLabel", property="position", value={"x": -40, "y": 45})
print("  TimeLabel: ok")

# Reputation (bottom-left)
cmd("add_widget_child", widget_name="WBP_GameHUD", type="TextBlock", name="RepLabel", parent="Root")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="RepLabel", property="Text", value="REP: 50")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="RepLabel", property="FontSize", value="18")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="RepLabel", property="Color", value="#FFC733")
cmd("set_widget_anchor", widget_name="WBP_GameHUD", target="RepLabel", preset="BottomLeft")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="RepLabel", property="position", value={"x": 30, "y": -60})
print("  RepLabel: ok")

# Station prompt (bottom-center)
cmd("add_widget_child", widget_name="WBP_GameHUD", type="TextBlock", name="StationPrompt", parent="Root")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="StationPrompt", property="Text", value="Press E to interact")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="StationPrompt", property="FontSize", value="20")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="StationPrompt", property="Color", value="#FFFFFF")
cmd("set_widget_anchor", widget_name="WBP_GameHUD", target="StationPrompt", preset="BottomCenter")
cmd("set_widget_property", widget_name="WBP_GameHUD", target="StationPrompt", property="position", value={"x": -100, "y": -80})
print("  StationPrompt: ok")

# Verify widget tree
r = cmd("get_widget_tree", widget_name="WBP_GameHUD")
tree = r.get("data", {})
print(f"  Widget count: {tree.get('widget_count', '?')}")

print()
print("=" * 60)
print("STEP 2: Rebuild BP_HUDManager with CreateWidget + AddToViewport")
print("=" * 60)

# Delete old HUDManager
cmd("delete_actor", label="HUDManager")
cmd("delete_blueprint", name="BP_HUDManager")
time.sleep(0.5)

# Create fresh BP
r = cmd("create_blueprint", name="BP_HUDManager", parent_class="Actor")
print(f"  Created BP_HUDManager: {r.get('status')}")

# Add CreateWidget + AddToViewport + PrintString
r = cmd("add_nodes_batch", blueprint="BP_HUDManager", nodes=[
    {"node_id": "create_widget", "node_type": "/Script/UMG.WidgetBlueprintLibrary:Create"},
    {"node_id": "add_viewport", "node_type": "/Script/UMG.UserWidget:AddToViewport"},
    {"node_id": "print_ok", "node_type": "PrintString", "params": {"InString": "HUD Active"}},
])
d = r.get("data", {})
print(f"  Nodes: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    Error: {e}")

# Wire: node_0 (BeginPlay) -> CreateWidget -> AddToViewport -> PrintString
r = cmd("add_connections_batch", blueprint="BP_HUDManager", connections=[
    {"from_node": "node_0", "from_pin": "then", "to_node": "create_widget", "to_pin": "execute"},
    {"from_node": "create_widget", "from_pin": "then", "to_node": "add_viewport", "to_pin": "execute"},
    {"from_node": "create_widget", "from_pin": "ReturnValue", "to_node": "add_viewport", "to_pin": "self"},
    {"from_node": "add_viewport", "from_pin": "then", "to_node": "print_ok", "to_pin": "execute"},
])
d = r.get("data", {})
print(f"  Connections: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    Error: {e}")

# Set the CreateWidget class pin to WBP_GameHUD
# Try multiple pin names since it varies
for pin_name in ["WidgetType", "Class", "WidgetClass"]:
    r = cmd("set_node_param", blueprint="BP_HUDManager", node_id="create_widget",
            param_name=pin_name, param_value="/Game/UI/WBP_GameHUD.WBP_GameHUD_C")
    if r.get("status") == "ok":
        print(f"  Set widget class via '{pin_name}': ok")
        break
    else:
        print(f"  Tried '{pin_name}': {r.get('message', '')[:80]}")

# Compile
r = cmd("compile_blueprint", name="BP_HUDManager")
print(f"  Compiled: {r.get('data',{}).get('compiled')}, Saved: {r.get('data',{}).get('saved')}")

# Check graph
r = cmd("get_blueprint_details", blueprint="BP_HUDManager")
d = r.get("data", {})
print(f"  Graph: {d.get('node_count')} nodes, {d.get('connection_count')} connections")
for node in d.get("nodes", []):
    print(f"    {node.get('id')}: {node.get('title')} ({node.get('class')})")
print("  Connections:")
for conn in d.get("connections", []):
    print(f"    {conn.get('source_node')}.{conn.get('source_pin')} -> {conn.get('target_node')}.{conn.get('target_pin')}")

# Check compiler messages
msgs = d.get("messages", [])
if msgs:
    print("  Compiler messages:")
    for m in msgs:
        print(f"    {m}")

# Spawn HUDManager
r = cmd("spawn_actor_at", label="HUDManager", x=0, y=0, z=0,
        **{"class": "/Game/Arcwright/Generated/BP_HUDManager.BP_HUDManager_C"})
print(f"  Spawned HUDManager: {r.get('status')}")

cmd("save_all")
print("  Saved!")

# Verify with PIE
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
    print("  PIE started")
    time.sleep(3)

    # Check for HUD messages
    r = cmd("get_output_log", lines=100)
    lines = r.get("data", {}).get("lines", [])
    hud_msgs = [str(l) for l in lines if "HUD" in str(l) or "Widget" in str(l)]
    print(f"  HUD-related messages: {len(hud_msgs)}")
    for m in hud_msgs:
        print(f"    {m[:120]}")

    # Take screenshot to see if HUD is visible
    import os
    os.makedirs("C:/Arcwright/screenshots", exist_ok=True)
    cmd("get_player_view", filename="C:/Arcwright/screenshots/hud_test.png")
    print("  Screenshot: screenshots/hud_test.png")

    cmd("stop_play")
    time.sleep(1)
else:
    print("  PIE did not start!")

print()
print("=" * 60)
print("HUD FIX COMPLETE")
print("=" * 60)
