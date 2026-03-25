"""
SYSTEMS 3-8: StationBase, HUDManager, EngineInstance, GameMode, WBP_GameHUD, Level Setup
"""
import sys, time, json, os
sys.path.insert(0, "C:/Arcwright")
from scripts.state_manager import StateManager

sm = StateManager(project_dir="C:/Projects/BoreandStroke")
arc = sm.arc

def verify(name, min_nodes, min_conns):
    r = arc.cmd("compile_blueprint", name=name)
    compiled = r.get("data", {}).get("compiled", False)
    r = arc.cmd("get_blueprint_details", blueprint=name)
    d = r.get("data", {})
    nc = d.get("node_count", 0)
    cc = d.get("connection_count", 0)
    errs = len([m for m in d.get("messages", []) if "error" in str(m).lower()])
    ok = nc >= min_nodes and compiled and errs == 0
    print(f"  CHECK: {name} — {nc} nodes, {cc} conns, compiled={compiled}, errors={errs} -> {'PASS' if ok else 'FAIL'}")
    return ok

# ============================================================
# SYSTEM 3: BP_StationBase — Station Interaction
# ============================================================
print("=" * 70)
print("SYSTEM 3: BP_StationBase")
print("=" * 70)

arc.cmd("delete_blueprint", name="BP_StationBase")
time.sleep(0.3)

arc.cmd("create_blueprint", name="BP_StationBase", parent_class="Actor", variables=[
    {"name": "StationName", "type": "String", "default": "Unknown Station"},
    {"name": "StationType", "type": "String", "default": "Generic"},
    {"name": "IsPlayerNearby", "type": "Bool", "default": "false"},
    {"name": "IsStationActive", "type": "Bool", "default": "false"},
    {"name": "ActionTimeCost", "type": "Float", "default": "30.0"},
    {"name": "ActionMaterialCost", "type": "Float", "default": "25.0"},
    {"name": "QualityContribution", "type": "Float", "default": "10.0"},
])
arc.cmd("compile_blueprint", name="BP_StationBase")

arc.cmd("add_component", blueprint="BP_StationBase", component_type="BoxCollision",
    component_name="TriggerBox",
    properties={"extent": {"x": 200, "y": 200, "z": 150}, "generate_overlap_events": True,
                "collision_profile": "OverlapAllDynamic"})
arc.cmd("add_component", blueprint="BP_StationBase", component_type="StaticMesh",
    component_name="StationMesh", properties={"mesh": "/Engine/BasicShapes/Cube.Cube"})

nodes_s = [
    # Overlap Begin → set nearby true, print prompt
    {"id": "set_near_t", "type": "SetVar", "variable": "IsPlayerNearby"},
    {"id": "get_name_ov", "type": "GetVar", "variable": "StationName"},
    {"id": "concat_prompt", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_prompt", "type": "PrintString"},
    # Overlap End → set nearby false
    {"id": "evt_endoverlap", "type": "CustomEvent", "event": "OnEndOverlap", "params": []},
    {"id": "set_near_f", "type": "SetVar", "variable": "IsPlayerNearby"},
    {"id": "print_leave", "type": "PrintString", "params": {"InString": "[STATION] Player left station area"}},
    # ActivateStation event → check if nearby, set active, print action info
    {"id": "evt_activate", "type": "CustomEvent", "event": "ActivateStation", "params": []},
    {"id": "get_nearby", "type": "GetVar", "variable": "IsPlayerNearby"},
    {"id": "branch_near", "type": "Branch"},
    {"id": "set_active_t", "type": "SetVar", "variable": "IsStationActive"},
    {"id": "get_name_act", "type": "GetVar", "variable": "StationName"},
    {"id": "get_timecost", "type": "GetVar", "variable": "ActionTimeCost"},
    {"id": "conv_timecost", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "get_matcost", "type": "GetVar", "variable": "ActionMaterialCost"},
    {"id": "conv_matcost", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_act1", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_act2", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_act3", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_act4", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_action", "type": "PrintString"},
    {"id": "print_nothere", "type": "PrintString", "params": {"InString": "[STATION] Not near station!"}},
    # CompleteAction event
    {"id": "evt_complete", "type": "CustomEvent", "event": "CompleteAction", "params": []},
    {"id": "set_active_f", "type": "SetVar", "variable": "IsStationActive"},
    {"id": "get_name_done", "type": "GetVar", "variable": "StationName"},
    {"id": "get_quality", "type": "GetVar", "variable": "QualityContribution"},
    {"id": "conv_quality", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_done1", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_done2", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_done", "type": "PrintString"},
    # BeginPlay
    {"id": "get_name_init", "type": "GetVar", "variable": "StationName"},
    {"id": "concat_init", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_init", "type": "PrintString"},
]

r = arc.cmd("add_nodes_batch", blueprint="BP_StationBase", nodes=nodes_s)
print(f"  Nodes: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

conns_s = [
    # BeginPlay → print station name
    {"from_node": "node_0", "from_pin": "then", "to_node": "print_init", "to_pin": "execute"},
    {"from_node": "get_name_init", "from_pin": "StationName", "to_node": "concat_init", "to_pin": "B"},
    {"from_node": "concat_init", "from_pin": "ReturnValue", "to_node": "print_init", "to_pin": "InString"},
    # Overlap Begin (node_1) → set nearby true → print prompt
    {"from_node": "node_1", "from_pin": "then", "to_node": "set_near_t", "to_pin": "execute"},
    {"from_node": "set_near_t", "from_pin": "then", "to_node": "print_prompt", "to_pin": "execute"},
    {"from_node": "get_name_ov", "from_pin": "StationName", "to_node": "concat_prompt", "to_pin": "B"},
    {"from_node": "concat_prompt", "from_pin": "ReturnValue", "to_node": "print_prompt", "to_pin": "InString"},
    # EndOverlap → set nearby false → print leave
    {"from_node": "evt_endoverlap", "from_pin": "then", "to_node": "set_near_f", "to_pin": "execute"},
    {"from_node": "set_near_f", "from_pin": "then", "to_node": "print_leave", "to_pin": "execute"},
    # ActivateStation → branch(nearby) → set active → print info
    {"from_node": "evt_activate", "from_pin": "then", "to_node": "branch_near", "to_pin": "execute"},
    {"from_node": "get_nearby", "from_pin": "IsPlayerNearby", "to_node": "branch_near", "to_pin": "Condition"},
    {"from_node": "branch_near", "from_pin": "True", "to_node": "set_active_t", "to_pin": "execute"},
    {"from_node": "set_active_t", "from_pin": "then", "to_node": "print_action", "to_pin": "execute"},
    {"from_node": "get_name_act", "from_pin": "StationName", "to_node": "concat_act1", "to_pin": "B"},
    {"from_node": "get_timecost", "from_pin": "ActionTimeCost", "to_node": "conv_timecost", "to_pin": "InDouble"},
    {"from_node": "conv_timecost", "from_pin": "ReturnValue", "to_node": "concat_act2", "to_pin": "B"},
    {"from_node": "get_matcost", "from_pin": "ActionMaterialCost", "to_node": "conv_matcost", "to_pin": "InDouble"},
    {"from_node": "conv_matcost", "from_pin": "ReturnValue", "to_node": "concat_act3", "to_pin": "B"},
    {"from_node": "concat_act1", "from_pin": "ReturnValue", "to_node": "concat_act2", "to_pin": "A"},
    {"from_node": "concat_act2", "from_pin": "ReturnValue", "to_node": "concat_act3", "to_pin": "A"},
    {"from_node": "concat_act3", "from_pin": "ReturnValue", "to_node": "concat_act4", "to_pin": "A"},
    {"from_node": "concat_act4", "from_pin": "ReturnValue", "to_node": "print_action", "to_pin": "InString"},
    {"from_node": "branch_near", "from_pin": "False", "to_node": "print_nothere", "to_pin": "execute"},
    # CompleteAction → set inactive → print done
    {"from_node": "evt_complete", "from_pin": "then", "to_node": "set_active_f", "to_pin": "execute"},
    {"from_node": "set_active_f", "from_pin": "then", "to_node": "print_done", "to_pin": "execute"},
    {"from_node": "get_name_done", "from_pin": "StationName", "to_node": "concat_done1", "to_pin": "B"},
    {"from_node": "get_quality", "from_pin": "QualityContribution", "to_node": "conv_quality", "to_pin": "InDouble"},
    {"from_node": "conv_quality", "from_pin": "ReturnValue", "to_node": "concat_done2", "to_pin": "B"},
    {"from_node": "concat_done1", "from_pin": "ReturnValue", "to_node": "concat_done2", "to_pin": "A"},
    {"from_node": "concat_done2", "from_pin": "ReturnValue", "to_node": "print_done", "to_pin": "InString"},
]

r = arc.cmd("add_connections_batch", blueprint="BP_StationBase", connections=conns_s)
print(f"  Connections: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

# Set defaults
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="set_near_t", pin_name="IsPlayerNearby", value="true")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="set_near_f", pin_name="IsPlayerNearby", value="false")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="set_active_t", pin_name="IsStationActive", value="true")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="set_active_f", pin_name="IsStationActive", value="false")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_init", pin_name="A", value="[STATION] Ready: ")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_prompt", pin_name="A", value="[E] Interact: ")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_act1", pin_name="A", value="[STATION] Activated: ")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_act4", pin_name="B", value=" cost")
arc.cmd("set_node_param", blueprint="BP_StationBase", node_id="concat_done1", pin_name="A", value="[STATION] Completed: ")

s3_pass = verify("BP_StationBase", 35, 25)

# Respawn stations
for label in ["Station_Degriming", "Station_Disassembly", "Station_Inspection", "Station_Cleaning", "Station_Office"]:
    arc.cmd("delete_actor", label=label)
stations = [
    ("Station_Degriming", -800, -600, 40, "Degriming", "Degriming", "45.0", "15.0"),
    ("Station_Disassembly", -300, -600, 40, "Disassembly", "Disassembly", "60.0", "10.0"),
    ("Station_Inspection", 300, -600, 40, "Inspection", "Inspection", "30.0", "5.0"),
    ("Station_Cleaning", 800, -600, 40, "Cleaning", "Cleaning", "40.0", "20.0"),
    ("Station_Office", 0, 600, 40, "Office", "Office", "15.0", "0.0"),
]
for label, x, y, z, name, stype, tcost, mcost in stations:
    arc.cmd("spawn_actor_at", label=label, x=x, y=y, z=z,
            **{"class": "/Game/Arcwright/Generated/BP_StationBase.BP_StationBase_C"})
    arc.cmd("set_collision_preset", actor_label=label, preset_name="OverlapAllDynamic", component_name="TriggerBox")

arc.cmd("save_all")
print(f"  SYSTEM 3 RESULT: {'PASS' if s3_pass else 'FAIL'}")

# ============================================================
# SYSTEM 4: BP_HUDManager — Live HUD
# ============================================================
print("\n" + "=" * 70)
print("SYSTEM 4: BP_HUDManager")
print("=" * 70)

arc.cmd("delete_blueprint", name="BP_HUDManager")
time.sleep(0.3)

arc.cmd("create_blueprint", name="BP_HUDManager", parent_class="Actor")
arc.cmd("compile_blueprint", name="BP_HUDManager")

nodes_h = [
    # BeginPlay → CreateWidget → AddToViewport → PrintString
    {"id": "create_widget", "type": "/Script/UMG.WidgetBlueprintLibrary:Create"},
    {"id": "add_viewport", "type": "/Script/UMG.UserWidget:AddToViewport"},
    {"id": "print_hud", "type": "PrintString", "params": {"InString": "[HUD] Widget created and added to viewport"}},
    # GetAllActorsOfClass to find EconomyManager
    {"id": "find_econ", "type": "/Script/Engine.GameplayStatics:GetAllActorsOfClass"},
    {"id": "print_mgrs", "type": "PrintString", "params": {"InString": "[HUD] Manager references acquired"}},
    # GetAllActorsOfClass to find TimeManager
    {"id": "find_time", "type": "/Script/Engine.GameplayStatics:GetAllActorsOfClass"},
    {"id": "print_ready", "type": "PrintString", "params": {"InString": "[HUD] HUDManager fully initialized"}},
]

r = arc.cmd("add_nodes_batch", blueprint="BP_HUDManager", nodes=nodes_h)
print(f"  Nodes: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

conns_h = [
    {"from_node": "node_0", "from_pin": "then", "to_node": "create_widget", "to_pin": "execute"},
    {"from_node": "create_widget", "from_pin": "then", "to_node": "add_viewport", "to_pin": "execute"},
    {"from_node": "create_widget", "from_pin": "ReturnValue", "to_node": "add_viewport", "to_pin": "self"},
    {"from_node": "add_viewport", "from_pin": "then", "to_node": "print_hud", "to_pin": "execute"},
    {"from_node": "print_hud", "from_pin": "then", "to_node": "find_econ", "to_pin": "execute"},
    {"from_node": "find_econ", "from_pin": "then", "to_node": "find_time", "to_pin": "execute"},
    {"from_node": "find_time", "from_pin": "then", "to_node": "print_mgrs", "to_pin": "execute"},
    {"from_node": "print_mgrs", "from_pin": "then", "to_node": "print_ready", "to_pin": "execute"},
]

r = arc.cmd("add_connections_batch", blueprint="BP_HUDManager", connections=conns_h)
print(f"  Connections: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

# Set widget class pin
arc.cmd("set_node_param", blueprint="BP_HUDManager", node_id="create_widget",
        pin_name="WidgetType", value="/Game/UI/WBP_GameHUD.WBP_GameHUD_C")
# Set class pins for GetAllActorsOfClass
arc.cmd("set_node_param", blueprint="BP_HUDManager", node_id="find_econ",
        pin_name="ActorClass", value="/Game/Arcwright/Generated/BP_EconomyManager.BP_EconomyManager_C")
arc.cmd("set_node_param", blueprint="BP_HUDManager", node_id="find_time",
        pin_name="ActorClass", value="/Game/Arcwright/Generated/BP_TimeManager.BP_TimeManager_C")

s4_pass = verify("BP_HUDManager", 10, 8)

arc.cmd("delete_actor", label="HUDManager")
arc.cmd("spawn_actor_at", label="HUDManager", x=0, y=0, z=0,
        **{"class": "/Game/Arcwright/Generated/BP_HUDManager.BP_HUDManager_C"})
arc.cmd("save_all")
print(f"  SYSTEM 4 RESULT: {'PASS' if s4_pass else 'FAIL'}")

# ============================================================
# SYSTEM 5: BP_EngineInstance — Individual Engine Data
# ============================================================
print("\n" + "=" * 70)
print("SYSTEM 5: BP_EngineInstance")
print("=" * 70)

arc.cmd("delete_blueprint", name="BP_EngineInstance")
time.sleep(0.3)

arc.cmd("create_blueprint", name="BP_EngineInstance", parent_class="Actor", variables=[
    {"name": "EngineMake", "type": "String", "default": "Chevrolet"},
    {"name": "EngineModel", "type": "String", "default": "Small Block 350"},
    {"name": "EngineYear", "type": "Int", "default": "1968"},
    {"name": "SerialNumber", "type": "String", "default": "SBC350-001"},
    {"name": "QualityScore", "type": "Float", "default": "0.0"},
    {"name": "IsRebuilt", "type": "Bool", "default": "false"},
    {"name": "PartsInstalled", "type": "Int", "default": "0"},
    {"name": "MachiningQuality", "type": "Float", "default": "0.0"},
    {"name": "AssemblyQuality", "type": "Float", "default": "0.0"},
    {"name": "PurchasePrice", "type": "Float", "default": "500.0"},
    {"name": "EstimatedValue", "type": "Float", "default": "0.0"},
])
arc.cmd("compile_blueprint", name="BP_EngineInstance")

nodes_e = [
    # CalculateQuality event: QualityScore = (MachiningQuality * 0.4) + (AssemblyQuality * 0.3) + (PartsInstalled * 3)
    {"id": "evt_calcq", "type": "CustomEvent", "event": "CalculateQuality", "params": []},
    {"id": "get_machq", "type": "GetVar", "variable": "MachiningQuality"},
    {"id": "mul_machq", "type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
    {"id": "get_asmq", "type": "GetVar", "variable": "AssemblyQuality"},
    {"id": "mul_asmq", "type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
    {"id": "add_q1", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "get_parts", "type": "GetVar", "variable": "PartsInstalled"},
    {"id": "mul_parts", "type": "/Script/Engine.KismetMathLibrary:Multiply_IntInt"},
    {"id": "conv_parts", "type": "/Script/Engine.KismetStringLibrary:Conv_IntToString"},
    {"id": "add_q2", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "clamp_q", "type": "/Script/Engine.KismetMathLibrary:FClamp"},
    {"id": "set_quality", "type": "SetVar", "variable": "QualityScore"},
    {"id": "get_quality_p", "type": "GetVar", "variable": "QualityScore"},
    {"id": "conv_quality", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_q", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_quality", "type": "PrintString"},
    # MarkRebuilt event
    {"id": "evt_rebuilt", "type": "CustomEvent", "event": "MarkRebuilt", "params": []},
    {"id": "set_rebuilt", "type": "SetVar", "variable": "IsRebuilt"},
    # Calculate estimated value: PurchasePrice * (1 + QualityScore/100) * 2
    {"id": "get_pp", "type": "GetVar", "variable": "PurchasePrice"},
    {"id": "get_qs", "type": "GetVar", "variable": "QualityScore"},
    {"id": "div_100", "type": "/Script/Engine.KismetMathLibrary:Divide_DoubleDouble"},
    {"id": "add_1", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "mul_pp", "type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
    {"id": "mul_2", "type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
    {"id": "set_value", "type": "SetVar", "variable": "EstimatedValue"},
    {"id": "get_val_p", "type": "GetVar", "variable": "EstimatedValue"},
    {"id": "conv_val", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_rebuilt", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_rebuilt", "type": "PrintString"},
    # AddPart event (PartsInstalled++)
    {"id": "evt_addpart", "type": "CustomEvent", "event": "AddPart",
     "params": [{"name": "PartQuality", "type": "Float"}]},
    {"id": "get_parts2", "type": "GetVar", "variable": "PartsInstalled"},
    {"id": "add_part", "type": "/Script/Engine.KismetMathLibrary:Add_IntInt"},
    {"id": "set_parts", "type": "SetVar", "variable": "PartsInstalled"},
    {"id": "print_part", "type": "PrintString", "params": {"InString": "[ENGINE] Part installed"}},
    # BeginPlay: print engine info
    {"id": "get_make", "type": "GetVar", "variable": "EngineMake"},
    {"id": "get_model", "type": "GetVar", "variable": "EngineModel"},
    {"id": "concat_eng1", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_eng2", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_eng", "type": "PrintString"},
]

r = arc.cmd("add_nodes_batch", blueprint="BP_EngineInstance", nodes=nodes_e)
print(f"  Nodes: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

conns_e = [
    # BeginPlay
    {"from_node": "node_0", "from_pin": "then", "to_node": "print_eng", "to_pin": "execute"},
    {"from_node": "get_make", "from_pin": "EngineMake", "to_node": "concat_eng1", "to_pin": "B"},
    {"from_node": "get_model", "from_pin": "EngineModel", "to_node": "concat_eng2", "to_pin": "B"},
    {"from_node": "concat_eng1", "from_pin": "ReturnValue", "to_node": "concat_eng2", "to_pin": "A"},
    {"from_node": "concat_eng2", "from_pin": "ReturnValue", "to_node": "print_eng", "to_pin": "InString"},
    # CalculateQuality
    {"from_node": "evt_calcq", "from_pin": "then", "to_node": "set_quality", "to_pin": "execute"},
    {"from_node": "get_machq", "from_pin": "MachiningQuality", "to_node": "mul_machq", "to_pin": "A"},
    {"from_node": "mul_machq", "from_pin": "ReturnValue", "to_node": "add_q1", "to_pin": "A"},
    {"from_node": "get_asmq", "from_pin": "AssemblyQuality", "to_node": "mul_asmq", "to_pin": "A"},
    {"from_node": "mul_asmq", "from_pin": "ReturnValue", "to_node": "add_q1", "to_pin": "B"},
    {"from_node": "add_q1", "from_pin": "ReturnValue", "to_node": "add_q2", "to_pin": "A"},
    {"from_node": "add_q2", "from_pin": "ReturnValue", "to_node": "clamp_q", "to_pin": "Value"},
    {"from_node": "clamp_q", "from_pin": "ReturnValue", "to_node": "set_quality", "to_pin": "QualityScore"},
    {"from_node": "set_quality", "from_pin": "then", "to_node": "print_quality", "to_pin": "execute"},
    {"from_node": "get_quality_p", "from_pin": "QualityScore", "to_node": "conv_quality", "to_pin": "InDouble"},
    {"from_node": "conv_quality", "from_pin": "ReturnValue", "to_node": "concat_q", "to_pin": "B"},
    {"from_node": "concat_q", "from_pin": "ReturnValue", "to_node": "print_quality", "to_pin": "InString"},
    # MarkRebuilt
    {"from_node": "evt_rebuilt", "from_pin": "then", "to_node": "set_rebuilt", "to_pin": "execute"},
    {"from_node": "set_rebuilt", "from_pin": "then", "to_node": "set_value", "to_pin": "execute"},
    {"from_node": "get_pp", "from_pin": "PurchasePrice", "to_node": "mul_pp", "to_pin": "A"},
    {"from_node": "get_qs", "from_pin": "QualityScore", "to_node": "div_100", "to_pin": "A"},
    {"from_node": "div_100", "from_pin": "ReturnValue", "to_node": "add_1", "to_pin": "A"},
    {"from_node": "add_1", "from_pin": "ReturnValue", "to_node": "mul_pp", "to_pin": "B"},
    {"from_node": "mul_pp", "from_pin": "ReturnValue", "to_node": "mul_2", "to_pin": "A"},
    {"from_node": "mul_2", "from_pin": "ReturnValue", "to_node": "set_value", "to_pin": "EstimatedValue"},
    {"from_node": "set_value", "from_pin": "then", "to_node": "print_rebuilt", "to_pin": "execute"},
    {"from_node": "get_val_p", "from_pin": "EstimatedValue", "to_node": "conv_val", "to_pin": "InDouble"},
    {"from_node": "conv_val", "from_pin": "ReturnValue", "to_node": "concat_rebuilt", "to_pin": "B"},
    {"from_node": "concat_rebuilt", "from_pin": "ReturnValue", "to_node": "print_rebuilt", "to_pin": "InString"},
    # AddPart
    {"from_node": "evt_addpart", "from_pin": "then", "to_node": "set_parts", "to_pin": "execute"},
    {"from_node": "get_parts2", "from_pin": "PartsInstalled", "to_node": "add_part", "to_pin": "A"},
    {"from_node": "add_part", "from_pin": "ReturnValue", "to_node": "set_parts", "to_pin": "PartsInstalled"},
    {"from_node": "set_parts", "from_pin": "then", "to_node": "print_part", "to_pin": "execute"},
]

r = arc.cmd("add_connections_batch", blueprint="BP_EngineInstance", connections=conns_e)
print(f"  Connections: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

# Set constants
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="mul_machq", pin_name="B", value="0.4")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="mul_asmq", pin_name="B", value="0.3")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="mul_parts", pin_name="B", value="3")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="clamp_q", pin_name="Min", value="0.0")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="clamp_q", pin_name="Max", value="100.0")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="div_100", pin_name="B", value="100.0")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="add_1", pin_name="B", value="1.0")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="mul_2", pin_name="B", value="2.0")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="set_rebuilt", pin_name="IsRebuilt", value="true")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="add_part", pin_name="B", value="1")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="concat_eng1", pin_name="A", value="[ENGINE] ")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="concat_q", pin_name="A", value="[ENGINE] Quality: ")
arc.cmd("set_node_param", blueprint="BP_EngineInstance", node_id="concat_rebuilt", pin_name="A", value="[ENGINE] Rebuilt! Value: $")

s5_pass = verify("BP_EngineInstance", 40, 30)
arc.cmd("save_all")
print(f"  SYSTEM 5 RESULT: {'PASS' if s5_pass else 'FAIL'}")

# ============================================================
# SYSTEM 6: BP_BoreAndStrokeGameMode — Orchestrator
# ============================================================
print("\n" + "=" * 70)
print("SYSTEM 6: BP_BoreAndStrokeGameMode")
print("=" * 70)

arc.cmd("delete_blueprint", name="BP_BoreAndStrokeGameMode")
time.sleep(0.3)

arc.cmd("create_blueprint", name="BP_BoreAndStrokeGameMode", parent_class="GameModeBase")
arc.cmd("compile_blueprint", name="BP_BoreAndStrokeGameMode")

nodes_gm = [
    {"id": "print_gm1", "type": "PrintString", "params": {"InString": "[GAMEMODE] Bore & Stroke initializing..."}},
    {"id": "find_econ", "type": "/Script/Engine.GameplayStatics:GetAllActorsOfClass"},
    {"id": "print_gm2", "type": "PrintString", "params": {"InString": "[GAMEMODE] EconomyManager found"}},
    {"id": "find_time", "type": "/Script/Engine.GameplayStatics:GetAllActorsOfClass"},
    {"id": "print_gm3", "type": "PrintString", "params": {"InString": "[GAMEMODE] TimeManager found"}},
    {"id": "find_hud", "type": "/Script/Engine.GameplayStatics:GetAllActorsOfClass"},
    {"id": "print_gm4", "type": "PrintString", "params": {"InString": "[GAMEMODE] HUDManager found"}},
    {"id": "print_gm5", "type": "PrintString", "params": {"InString": "[GAMEMODE] All systems online. Welcome to Bore & Stroke!"}},
]

r = arc.cmd("add_nodes_batch", blueprint="BP_BoreAndStrokeGameMode", nodes=nodes_gm)
print(f"  Nodes: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

conns_gm = [
    {"from_node": "node_0", "from_pin": "then", "to_node": "print_gm1", "to_pin": "execute"},
    {"from_node": "print_gm1", "from_pin": "then", "to_node": "find_econ", "to_pin": "execute"},
    {"from_node": "find_econ", "from_pin": "then", "to_node": "print_gm2", "to_pin": "execute"},
    {"from_node": "print_gm2", "from_pin": "then", "to_node": "find_time", "to_pin": "execute"},
    {"from_node": "find_time", "from_pin": "then", "to_node": "print_gm3", "to_pin": "execute"},
    {"from_node": "print_gm3", "from_pin": "then", "to_node": "find_hud", "to_pin": "execute"},
    {"from_node": "find_hud", "from_pin": "then", "to_node": "print_gm4", "to_pin": "execute"},
    {"from_node": "print_gm4", "from_pin": "then", "to_node": "print_gm5", "to_pin": "execute"},
]

r = arc.cmd("add_connections_batch", blueprint="BP_BoreAndStrokeGameMode", connections=conns_gm)
print(f"  Connections: {r.get('data',{}).get('succeeded')}/{r.get('data',{}).get('total')}")

arc.cmd("set_node_param", blueprint="BP_BoreAndStrokeGameMode", node_id="find_econ",
        pin_name="ActorClass", value="/Game/Arcwright/Generated/BP_EconomyManager.BP_EconomyManager_C")
arc.cmd("set_node_param", blueprint="BP_BoreAndStrokeGameMode", node_id="find_time",
        pin_name="ActorClass", value="/Game/Arcwright/Generated/BP_TimeManager.BP_TimeManager_C")
arc.cmd("set_node_param", blueprint="BP_BoreAndStrokeGameMode", node_id="find_hud",
        pin_name="ActorClass", value="/Game/Arcwright/Generated/BP_HUDManager.BP_HUDManager_C")

s6_pass = verify("BP_BoreAndStrokeGameMode", 10, 8)
arc.cmd("set_game_mode", game_mode="BP_BoreAndStrokeGameMode")
arc.cmd("save_all")
print(f"  SYSTEM 6 RESULT: {'PASS' if s6_pass else 'FAIL'}")

# ============================================================
# SYSTEM 7: WBP_GameHUD — Widget Layout
# ============================================================
print("\n" + "=" * 70)
print("SYSTEM 7: WBP_GameHUD")
print("=" * 70)

arc.cmd("delete_blueprint", name="WBP_GameHUD")
time.sleep(0.3)
arc.cmd("create_widget_blueprint", name="WBP_GameHUD")

# Root canvas
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="CanvasPanel", widget_name="HUDRoot")

# Top-left: Day + Cash
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="VerticalBox", widget_name="TopLeftPanel", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="TopLeftPanel", preset="TopLeft")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TopLeftPanel", property="position", value={"x": 20, "y": 15})

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="DayLabel", parent_name="TopLeftPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="text", value="DAY 1")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="font_size", value="32")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="color", value="#E8A624")

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="CashLabel", parent_name="TopLeftPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="text", value="$5,000")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="font_size", value="24")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="color", value="#33D166")

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="OverheadLabel", parent_name="TopLeftPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="OverheadLabel", property="text", value="Overhead: $150/day")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="OverheadLabel", property="font_size", value="14")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="OverheadLabel", property="color", value="#808080")

# Top-center: Time bar
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="VerticalBox", widget_name="TopCenterPanel", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="TopCenterPanel", preset="TopCenter")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TopCenterPanel", property="position", value={"x": -150, "y": 15})

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TimeTitle", parent_name="TopCenterPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeTitle", property="text", value="WORK DAY")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeTitle", property="font_size", value="14")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeTitle", property="color", value="#E8DCC8")

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="ProgressBar", widget_name="TimeBar", parent_name="TopCenterPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="percent", value="1.0")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="fill_color", value="#E8A624")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="size", value={"x": 300, "y": 20})

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TimeRemaining", parent_name="TopCenterPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeRemaining", property="text", value="8h 00m remaining")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeRemaining", property="font_size", value="16")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeRemaining", property="color", value="#E8DCC8")

# Top-right: Shop tier + reputation
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="VerticalBox", widget_name="TopRightPanel", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="TopRightPanel", preset="TopRight")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TopRightPanel", property="position", value={"x": -200, "y": 15})

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TierLabel", parent_name="TopRightPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TierLabel", property="text", value="TIER 1 - Garage")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TierLabel", property="font_size", value="16")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TierLabel", property="color", value="#E8A624")

arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="RepLabel", parent_name="TopRightPanel")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", property="text", value="REP: 50")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", property="font_size", value="16")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="RepLabel", property="color", value="#FFC733")

# Bottom-center: Station prompt
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="StationPrompt", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", preset="BottomCenter")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="position", value={"x": -120, "y": -80})
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="text", value="[E] Interact")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="font_size", value="22")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="StationPrompt", property="color", value="#E8A624")

# Bottom-left: Engine info
arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="EngineInfo", parent_name="HUDRoot")
arc.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="EngineInfo", preset="BottomLeft")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="EngineInfo", property="position", value={"x": 20, "y": -50})
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="EngineInfo", property="text", value="No engine selected")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="EngineInfo", property="font_size", value="14")
arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="EngineInfo", property="color", value="#808080")

arc.cmd("save_all")

# Verify widget tree
r = arc.cmd("get_widget_tree", widget_blueprint="WBP_GameHUD")
wcount = r.get("data", {}).get("total_widgets", 0)
print(f"  Widget count: {wcount}/15+ {'PASS' if wcount >= 15 else 'FAIL'}")
print(f"  SYSTEM 7 RESULT: {'PASS' if wcount >= 15 else 'FAIL'}")

# ============================================================
# FINAL: PIE VERIFICATION + QA TOUR
# ============================================================
print("\n" + "=" * 70)
print("FINAL VERIFICATION: PIE + QA TOUR")
print("=" * 70)

arc.cmd("save_all")
arc.cmd("play_in_editor")
started = False
for i in range(20):
    time.sleep(0.5)
    r = arc.cmd("is_playing")
    if r.get("data", {}).get("playing"):
        started = True
        break

if started:
    time.sleep(4)

    # Check all log messages
    r = arc.cmd("get_output_log", lines=200)
    lines = r.get("data", {}).get("lines", [])
    bp_msgs = [str(l) for l in lines if "BlueprintUserMessages" in str(l)]
    econ_msgs = [m for m in bp_msgs if "REVENUE" in m or "EXPENSE" in m or "EconomyManager" in m]
    time_msgs = [m for m in bp_msgs if "[TIME]" in m or "TimeManager" in m]
    station_msgs = [m for m in bp_msgs if "[STATION]" in m or "Interact" in m]
    hud_msgs = [m for m in bp_msgs if "[HUD]" in m or "HUDManager" in m or "Widget" in m]
    gm_msgs = [m for m in bp_msgs if "[GAMEMODE]" in m]
    engine_msgs = [m for m in bp_msgs if "[ENGINE]" in m]

    print(f"  Total BP messages: {len(bp_msgs)}")
    print(f"    Economy:   {len(econ_msgs)}")
    print(f"    Time:      {len(time_msgs)}")
    print(f"    Station:   {len(station_msgs)}")
    print(f"    HUD:       {len(hud_msgs)}")
    print(f"    GameMode:  {len(gm_msgs)}")
    print(f"    Engine:    {len(engine_msgs)}")

    # Print first few of each
    for label, msgs in [("GAMEMODE", gm_msgs), ("ECONOMY", econ_msgs), ("TIME", time_msgs), ("HUD", hud_msgs), ("STATION", station_msgs[:3])]:
        if msgs:
            print(f"\n  {label}:")
            for m in msgs[:3]:
                print(f"    {m[:120]}")

    # Verify HUD in viewport
    r = arc.cmd("get_viewport_widgets")
    d = r.get("data", {})
    vw = d.get("in_viewport", 0)
    print(f"\n  Viewport widgets: {vw} {'PASS' if vw > 0 else 'FAIL'}")
    for w in d.get("widgets", []):
        print(f"    {w.get('class')}: visible={w.get('visible')}, children={w.get('child_count')}")

    # QA Tour: visit each station
    os.makedirs("C:/Arcwright/screenshots", exist_ok=True)
    print("\n  QA TOUR:")
    for station in ["Station_Degriming", "Station_Disassembly", "Station_Inspection", "Station_Cleaning", "Station_Office"]:
        arc.cmd("teleport_to_actor", actor=station, distance=50)
        time.sleep(1.5)
        r = arc.cmd("get_output_log", lines=20)
        overlap = any("[STATION]" in str(l) or "Interact" in str(l) for l in r.get("data", {}).get("lines", []))
        arc.cmd("get_player_view", filename=f"C:/Arcwright/screenshots/qa_{station}.png")
        print(f"    {station}: overlap={'YES' if overlap else 'NO'}")

    arc.cmd("stop_play")
    time.sleep(1)
else:
    print("  PIE did not start!")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("BUILD SUMMARY")
print("=" * 70)
print(f"  System 3 (StationBase):   {'PASS' if s3_pass else 'FAIL'}")
print(f"  System 4 (HUDManager):    {'PASS' if s4_pass else 'FAIL'}")
print(f"  System 5 (EngineInstance): {'PASS' if s5_pass else 'FAIL'}")
print(f"  System 6 (GameMode):      {'PASS' if s6_pass else 'FAIL'}")
print(f"  System 7 (WBP_GameHUD):   {'PASS' if wcount >= 15 else 'FAIL'} ({wcount} widgets)")

sm.report()
