"""
SYSTEM 2: BP_TimeManager — Day Cycle
Design:
  Variables: HumanTimeRemaining (Float, 480=8hrs in minutes), MaxDailyTime (Float, 480),
             DayNumber (Int, 1), IsDayActive (Bool, true), TimeSpeed (Float, 1.0)
  Events:
    ConsumeTime(Minutes:Float) — deducts from HumanTimeRemaining, checks if day should end
    EndDay() — resets time, increments day, prints summary
    StartNewDay() — resets HumanTimeRemaining to MaxDailyTime
  BeginPlay: Initialize, print "Day 1 begins"
  Target: 40+ nodes
"""
import sys, time
sys.path.insert(0, "C:/Arcwright")
from scripts.state_manager import StateManager

sm = StateManager(project_dir="C:/Projects/BoreandStroke")
arc = sm.arc

print("=" * 70)
print("SYSTEM 2: BP_TimeManager")
print("=" * 70)

arc.cmd("delete_blueprint", name="BP_TimeManager")
time.sleep(0.3)

r = arc.cmd("create_blueprint", name="BP_TimeManager", parent_class="Actor", variables=[
    {"name": "HumanTimeRemaining", "type": "Float", "default": "480.0"},
    {"name": "MaxDailyTime", "type": "Float", "default": "480.0"},
    {"name": "DayNumber", "type": "Int", "default": "1"},
    {"name": "IsDayActive", "type": "Bool", "default": "true"},
    {"name": "TotalTimeSpent", "type": "Float", "default": "0.0"},
])
print(f"  Created: {r.get('status')}")
arc.cmd("compile_blueprint", name="BP_TimeManager")

nodes = [
    # === ConsumeTime Event (Minutes:Float) ===
    {"id": "evt_consume", "type": "CustomEvent", "event": "ConsumeTime",
     "params": [{"name": "Minutes", "type": "Float"}]},
    # Check if day is active
    {"id": "get_active", "type": "GetVar", "variable": "IsDayActive"},
    {"id": "branch_active", "type": "Branch"},
    # Deduct time: HumanTimeRemaining -= Minutes
    {"id": "get_time", "type": "GetVar", "variable": "HumanTimeRemaining"},
    {"id": "sub_time", "type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
    {"id": "set_time", "type": "SetVar", "variable": "HumanTimeRemaining"},
    # Track total
    {"id": "get_total", "type": "GetVar", "variable": "TotalTimeSpent"},
    {"id": "add_total", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_total", "type": "SetVar", "variable": "TotalTimeSpent"},
    # Check if time ran out: HumanTimeRemaining <= 0
    {"id": "get_time2", "type": "GetVar", "variable": "HumanTimeRemaining"},
    {"id": "le_zero", "type": "/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble"},
    {"id": "branch_timeup", "type": "Branch"},
    # Print time consumed
    {"id": "get_time3", "type": "GetVar", "variable": "HumanTimeRemaining"},
    {"id": "conv_time", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_time", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_time", "type": "PrintString"},
    # Day ended auto-trigger
    {"id": "print_dayover", "type": "PrintString", "params": {"InString": "[TIME] Day over! No time remaining."}},

    # === EndDay Event ===
    {"id": "evt_endday", "type": "CustomEvent", "event": "EndDay", "params": []},
    {"id": "set_inactive", "type": "SetVar", "variable": "IsDayActive"},
    # Print day end summary
    {"id": "get_day_end", "type": "GetVar", "variable": "DayNumber"},
    {"id": "conv_day_end", "type": "/Script/Engine.KismetStringLibrary:Conv_IntToString"},
    {"id": "concat_dayend", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_dayend", "type": "PrintString"},

    # === StartNewDay Event ===
    {"id": "evt_newday", "type": "CustomEvent", "event": "StartNewDay", "params": []},
    # Increment day
    {"id": "get_day_new", "type": "GetVar", "variable": "DayNumber"},
    {"id": "add_day", "type": "/Script/Engine.KismetMathLibrary:Add_IntInt"},
    {"id": "set_day", "type": "SetVar", "variable": "DayNumber"},
    # Reset time
    {"id": "get_maxtime", "type": "GetVar", "variable": "MaxDailyTime"},
    {"id": "set_time_new", "type": "SetVar", "variable": "HumanTimeRemaining"},
    {"id": "set_active", "type": "SetVar", "variable": "IsDayActive"},
    # Print new day
    {"id": "get_day_new2", "type": "GetVar", "variable": "DayNumber"},
    {"id": "conv_day_new", "type": "/Script/Engine.KismetStringLibrary:Conv_IntToString"},
    {"id": "get_time_new", "type": "GetVar", "variable": "HumanTimeRemaining"},
    {"id": "conv_time_new", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_nd1", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_nd2", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_nd3", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_newday", "type": "PrintString"},

    # === BeginPlay ===
    {"id": "print_init", "type": "PrintString", "params": {"InString": "TimeManager: Day 1, 480 min available"}},
]

r = arc.cmd("add_nodes_batch", blueprint="BP_TimeManager", nodes=nodes)
d = r.get("data", {})
print(f"  Nodes: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    ERR: {e}")

conns = [
    # BeginPlay → print_init
    {"from_node": "node_0", "from_pin": "then", "to_node": "print_init", "to_pin": "execute"},

    # === ConsumeTime chain ===
    {"from_node": "evt_consume", "from_pin": "then", "to_node": "branch_active", "to_pin": "execute"},
    {"from_node": "get_active", "from_pin": "IsDayActive", "to_node": "branch_active", "to_pin": "Condition"},
    # True: deduct time
    {"from_node": "branch_active", "from_pin": "True", "to_node": "set_time", "to_pin": "execute"},
    {"from_node": "get_time", "from_pin": "HumanTimeRemaining", "to_node": "sub_time", "to_pin": "A"},
    {"from_node": "evt_consume", "from_pin": "Minutes", "to_node": "sub_time", "to_pin": "B"},
    {"from_node": "sub_time", "from_pin": "ReturnValue", "to_node": "set_time", "to_pin": "HumanTimeRemaining"},
    # Track total time
    {"from_node": "set_time", "from_pin": "then", "to_node": "set_total", "to_pin": "execute"},
    {"from_node": "get_total", "from_pin": "TotalTimeSpent", "to_node": "add_total", "to_pin": "A"},
    {"from_node": "evt_consume", "from_pin": "Minutes", "to_node": "add_total", "to_pin": "B"},
    {"from_node": "add_total", "from_pin": "ReturnValue", "to_node": "set_total", "to_pin": "TotalTimeSpent"},
    # Check time remaining
    {"from_node": "set_total", "from_pin": "then", "to_node": "branch_timeup", "to_pin": "execute"},
    {"from_node": "get_time2", "from_pin": "HumanTimeRemaining", "to_node": "le_zero", "to_pin": "A"},
    {"from_node": "le_zero", "from_pin": "ReturnValue", "to_node": "branch_timeup", "to_pin": "Condition"},
    # Time not up: print remaining
    {"from_node": "branch_timeup", "from_pin": "False", "to_node": "print_time", "to_pin": "execute"},
    {"from_node": "get_time3", "from_pin": "HumanTimeRemaining", "to_node": "conv_time", "to_pin": "InDouble"},
    {"from_node": "conv_time", "from_pin": "ReturnValue", "to_node": "concat_time", "to_pin": "B"},
    {"from_node": "concat_time", "from_pin": "ReturnValue", "to_node": "print_time", "to_pin": "InString"},
    # Time up: print day over
    {"from_node": "branch_timeup", "from_pin": "True", "to_node": "print_dayover", "to_pin": "execute"},

    # === EndDay chain ===
    {"from_node": "evt_endday", "from_pin": "then", "to_node": "set_inactive", "to_pin": "execute"},
    {"from_node": "set_inactive", "from_pin": "then", "to_node": "print_dayend", "to_pin": "execute"},
    {"from_node": "get_day_end", "from_pin": "DayNumber", "to_node": "conv_day_end", "to_pin": "InInt"},
    {"from_node": "conv_day_end", "from_pin": "ReturnValue", "to_node": "concat_dayend", "to_pin": "B"},
    {"from_node": "concat_dayend", "from_pin": "ReturnValue", "to_node": "print_dayend", "to_pin": "InString"},

    # === StartNewDay chain ===
    {"from_node": "evt_newday", "from_pin": "then", "to_node": "set_day", "to_pin": "execute"},
    {"from_node": "get_day_new", "from_pin": "DayNumber", "to_node": "add_day", "to_pin": "A"},
    {"from_node": "add_day", "from_pin": "ReturnValue", "to_node": "set_day", "to_pin": "DayNumber"},
    {"from_node": "set_day", "from_pin": "then", "to_node": "set_time_new", "to_pin": "execute"},
    {"from_node": "get_maxtime", "from_pin": "MaxDailyTime", "to_node": "set_time_new", "to_pin": "HumanTimeRemaining"},
    {"from_node": "set_time_new", "from_pin": "then", "to_node": "set_active", "to_pin": "execute"},
    {"from_node": "set_active", "from_pin": "then", "to_node": "print_newday", "to_pin": "execute"},
    # Build new day message
    {"from_node": "get_day_new2", "from_pin": "DayNumber", "to_node": "conv_day_new", "to_pin": "InInt"},
    {"from_node": "conv_day_new", "from_pin": "ReturnValue", "to_node": "concat_nd1", "to_pin": "B"},
    {"from_node": "get_time_new", "from_pin": "HumanTimeRemaining", "to_node": "conv_time_new", "to_pin": "InDouble"},
    {"from_node": "conv_time_new", "from_pin": "ReturnValue", "to_node": "concat_nd2", "to_pin": "B"},
    {"from_node": "concat_nd1", "from_pin": "ReturnValue", "to_node": "concat_nd2", "to_pin": "A"},
    {"from_node": "concat_nd2", "from_pin": "ReturnValue", "to_node": "concat_nd3", "to_pin": "A"},
    {"from_node": "concat_nd3", "from_pin": "ReturnValue", "to_node": "print_newday", "to_pin": "InString"},
]

r = arc.cmd("add_connections_batch", blueprint="BP_TimeManager", connections=conns)
d = r.get("data", {})
print(f"  Connections: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    CONN ERR: {e}")

# Set string prefixes and constants
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="concat_time",
        pin_name="A", value="[TIME] Remaining: ")
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="concat_dayend",
        pin_name="A", value="[TIME] Day ended: Day ")
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="le_zero",
        pin_name="B", value="0.0")
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="set_inactive",
        pin_name="IsDayActive", value="false")
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="set_active",
        pin_name="IsDayActive", value="true")
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="add_day",
        pin_name="B", value="1")
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="concat_nd1",
        pin_name="A", value="[TIME] New day: Day ")
arc.cmd("set_node_param", blueprint="BP_TimeManager", node_id="concat_nd3",
        pin_name="B", value=" min available")

# Compile & verify
r = arc.cmd("compile_blueprint", name="BP_TimeManager")
compiled = r.get("data", {}).get("compiled", False)

r = arc.cmd("get_blueprint_details", blueprint="BP_TimeManager")
d = r.get("data", {})
nc = d.get("node_count", 0)
cc = d.get("connection_count", 0)
errs = len([m for m in d.get("messages", []) if "error" in str(m).lower()])

# Spawn
arc.cmd("delete_actor", label="TimeManager")
arc.cmd("spawn_actor_at", label="TimeManager", x=0, y=100, z=10,
        **{"class": "/Game/Arcwright/Generated/BP_TimeManager.BP_TimeManager_C"})
arc.cmd("save_all")

sm.manifest.setdefault("blueprints", [])
if "BP_TimeManager" not in sm.manifest["blueprints"]:
    sm.manifest["blueprints"].append("BP_TimeManager")
sm.manifest.setdefault("actors", [])
if "TimeManager" not in sm.manifest["actors"]:
    sm.manifest["actors"].append("TimeManager")
sm.save_manifest()

# PIE
arc.cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = arc.cmd("is_playing")
    if r.get("data", {}).get("playing"):
        started = True
        break
if started:
    time.sleep(3)
    r = arc.cmd("get_output_log", lines=50)
    msgs = [str(l) for l in r.get("data", {}).get("lines", []) if "TimeManager" in str(l) or "[TIME]" in str(l)]
    print(f"\n  PIE Messages ({len(msgs)}):")
    for m in msgs:
        print(f"    {m[:120]}")
    arc.cmd("stop_play")
else:
    print("\n  PIE did not start!")

print(f"\n  CHECK & CONFIRM:")
print(f"    Nodes:       {nc}/40+ {'PASS' if nc >= 40 else 'FAIL'}")
print(f"    Connections: {cc}/30+ {'PASS' if cc >= 30 else 'FAIL'}")
print(f"    Compiled:    {compiled} {'PASS' if compiled else 'FAIL'}")
print(f"    Errors:      {errs} {'PASS' if errs == 0 else 'FAIL'}")

overall = nc >= 40 and cc >= 30 and compiled and errs == 0
print(f"\n  SYSTEM 2 RESULT: {'PASS' if overall else 'FAIL'}")
