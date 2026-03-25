"""
Arcwright Advanced Blueprint Test Suite
========================================
Tests 12-23: Advanced patterns for Bore & Stroke game.
Run: PYTHONIOENCODING=utf-8 python tests/test_advanced_blueprints.py
"""

import socket
import json
import sys
import time
from datetime import datetime

LOG_FILE = "tests/advanced_test_results.log"
PASS_COUNT = 0
FAIL_COUNT = 0
RESULTS = []


def cmd(command, **params):
    s = socket.socket()
    s.settimeout(30)
    s.connect(('localhost', 13377))
    s.sendall(json.dumps({"command": command, "params": params}).encode() + b'\n')
    data = b''
    while b'\n' not in data:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
    s.close()
    return json.loads(data.decode().strip())


def delete_bp(name):
    try:
        cmd("delete_blueprint", blueprint=name)
    except Exception:
        pass


def create_bp(name, parent="Actor", variables=None):
    delete_bp(name)
    p = {"name": name, "parent_class": parent}
    if variables:
        p["variables"] = variables
    r = cmd("create_blueprint", **p)
    assert r["status"] == "ok", f"create_blueprint failed: {r}"


def add_nodes(bp, nodes):
    r = cmd("add_nodes_batch", blueprint=bp, nodes=nodes)
    assert r["status"] == "ok", f"add_nodes_batch failed: {r}"
    d = r["data"]
    failed_nodes = [n for n in d.get("results", []) if not n.get("success")]
    if failed_nodes:
        for fn in failed_nodes:
            print(f"    NODE FAIL: {fn.get('node_id','?')} ({fn.get('node_type','?')}): {fn.get('error','?')}")
    return d["succeeded"], d["failed"]


def add_conns(bp, connections):
    r = cmd("add_connections_batch", blueprint=bp, connections=connections)
    assert r["status"] == "ok", f"add_connections_batch failed: {r}"
    d = r["data"]
    failed_conns = [c for c in d.get("results", []) if not c.get("success")]
    if failed_conns:
        for fc in failed_conns:
            src = fc.get("source_node", fc.get("from_node", "?"))
            dst = fc.get("target_node", fc.get("to_node", "?"))
            err = fc.get("error", "?")
            print(f"    CONN FAIL: {src} -> {dst}: {err}")
            for key in ["available_source_pins", "available_target_pins"]:
                if key in fc:
                    print(f"      {key}: {[p['name'] for p in fc[key]]}")
    return d["succeeded"], d["failed"]


def log(msg):
    print(msg, flush=True)


def run_test(name, fn):
    global PASS_COUNT, FAIL_COUNT
    log(f"\n{'='*70}")
    log(f"TEST: {name}")
    log(f"{'='*70}")
    try:
        fn()
        PASS_COUNT += 1
        RESULTS.append(("PASS", name, ""))
        log(f"  >> PASS")
    except Exception as e:
        FAIL_COUNT += 1
        RESULTS.append(("FAIL", name, str(e)))
        log(f"  >> FAIL: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# Test 12: Multiple Branches in Chain
# ============================================================
def test_12_chained_branches():
    bp = "BP_Test12_ChainedBranch"
    create_bp(bp, variables=[{"name": "QualityScore", "type": "Float", "default": "75.0"}])

    nok, nf = add_nodes(bp, [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "get_q", "node_type": "GetVar", "params": {"Variable": "QualityScore"}},
        {"node_id": "ge90", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
        {"node_id": "br1", "node_type": "Branch"},
        {"node_id": "ge70", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
        {"node_id": "br2", "node_type": "Branch"},
        {"node_id": "ge50", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
        {"node_id": "br3", "node_type": "Branch"},
        {"node_id": "p_exc", "node_type": "PrintString", "params": {"InString": "Excellent!"}},
        {"node_id": "p_good", "node_type": "PrintString", "params": {"InString": "Good"}},
        {"node_id": "p_fair", "node_type": "PrintString", "params": {"InString": "Fair"}},
        {"node_id": "p_poor", "node_type": "PrintString", "params": {"InString": "Poor"}},
    ])
    assert nf == 0, f"Node failures: {nf}"
    log(f"  Nodes: {nok}/{nok+nf}")

    cok, cf = add_conns(bp, [
        {"from_node": "begin", "from_pin": "then", "to_node": "br1", "to_pin": "execute"},
        {"from_node": "get_q", "from_pin": "QualityScore", "to_node": "ge90", "to_pin": "A"},
        {"from_node": "ge90", "from_pin": "ReturnValue", "to_node": "br1", "to_pin": "Condition"},
        {"from_node": "br1", "from_pin": "True", "to_node": "p_exc", "to_pin": "execute"},
        {"from_node": "br1", "from_pin": "False", "to_node": "br2", "to_pin": "execute"},
        {"from_node": "get_q", "from_pin": "QualityScore", "to_node": "ge70", "to_pin": "A"},
        {"from_node": "ge70", "from_pin": "ReturnValue", "to_node": "br2", "to_pin": "Condition"},
        {"from_node": "br2", "from_pin": "True", "to_node": "p_good", "to_pin": "execute"},
        {"from_node": "br2", "from_pin": "False", "to_node": "br3", "to_pin": "execute"},
        {"from_node": "get_q", "from_pin": "QualityScore", "to_node": "ge50", "to_pin": "A"},
        {"from_node": "ge50", "from_pin": "ReturnValue", "to_node": "br3", "to_pin": "Condition"},
        {"from_node": "br3", "from_pin": "True", "to_node": "p_fair", "to_pin": "execute"},
        {"from_node": "br3", "from_pin": "False", "to_node": "p_poor", "to_pin": "execute"},
    ])
    log(f"  Connections: {cok}/{cok+cf}")
    assert cf == 0, f"Connection failures: {cf}"
    cmd("compile_blueprint", blueprint=bp)


# ============================================================
# Test 13: Purchase Flow (Get -> Math -> Compare -> Branch -> Set)
# ============================================================
def test_13_purchase_flow():
    bp = "BP_Test13_Purchase"
    create_bp(bp, variables=[
        {"name": "Cash", "type": "Float", "default": "1000.0"},
        {"name": "Price", "type": "Float", "default": "250.0"},
    ])

    nok, nf = add_nodes(bp, [
        {"node_id": "evt", "node_type": "CustomEvent", "params": {"EventName": "TryPurchase"}},
        {"node_id": "get_cash", "node_type": "GetVar", "params": {"Variable": "Cash"}},
        {"node_id": "get_price", "node_type": "GetVar", "params": {"Variable": "Price"}},
        {"node_id": "sub", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
        {"node_id": "ge0", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
        {"node_id": "branch", "node_type": "Branch"},
        {"node_id": "set_cash", "node_type": "SetVar", "params": {"Variable": "Cash"}},
        {"node_id": "p_bought", "node_type": "PrintString", "params": {"InString": "Purchased!"}},
        {"node_id": "p_cant", "node_type": "PrintString", "params": {"InString": "Can't afford!"}},
    ])
    assert nf == 0, f"Node failures: {nf}"
    log(f"  Nodes: {nok}/{nok+nf}")

    cok, cf = add_conns(bp, [
        {"from_node": "evt", "from_pin": "then", "to_node": "branch", "to_pin": "execute"},
        {"from_node": "get_cash", "from_pin": "Cash", "to_node": "sub", "to_pin": "A"},
        {"from_node": "get_price", "from_pin": "Price", "to_node": "sub", "to_pin": "B"},
        {"from_node": "sub", "from_pin": "ReturnValue", "to_node": "ge0", "to_pin": "A"},
        {"from_node": "ge0", "from_pin": "ReturnValue", "to_node": "branch", "to_pin": "Condition"},
        {"from_node": "branch", "from_pin": "True", "to_node": "set_cash", "to_pin": "execute"},
        {"from_node": "sub", "from_pin": "ReturnValue", "to_node": "set_cash", "to_pin": "Cash"},
        {"from_node": "set_cash", "from_pin": "then", "to_node": "p_bought", "to_pin": "execute"},
        {"from_node": "branch", "from_pin": "False", "to_node": "p_cant", "to_pin": "execute"},
    ])
    log(f"  Connections: {cok}/{cok+cf}")
    assert cf == 0, f"Connection failures: {cf}"
    cmd("compile_blueprint", blueprint=bp)


# ============================================================
# Test 14: String Concatenation Chain
# ============================================================
def test_14_string_concat():
    bp = "BP_Test14_StringConcat"
    create_bp(bp, variables=[
        {"name": "Make", "type": "String", "default": "Chevrolet"},
        {"name": "Model", "type": "String", "default": "350"},
        {"name": "Year", "type": "Int", "default": "1967"},
    ])

    nok, nf = add_nodes(bp, [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "get_make", "node_type": "GetVar", "params": {"Variable": "Make"}},
        {"node_id": "get_model", "node_type": "GetVar", "params": {"Variable": "Model"}},
        {"node_id": "get_year", "node_type": "GetVar", "params": {"Variable": "Year"}},
        {"node_id": "yr2str", "node_type": "/Script/Engine.KismetStringLibrary:Conv_IntToString"},
        {"node_id": "c1", "node_type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
        {"node_id": "c2", "node_type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
        {"node_id": "print", "node_type": "PrintString"},
    ])
    assert nf == 0, f"Node failures: {nf}"
    log(f"  Nodes: {nok}/{nok+nf}")

    cok, cf = add_conns(bp, [
        {"from_node": "begin", "from_pin": "then", "to_node": "print", "to_pin": "execute"},
        {"from_node": "get_make", "from_pin": "Make", "to_node": "c1", "to_pin": "A"},
        {"from_node": "get_model", "from_pin": "Model", "to_node": "c1", "to_pin": "B"},
        {"from_node": "c1", "from_pin": "ReturnValue", "to_node": "c2", "to_pin": "A"},
        {"from_node": "get_year", "from_pin": "Year", "to_node": "yr2str", "to_pin": "InInt"},
        {"from_node": "yr2str", "from_pin": "ReturnValue", "to_node": "c2", "to_pin": "B"},
        {"from_node": "c2", "from_pin": "ReturnValue", "to_node": "print", "to_pin": "InString"},
    ])
    log(f"  Connections: {cok}/{cok+cf}")
    assert cf == 0, f"Connection failures: {cf}"
    cmd("compile_blueprint", blueprint=bp)


# ============================================================
# Test 15: Full BP_TimeManager
# ============================================================
def test_15_time_manager():
    bp = "BP_Test15_TimeManager"
    create_bp(bp, variables=[
        {"name": "CurrentDay", "type": "Int", "default": "1"},
        {"name": "HumanTimeRemaining", "type": "Float", "default": "480.0"},
        {"name": "DailyBudget", "type": "Float", "default": "480.0"},
        {"name": "IsEndOfDay", "type": "Bool", "default": "false"},
    ])

    nodes = [
        # BeginPlay
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "get_budget", "node_type": "GetVar", "params": {"Variable": "DailyBudget"}},
        {"node_id": "set_time_init", "node_type": "SetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "p_start", "node_type": "PrintString", "params": {"InString": "Day started"}},
        # ConsumeTime
        {"node_id": "evt_consume", "node_type": "CustomEvent", "params": {"EventName": "ConsumeTime"}},
        {"node_id": "get_time", "node_type": "GetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "sub_time", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
        {"node_id": "set_time", "node_type": "SetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "leq_zero", "node_type": "/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble"},
        {"node_id": "br_end", "node_type": "Branch"},
        {"node_id": "p_consumed", "node_type": "PrintString", "params": {"InString": "Time consumed"}},
        # EndDay
        {"node_id": "evt_endday", "node_type": "CustomEvent", "params": {"EventName": "EndDay"}},
        {"node_id": "set_eod", "node_type": "SetVar", "params": {"Variable": "IsEndOfDay"}},
        {"node_id": "get_day", "node_type": "GetVar", "params": {"Variable": "CurrentDay"}},
        {"node_id": "add_day", "node_type": "/Script/Engine.KismetMathLibrary:Add_IntInt"},
        {"node_id": "set_day", "node_type": "SetVar", "params": {"Variable": "CurrentDay"}},
        {"node_id": "get_budget2", "node_type": "GetVar", "params": {"Variable": "DailyBudget"}},
        {"node_id": "set_time2", "node_type": "SetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "set_eod_f", "node_type": "SetVar", "params": {"Variable": "IsEndOfDay"}},
        {"node_id": "p_newday", "node_type": "PrintString", "params": {"InString": "New day started"}},
    ]

    nok, nf = add_nodes(bp, nodes)
    assert nf == 0, f"Node failures: {nf}"
    log(f"  Nodes: {nok}/{nok+nf} ({len(nodes)} expected)")

    connections = [
        # BeginPlay chain
        {"from_node": "begin", "from_pin": "then", "to_node": "set_time_init", "to_pin": "execute"},
        {"from_node": "get_budget", "from_pin": "DailyBudget", "to_node": "set_time_init", "to_pin": "HumanTimeRemaining"},
        {"from_node": "set_time_init", "from_pin": "then", "to_node": "p_start", "to_pin": "execute"},
        # ConsumeTime chain
        {"from_node": "evt_consume", "from_pin": "then", "to_node": "set_time", "to_pin": "execute"},
        {"from_node": "get_time", "from_pin": "HumanTimeRemaining", "to_node": "sub_time", "to_pin": "A"},
        {"from_node": "sub_time", "from_pin": "ReturnValue", "to_node": "set_time", "to_pin": "HumanTimeRemaining"},
        {"from_node": "set_time", "from_pin": "then", "to_node": "br_end", "to_pin": "execute"},
        {"from_node": "set_time", "from_pin": "HumanTimeRemaining", "to_node": "leq_zero", "to_pin": "A"},
        {"from_node": "leq_zero", "from_pin": "ReturnValue", "to_node": "br_end", "to_pin": "Condition"},
        {"from_node": "br_end", "from_pin": "False", "to_node": "p_consumed", "to_pin": "execute"},
        # EndDay chain
        {"from_node": "evt_endday", "from_pin": "then", "to_node": "set_eod", "to_pin": "execute"},
        {"from_node": "set_eod", "from_pin": "then", "to_node": "set_day", "to_pin": "execute"},
        {"from_node": "get_day", "from_pin": "CurrentDay", "to_node": "add_day", "to_pin": "A"},
        {"from_node": "add_day", "from_pin": "ReturnValue", "to_node": "set_day", "to_pin": "CurrentDay"},
        {"from_node": "set_day", "from_pin": "then", "to_node": "set_time2", "to_pin": "execute"},
        {"from_node": "get_budget2", "from_pin": "DailyBudget", "to_node": "set_time2", "to_pin": "HumanTimeRemaining"},
        {"from_node": "set_time2", "from_pin": "then", "to_node": "set_eod_f", "to_pin": "execute"},
        {"from_node": "set_eod_f", "from_pin": "then", "to_node": "p_newday", "to_pin": "execute"},
    ]

    cok, cf = add_conns(bp, connections)
    log(f"  Connections: {cok}/{cok+cf} ({len(connections)} expected)")
    assert cf == 0, f"Connection failures: {cf}"
    cmd("compile_blueprint", blueprint=bp)
    log(f"  Total: {len(nodes)} nodes, {len(connections)} connections")


# ============================================================
# Test 16: Full BP_EconomyManager
# ============================================================
def test_16_economy_manager():
    bp = "BP_Test16_EconomyMgr"
    create_bp(bp, variables=[
        {"name": "Cash", "type": "Float", "default": "15000.0"},
        {"name": "TotalRevenue", "type": "Float", "default": "0.0"},
        {"name": "TotalExpenses", "type": "Float", "default": "0.0"},
        {"name": "DailyOverhead", "type": "Float", "default": "50.0"},
    ])

    nodes = [
        # BeginPlay
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_start", "node_type": "PrintString", "params": {"InString": "Economy Manager initialized"}},
        # AddCash
        {"node_id": "evt_add", "node_type": "CustomEvent", "params": {"EventName": "AddCash"}},
        {"node_id": "gc_add", "node_type": "GetVar", "params": {"Variable": "Cash"}},
        {"node_id": "math_add", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "sc_add", "node_type": "SetVar", "params": {"Variable": "Cash"}},
        {"node_id": "gr_add", "node_type": "GetVar", "params": {"Variable": "TotalRevenue"}},
        {"node_id": "math_rev", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "sr_add", "node_type": "SetVar", "params": {"Variable": "TotalRevenue"}},
        {"node_id": "p_added", "node_type": "PrintString", "params": {"InString": "Cash added"}},
        # DeductCash
        {"node_id": "evt_ded", "node_type": "CustomEvent", "params": {"EventName": "DeductCash"}},
        {"node_id": "gc_ded", "node_type": "GetVar", "params": {"Variable": "Cash"}},
        {"node_id": "ge_ded", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
        {"node_id": "br_ded", "node_type": "Branch"},
        {"node_id": "sub_ded", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
        {"node_id": "sc_ded", "node_type": "SetVar", "params": {"Variable": "Cash"}},
        {"node_id": "ge_exp", "node_type": "GetVar", "params": {"Variable": "TotalExpenses"}},
        {"node_id": "math_exp", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "se_exp", "node_type": "SetVar", "params": {"Variable": "TotalExpenses"}},
        {"node_id": "p_deducted", "node_type": "PrintString", "params": {"InString": "Cash deducted"}},
        {"node_id": "p_insuff", "node_type": "PrintString", "params": {"InString": "Insufficient funds"}},
        # ProcessEndOfDay
        {"node_id": "evt_eod", "node_type": "CustomEvent", "params": {"EventName": "ProcessEndOfDay"}},
        {"node_id": "get_oh", "node_type": "GetVar", "params": {"Variable": "DailyOverhead"}},
        {"node_id": "p_eod", "node_type": "PrintString", "params": {"InString": "End of day processed"}},
    ]

    nok, nf = add_nodes(bp, nodes)
    assert nf == 0, f"Node failures: {nf}"
    log(f"  Nodes: {nok}/{nok+nf}")

    connections = [
        # BeginPlay
        {"from_node": "begin", "from_pin": "then", "to_node": "p_start", "to_pin": "execute"},
        # AddCash exec
        {"from_node": "evt_add", "from_pin": "then", "to_node": "sc_add", "to_pin": "execute"},
        {"from_node": "sc_add", "from_pin": "then", "to_node": "sr_add", "to_pin": "execute"},
        {"from_node": "sr_add", "from_pin": "then", "to_node": "p_added", "to_pin": "execute"},
        # AddCash data
        {"from_node": "gc_add", "from_pin": "Cash", "to_node": "math_add", "to_pin": "A"},
        {"from_node": "math_add", "from_pin": "ReturnValue", "to_node": "sc_add", "to_pin": "Cash"},
        {"from_node": "gr_add", "from_pin": "TotalRevenue", "to_node": "math_rev", "to_pin": "A"},
        {"from_node": "math_rev", "from_pin": "ReturnValue", "to_node": "sr_add", "to_pin": "TotalRevenue"},
        # DeductCash exec
        {"from_node": "evt_ded", "from_pin": "then", "to_node": "br_ded", "to_pin": "execute"},
        {"from_node": "br_ded", "from_pin": "True", "to_node": "sc_ded", "to_pin": "execute"},
        {"from_node": "sc_ded", "from_pin": "then", "to_node": "se_exp", "to_pin": "execute"},
        {"from_node": "se_exp", "from_pin": "then", "to_node": "p_deducted", "to_pin": "execute"},
        {"from_node": "br_ded", "from_pin": "False", "to_node": "p_insuff", "to_pin": "execute"},
        # DeductCash data
        {"from_node": "gc_ded", "from_pin": "Cash", "to_node": "ge_ded", "to_pin": "A"},
        {"from_node": "ge_ded", "from_pin": "ReturnValue", "to_node": "br_ded", "to_pin": "Condition"},
        {"from_node": "gc_ded", "from_pin": "Cash", "to_node": "sub_ded", "to_pin": "A"},
        {"from_node": "sub_ded", "from_pin": "ReturnValue", "to_node": "sc_ded", "to_pin": "Cash"},
        {"from_node": "ge_exp", "from_pin": "TotalExpenses", "to_node": "math_exp", "to_pin": "A"},
        {"from_node": "math_exp", "from_pin": "ReturnValue", "to_node": "se_exp", "to_pin": "TotalExpenses"},
        # ProcessEndOfDay
        {"from_node": "evt_eod", "from_pin": "then", "to_node": "p_eod", "to_pin": "execute"},
    ]

    cok, cf = add_conns(bp, connections)
    log(f"  Connections: {cok}/{cok+cf}")
    assert cf == 0, f"Connection failures: {cf}"
    cmd("compile_blueprint", blueprint=bp)
    log(f"  Total: {len(nodes)} nodes, {len(connections)} connections")


# ============================================================
# Test 17: Full BP_StationBase
# ============================================================
def test_17_station_base():
    bp = "BP_Test17_StationBase"
    create_bp(bp, variables=[
        {"name": "StationName", "type": "String", "default": "Workstation"},
        {"name": "IsPlayerNearby", "type": "Bool", "default": "false"},
        {"name": "IsStationActive", "type": "Bool", "default": "false"},
        {"name": "InteractionPrompt", "type": "String", "default": "Press E to interact"},
    ])

    nodes = [
        {"node_id": "overlap_in", "node_type": "Event_ReceiveActorBeginOverlap"},
        {"node_id": "overlap_out", "node_type": "Event_ReceiveActorEndOverlap"},
        {"node_id": "set_near_t", "node_type": "SetVar", "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "set_near_f", "node_type": "SetVar", "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "get_name", "node_type": "GetVar", "params": {"Variable": "StationName"}},
        {"node_id": "get_prompt", "node_type": "GetVar", "params": {"Variable": "InteractionPrompt"}},
        {"node_id": "concat", "node_type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
        {"node_id": "p_prompt", "node_type": "PrintString"},
        # Activate
        {"node_id": "evt_act", "node_type": "CustomEvent", "params": {"EventName": "ActivateStation"}},
        {"node_id": "get_nearby", "node_type": "GetVar", "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "get_active", "node_type": "GetVar", "params": {"Variable": "IsStationActive"}},
        {"node_id": "not_active", "node_type": "/Script/Engine.KismetMathLibrary:Not_PreBool"},
        {"node_id": "and_check", "node_type": "/Script/Engine.KismetMathLibrary:BooleanAND"},
        {"node_id": "br_act", "node_type": "Branch"},
        {"node_id": "set_active_t", "node_type": "SetVar", "params": {"Variable": "IsStationActive"}},
        {"node_id": "p_activated", "node_type": "PrintString", "params": {"InString": "Station activated"}},
        # Deactivate
        {"node_id": "evt_deact", "node_type": "CustomEvent", "params": {"EventName": "DeactivateStation"}},
        {"node_id": "set_active_f", "node_type": "SetVar", "params": {"Variable": "IsStationActive"}},
    ]

    nok, nf = add_nodes(bp, nodes)
    assert nf == 0, f"Node failures: {nf}"
    log(f"  Nodes: {nok}/{nok+nf}")

    connections = [
        # Overlap in
        {"from_node": "overlap_in", "from_pin": "then", "to_node": "set_near_t", "to_pin": "execute"},
        {"from_node": "set_near_t", "from_pin": "then", "to_node": "p_prompt", "to_pin": "execute"},
        {"from_node": "get_name", "from_pin": "StationName", "to_node": "concat", "to_pin": "A"},
        {"from_node": "get_prompt", "from_pin": "InteractionPrompt", "to_node": "concat", "to_pin": "B"},
        {"from_node": "concat", "from_pin": "ReturnValue", "to_node": "p_prompt", "to_pin": "InString"},
        # Overlap out
        {"from_node": "overlap_out", "from_pin": "then", "to_node": "set_near_f", "to_pin": "execute"},
        # Activate
        {"from_node": "evt_act", "from_pin": "then", "to_node": "br_act", "to_pin": "execute"},
        {"from_node": "get_nearby", "from_pin": "IsPlayerNearby", "to_node": "and_check", "to_pin": "A"},
        {"from_node": "get_active", "from_pin": "IsStationActive", "to_node": "not_active", "to_pin": "A"},
        {"from_node": "not_active", "from_pin": "ReturnValue", "to_node": "and_check", "to_pin": "B"},
        {"from_node": "and_check", "from_pin": "ReturnValue", "to_node": "br_act", "to_pin": "Condition"},
        {"from_node": "br_act", "from_pin": "True", "to_node": "set_active_t", "to_pin": "execute"},
        {"from_node": "set_active_t", "from_pin": "then", "to_node": "p_activated", "to_pin": "execute"},
        # Deactivate
        {"from_node": "evt_deact", "from_pin": "then", "to_node": "set_active_f", "to_pin": "execute"},
    ]

    cok, cf = add_conns(bp, connections)
    log(f"  Connections: {cok}/{cok+cf}")
    assert cf == 0, f"Connection failures: {cf}"
    cmd("compile_blueprint", blueprint=bp)
    log(f"  Total: {len(nodes)} nodes, {len(connections)} connections")


# ============================================================
# Test 18: GameMode with Sequence Spawner
# ============================================================
def test_18_gamemode_sequence():
    bp = "BP_Test18_GameMode"
    create_bp(bp, parent="GameModeBase")

    nodes = [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p1", "node_type": "PrintString", "params": {"InString": "Spawning Time Manager..."}},
        {"node_id": "p2", "node_type": "PrintString", "params": {"InString": "Spawning Economy Manager..."}},
        {"node_id": "p3", "node_type": "PrintString", "params": {"InString": "Spawning Shop Inventory..."}},
        {"node_id": "p4", "node_type": "PrintString", "params": {"InString": "Spawning Heat Manager..."}},
        {"node_id": "p5", "node_type": "PrintString", "params": {"InString": "Spawning HUD Manager..."}},
        {"node_id": "p_done", "node_type": "PrintString", "params": {"InString": "All managers spawned!"}},
    ]

    nok, nf = add_nodes(bp, nodes)
    assert nf == 0, f"Node failures: {nf}"
    log(f"  Nodes: {nok}/{nok+nf}")

    connections = [
        {"from_node": "begin", "from_pin": "then", "to_node": "p1", "to_pin": "execute"},
        {"from_node": "p1", "from_pin": "then", "to_node": "p2", "to_pin": "execute"},
        {"from_node": "p2", "from_pin": "then", "to_node": "p3", "to_pin": "execute"},
        {"from_node": "p3", "from_pin": "then", "to_node": "p4", "to_pin": "execute"},
        {"from_node": "p4", "from_pin": "then", "to_node": "p5", "to_pin": "execute"},
        {"from_node": "p5", "from_pin": "then", "to_node": "p_done", "to_pin": "execute"},
    ]

    cok, cf = add_conns(bp, connections)
    log(f"  Connections: {cok}/{cok+cf}")
    assert cf == 0, f"Connection failures: {cf}"
    cmd("compile_blueprint", blueprint=bp)


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    start = time.time()
    log(f"Arcwright Advanced Blueprint Test Suite")
    log(f"{'='*70}")

    try:
        r = cmd("health_check")
        assert r["status"] == "ok"
        log(f"Connected to UE: {r.get('data',{}).get('server','?')}")
    except Exception as e:
        log(f"FATAL: Cannot connect: {e}")
        sys.exit(1)

    tests = [
        ("Test 12: Chained Branches (quality eval)", test_12_chained_branches),
        ("Test 13: Purchase Flow (cash check)", test_13_purchase_flow),
        ("Test 14: String Concatenation", test_14_string_concat),
        ("Test 15: BP_TimeManager (20 nodes, 18 conns)", test_15_time_manager),
        ("Test 16: BP_EconomyManager (24 nodes, 20 conns)", test_16_economy_manager),
        ("Test 17: BP_StationBase (18 nodes, 14 conns)", test_17_station_base),
        ("Test 18: GameMode Sequence (7 nodes, 6 conns)", test_18_gamemode_sequence),
    ]

    for name, fn in tests:
        run_test(name, fn)

    elapsed = time.time() - start
    log(f"\n{'='*70}")
    log(f"RESULTS: {PASS_COUNT} PASS, {FAIL_COUNT} FAIL -- {elapsed:.1f}s")
    log(f"{'='*70}")
    for status, name, err in RESULTS:
        marker = "PASS" if status == "PASS" else "FAIL"
        log(f"  [{marker}] {name}")
        if err:
            log(f"         {err[:120]}")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Arcwright Advanced Test Results -- {datetime.now().isoformat()}\n")
        f.write(f"PASS: {PASS_COUNT}, FAIL: {FAIL_COUNT}\n\n")
        for status, name, err in RESULTS:
            f.write(f"{status}: {name}\n")
            if err:
                f.write(f"  Error: {err}\n")
    log(f"\nResults saved to {LOG_FILE}")
