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

# Fix BP_TimeManager - use separate GetVar for post-set comparison
print("=== Fixing BP_TimeManager ===")
cmd("delete_blueprint", name="BP_TimeManager")
cmd("create_blueprint", name="BP_TimeManager", parent_class="Actor", variables=[
    {"name":"CurrentDay","type":"Int","default":"1"},
    {"name":"HumanTimeRemaining","type":"Float","default":"480.0"},
    {"name":"DailyBudget","type":"Float","default":"480.0"},
    {"name":"IsEndOfDay","type":"Bool","default":"false"}])

r = cmd("add_nodes_batch", blueprint="BP_TimeManager", nodes=[
    {"node_id":"begin","node_type":"Event_ReceiveBeginPlay"},
    {"node_id":"get_budget","node_type":"GetVar","params":{"Variable":"DailyBudget"}},
    {"node_id":"set_time_init","node_type":"SetVar","params":{"Variable":"HumanTimeRemaining"}},
    {"node_id":"p_start","node_type":"PrintString","params":{"InString":"Day started"}},
    {"node_id":"evt_consume","node_type":"CustomEvent","params":{"EventName":"ConsumeTime"}},
    {"node_id":"get_time","node_type":"GetVar","params":{"Variable":"HumanTimeRemaining"}},
    {"node_id":"sub_time","node_type":"/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
    {"node_id":"set_time","node_type":"SetVar","params":{"Variable":"HumanTimeRemaining"}},
    {"node_id":"get_time_after","node_type":"GetVar","params":{"Variable":"HumanTimeRemaining"}},
    {"node_id":"leq_zero","node_type":"/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble"},
    {"node_id":"br_end","node_type":"Branch"},
    {"node_id":"p_consumed","node_type":"PrintString","params":{"InString":"Time consumed"}},
    {"node_id":"evt_endday","node_type":"CustomEvent","params":{"EventName":"EndDay"}},
    {"node_id":"set_eod_t","node_type":"SetVar","params":{"Variable":"IsEndOfDay"}},
    {"node_id":"get_day","node_type":"GetVar","params":{"Variable":"CurrentDay"}},
    {"node_id":"add_day","node_type":"/Script/Engine.KismetMathLibrary:Add_IntInt"},
    {"node_id":"set_day","node_type":"SetVar","params":{"Variable":"CurrentDay"}},
    {"node_id":"get_budget2","node_type":"GetVar","params":{"Variable":"DailyBudget"}},
    {"node_id":"set_time2","node_type":"SetVar","params":{"Variable":"HumanTimeRemaining"}},
    {"node_id":"set_eod_f","node_type":"SetVar","params":{"Variable":"IsEndOfDay"}},
    {"node_id":"p_newday","node_type":"PrintString","params":{"InString":"New day started"}},
])
print(f"  Nodes: {r['data']['succeeded']}/{r['data']['total']}")

r = cmd("add_connections_batch", blueprint="BP_TimeManager", connections=[
    {"from_node":"begin","from_pin":"then","to_node":"set_time_init","to_pin":"execute"},
    {"from_node":"get_budget","from_pin":"DailyBudget","to_node":"set_time_init","to_pin":"HumanTimeRemaining"},
    {"from_node":"set_time_init","from_pin":"then","to_node":"p_start","to_pin":"execute"},
    {"from_node":"evt_consume","from_pin":"then","to_node":"set_time","to_pin":"execute"},
    {"from_node":"get_time","from_pin":"HumanTimeRemaining","to_node":"sub_time","to_pin":"A"},
    {"from_node":"sub_time","from_pin":"ReturnValue","to_node":"set_time","to_pin":"HumanTimeRemaining"},
    {"from_node":"set_time","from_pin":"then","to_node":"br_end","to_pin":"execute"},
    {"from_node":"get_time_after","from_pin":"HumanTimeRemaining","to_node":"leq_zero","to_pin":"A"},
    {"from_node":"leq_zero","from_pin":"ReturnValue","to_node":"br_end","to_pin":"Condition"},
    {"from_node":"br_end","from_pin":"False","to_node":"p_consumed","to_pin":"execute"},
    {"from_node":"evt_endday","from_pin":"then","to_node":"set_eod_t","to_pin":"execute"},
    {"from_node":"set_eod_t","from_pin":"then","to_node":"set_day","to_pin":"execute"},
    {"from_node":"get_day","from_pin":"CurrentDay","to_node":"add_day","to_pin":"A"},
    {"from_node":"add_day","from_pin":"ReturnValue","to_node":"set_day","to_pin":"CurrentDay"},
    {"from_node":"set_day","from_pin":"then","to_node":"set_time2","to_pin":"execute"},
    {"from_node":"get_budget2","from_pin":"DailyBudget","to_node":"set_time2","to_pin":"HumanTimeRemaining"},
    {"from_node":"set_time2","from_pin":"then","to_node":"set_eod_f","to_pin":"execute"},
    {"from_node":"set_eod_f","from_pin":"then","to_node":"p_newday","to_pin":"execute"},
])
print(f"  Connections: {r['data']['succeeded']}/{r['data']['total']}")

r = cmd("compile_blueprint", name="BP_TimeManager")
d = r.get("data", {})
print(f"  Compiled: {d.get('compiled')}, saved: {d.get('saved')}, msgs: {len(d.get('messages',[]))}")
for m in d.get("messages", []):
    print(f"    [{m['severity']}] {m['message'][:80]}")

# Fix BP_HeatManager - same pattern
print("\n=== Fixing BP_HeatManager ===")
cmd("delete_blueprint", name="BP_HeatManager")
cmd("create_blueprint", name="BP_HeatManager", parent_class="Actor", variables=[
    {"name":"HeatLevel","type":"Float","default":"0.0"},
    {"name":"HeatDecayRate","type":"Float","default":"0.1"},
    {"name":"MaxHeat","type":"Float","default":"100.0"}])

r = cmd("add_nodes_batch", blueprint="BP_HeatManager", nodes=[
    {"node_id":"begin","node_type":"Event_ReceiveBeginPlay"},
    {"node_id":"p_init","node_type":"PrintString","params":{"InString":"Heat Manager active"}},
    {"node_id":"evt_add","node_type":"CustomEvent","params":{"EventName":"AddHeat"}},
    {"node_id":"get_h","node_type":"GetVar","params":{"Variable":"HeatLevel"}},
    {"node_id":"add_h","node_type":"/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"node_id":"clamp_h","node_type":"/Script/Engine.KismetMathLibrary:FClamp"},
    {"node_id":"set_h","node_type":"SetVar","params":{"Variable":"HeatLevel"}},
    {"node_id":"get_h_after","node_type":"GetVar","params":{"Variable":"HeatLevel"}},
    {"node_id":"ge50","node_type":"/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
    {"node_id":"br_warn","node_type":"Branch"},
    {"node_id":"p_warn","node_type":"PrintString","params":{"InString":"WARNING: Heat elevated!"}},
    {"node_id":"evt_decay","node_type":"CustomEvent","params":{"EventName":"DecayHeat"}},
    {"node_id":"get_h2","node_type":"GetVar","params":{"Variable":"HeatLevel"}},
    {"node_id":"get_rate","node_type":"GetVar","params":{"Variable":"HeatDecayRate"}},
    {"node_id":"sub_dec","node_type":"/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
    {"node_id":"clamp_d","node_type":"/Script/Engine.KismetMathLibrary:FClamp"},
    {"node_id":"set_h2","node_type":"SetVar","params":{"Variable":"HeatLevel"}},
])
print(f"  Nodes: {r['data']['succeeded']}/{r['data']['total']}")

r = cmd("add_connections_batch", blueprint="BP_HeatManager", connections=[
    {"from_node":"begin","from_pin":"then","to_node":"p_init","to_pin":"execute"},
    {"from_node":"evt_add","from_pin":"then","to_node":"set_h","to_pin":"execute"},
    {"from_node":"get_h","from_pin":"HeatLevel","to_node":"add_h","to_pin":"A"},
    {"from_node":"add_h","from_pin":"ReturnValue","to_node":"clamp_h","to_pin":"Value"},
    {"from_node":"clamp_h","from_pin":"ReturnValue","to_node":"set_h","to_pin":"HeatLevel"},
    {"from_node":"set_h","from_pin":"then","to_node":"br_warn","to_pin":"execute"},
    {"from_node":"get_h_after","from_pin":"HeatLevel","to_node":"ge50","to_pin":"A"},
    {"from_node":"ge50","from_pin":"ReturnValue","to_node":"br_warn","to_pin":"Condition"},
    {"from_node":"br_warn","from_pin":"True","to_node":"p_warn","to_pin":"execute"},
    {"from_node":"evt_decay","from_pin":"then","to_node":"set_h2","to_pin":"execute"},
    {"from_node":"get_h2","from_pin":"HeatLevel","to_node":"sub_dec","to_pin":"A"},
    {"from_node":"get_rate","from_pin":"HeatDecayRate","to_node":"sub_dec","to_pin":"B"},
    {"from_node":"sub_dec","from_pin":"ReturnValue","to_node":"clamp_d","to_pin":"Value"},
    {"from_node":"clamp_d","from_pin":"ReturnValue","to_node":"set_h2","to_pin":"HeatLevel"},
])
print(f"  Connections: {r['data']['succeeded']}/{r['data']['total']}")

r = cmd("compile_blueprint", name="BP_HeatManager")
d = r.get("data", {})
print(f"  Compiled: {d.get('compiled')}, saved: {d.get('saved')}, msgs: {len(d.get('messages',[]))}")
for m in d.get("messages", []):
    print(f"    [{m['severity']}] {m['message'][:80]}")

# Verify ALL 5
print(f"\n{'='*60}")
print("ALL BLUEPRINTS - FINAL STATUS")
print(f"{'='*60}")
all_pass = True
for bp in ["BP_TimeManager", "BP_EconomyManager", "BP_StationBase", "BP_HeatManager", "BP_BoreAndStrokeGameMode"]:
    r = cmd("compile_blueprint", name=bp)
    d = r.get("data", {})
    compiled = d.get("compiled", False)
    nodes = d.get("node_count", 0)
    conns = d.get("connection_count", 0)
    status = "PASS" if compiled else "FAIL"
    if not compiled: all_pass = False
    print(f"  {status}: {bp} ({nodes} nodes, {conns} conns)")

print(f"\nAll 5 compile: {'ALL PASS' if all_pass else 'SOME FAIL'}")
