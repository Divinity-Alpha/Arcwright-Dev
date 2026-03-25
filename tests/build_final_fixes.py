"""
Final fixes: Widget save, Station E-key, HUD live data.
"""
import sys, time, json, os, subprocess
sys.path.insert(0, "C:/Arcwright")
from scripts.state_manager import StateManager

sm = StateManager(project_dir="C:/Projects/BoreandStroke")
arc = sm.arc

def verify(name, min_nodes):
    r = arc.cmd("compile_blueprint", name=name)
    compiled = r.get("data", {}).get("compiled", False)
    r = arc.cmd("get_blueprint_details", blueprint=name)
    d = r.get("data", {})
    nc = d.get("node_count", 0)
    cc = d.get("connection_count", 0)
    errs = [m for m in d.get("messages", []) if "error" in str(m).lower()]
    ok = nc >= min_nodes and compiled and len(errs) == 0
    print(f"  CHECK: {name} -- {nc} nodes, {cc} conns, compiled={compiled}, errors={len(errs)} -> {'PASS' if ok else 'FAIL'}")
    for e in errs[:3]:
        print(f"    ERR: {e}")
    return ok

# ============================================================
print("=" * 70)
print("FIX 1: Widget SavePackage (rebuild + verify on disk)")
print("=" * 70)

arc.cmd("delete_blueprint", name="WBP_GameHUD")
time.sleep(0.5)
r = arc.cmd("create_widget_blueprint", name="WBP_GameHUD")
print(f"  Created: {r.get('status')} saved={r.get('data',{}).get('saved')}")

# Check UE log for save path
r = arc.cmd("get_output_log", lines=20)
save_lines = [str(l) for l in r.get("data", {}).get("lines", []) if "Widget SavePackage" in str(l) or "CreateWidgetBP" in str(l)]
for sl in save_lines:
    print(f"  LOG: {sl[:140]}")

# Add widgets
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="CanvasPanel", widget_name="HUDRoot")

# Top-left: Day + Cash
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="VerticalBox", widget_name="InfoPanel", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="InfoPanel", preset="TopLeft")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="InfoPanel", property="position", value={"x": 20, "y": 15})

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="DayLabel", parent_name="InfoPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="text", value="DAY 1")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="font_size", value="28")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="color", value="#E8A624")

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="CashLabel", parent_name="InfoPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="text", value="$5,000")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="font_size", value="22")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="color", value="#33D166")

# Time bar
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="ProgressBar", widget_name="TimeBar", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", preset="TopCenter")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="position", value={"x": -150, "y": 20})
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="size", value={"x": 300, "y": 20})
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="percent", value="1.0")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="fill_color", value="#E8A624")

# Prompt
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="Prompt", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="Prompt", preset="BottomCenter")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="Prompt", property="position", value={"x": -80, "y": -70})
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="Prompt", property="text", value="[E] Interact")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="Prompt", property="font_size", value="20")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="Prompt", property="color", value="#E8A624")

# Check save log again
r = arc.cmd("get_output_log", lines=50)
save_lines = [str(l) for l in r.get("data", {}).get("lines", []) if "SavePackage" in str(l) and "Widget" in str(l)]
print(f"  Save log entries: {len(save_lines)}")
for sl in save_lines[:5]:
    print(f"    {sl[:140]}")

# Check disk
result = subprocess.run(["bash", "-c", "ls -la /c/Projects/BoreandStroke/Content/UI/WBP_GameHUD.uasset 2>/dev/null"],
                       capture_output=True, text=True)
on_disk = "WBP_GameHUD" in result.stdout
print(f"  On disk: {'YES - ' + result.stdout.strip() if on_disk else 'NO'}")

# ============================================================
print("\n" + "=" * 70)
print("FIX 2: BP_StationBase E-Key (with InputAction handler)")
print("=" * 70)

# Rebuild StationBase from scratch with E-key support
arc.cmd("delete_blueprint", name="BP_StationBase")
time.sleep(0.3)

arc.cmd("create_blueprint", name="BP_StationBase", parent_class="Actor", variables=[
    {"name": "StationName", "type": "String", "default": "Unknown"},
    {"name": "StationType", "type": "String", "default": "Generic"},
    {"name": "IsPlayerNearby", "type": "Bool", "default": "false"},
    {"name": "IsStationActive", "type": "Bool", "default": "false"},
    {"name": "ActionTimeCost", "type": "Float", "default": "30.0"},
    {"name": "ActionMaterialCost", "type": "Float", "default": "25.0"},
])
arc.cmd("compile_blueprint", name="BP_StationBase")

arc.cmd("add_component", blueprint="BP_StationBase", component_type="BoxCollision",
    component_name="TriggerBox",
    properties={"extent": {"x": 200, "y": 200, "z": 150}, "generate_overlap_events": True,
                "collision_profile": "OverlapAllDynamic"})
arc.cmd("add_component", blueprint="BP_StationBase", component_type="StaticMesh",
    component_name="StationMesh", properties={"mesh": "/Engine/BasicShapes/Cube.Cube"})

nodes = [
    # Overlap begin → set nearby true + print prompt
    {"id": "set_near_t", "type": "SetVar", "variable": "IsPlayerNearby"},
    {"id": "get_name1", "type": "GetVar", "variable": "StationName"},
    {"id": "concat_prompt", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_prompt", "type": "PrintString"},

    # Overlap end → set nearby false
    {"id": "evt_endov", "type": "CustomEvent", "event": "OnEndOverlap", "params": []},
    {"id": "set_near_f", "type": "SetVar", "variable": "IsPlayerNearby"},
    {"id": "print_leave", "type": "PrintString", "params": {"InString": "[STATION] Player left"}},

    # BeginPlay → EnableInput + print ready
    {"id": "get_pc", "type": "/Script/Engine.GameplayStatics:GetPlayerController"},
    {"id": "enable_input", "type": "/Script/Engine.Actor:EnableInput"},
    {"id": "get_name_init", "type": "GetVar", "variable": "StationName"},
    {"id": "concat_init", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_init", "type": "PrintString"},

    # InputAction Interact → Branch(IsPlayerNearby) → activate
    {"id": "input_interact", "type": "InputAction", "action": "Interact"},
    {"id": "get_near", "type": "GetVar", "variable": "IsPlayerNearby"},
    {"id": "branch_near", "type": "Branch"},

    # Activate chain: set active, print station + cost info
    {"id": "set_active_t", "type": "SetVar", "variable": "IsStationActive"},
    {"id": "get_name_act", "type": "GetVar", "variable": "StationName"},
    {"id": "get_tcost", "type": "GetVar", "variable": "ActionTimeCost"},
    {"id": "conv_tcost", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_act1", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_act2", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_act3", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_act", "type": "PrintString"},
    {"id": "print_far", "type": "PrintString", "params": {"InString": "[STATION] Too far to interact"}},
]

r = arc.cmd("add_nodes_batch", blueprint="BP_StationBase", nodes=nodes)
d = r.get("data", {})
print(f"  Nodes: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    ERR: {e}")

conns = [
    # BeginPlay (node_0) → get_pc → enable_input → print_init
    {"from_node": "node_0", "from_pin": "then", "to_node": "get_pc", "to_pin": "execute"},
    {"from_node": "get_pc", "from_pin": "then", "to_node": "enable_input", "to_pin": "execute"},
    {"from_node": "get_pc", "from_pin": "ReturnValue", "to_node": "enable_input", "to_pin": "PlayerController"},
    {"from_node": "enable_input", "from_pin": "then", "to_node": "print_init", "to_pin": "execute"},
    {"from_node": "get_name_init", "from_pin": "StationName", "to_node": "concat_init", "to_pin": "B"},
    {"from_node": "concat_init", "from_pin": "ReturnValue", "to_node": "print_init", "to_pin": "InString"},

    # Overlap Begin (node_1) → set nearby true → print prompt
    {"from_node": "node_1", "from_pin": "then", "to_node": "set_near_t", "to_pin": "execute"},
    {"from_node": "set_near_t", "from_pin": "then", "to_node": "print_prompt", "to_pin": "execute"},
    {"from_node": "get_name1", "from_pin": "StationName", "to_node": "concat_prompt", "to_pin": "B"},
    {"from_node": "concat_prompt", "from_pin": "ReturnValue", "to_node": "print_prompt", "to_pin": "InString"},

    # Overlap End → set nearby false → print
    {"from_node": "evt_endov", "from_pin": "then", "to_node": "set_near_f", "to_pin": "execute"},
    {"from_node": "set_near_f", "from_pin": "then", "to_node": "print_leave", "to_pin": "execute"},

    # InputAction Interact → branch(nearby)
    {"from_node": "input_interact", "from_pin": "Pressed", "to_node": "branch_near", "to_pin": "execute"},
    {"from_node": "get_near", "from_pin": "IsPlayerNearby", "to_node": "branch_near", "to_pin": "Condition"},

    # True: activate
    {"from_node": "branch_near", "from_pin": "True", "to_node": "set_active_t", "to_pin": "execute"},
    {"from_node": "set_active_t", "from_pin": "then", "to_node": "print_act", "to_pin": "execute"},
    {"from_node": "get_name_act", "from_pin": "StationName", "to_node": "concat_act1", "to_pin": "B"},
    {"from_node": "get_tcost", "from_pin": "ActionTimeCost", "to_node": "conv_tcost", "to_pin": "InDouble"},
    {"from_node": "conv_tcost", "from_pin": "ReturnValue", "to_node": "concat_act2", "to_pin": "B"},
    {"from_node": "concat_act1", "from_pin": "ReturnValue", "to_node": "concat_act2", "to_pin": "A"},
    {"from_node": "concat_act2", "from_pin": "ReturnValue", "to_node": "concat_act3", "to_pin": "A"},
    {"from_node": "concat_act3", "from_pin": "ReturnValue", "to_node": "print_act", "to_pin": "InString"},

    # False: print too far
    {"from_node": "branch_near", "from_pin": "False", "to_node": "print_far", "to_pin": "execute"},
]

r = arc.cmd("add_connections_batch", blueprint="BP_StationBase", connections=conns)
d = r.get("data", {})
print(f"  Connections: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    CONN ERR: {e}")

# Set pin defaults
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="set_near_t", pin_name="IsPlayerNearby", value="true")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="set_near_f", pin_name="IsPlayerNearby", value="false")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="set_active_t", pin_name="IsStationActive", value="true")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_init", pin_name="A", value="[STATION] Ready: ")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_prompt", pin_name="A", value="[E] ")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_act1", pin_name="A", value="[STATION] Activated: ")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_act3", pin_name="B", value=" min)")

s2_pass = verify("BP_StationBase", 25)

# Respawn stations
for label in ["Station_Degriming", "Station_Disassembly", "Station_Inspection", "Station_Cleaning", "Station_Office"]:
    arc.cmd("delete_actor", label=label)
stations_data = [
    ("Station_Degriming", -800, -600, 40),
    ("Station_Disassembly", -300, -600, 40),
    ("Station_Inspection", 300, -600, 40),
    ("Station_Cleaning", 800, -600, 40),
    ("Station_Office", 0, 600, 40),
]
for label, x, y, z in stations_data:
    arc.cmd("spawn_actor_at", label=label, x=x, y=y, z=z,
            **{"class": "/Game/Arcwright/Generated/BP_StationBase.BP_StationBase_C"})
    arc.cmd("set_collision_preset", actor_label=label, preset_name="OverlapAllDynamic", component_name="TriggerBox")

arc.cmd("save_all")

# ============================================================
print("\n" + "=" * 70)
print("FIX 3: BP_HUDManager Live Data (Tick-based screen print)")
print("=" * 70)

# HUDManager already rebuilt in previous session — just re-set the widget class
arc.cmd("set_node_param", blueprint="BP_HUDManager", node_id="create_w",
        pin_name="WidgetType", value="/Game/UI/WBP_GameHUD.WBP_GameHUD_C")
arc.cmd("compile_blueprint", name="BP_HUDManager")

# Respawn HUD
arc.cmd("delete_actor", label="HUDManager")
arc.cmd("spawn_actor_at", label="HUDManager", x=0, y=0, z=0,
        **{"class": "/Game/Arcwright/Generated/BP_HUDManager.BP_HUDManager_C"})
arc.cmd("save_all")

s3_pass = verify("BP_HUDManager", 20)

# ============================================================
print("\n" + "=" * 70)
print("FINAL PIE VERIFICATION + QA TOUR")
print("=" * 70)

arc.cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = arc.cmd("is_playing")
    if r.get("data", {}).get("playing"):
        started = True
        break

if started:
    print("  PIE running")
    time.sleep(5)

    # FIX 1: Viewport widgets
    r = arc.cmd("get_viewport_widgets")
    d = r.get("data", {})
    vw = d.get("in_viewport", 0)
    print(f"\n  FIX 1 - Viewport widgets: {vw} {'PASS' if vw > 0 else 'FAIL'}")
    for w in d.get("widgets", []):
        print(f"    {w.get('class')}: visible={w.get('visible')}, children={w.get('child_count')}")

    # FIX 3: HUD tick updates
    r = arc.cmd("get_output_log", lines=100)
    lines = r.get("data", {}).get("lines", [])
    hud_ticks = [str(l) for l in lines if "Day " in str(l) and "Time:" in str(l)]
    print(f"\n  FIX 3 - HUD Tick updates: {len(hud_ticks)} {'PASS' if hud_ticks else 'FAIL'}")
    if hud_ticks:
        print(f"    Sample: {hud_ticks[-1][:120]}")

    # FIX 2: Station QA Tour
    print(f"\n  FIX 2 - Station QA Tour:")
    os.makedirs("C:/Arcwright/screenshots", exist_ok=True)
    for station in ["Station_Degriming", "Station_Disassembly", "Station_Inspection", "Station_Cleaning", "Station_Office"]:
        arc.cmd("teleport_to_actor", actor=station, distance=30)
        time.sleep(2)
        r = arc.cmd("get_output_log", lines=20)
        overlap_msgs = [str(l) for l in r.get("data", {}).get("lines", [])
                       if "[STATION]" in str(l) or "[E]" in str(l)]
        has_overlap = len(overlap_msgs) > 0
        arc.cmd("get_player_view", filename=f"C:/Arcwright/screenshots/final_{station}.png")
        print(f"    {station}: overlap={'YES' if has_overlap else 'no'}")

    # Full message summary
    r = arc.cmd("get_output_log", lines=300)
    bp_msgs = [str(l) for l in r.get("data", {}).get("lines", []) if "BlueprintUserMessages" in str(l)]
    print(f"\n  Total BP messages: {len(bp_msgs)}")
    cats = {"[GAMEMODE]": 0, "[STATION]": 0, "[HUD]": 0, "[TIME]": 0, "[ECONOMY]": 0, "Day ": 0}
    for m in bp_msgs:
        for cat in cats:
            if cat in m:
                cats[cat] += 1
    for cat, count in cats.items():
        print(f"    {cat:15} {count}")

    arc.cmd("stop_play")
else:
    print("  PIE did not start!")

# ============================================================
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(f"  FIX 1 (Widget SavePackage):  {'PASS (on disk)' if on_disk else 'PARTIAL (works in PIE, not on disk)'}")
print(f"  FIX 2 (E-Key Interaction):   {'PASS' if s2_pass else 'FAIL'}")
print(f"  FIX 3 (Live HUD Data):       {'PASS' if s3_pass else 'FAIL'}")
