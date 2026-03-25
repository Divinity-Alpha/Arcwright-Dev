"""Create WBP_MainHUD with BSMainHUDWidget parent + full industrial HUD layout.
Then PIE to verify live subsystem data."""
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
print("Creating WBP_MainHUD with BSMainHUDWidget parent")
print("=" * 60)

# Create with C++ parent
r = cmd("create_widget_blueprint", name="WBP_MainHUD",
        parent_class="/Script/BoreAndStroke.BSMainHUDWidget")
print(f"Created: {r.get('status')} saved={r.get('data',{}).get('saved')}")
print(f"Parent: {r.get('data',{}).get('parent_class')}")

# Build HUD layout — dark industrial theme per GDD
# Root canvas
cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="CanvasPanel", widget_name="HUDRoot")

# === TOP-LEFT: Day/Date + Cash ===
cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="VerticalBox", widget_name="InfoPanel", parent_name="HUDRoot")
cmd("set_widget_anchor", widget_blueprint="WBP_MainHUD", widget_name="InfoPanel", preset="TopLeft")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="InfoPanel", property="position", value={"x": 20, "y": 15})

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_Date", parent_name="InfoPanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Date", property="text", value="Mar 1, 1957")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Date", property="font_size", value="28")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Date", property="color", value="#E8A624")

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_Cash", parent_name="InfoPanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Cash", property="text", value="$500.00")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Cash", property="font_size", value="22")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Cash", property="color", value="#33D166")

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_Overhead", parent_name="InfoPanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Overhead", property="text", value="Overhead: $50/day")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Overhead", property="font_size", value="13")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Overhead", property="color", value="#666666")

# === TOP-CENTER: Time remaining bar ===
cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="VerticalBox", widget_name="TimePanel", parent_name="HUDRoot")
cmd("set_widget_anchor", widget_blueprint="WBP_MainHUD", widget_name="TimePanel", preset="TopCenter")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="TimePanel", property="position", value={"x": -150, "y": 15})

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_TimeLabel", parent_name="TimePanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_TimeLabel", property="text", value="WORK DAY")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_TimeLabel", property="font_size", value="12")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_TimeLabel", property="color", value="#999999")

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="ProgressBar", widget_name="bar_TimeRemaining", parent_name="TimePanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="bar_TimeRemaining", property="percent", value="1.0")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="bar_TimeRemaining", property="fill_color", value="#E8A624")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="bar_TimeRemaining", property="size", value={"x": 300, "y": 18})

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_TimeRemaining", parent_name="TimePanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_TimeRemaining", property="text", value="8h 00m remaining")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_TimeRemaining", property="font_size", value="14")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_TimeRemaining", property="color", value="#CCCCCC")

# === TOP-RIGHT: Shop info ===
cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="VerticalBox", widget_name="ShopPanel", parent_name="HUDRoot")
cmd("set_widget_anchor", widget_blueprint="WBP_MainHUD", widget_name="ShopPanel", preset="TopRight")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="ShopPanel", property="position", value={"x": -180, "y": 15})

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_ShopTier", parent_name="ShopPanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_ShopTier", property="text", value="TIER 1 - Garage")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_ShopTier", property="font_size", value="14")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_ShopTier", property="color", value="#E8A624")

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_EngineCount", parent_name="ShopPanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_EngineCount", property="text", value="Engines: 0")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_EngineCount", property="font_size", value="13")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_EngineCount", property="color", value="#AAAAAA")

cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_Reputation", parent_name="ShopPanel")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Reputation", property="text", value="REP: 50")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Reputation", property="font_size", value="13")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_Reputation", property="color", value="#FFC733")

# === BOTTOM-CENTER: Interaction prompt ===
cmd("add_widget_child", widget_blueprint="WBP_MainHUD", widget_type="TextBlock", widget_name="txt_InteractionPrompt", parent_name="HUDRoot")
cmd("set_widget_anchor", widget_blueprint="WBP_MainHUD", widget_name="txt_InteractionPrompt", preset="BottomCenter")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_InteractionPrompt", property="position", value={"x": -100, "y": -70})
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_InteractionPrompt", property="text", value="")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_InteractionPrompt", property="font_size", value="20")
cmd("set_widget_property", widget_blueprint="WBP_MainHUD", widget_name="txt_InteractionPrompt", property="color", value="#E8A624")

# Verify widget tree
r = cmd("get_widget_tree", widget_blueprint="WBP_MainHUD")
wcount = r.get("data", {}).get("total_widgets", 0)
print(f"\nWidget tree: {wcount} elements")
cmd("save_all")

# Verify on disk
import subprocess
result = subprocess.run(["bash", "-c", "ls -la /c/Projects/BoreAndStroke_Original/Content/WBP_MainHUD.uasset 2>/dev/null"],
                       capture_output=True, text=True)
on_disk = "WBP_MainHUD" in result.stdout
print(f"On disk: {'YES' if on_disk else 'NO'} {result.stdout.strip()}")

# Check compile warnings
r = cmd("get_output_log", lines=30)
warns = [str(l) for l in r.get("data",{}).get("lines",[])
         if "always fail" in str(l) or "does not inherit" in str(l) or "SetInteractionPrompt" in str(l)]
print(f"Compile warnings: {len(warns)}")
for w in warns:
    print(f"  {w[:140]}")

# === PIE TEST ===
print("\n" + "=" * 60)
print("PIE VERIFICATION")
print("=" * 60)

cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = cmd("is_playing")
    if r.get("data",{}).get("playing"):
        started = True
        break

if started:
    print("PIE running")
    time.sleep(5)

    # Check viewport widgets
    r = cmd("get_viewport_widgets")
    d = r.get("data", {})
    vw = d.get("in_viewport", 0)
    print(f"\nViewport widgets: {vw}")
    for w in d.get("widgets", []):
        print(f"  {w.get('class')}: in_viewport={w.get('in_viewport')}, children={w.get('child_count')}")
        if w.get("in_viewport"):
            for child in w.get("children", [])[:15]:
                text = child.get("text", "")
                pct = child.get("percent", "")
                extra = ""
                if text: extra = f' "{text}"'
                elif pct != "": extra = f" {pct}"
                print(f"    {child.get('name')}: {child.get('type')}{extra}")

    # Check log for HUD diagnostic
    r = cmd("get_output_log", lines=100)
    lines = r.get("data",{}).get("lines",[])
    hud_msgs = [str(l) for l in lines if "BSPlayerController" in str(l) or "HUD" in str(l) or "InitHUD" in str(l)]
    print(f"\nHUD log ({len(hud_msgs)}):")
    for m in hud_msgs[:5]:
        print(f"  {m[:140]}")

    # Screenshot
    os.makedirs("C:/BlueprintLLM/screenshots", exist_ok=True)
    cmd("get_player_view", filename="C:/BlueprintLLM/screenshots/bs_hud_final_v2.png")
    print("\nScreenshot: bs_hud_final_v2.png")

    cmd("stop_play")
else:
    print("PIE did not start!")

print("\n" + "=" * 60)
print("COMPLETE")
print("=" * 60)
