"""
SYSTEM 1: BP_EconomyManager — The Money System
Design:
  Variables: Cash, Revenue, Expenses, ShopTier, DailyOverhead, LoanBalance,
             LoanInterestRate, DayNumber, TotalRevenue, TotalExpenses
  Events:
    AddRevenue(Amount:Float) — adds to Cash and tracks Revenue
    DeductExpense(Amount:Float) — subtracts from Cash and tracks Expenses
    ProcessEndOfDay() — deducts overhead, compounds loan interest, resets daily counters
    CheckAffordability() — branch on Cash >= threshold
  BeginPlay: Initialize with starting values, print status
  Target: 50+ nodes, 40+ connections
"""
import sys, os
sys.path.insert(0, "C:/Arcwright")
from scripts.state_manager import StateManager

sm = StateManager(project_dir="C:/Projects/BoreandStroke")
arc = sm.arc

print("=" * 70)
print("SYSTEM 1: BP_EconomyManager")
print("=" * 70)

# --- Delete old version to rebuild from scratch ---
arc.cmd("delete_blueprint", name="BP_EconomyManager")
import time; time.sleep(0.3)

# --- Create with variables ---
r = arc.cmd("create_blueprint", name="BP_EconomyManager", parent_class="Actor", variables=[
    {"name": "Cash", "type": "Float", "default": "5000.0"},
    {"name": "DailyRevenue", "type": "Float", "default": "0.0"},
    {"name": "DailyExpenses", "type": "Float", "default": "0.0"},
    {"name": "TotalRevenue", "type": "Float", "default": "0.0"},
    {"name": "TotalExpenses", "type": "Float", "default": "0.0"},
    {"name": "ShopTier", "type": "Int", "default": "1"},
    {"name": "DailyOverhead", "type": "Float", "default": "150.0"},
    {"name": "LoanBalance", "type": "Float", "default": "0.0"},
    {"name": "LoanInterestRate", "type": "Float", "default": "0.08"},
    {"name": "DayNumber", "type": "Int", "default": "1"},
])
print(f"  Created: {r.get('status')}")

# Skeleton compile
arc.cmd("compile_blueprint", name="BP_EconomyManager")
print("  Skeleton compiled")

# --- NODES ---
# BeginPlay chain: print starting cash
# AddRevenue event: Cash += Amount, DailyRevenue += Amount, TotalRevenue += Amount, print
# DeductExpense event: Cash -= Amount, DailyExpenses += Amount, TotalExpenses += Amount, print
# ProcessEndOfDay: deduct overhead, compound loan interest, reset daily, increment day, print summary
nodes = [
    # === AddRevenue Event (with Amount parameter) ===
    {"id": "evt_revenue", "type": "CustomEvent", "event": "AddRevenue",
     "params": [{"name": "Amount", "type": "Float"}]},
    {"id": "get_cash_r", "type": "GetVar", "variable": "Cash"},
    {"id": "add_cash_r", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_cash_r", "type": "SetVar", "variable": "Cash"},
    {"id": "get_rev", "type": "GetVar", "variable": "DailyRevenue"},
    {"id": "add_rev", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_rev", "type": "SetVar", "variable": "DailyRevenue"},
    {"id": "get_trev", "type": "GetVar", "variable": "TotalRevenue"},
    {"id": "add_trev", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_trev", "type": "SetVar", "variable": "TotalRevenue"},
    {"id": "get_cash_r2", "type": "GetVar", "variable": "Cash"},
    {"id": "conv_cash_r", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_rev", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_rev", "type": "PrintString"},

    # === DeductExpense Event (with Amount parameter) ===
    {"id": "evt_expense", "type": "CustomEvent", "event": "DeductExpense",
     "params": [{"name": "Amount", "type": "Float"}]},
    {"id": "get_cash_e", "type": "GetVar", "variable": "Cash"},
    {"id": "sub_cash_e", "type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
    {"id": "set_cash_e", "type": "SetVar", "variable": "Cash"},
    {"id": "get_exp", "type": "GetVar", "variable": "DailyExpenses"},
    {"id": "add_exp", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_exp", "type": "SetVar", "variable": "DailyExpenses"},
    {"id": "get_texp", "type": "GetVar", "variable": "TotalExpenses"},
    {"id": "add_texp", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_texp", "type": "SetVar", "variable": "TotalExpenses"},
    {"id": "get_cash_e2", "type": "GetVar", "variable": "Cash"},
    {"id": "conv_cash_e", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_exp", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_exp", "type": "PrintString"},

    # === ProcessEndOfDay Event ===
    {"id": "evt_eod", "type": "CustomEvent", "event": "ProcessEndOfDay",
     "params": []},
    # Deduct daily overhead from Cash
    {"id": "get_cash_oh", "type": "GetVar", "variable": "Cash"},
    {"id": "get_overhead", "type": "GetVar", "variable": "DailyOverhead"},
    {"id": "sub_overhead", "type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
    {"id": "set_cash_oh", "type": "SetVar", "variable": "Cash"},
    # Compound loan interest: LoanBalance += LoanBalance * (InterestRate / 365)
    {"id": "get_loan", "type": "GetVar", "variable": "LoanBalance"},
    {"id": "get_rate", "type": "GetVar", "variable": "LoanInterestRate"},
    {"id": "div_365", "type": "/Script/Engine.KismetMathLibrary:Divide_DoubleDouble"},
    {"id": "mul_interest", "type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
    {"id": "add_interest", "type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
    {"id": "set_loan", "type": "SetVar", "variable": "LoanBalance"},
    # Reset daily counters
    {"id": "set_rev_zero", "type": "SetVar", "variable": "DailyRevenue"},
    {"id": "set_exp_zero", "type": "SetVar", "variable": "DailyExpenses"},
    # Increment day
    {"id": "get_day", "type": "GetVar", "variable": "DayNumber"},
    {"id": "add_day", "type": "/Script/Engine.KismetMathLibrary:Add_IntInt"},
    {"id": "set_day", "type": "SetVar", "variable": "DayNumber"},
    # Print end-of-day summary
    {"id": "get_day2", "type": "GetVar", "variable": "DayNumber"},
    {"id": "conv_day", "type": "/Script/Engine.KismetStringLibrary:Conv_IntToString"},
    {"id": "get_cash_eod", "type": "GetVar", "variable": "Cash"},
    {"id": "conv_cash_eod", "type": "/Script/Engine.KismetStringLibrary:Conv_DoubleToString"},
    {"id": "concat_eod1", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_eod2", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "concat_eod3", "type": "/Script/Engine.KismetStringLibrary:Concat_StrStr"},
    {"id": "print_eod", "type": "PrintString"},

    # === BeginPlay: print init ===
    {"id": "print_init", "type": "PrintString", "params": {"InString": "EconomyManager: Cash=$5000, Tier=1, Overhead=$150/day"}},
]

r = arc.cmd("add_nodes_batch", blueprint="BP_EconomyManager", nodes=nodes)
d = r.get("data", {})
print(f"  Nodes: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    ERR: {e}")

# --- CONNECTIONS ---
conns = [
    # BeginPlay → print_init
    {"from_node": "node_0", "from_pin": "then", "to_node": "print_init", "to_pin": "execute"},

    # === AddRevenue chain ===
    {"from_node": "evt_revenue", "from_pin": "then", "to_node": "set_cash_r", "to_pin": "execute"},
    {"from_node": "get_cash_r", "from_pin": "Cash", "to_node": "add_cash_r", "to_pin": "A"},
    {"from_node": "evt_revenue", "from_pin": "Amount", "to_node": "add_cash_r", "to_pin": "B"},
    {"from_node": "add_cash_r", "from_pin": "ReturnValue", "to_node": "set_cash_r", "to_pin": "Cash"},
    {"from_node": "set_cash_r", "from_pin": "then", "to_node": "set_rev", "to_pin": "execute"},
    {"from_node": "get_rev", "from_pin": "DailyRevenue", "to_node": "add_rev", "to_pin": "A"},
    {"from_node": "evt_revenue", "from_pin": "Amount", "to_node": "add_rev", "to_pin": "B"},
    {"from_node": "add_rev", "from_pin": "ReturnValue", "to_node": "set_rev", "to_pin": "DailyRevenue"},
    {"from_node": "set_rev", "from_pin": "then", "to_node": "set_trev", "to_pin": "execute"},
    {"from_node": "get_trev", "from_pin": "TotalRevenue", "to_node": "add_trev", "to_pin": "A"},
    {"from_node": "evt_revenue", "from_pin": "Amount", "to_node": "add_trev", "to_pin": "B"},
    {"from_node": "add_trev", "from_pin": "ReturnValue", "to_node": "set_trev", "to_pin": "TotalRevenue"},
    {"from_node": "set_trev", "from_pin": "then", "to_node": "print_rev", "to_pin": "execute"},
    {"from_node": "get_cash_r2", "from_pin": "Cash", "to_node": "conv_cash_r", "to_pin": "InDouble"},
    {"from_node": "conv_cash_r", "from_pin": "ReturnValue", "to_node": "concat_rev", "to_pin": "B"},
    {"from_node": "concat_rev", "from_pin": "ReturnValue", "to_node": "print_rev", "to_pin": "InString"},

    # === DeductExpense chain ===
    {"from_node": "evt_expense", "from_pin": "then", "to_node": "set_cash_e", "to_pin": "execute"},
    {"from_node": "get_cash_e", "from_pin": "Cash", "to_node": "sub_cash_e", "to_pin": "A"},
    {"from_node": "evt_expense", "from_pin": "Amount", "to_node": "sub_cash_e", "to_pin": "B"},
    {"from_node": "sub_cash_e", "from_pin": "ReturnValue", "to_node": "set_cash_e", "to_pin": "Cash"},
    {"from_node": "set_cash_e", "from_pin": "then", "to_node": "set_exp", "to_pin": "execute"},
    {"from_node": "get_exp", "from_pin": "DailyExpenses", "to_node": "add_exp", "to_pin": "A"},
    {"from_node": "evt_expense", "from_pin": "Amount", "to_node": "add_exp", "to_pin": "B"},
    {"from_node": "add_exp", "from_pin": "ReturnValue", "to_node": "set_exp", "to_pin": "DailyExpenses"},
    {"from_node": "set_exp", "from_pin": "then", "to_node": "set_texp", "to_pin": "execute"},
    {"from_node": "get_texp", "from_pin": "TotalExpenses", "to_node": "add_texp", "to_pin": "A"},
    {"from_node": "evt_expense", "from_pin": "Amount", "to_node": "add_texp", "to_pin": "B"},
    {"from_node": "add_texp", "from_pin": "ReturnValue", "to_node": "set_texp", "to_pin": "TotalExpenses"},
    {"from_node": "set_texp", "from_pin": "then", "to_node": "print_exp", "to_pin": "execute"},
    {"from_node": "get_cash_e2", "from_pin": "Cash", "to_node": "conv_cash_e", "to_pin": "InDouble"},
    {"from_node": "conv_cash_e", "from_pin": "ReturnValue", "to_node": "concat_exp", "to_pin": "B"},
    {"from_node": "concat_exp", "from_pin": "ReturnValue", "to_node": "print_exp", "to_pin": "InString"},

    # === ProcessEndOfDay chain ===
    # Deduct overhead
    {"from_node": "evt_eod", "from_pin": "then", "to_node": "set_cash_oh", "to_pin": "execute"},
    {"from_node": "get_cash_oh", "from_pin": "Cash", "to_node": "sub_overhead", "to_pin": "A"},
    {"from_node": "get_overhead", "from_pin": "DailyOverhead", "to_node": "sub_overhead", "to_pin": "B"},
    {"from_node": "sub_overhead", "from_pin": "ReturnValue", "to_node": "set_cash_oh", "to_pin": "Cash"},
    # Compound interest: rate/365
    {"from_node": "set_cash_oh", "from_pin": "then", "to_node": "set_loan", "to_pin": "execute"},
    {"from_node": "get_rate", "from_pin": "LoanInterestRate", "to_node": "div_365", "to_pin": "A"},
    # loan * (rate/365)
    {"from_node": "get_loan", "from_pin": "LoanBalance", "to_node": "mul_interest", "to_pin": "A"},
    {"from_node": "div_365", "from_pin": "ReturnValue", "to_node": "mul_interest", "to_pin": "B"},
    # loan + interest
    {"from_node": "get_loan", "from_pin": "LoanBalance", "to_node": "add_interest", "to_pin": "A"},
    {"from_node": "mul_interest", "from_pin": "ReturnValue", "to_node": "add_interest", "to_pin": "B"},
    {"from_node": "add_interest", "from_pin": "ReturnValue", "to_node": "set_loan", "to_pin": "LoanBalance"},
    # Reset daily counters
    {"from_node": "set_loan", "from_pin": "then", "to_node": "set_rev_zero", "to_pin": "execute"},
    {"from_node": "set_rev_zero", "from_pin": "then", "to_node": "set_exp_zero", "to_pin": "execute"},
    # Increment day
    {"from_node": "set_exp_zero", "from_pin": "then", "to_node": "set_day", "to_pin": "execute"},
    {"from_node": "get_day", "from_pin": "DayNumber", "to_node": "add_day", "to_pin": "A"},
    {"from_node": "add_day", "from_pin": "ReturnValue", "to_node": "set_day", "to_pin": "DayNumber"},
    # Print EOD summary
    {"from_node": "set_day", "from_pin": "then", "to_node": "print_eod", "to_pin": "execute"},
    {"from_node": "get_day2", "from_pin": "DayNumber", "to_node": "conv_day", "to_pin": "InInt"},
    {"from_node": "conv_day", "from_pin": "ReturnValue", "to_node": "concat_eod1", "to_pin": "B"},
    {"from_node": "get_cash_eod", "from_pin": "Cash", "to_node": "conv_cash_eod", "to_pin": "InDouble"},
    {"from_node": "conv_cash_eod", "from_pin": "ReturnValue", "to_node": "concat_eod2", "to_pin": "B"},
    {"from_node": "concat_eod1", "from_pin": "ReturnValue", "to_node": "concat_eod2", "to_pin": "A"},
    {"from_node": "concat_eod2", "from_pin": "ReturnValue", "to_node": "concat_eod3", "to_pin": "A"},
    {"from_node": "concat_eod3", "from_pin": "ReturnValue", "to_node": "print_eod", "to_pin": "InString"},
]

r = arc.cmd("add_connections_batch", blueprint="BP_EconomyManager", connections=conns)
d = r.get("data", {})
print(f"  Connections: {d.get('succeeded')}/{d.get('total')}")
for e in d.get("errors", []):
    print(f"    CONN ERR: {e}")

# Set string prefixes
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="concat_rev",
        pin_name="A", value="[REVENUE] Cash: $")
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="concat_exp",
        pin_name="A", value="[EXPENSE] Cash: $")
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="concat_eod1",
        pin_name="A", value="[END OF DAY] Day ")
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="concat_eod3",
        pin_name="B", value=" | Overhead deducted, interest compounded")
# Set div_365 divisor
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="div_365",
        pin_name="B", value="365.0")
# Set daily counter reset values
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="set_rev_zero",
        pin_name="DailyRevenue", value="0.0")
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="set_exp_zero",
        pin_name="DailyExpenses", value="0.0")
# Set add_day increment
arc.cmd("set_node_param", blueprint="BP_EconomyManager", node_id="add_day",
        pin_name="B", value="1")

# --- COMPILE & VERIFY ---
r = arc.cmd("compile_blueprint", name="BP_EconomyManager")
compiled = r.get("data", {}).get("compiled", False)

r = arc.cmd("get_blueprint_details", blueprint="BP_EconomyManager")
d = r.get("data", {})
nodes_count = d.get("node_count", 0)
conns_count = d.get("connection_count", 0)
errors = [m for m in d.get("messages", []) if "error" in str(m).lower()]

print(f"\n  CHECK & CONFIRM:")
print(f"    Nodes:       {nodes_count}/50+ {'PASS' if nodes_count >= 50 else 'FAIL'}")
print(f"    Connections: {conns_count}/40+ {'PASS' if conns_count >= 40 else 'FAIL'}")
print(f"    Compiled:    {compiled} {'PASS' if compiled else 'FAIL'}")
print(f"    Errors:      {len(errors)} {'PASS' if len(errors) == 0 else 'FAIL'}")

# Check event parameter pins
for node in d.get("nodes", []):
    if "AddRevenue" in node.get("title", "") or "DeductExpense" in node.get("title", ""):
        pins = [p for p in node.get("pins", []) if not p.get("hidden")]
        param_pins = [p for p in pins if p.get("direction") == "output" and p.get("type") != "exec" and p.get("type") != "delegate"]
        print(f"    {node.get('title')} params: {[p.get('name') for p in param_pins]}")

# Spawn and PIE test
arc.cmd("delete_actor", label="EconomyManager")
arc.cmd("spawn_actor_at", label="EconomyManager", x=0, y=50, z=10,
        **{"class": "/Game/Arcwright/Generated/BP_EconomyManager.BP_EconomyManager_C"})
arc.cmd("save_all")

# Track in manifest
if "BP_EconomyManager" not in sm.manifest.get("blueprints", []):
    sm.manifest.setdefault("blueprints", []).append("BP_EconomyManager")
if "EconomyManager" not in sm.manifest.get("actors", []):
    sm.manifest.setdefault("actors", []).append("EconomyManager")
sm.save_manifest()

# PIE test
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
    msgs = [str(l) for l in r.get("data", {}).get("lines", []) if "EconomyManager" in str(l) or "REVENUE" in str(l) or "EXPENSE" in str(l) or "END OF DAY" in str(l)]
    print(f"\n  PIE Messages ({len(msgs)}):")
    for m in msgs:
        print(f"    {m[:120]}")
    arc.cmd("stop_play")
    time.sleep(1)
else:
    print("\n  PIE did not start!")

overall = nodes_count >= 50 and conns_count >= 40 and compiled and len(errors) == 0
print(f"\n  SYSTEM 1 RESULT: {'PASS' if overall else 'FAIL'}")
print(f"  Economy: {nodes_count} nodes, {conns_count} connections, compiled={compiled}")
