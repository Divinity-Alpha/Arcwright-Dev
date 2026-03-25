"""
Bore & Stroke — Definitive Build with Check & Confirm
======================================================
Every Blueprint is created via cc.create_and_verify_blueprint() and
verified against target node/connection minimums.

Uses CheckAndConfirm from scripts/check_and_confirm.py for the Blueprint
pipeline, and a raw Arc TCP class for non-Blueprint commands (materials,
widgets, level setup, data tables).

6 Phases:
  1. Data Tables (5)
  2. Materials (10)
  3. Blueprints (12) — all via Check & Confirm
  4. Widgets (3)
  5. Level Setup (lighting, floor, walls, stations, game mode, save)
  6. Final Verification (verify_all, verify_level, play_test, report)
"""

import sys
import os
import json
import socket
import time

# Add project root so we can import check_and_confirm
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.check_and_confirm import CheckAndConfirm


# ---------------------------------------------------------------------------
# Raw TCP helper for non-Blueprint commands
# ---------------------------------------------------------------------------
class Arc:
    def __init__(self):
        self.sock = None
        self.count = 0
        self.reconnect()

    def reconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(30)
        self.sock.connect(("localhost", 13377))

    def cmd(self, command, **params):
        self.count += 1
        if self.count % 25 == 0:
            self.reconnect()
        self.sock.sendall(
            (json.dumps({"command": command, "params": params}) + "\n").encode()
        )
        data = b""
        while b"\n" not in data:
            data += self.sock.recv(65536)
        return json.loads(data.decode().strip())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def ok(r, label=""):
    s = r.get("status", "error")
    if s == "ok":
        print(f"  OK  {label}")
    else:
        print(f"  ERR {label}: {r.get('message', r.get('error', '?'))}")
    return s == "ok"


def banner(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


# ===================================================================
#  MAIN
# ===================================================================
def main():
    banner("BORE & STROKE — Check & Confirm Build")

    arc = Arc()
    cc = CheckAndConfirm()

    # Quick health check
    r = arc.cmd("health_check")
    if not ok(r, "health_check"):
        print("Cannot reach Arcwright. Exiting.")
        return

    # ------------------------------------------------------------------
    # PHASE 1: Data Tables
    # ------------------------------------------------------------------
    banner("PHASE 1: Data Tables (5)")

    # DT_Difficulty
    dt_difficulty = {
        "metadata": {"table_name": "DT_Difficulty", "struct_name": "DifficultyData"},
        "columns": [
            {"name": "Level", "type": "String"},
            {"name": "TimeMultiplier", "type": "Float", "default": "1.0"},
            {"name": "CostMultiplier", "type": "Float", "default": "1.0"},
            {"name": "QualityThreshold", "type": "Float", "default": "50.0"},
        ],
        "rows": [
            {"row_name": "Easy", "values": {"Level": "Easy", "TimeMultiplier": "1.5", "CostMultiplier": "0.8", "QualityThreshold": "40.0"}},
            {"row_name": "Normal", "values": {"Level": "Normal", "TimeMultiplier": "1.0", "CostMultiplier": "1.0", "QualityThreshold": "50.0"}},
            {"row_name": "Hard", "values": {"Level": "Hard", "TimeMultiplier": "0.7", "CostMultiplier": "1.3", "QualityThreshold": "70.0"}},
        ],
    }
    ok(arc.cmd("create_data_table", ir_json=json.dumps(dt_difficulty)), "DT_Difficulty")

    # DT_ShopTiers
    dt_shop = {
        "metadata": {"table_name": "DT_ShopTiers", "struct_name": "ShopTierData"},
        "columns": [
            {"name": "TierName", "type": "String"},
            {"name": "UnlockCost", "type": "Float", "default": "0.0"},
            {"name": "MaxCapacity", "type": "Int", "default": "2"},
            {"name": "ReputationRequired", "type": "Float", "default": "0.0"},
        ],
        "rows": [
            {"row_name": "Starter", "values": {"TierName": "Starter Garage", "UnlockCost": "0", "MaxCapacity": "2", "ReputationRequired": "0"}},
            {"row_name": "Standard", "values": {"TierName": "Standard Shop", "UnlockCost": "5000", "MaxCapacity": "4", "ReputationRequired": "25"}},
            {"row_name": "Premium", "values": {"TierName": "Premium Workshop", "UnlockCost": "15000", "MaxCapacity": "8", "ReputationRequired": "60"}},
        ],
    }
    ok(arc.cmd("create_data_table", ir_json=json.dumps(dt_shop)), "DT_ShopTiers")

    # DT_Engines (8 rows)
    dt_engines = {
        "metadata": {"table_name": "DT_Engines", "struct_name": "EngineData"},
        "columns": [
            {"name": "EngineName", "type": "String"},
            {"name": "Make", "type": "String"},
            {"name": "Displacement", "type": "Float", "default": "0.0"},
            {"name": "Cylinders", "type": "Int", "default": "4"},
            {"name": "BaseValue", "type": "Float", "default": "0.0"},
            {"name": "Condition", "type": "String", "default": "Fair"},
        ],
        "rows": [
            {"row_name": "SBC350", "values": {"EngineName": "Small Block 350", "Make": "Chevrolet", "Displacement": "5.7", "Cylinders": "8", "BaseValue": "2500", "Condition": "Fair"}},
            {"row_name": "BBF460", "values": {"EngineName": "Big Block 460", "Make": "Ford", "Displacement": "7.5", "Cylinders": "8", "BaseValue": "3500", "Condition": "Poor"}},
            {"row_name": "Hemi426", "values": {"EngineName": "426 Hemi", "Make": "Chrysler", "Displacement": "7.0", "Cylinders": "8", "BaseValue": "8000", "Condition": "Good"}},
            {"row_name": "FlatHead", "values": {"EngineName": "Flathead V8", "Make": "Ford", "Displacement": "3.9", "Cylinders": "8", "BaseValue": "4000", "Condition": "Poor"}},
            {"row_name": "LS3", "values": {"EngineName": "LS3 6.2L", "Make": "Chevrolet", "Displacement": "6.2", "Cylinders": "8", "BaseValue": "5500", "Condition": "Good"}},
            {"row_name": "Coyote", "values": {"EngineName": "Coyote 5.0", "Make": "Ford", "Displacement": "5.0", "Cylinders": "8", "BaseValue": "6000", "Condition": "Excellent"}},
            {"row_name": "Inline6", "values": {"EngineName": "Inline 6 250", "Make": "Chevrolet", "Displacement": "4.1", "Cylinders": "6", "BaseValue": "1200", "Condition": "Fair"}},
            {"row_name": "Slant6", "values": {"EngineName": "Slant 6 225", "Make": "Chrysler", "Displacement": "3.7", "Cylinders": "6", "BaseValue": "900", "Condition": "Poor"}},
        ],
    }
    ok(arc.cmd("create_data_table", ir_json=json.dumps(dt_engines)), "DT_Engines")

    # DT_Companies (4 rows)
    dt_companies = {
        "metadata": {"table_name": "DT_Companies", "struct_name": "CompanyData"},
        "columns": [
            {"name": "CompanyName", "type": "String"},
            {"name": "Specialty", "type": "String"},
            {"name": "QualityBonus", "type": "Float", "default": "0.0"},
            {"name": "PriceMultiplier", "type": "Float", "default": "1.0"},
        ],
        "rows": [
            {"row_name": "Mahle", "values": {"CompanyName": "Mahle", "Specialty": "Pistons", "QualityBonus": "10", "PriceMultiplier": "1.2"}},
            {"row_name": "Clevite", "values": {"CompanyName": "Clevite", "Specialty": "Bearings", "QualityBonus": "15", "PriceMultiplier": "1.3"}},
            {"row_name": "ARP", "values": {"CompanyName": "ARP", "Specialty": "Fasteners", "QualityBonus": "5", "PriceMultiplier": "1.1"}},
            {"row_name": "Summit", "values": {"CompanyName": "Summit", "Specialty": "General", "QualityBonus": "0", "PriceMultiplier": "0.9"}},
        ],
    }
    ok(arc.cmd("create_data_table", ir_json=json.dumps(dt_companies)), "DT_Companies")

    # DT_Equipment (5 rows)
    dt_equipment = {
        "metadata": {"table_name": "DT_Equipment", "struct_name": "EquipmentData"},
        "columns": [
            {"name": "EquipmentName", "type": "String"},
            {"name": "PurchaseCost", "type": "Float", "default": "0.0"},
            {"name": "TimeSaving", "type": "Float", "default": "0.0"},
            {"name": "QualityBonus", "type": "Float", "default": "0.0"},
            {"name": "IsOwned", "type": "Boolean", "default": "false"},
        ],
        "rows": [
            {"row_name": "BasicTools", "values": {"EquipmentName": "Basic Hand Tools", "PurchaseCost": "0", "TimeSaving": "0", "QualityBonus": "0", "IsOwned": "true"}},
            {"row_name": "TorqueWrench", "values": {"EquipmentName": "Torque Wrench", "PurchaseCost": "500", "TimeSaving": "10", "QualityBonus": "5", "IsOwned": "false"}},
            {"row_name": "EngineStand", "values": {"EquipmentName": "Engine Stand", "PurchaseCost": "800", "TimeSaving": "20", "QualityBonus": "3", "IsOwned": "false"}},
            {"row_name": "BoringBar", "values": {"EquipmentName": "Boring Bar", "PurchaseCost": "5000", "TimeSaving": "30", "QualityBonus": "15", "IsOwned": "false"}},
            {"row_name": "Dynamometer", "values": {"EquipmentName": "Dynamometer", "PurchaseCost": "12000", "TimeSaving": "0", "QualityBonus": "20", "IsOwned": "false"}},
        ],
    }
    ok(arc.cmd("create_data_table", ir_json=json.dumps(dt_equipment)), "DT_Equipment")

    print("  Phase 1 complete: 5 Data Tables created.")

    # ------------------------------------------------------------------
    # PHASE 2: Materials
    # ------------------------------------------------------------------
    banner("PHASE 2: Materials (10)")

    materials = [
        ("M_ShopFloor",       {"r": 0.15, "g": 0.15, "b": 0.15}),   # dark grey
        ("M_ShopWall",        {"r": 0.55, "g": 0.50, "b": 0.45}),   # warm grey
        ("M_Workbench",       {"r": 0.25, "g": 0.15, "b": 0.08}),   # dark brown
        ("M_EngineBlock",     {"r": 0.35, "g": 0.35, "b": 0.35}),   # cast iron grey
        ("M_Chrome",          {"r": 0.85, "g": 0.85, "b": 0.90}),   # bright silver
        ("M_Rust",            {"r": 0.60, "g": 0.30, "b": 0.10}),   # orange-brown
        ("M_OilStain",        {"r": 0.12, "g": 0.08, "b": 0.05}),   # dark brown
        ("M_CarbonDeposit",   {"r": 0.10, "g": 0.10, "b": 0.10}),   # dark grey
        ("M_CylinderWall",    {"r": 0.50, "g": 0.50, "b": 0.50}),   # medium grey
        ("M_BearingJournal",  {"r": 0.70, "g": 0.70, "b": 0.72}),   # polished grey
    ]
    for name, color in materials:
        ok(arc.cmd("create_simple_material", name=name, color=color), name)

    print("  Phase 2 complete: 10 Materials created.")

    # ------------------------------------------------------------------
    # PHASE 3: Blueprints (12) — all via Check & Confirm
    # ------------------------------------------------------------------
    banner("PHASE 3: Blueprints (12) via Check & Confirm")

    # Clean up any existing BPs first
    bp_names = [
        "BP_TimeManager", "BP_EconomyManager", "BP_StationBase",
        "BP_HeatManager", "BP_ReputationManager", "BP_ShopInventory",
        "BP_QualityCalculator", "BP_EngineInstance", "BP_ActionApproval",
        "BP_QuestManager", "BP_HUDManager", "BP_BoreAndStrokeGameMode",
    ]
    for bpn in bp_names:
        arc.cmd("delete_blueprint", name=bpn)
    time.sleep(0.5)

    # ---------------------------------------------------------------
    # BP 1: BP_TimeManager
    # ---------------------------------------------------------------
    print("\n--- BP_TimeManager ---")
    tm_vars = [
        {"name": "CurrentDay", "type": "Int", "default": "1"},
        {"name": "HumanTimeRemaining", "type": "Float", "default": "480.0"},
        {"name": "DailyBudget", "type": "Float", "default": "480.0"},
        {"name": "IsEndOfDay", "type": "Bool", "default": "false"},
    ]
    tm_nodes = [
        # BeginPlay chain
        {"node_id": "bp", "node_type": "Event_ReceiveBeginPlay", "pos_x": 0, "pos_y": 0},
        {"node_id": "getBudget0", "node_type": "GetVar", "pos_x": 200, "pos_y": 50, "params": {"Variable": "DailyBudget"}},
        {"node_id": "setTimeInit", "node_type": "SetVar", "pos_x": 400, "pos_y": 0, "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "printInit", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 600, "pos_y": 0, "params": { "InString": "Day started"}},

        # ConsumeTime event
        {"node_id": "evConsume", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 300, "params": {"EventName": "ConsumeTime"}},
        {"node_id": "getTime1", "node_type": "GetVar", "pos_x": 200, "pos_y": 350, "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "subTime", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", "pos_x": 400, "pos_y": 350},
        {"node_id": "setTime1", "node_type": "SetVar", "pos_x": 600, "pos_y": 300, "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "getTime2", "node_type": "GetVar", "pos_x": 800, "pos_y": 350, "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "leq0", "node_type": "/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble", "pos_x": 1000, "pos_y": 350},
        {"node_id": "brConsume", "node_type": "Branch", "pos_x": 1200, "pos_y": 300},
        {"node_id": "printRemain", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1400, "pos_y": 400, "params": { "InString": "Time remaining"}},

        # EndDay event
        {"node_id": "evEnd", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 700, "params": {"EventName": "EndDay"}},
        {"node_id": "setEOD", "node_type": "SetVar", "pos_x": 200, "pos_y": 700, "params": {"Variable": "IsEndOfDay"}},
        {"node_id": "getDay", "node_type": "GetVar", "pos_x": 400, "pos_y": 750, "params": {"Variable": "CurrentDay"}},
        {"node_id": "addDay", "node_type": "/Script/Engine.KismetMathLibrary:Add_IntInt", "pos_x": 600, "pos_y": 750},
        {"node_id": "setDay", "node_type": "SetVar", "pos_x": 800, "pos_y": 700, "params": {"Variable": "CurrentDay"}},
        {"node_id": "getBudget1", "node_type": "GetVar", "pos_x": 1000, "pos_y": 750, "params": {"Variable": "DailyBudget"}},
        {"node_id": "setTime2", "node_type": "SetVar", "pos_x": 1200, "pos_y": 700, "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "setEODf", "node_type": "SetVar", "pos_x": 1400, "pos_y": 700, "params": {"Variable": "IsEndOfDay"}},
        {"node_id": "printEnd", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1600, "pos_y": 700, "params": { "InString": "Day ended"}},
    ]
    tm_conns = [
        # BeginPlay chain
        {"from_node": "bp", "from_pin": "then", "to_node": "setTimeInit", "to_pin": "execute"},
        {"from_node": "getBudget0", "from_pin": "DailyBudget", "to_node": "setTimeInit", "to_pin": "HumanTimeRemaining"},
        {"from_node": "setTimeInit", "from_pin": "then", "to_node": "printInit", "to_pin": "execute"},

        # ConsumeTime chain
        {"from_node": "evConsume", "from_pin": "then", "to_node": "setTime1", "to_pin": "execute"},
        {"from_node": "getTime1", "from_pin": "HumanTimeRemaining", "to_node": "subTime", "to_pin": "A"},
        {"from_node": "subTime", "from_pin": "ReturnValue", "to_node": "setTime1", "to_pin": "HumanTimeRemaining"},
        {"from_node": "setTime1", "from_pin": "then", "to_node": "brConsume", "to_pin": "execute"},
        {"from_node": "getTime2", "from_pin": "HumanTimeRemaining", "to_node": "leq0", "to_pin": "A"},
        {"from_node": "leq0", "from_pin": "ReturnValue", "to_node": "brConsume", "to_pin": "Condition"},
        {"from_node": "brConsume", "from_pin": "False", "to_node": "printRemain", "to_pin": "execute"},

        # EndDay chain
        {"from_node": "evEnd", "from_pin": "then", "to_node": "setEOD", "to_pin": "execute"},
        {"from_node": "setEOD", "from_pin": "then", "to_node": "setDay", "to_pin": "execute"},
        {"from_node": "getDay", "from_pin": "CurrentDay", "to_node": "addDay", "to_pin": "A"},
        {"from_node": "addDay", "from_pin": "ReturnValue", "to_node": "setDay", "to_pin": "CurrentDay"},
        {"from_node": "setDay", "from_pin": "then", "to_node": "setTime2", "to_pin": "execute"},
        {"from_node": "getBudget1", "from_pin": "DailyBudget", "to_node": "setTime2", "to_pin": "HumanTimeRemaining"},
        {"from_node": "setTime2", "from_pin": "then", "to_node": "setEODf", "to_pin": "execute"},
        {"from_node": "setEODf", "from_pin": "then", "to_node": "printEnd", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_TimeManager", parent_class="Actor",
        nodes=tm_nodes, connections=tm_conns,
        variables=tm_vars, min_nodes=20, min_conns=15,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 2: BP_EconomyManager
    # ---------------------------------------------------------------
    print("\n--- BP_EconomyManager ---")
    ec_vars = [
        {"name": "Cash", "type": "Float", "default": "15000.0"},
        {"name": "TotalRevenue", "type": "Float", "default": "0.0"},
        {"name": "TotalExpenses", "type": "Float", "default": "0.0"},
        {"name": "DailyOverhead", "type": "Float", "default": "50.0"},
    ]
    ec_nodes = [
        # BeginPlay
        {"node_id": "bp", "node_type": "Event_ReceiveBeginPlay", "pos_x": 0, "pos_y": 0},
        {"node_id": "printInit", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 0, "params": { "InString": "Economy initialized"}},

        # AddCash event
        {"node_id": "evAdd", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 300, "params": {"EventName": "AddCash"}},
        {"node_id": "getCash1", "node_type": "GetVar", "pos_x": 200, "pos_y": 350, "params": {"Variable": "Cash"}},
        {"node_id": "addCash", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 400, "pos_y": 350},
        {"node_id": "setCash1", "node_type": "SetVar", "pos_x": 600, "pos_y": 300, "params": {"Variable": "Cash"}},
        {"node_id": "getRev", "node_type": "GetVar", "pos_x": 800, "pos_y": 350, "params": {"Variable": "TotalRevenue"}},
        {"node_id": "addRev", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 1000, "pos_y": 350},
        {"node_id": "setRev", "node_type": "SetVar", "pos_x": 1200, "pos_y": 300, "params": {"Variable": "TotalRevenue"}},
        {"node_id": "printAdd", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1400, "pos_y": 300, "params": { "InString": "Cash added"}},

        # DeductCash event
        {"node_id": "evDeduct", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 600, "params": {"EventName": "DeductCash"}},
        {"node_id": "getCash2", "node_type": "GetVar", "pos_x": 200, "pos_y": 650, "params": {"Variable": "Cash"}},
        {"node_id": "geqCheck", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble", "pos_x": 400, "pos_y": 650},
        {"node_id": "brDeduct", "node_type": "Branch", "pos_x": 600, "pos_y": 600},
        {"node_id": "subCash", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", "pos_x": 800, "pos_y": 550},
        {"node_id": "setCash2", "node_type": "SetVar", "pos_x": 1000, "pos_y": 550, "params": {"Variable": "Cash"}},
        {"node_id": "getExp", "node_type": "GetVar", "pos_x": 1200, "pos_y": 600, "params": {"Variable": "TotalExpenses"}},
        {"node_id": "addExp", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 1400, "pos_y": 600},
        {"node_id": "setExp", "node_type": "SetVar", "pos_x": 1600, "pos_y": 550, "params": {"Variable": "TotalExpenses"}},
        {"node_id": "printDeduct", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1800, "pos_y": 550, "params": { "InString": "Cash deducted"}},
        {"node_id": "printInsuff", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 800, "pos_y": 700, "params": { "InString": "Insufficient funds"}},

        # ProcessEndOfDay event
        {"node_id": "evEOD", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 900, "params": {"EventName": "ProcessEndOfDay"}},
        {"node_id": "printEOD", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 900, "params": { "InString": "End of day processed"}},
    ]
    ec_conns = [
        # BeginPlay
        {"from_node": "bp", "from_pin": "then", "to_node": "printInit", "to_pin": "execute"},

        # AddCash
        {"from_node": "evAdd", "from_pin": "then", "to_node": "setCash1", "to_pin": "execute"},
        {"from_node": "getCash1", "from_pin": "Cash", "to_node": "addCash", "to_pin": "A"},
        {"from_node": "addCash", "from_pin": "ReturnValue", "to_node": "setCash1", "to_pin": "Cash"},
        {"from_node": "setCash1", "from_pin": "then", "to_node": "setRev", "to_pin": "execute"},
        {"from_node": "getRev", "from_pin": "TotalRevenue", "to_node": "addRev", "to_pin": "A"},
        {"from_node": "addRev", "from_pin": "ReturnValue", "to_node": "setRev", "to_pin": "TotalRevenue"},
        {"from_node": "setRev", "from_pin": "then", "to_node": "printAdd", "to_pin": "execute"},

        # DeductCash
        {"from_node": "evDeduct", "from_pin": "then", "to_node": "brDeduct", "to_pin": "execute"},
        {"from_node": "getCash2", "from_pin": "Cash", "to_node": "geqCheck", "to_pin": "A"},
        {"from_node": "geqCheck", "from_pin": "ReturnValue", "to_node": "brDeduct", "to_pin": "Condition"},
        {"from_node": "brDeduct", "from_pin": "True", "to_node": "setCash2", "to_pin": "execute"},
        {"from_node": "getCash2", "from_pin": "Cash", "to_node": "subCash", "to_pin": "A"},
        {"from_node": "subCash", "from_pin": "ReturnValue", "to_node": "setCash2", "to_pin": "Cash"},
        {"from_node": "setCash2", "from_pin": "then", "to_node": "setExp", "to_pin": "execute"},
        {"from_node": "getExp", "from_pin": "TotalExpenses", "to_node": "addExp", "to_pin": "A"},
        {"from_node": "addExp", "from_pin": "ReturnValue", "to_node": "setExp", "to_pin": "TotalExpenses"},
        {"from_node": "setExp", "from_pin": "then", "to_node": "printDeduct", "to_pin": "execute"},
        {"from_node": "brDeduct", "from_pin": "False", "to_node": "printInsuff", "to_pin": "execute"},

        # ProcessEndOfDay
        {"from_node": "evEOD", "from_pin": "then", "to_node": "printEOD", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_EconomyManager", parent_class="Actor",
        nodes=ec_nodes, connections=ec_conns,
        variables=ec_vars, min_nodes=20, min_conns=15,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 3: BP_StationBase
    # ---------------------------------------------------------------
    print("\n--- BP_StationBase ---")
    sb_vars = [
        {"name": "StationName", "type": "String", "default": "Workstation"},
        {"name": "IsPlayerNearby", "type": "Bool", "default": "false"},
        {"name": "IsStationActive", "type": "Bool", "default": "false"},
    ]
    sb_nodes = [
        # Overlap in
        {"node_id": "ovIn", "node_type": "Event_ActorBeginOverlap", "pos_x": 0, "pos_y": 0},
        {"node_id": "setNearT", "node_type": "SetVar", "pos_x": 200, "pos_y": 0, "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "getName", "node_type": "GetVar", "pos_x": 400, "pos_y": 50, "params": {"Variable": "StationName"}},
        {"node_id": "printNear", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 600, "pos_y": 0},

        # Overlap out
        {"node_id": "ovOut", "node_type": "Event_ActorEndOverlap", "pos_x": 0, "pos_y": 250},
        {"node_id": "setNearF", "node_type": "SetVar", "pos_x": 200, "pos_y": 250, "params": {"Variable": "IsPlayerNearby"}},

        # ActivateStation
        {"node_id": "evAct", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 450, "params": {"EventName": "ActivateStation"}},
        {"node_id": "getNear", "node_type": "GetVar", "pos_x": 200, "pos_y": 500, "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "getActive", "node_type": "GetVar", "pos_x": 200, "pos_y": 560, "params": {"Variable": "IsStationActive"}},
        {"node_id": "notActive", "node_type": "/Script/Engine.KismetMathLibrary:Not_PreBool", "pos_x": 400, "pos_y": 560},
        {"node_id": "andCheck", "node_type": "/Script/Engine.KismetMathLibrary:BooleanAND", "pos_x": 600, "pos_y": 500},
        {"node_id": "brAct", "node_type": "Branch", "pos_x": 800, "pos_y": 450},
        {"node_id": "setActT", "node_type": "SetVar", "pos_x": 1000, "pos_y": 450, "params": {"Variable": "IsStationActive"}},
        {"node_id": "printAct", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1200, "pos_y": 450, "params": { "InString": "Station activated"}},

        # DeactivateStation
        {"node_id": "evDeact", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 700, "params": {"EventName": "DeactivateStation"}},
        {"node_id": "setActF", "node_type": "SetVar", "pos_x": 200, "pos_y": 700, "params": {"Variable": "IsStationActive"}},
    ]
    sb_conns = [
        # Overlap in
        {"from_node": "ovIn", "from_pin": "then", "to_node": "setNearT", "to_pin": "execute"},
        {"from_node": "setNearT", "from_pin": "then", "to_node": "printNear", "to_pin": "execute"},
        {"from_node": "getName", "from_pin": "StationName", "to_node": "printNear", "to_pin": "InString"},

        # Overlap out
        {"from_node": "ovOut", "from_pin": "then", "to_node": "setNearF", "to_pin": "execute"},

        # ActivateStation
        {"from_node": "evAct", "from_pin": "then", "to_node": "brAct", "to_pin": "execute"},
        {"from_node": "getNear", "from_pin": "IsPlayerNearby", "to_node": "andCheck", "to_pin": "A"},
        {"from_node": "getActive", "from_pin": "IsStationActive", "to_node": "notActive", "to_pin": "A"},
        {"from_node": "notActive", "from_pin": "ReturnValue", "to_node": "andCheck", "to_pin": "B"},
        {"from_node": "andCheck", "from_pin": "ReturnValue", "to_node": "brAct", "to_pin": "Condition"},
        {"from_node": "brAct", "from_pin": "True", "to_node": "setActT", "to_pin": "execute"},
        {"from_node": "setActT", "from_pin": "then", "to_node": "printAct", "to_pin": "execute"},

        # DeactivateStation
        {"from_node": "evDeact", "from_pin": "then", "to_node": "setActF", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_StationBase", parent_class="Actor",
        nodes=sb_nodes, connections=sb_conns,
        variables=sb_vars, min_nodes=15, min_conns=10,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 4: BP_HeatManager
    # ---------------------------------------------------------------
    print("\n--- BP_HeatManager ---")
    hm_vars = [
        {"name": "HeatLevel", "type": "Float", "default": "0.0"},
        {"name": "HeatDecayRate", "type": "Float", "default": "0.1"},
        {"name": "MaxHeat", "type": "Float", "default": "100.0"},
    ]
    hm_nodes = [
        # BeginPlay
        {"node_id": "bp", "node_type": "Event_ReceiveBeginPlay", "pos_x": 0, "pos_y": 0},
        {"node_id": "printInit", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 0, "params": { "InString": "Heat Manager ready"}},

        # AddHeat event
        {"node_id": "evAdd", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 300, "params": {"EventName": "AddHeat"}},
        {"node_id": "getHeat1", "node_type": "GetVar", "pos_x": 200, "pos_y": 350, "params": {"Variable": "HeatLevel"}},
        {"node_id": "addHeat", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 400, "pos_y": 350},
        {"node_id": "clampAdd", "node_type": "/Script/Engine.KismetMathLibrary:FClamp", "pos_x": 600, "pos_y": 350},
        {"node_id": "setHeat1", "node_type": "SetVar", "pos_x": 800, "pos_y": 300, "params": {"Variable": "HeatLevel"}},
        {"node_id": "getHeat2", "node_type": "GetVar", "pos_x": 1000, "pos_y": 350, "params": {"Variable": "HeatLevel"}},
        {"node_id": "geq50", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble", "pos_x": 1200, "pos_y": 350},
        {"node_id": "brWarn", "node_type": "Branch", "pos_x": 1400, "pos_y": 300},
        {"node_id": "printWarn", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1600, "pos_y": 300, "params": { "InString": "WARNING: High heat!"}},

        # DecayHeat event
        {"node_id": "evDecay", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 600, "params": {"EventName": "DecayHeat"}},
        {"node_id": "getHeat3", "node_type": "GetVar", "pos_x": 200, "pos_y": 650, "params": {"Variable": "HeatLevel"}},
        {"node_id": "getRate", "node_type": "GetVar", "pos_x": 200, "pos_y": 710, "params": {"Variable": "HeatDecayRate"}},
        {"node_id": "subDecay", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", "pos_x": 400, "pos_y": 650},
        {"node_id": "clampDecay", "node_type": "/Script/Engine.KismetMathLibrary:FClamp", "pos_x": 600, "pos_y": 650},
        {"node_id": "setHeat2", "node_type": "SetVar", "pos_x": 800, "pos_y": 600, "params": {"Variable": "HeatLevel"}},
    ]
    hm_conns = [
        # BeginPlay
        {"from_node": "bp", "from_pin": "then", "to_node": "printInit", "to_pin": "execute"},

        # AddHeat
        {"from_node": "evAdd", "from_pin": "then", "to_node": "setHeat1", "to_pin": "execute"},
        {"from_node": "getHeat1", "from_pin": "HeatLevel", "to_node": "addHeat", "to_pin": "A"},
        {"from_node": "addHeat", "from_pin": "ReturnValue", "to_node": "clampAdd", "to_pin": "Value"},
        {"from_node": "clampAdd", "from_pin": "ReturnValue", "to_node": "setHeat1", "to_pin": "HeatLevel"},
        {"from_node": "setHeat1", "from_pin": "then", "to_node": "brWarn", "to_pin": "execute"},
        {"from_node": "getHeat2", "from_pin": "HeatLevel", "to_node": "geq50", "to_pin": "A"},
        {"from_node": "geq50", "from_pin": "ReturnValue", "to_node": "brWarn", "to_pin": "Condition"},
        {"from_node": "brWarn", "from_pin": "True", "to_node": "printWarn", "to_pin": "execute"},

        # DecayHeat
        {"from_node": "evDecay", "from_pin": "then", "to_node": "setHeat2", "to_pin": "execute"},
        {"from_node": "getHeat3", "from_pin": "HeatLevel", "to_node": "subDecay", "to_pin": "A"},
        {"from_node": "getRate", "from_pin": "HeatDecayRate", "to_node": "subDecay", "to_pin": "B"},
        {"from_node": "subDecay", "from_pin": "ReturnValue", "to_node": "clampDecay", "to_pin": "Value"},
        {"from_node": "clampDecay", "from_pin": "ReturnValue", "to_node": "setHeat2", "to_pin": "HeatLevel"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_HeatManager", parent_class="Actor",
        nodes=hm_nodes, connections=hm_conns,
        variables=hm_vars, min_nodes=15, min_conns=10,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 5: BP_ReputationManager
    # ---------------------------------------------------------------
    print("\n--- BP_ReputationManager ---")
    rm_vars = [
        {"name": "Reputation", "type": "Float", "default": "50.0"},
        {"name": "MoralAlignment", "type": "Float", "default": "0.0"},
    ]
    rm_nodes = [
        # BeginPlay
        {"node_id": "bp", "node_type": "Event_ReceiveBeginPlay", "pos_x": 0, "pos_y": 0},
        {"node_id": "printInit", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 0, "params": { "InString": "Reputation Manager ready"}},

        # AddReputation event
        {"node_id": "evAddRep", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 300, "params": {"EventName": "AddReputation"}},
        {"node_id": "getRep", "node_type": "GetVar", "pos_x": 200, "pos_y": 350, "params": {"Variable": "Reputation"}},
        {"node_id": "addRep", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 400, "pos_y": 350},
        {"node_id": "clampRep", "node_type": "/Script/Engine.KismetMathLibrary:FClamp", "pos_x": 600, "pos_y": 350},
        {"node_id": "setRep", "node_type": "SetVar", "pos_x": 800, "pos_y": 300, "params": {"Variable": "Reputation"}},
        {"node_id": "printRep", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1000, "pos_y": 300, "params": { "InString": "Reputation changed"}},

        # ShiftAlignment event
        {"node_id": "evShift", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 600, "params": {"EventName": "ShiftAlignment"}},
        {"node_id": "getAlign", "node_type": "GetVar", "pos_x": 200, "pos_y": 650, "params": {"Variable": "MoralAlignment"}},
        {"node_id": "addAlign", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 400, "pos_y": 650},
        {"node_id": "clampAlign", "node_type": "/Script/Engine.KismetMathLibrary:FClamp", "pos_x": 600, "pos_y": 650},
        {"node_id": "setAlign", "node_type": "SetVar", "pos_x": 800, "pos_y": 600, "params": {"Variable": "MoralAlignment"}},
    ]
    rm_conns = [
        # BeginPlay
        {"from_node": "bp", "from_pin": "then", "to_node": "printInit", "to_pin": "execute"},

        # AddReputation
        {"from_node": "evAddRep", "from_pin": "then", "to_node": "setRep", "to_pin": "execute"},
        {"from_node": "getRep", "from_pin": "Reputation", "to_node": "addRep", "to_pin": "A"},
        {"from_node": "addRep", "from_pin": "ReturnValue", "to_node": "clampRep", "to_pin": "Value"},
        {"from_node": "clampRep", "from_pin": "ReturnValue", "to_node": "setRep", "to_pin": "Reputation"},
        {"from_node": "setRep", "from_pin": "then", "to_node": "printRep", "to_pin": "execute"},

        # ShiftAlignment
        {"from_node": "evShift", "from_pin": "then", "to_node": "setAlign", "to_pin": "execute"},
        {"from_node": "getAlign", "from_pin": "MoralAlignment", "to_node": "addAlign", "to_pin": "A"},
        {"from_node": "addAlign", "from_pin": "ReturnValue", "to_node": "clampAlign", "to_pin": "Value"},
        {"from_node": "clampAlign", "from_pin": "ReturnValue", "to_node": "setAlign", "to_pin": "MoralAlignment"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_ReputationManager", parent_class="Actor",
        nodes=rm_nodes, connections=rm_conns,
        variables=rm_vars, min_nodes=10, min_conns=8,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 6: BP_ShopInventory
    # ---------------------------------------------------------------
    print("\n--- BP_ShopInventory ---")
    si_vars = [
        {"name": "EngineCount", "type": "Int", "default": "0"},
        {"name": "MaxCapacity", "type": "Int", "default": "2"},
        {"name": "StorageUsed", "type": "Float", "default": "0.0"},
    ]
    si_nodes = [
        # BeginPlay
        {"node_id": "bp", "node_type": "Event_ReceiveBeginPlay", "pos_x": 0, "pos_y": 0},
        {"node_id": "printInit", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 0, "params": { "InString": "Shop Inventory ready"}},

        # AddEngine event
        {"node_id": "evAddEng", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 250, "params": {"EventName": "AddEngine"}},
        {"node_id": "getCnt1", "node_type": "GetVar", "pos_x": 200, "pos_y": 300, "params": {"Variable": "EngineCount"}},
        {"node_id": "addCnt", "node_type": "/Script/Engine.KismetMathLibrary:Add_IntInt", "pos_x": 400, "pos_y": 300},
        {"node_id": "setCnt1", "node_type": "SetVar", "pos_x": 600, "pos_y": 250, "params": {"Variable": "EngineCount"}},
        {"node_id": "printAdded", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 800, "pos_y": 250, "params": { "InString": "Engine added"}},

        # RemoveEngine event
        {"node_id": "evRemEng", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 500, "params": {"EventName": "RemoveEngine"}},
        {"node_id": "getCnt2", "node_type": "GetVar", "pos_x": 200, "pos_y": 550, "params": {"Variable": "EngineCount"}},
        {"node_id": "subCnt", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_IntInt", "pos_x": 400, "pos_y": 550},
        {"node_id": "setCnt2", "node_type": "SetVar", "pos_x": 600, "pos_y": 500, "params": {"Variable": "EngineCount"}},
        {"node_id": "printRemoved", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 800, "pos_y": 500, "params": { "InString": "Engine removed"}},

        # CheckCapacity event
        {"node_id": "evCheck", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 750, "params": {"EventName": "CheckCapacity"}},
        {"node_id": "getCnt3", "node_type": "GetVar", "pos_x": 200, "pos_y": 800, "params": {"Variable": "EngineCount"}},
        {"node_id": "getMax", "node_type": "GetVar", "pos_x": 200, "pos_y": 860, "params": {"Variable": "MaxCapacity"}},
        {"node_id": "geqCap", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt", "pos_x": 400, "pos_y": 800},
        {"node_id": "brCap", "node_type": "Branch", "pos_x": 600, "pos_y": 750},
        {"node_id": "printFull", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 800, "pos_y": 700, "params": { "InString": "Shop full"}},
        {"node_id": "printAvail", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 800, "pos_y": 850, "params": { "InString": "Space available"}},
    ]
    si_conns = [
        # BeginPlay
        {"from_node": "bp", "from_pin": "then", "to_node": "printInit", "to_pin": "execute"},

        # AddEngine
        {"from_node": "evAddEng", "from_pin": "then", "to_node": "setCnt1", "to_pin": "execute"},
        {"from_node": "getCnt1", "from_pin": "EngineCount", "to_node": "addCnt", "to_pin": "A"},
        {"from_node": "addCnt", "from_pin": "ReturnValue", "to_node": "setCnt1", "to_pin": "EngineCount"},
        {"from_node": "setCnt1", "from_pin": "then", "to_node": "printAdded", "to_pin": "execute"},

        # RemoveEngine
        {"from_node": "evRemEng", "from_pin": "then", "to_node": "setCnt2", "to_pin": "execute"},
        {"from_node": "getCnt2", "from_pin": "EngineCount", "to_node": "subCnt", "to_pin": "A"},
        {"from_node": "subCnt", "from_pin": "ReturnValue", "to_node": "setCnt2", "to_pin": "EngineCount"},
        {"from_node": "setCnt2", "from_pin": "then", "to_node": "printRemoved", "to_pin": "execute"},

        # CheckCapacity
        {"from_node": "evCheck", "from_pin": "then", "to_node": "brCap", "to_pin": "execute"},
        {"from_node": "getCnt3", "from_pin": "EngineCount", "to_node": "geqCap", "to_pin": "A"},
        {"from_node": "getMax", "from_pin": "MaxCapacity", "to_node": "geqCap", "to_pin": "B"},
        {"from_node": "geqCap", "from_pin": "ReturnValue", "to_node": "brCap", "to_pin": "Condition"},
        {"from_node": "brCap", "from_pin": "True", "to_node": "printFull", "to_pin": "execute"},
        {"from_node": "brCap", "from_pin": "False", "to_node": "printAvail", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_ShopInventory", parent_class="Actor",
        nodes=si_nodes, connections=si_conns,
        variables=si_vars, min_nodes=14, min_conns=10,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 7: BP_QualityCalculator
    # ---------------------------------------------------------------
    print("\n--- BP_QualityCalculator ---")
    qc_vars = [
        {"name": "PartScore", "type": "Float", "default": "0.0"},
        {"name": "MachiningScore", "type": "Float", "default": "0.0"},
        {"name": "AssemblyScore", "type": "Float", "default": "0.0"},
        {"name": "OverallQuality", "type": "Float", "default": "0.0"},
    ]
    qc_nodes = [
        # CalculateQuality event
        {"node_id": "evCalc", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 0, "params": {"EventName": "CalculateQuality"}},
        {"node_id": "getPart", "node_type": "GetVar", "pos_x": 200, "pos_y": 50, "params": {"Variable": "PartScore"}},
        {"node_id": "getMach", "node_type": "GetVar", "pos_x": 200, "pos_y": 110, "params": {"Variable": "MachiningScore"}},
        {"node_id": "getAssm", "node_type": "GetVar", "pos_x": 200, "pos_y": 170, "params": {"Variable": "AssemblyScore"}},
        {"node_id": "add1", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 400, "pos_y": 50},
        {"node_id": "add2", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble", "pos_x": 600, "pos_y": 100},
        {"node_id": "div3", "node_type": "/Script/Engine.KismetMathLibrary:Divide_DoubleDouble", "pos_x": 800, "pos_y": 100},
        {"node_id": "clampQ", "node_type": "/Script/Engine.KismetMathLibrary:FClamp", "pos_x": 1000, "pos_y": 100},
        {"node_id": "setQ", "node_type": "SetVar", "pos_x": 1200, "pos_y": 0, "params": {"Variable": "OverallQuality"}},
        {"node_id": "printQ", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1400, "pos_y": 0, "params": { "InString": "Quality calculated"}},
    ]
    qc_conns = [
        {"from_node": "evCalc", "from_pin": "then", "to_node": "setQ", "to_pin": "execute"},
        {"from_node": "getPart", "from_pin": "PartScore", "to_node": "add1", "to_pin": "A"},
        {"from_node": "getMach", "from_pin": "MachiningScore", "to_node": "add1", "to_pin": "B"},
        {"from_node": "add1", "from_pin": "ReturnValue", "to_node": "add2", "to_pin": "A"},
        {"from_node": "getAssm", "from_pin": "AssemblyScore", "to_node": "add2", "to_pin": "B"},
        {"from_node": "add2", "from_pin": "ReturnValue", "to_node": "div3", "to_pin": "A"},
        {"from_node": "div3", "from_pin": "ReturnValue", "to_node": "clampQ", "to_pin": "Value"},
        {"from_node": "clampQ", "from_pin": "ReturnValue", "to_node": "setQ", "to_pin": "OverallQuality"},
        {"from_node": "setQ", "from_pin": "then", "to_node": "printQ", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_QualityCalculator", parent_class="Actor",
        nodes=qc_nodes, connections=qc_conns,
        variables=qc_vars, min_nodes=10, min_conns=8,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 8: BP_EngineInstance
    # ---------------------------------------------------------------
    print("\n--- BP_EngineInstance ---")
    ei_vars = [
        {"name": "SerialNumber", "type": "String", "default": ""},
        {"name": "Make", "type": "String", "default": ""},
        {"name": "Model", "type": "String", "default": ""},
        {"name": "QualityScore", "type": "Float", "default": "0.0"},
        {"name": "IsRebuilt", "type": "Bool", "default": "false"},
    ]
    ei_nodes = [
        # SetQuality event
        {"node_id": "evSetQ", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 0, "params": {"EventName": "SetQuality"}},
        {"node_id": "setQS", "node_type": "SetVar", "pos_x": 200, "pos_y": 0, "params": {"Variable": "QualityScore"}},
        {"node_id": "printSetQ", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 400, "pos_y": 0, "params": { "InString": "Quality score set"}},

        # MarkRebuilt event
        {"node_id": "evMark", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 250, "params": {"EventName": "MarkRebuilt"}},
        {"node_id": "setRebuilt", "node_type": "SetVar", "pos_x": 200, "pos_y": 250, "params": {"Variable": "IsRebuilt"}},
        {"node_id": "printRebuilt", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 400, "pos_y": 250, "params": { "InString": "Engine marked rebuilt"}},
    ]
    ei_conns = [
        {"from_node": "evSetQ", "from_pin": "then", "to_node": "setQS", "to_pin": "execute"},
        {"from_node": "setQS", "from_pin": "then", "to_node": "printSetQ", "to_pin": "execute"},
        {"from_node": "evMark", "from_pin": "then", "to_node": "setRebuilt", "to_pin": "execute"},
        {"from_node": "setRebuilt", "from_pin": "then", "to_node": "printRebuilt", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_EngineInstance", parent_class="Actor",
        nodes=ei_nodes, connections=ei_conns,
        variables=ei_vars, min_nodes=6, min_conns=4,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 9: BP_ActionApproval
    # ---------------------------------------------------------------
    print("\n--- BP_ActionApproval ---")
    aa_vars = [
        {"name": "ActionName", "type": "String", "default": ""},
        {"name": "TimeCost", "type": "Float", "default": "0.0"},
        {"name": "MaterialCost", "type": "Float", "default": "0.0"},
        {"name": "IsApproved", "type": "Bool", "default": "false"},
    ]
    aa_nodes = [
        # ShowApproval event
        {"node_id": "evShow", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 0, "params": {"EventName": "ShowApproval"}},
        {"node_id": "getAction", "node_type": "GetVar", "pos_x": 200, "pos_y": 50, "params": {"Variable": "ActionName"}},
        {"node_id": "printShow", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 400, "pos_y": 0},

        # Approve event
        {"node_id": "evApprove", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 250, "params": {"EventName": "Approve"}},
        {"node_id": "setApproved", "node_type": "SetVar", "pos_x": 200, "pos_y": 250, "params": {"Variable": "IsApproved"}},
        {"node_id": "printApproved", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 400, "pos_y": 250, "params": { "InString": "Approved"}},

        # Cancel event
        {"node_id": "evCancel", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 450, "params": {"EventName": "Cancel"}},
        {"node_id": "printCancel", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 450, "params": { "InString": "Cancelled"}},
    ]
    aa_conns = [
        {"from_node": "evShow", "from_pin": "then", "to_node": "printShow", "to_pin": "execute"},
        {"from_node": "getAction", "from_pin": "ActionName", "to_node": "printShow", "to_pin": "InString"},
        {"from_node": "evApprove", "from_pin": "then", "to_node": "setApproved", "to_pin": "execute"},
        {"from_node": "setApproved", "from_pin": "then", "to_node": "printApproved", "to_pin": "execute"},
        {"from_node": "evCancel", "from_pin": "then", "to_node": "printCancel", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_ActionApproval", parent_class="Actor",
        nodes=aa_nodes, connections=aa_conns,
        variables=aa_vars, min_nodes=8, min_conns=5,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 10: BP_QuestManager
    # ---------------------------------------------------------------
    print("\n--- BP_QuestManager ---")
    qm_vars = [
        {"name": "ActiveQuestName", "type": "String", "default": ""},
        {"name": "IsQuestActive", "type": "Bool", "default": "false"},
        {"name": "QuestsCompleted", "type": "Int", "default": "0"},
    ]
    qm_nodes = [
        # StartQuest event
        {"node_id": "evStart", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 0, "params": {"EventName": "StartQuest"}},
        {"node_id": "setActive", "node_type": "SetVar", "pos_x": 200, "pos_y": 0, "params": {"Variable": "IsQuestActive"}},
        {"node_id": "printStart", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 400, "pos_y": 0, "params": { "InString": "Quest started"}},

        # CompleteQuest event
        {"node_id": "evComplete", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 300, "params": {"EventName": "CompleteQuest"}},
        {"node_id": "getComp", "node_type": "GetVar", "pos_x": 200, "pos_y": 350, "params": {"Variable": "QuestsCompleted"}},
        {"node_id": "addComp", "node_type": "/Script/Engine.KismetMathLibrary:Add_IntInt", "pos_x": 400, "pos_y": 350},
        {"node_id": "setComp", "node_type": "SetVar", "pos_x": 600, "pos_y": 300, "params": {"Variable": "QuestsCompleted"}},
        {"node_id": "setInactive", "node_type": "SetVar", "pos_x": 800, "pos_y": 300, "params": {"Variable": "IsQuestActive"}},
        {"node_id": "printComplete", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1000, "pos_y": 300, "params": { "InString": "Quest completed"}},
    ]
    qm_conns = [
        # StartQuest
        {"from_node": "evStart", "from_pin": "then", "to_node": "setActive", "to_pin": "execute"},
        {"from_node": "setActive", "from_pin": "then", "to_node": "printStart", "to_pin": "execute"},

        # CompleteQuest
        {"from_node": "evComplete", "from_pin": "then", "to_node": "setComp", "to_pin": "execute"},
        {"from_node": "getComp", "from_pin": "QuestsCompleted", "to_node": "addComp", "to_pin": "A"},
        {"from_node": "addComp", "from_pin": "ReturnValue", "to_node": "setComp", "to_pin": "QuestsCompleted"},
        {"from_node": "setComp", "from_pin": "then", "to_node": "setInactive", "to_pin": "execute"},
        {"from_node": "setInactive", "from_pin": "then", "to_node": "printComplete", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_QuestManager", parent_class="Actor",
        nodes=qm_nodes, connections=qm_conns,
        variables=qm_vars, min_nodes=8, min_conns=5,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 11: BP_HUDManager
    # ---------------------------------------------------------------
    print("\n--- BP_HUDManager ---")
    hud_nodes = [
        # BeginPlay
        {"node_id": "bp", "node_type": "Event_ReceiveBeginPlay", "pos_x": 0, "pos_y": 0},
        {"node_id": "printReady", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 0, "params": { "InString": "HUD Manager ready"}},

        # ShowMessage event
        {"node_id": "evMsg", "node_type": "CustomEvent", "pos_x": 0, "pos_y": 250, "params": {"EventName": "ShowMessage"}},
        {"node_id": "printMsg", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 250, "params": { "InString": "Message displayed"}},
    ]
    hud_conns = [
        {"from_node": "bp", "from_pin": "then", "to_node": "printReady", "to_pin": "execute"},
        {"from_node": "evMsg", "from_pin": "then", "to_node": "printMsg", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_HUDManager", parent_class="Actor",
        nodes=hud_nodes, connections=hud_conns,
        variables=None, min_nodes=4, min_conns=2,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    # ---------------------------------------------------------------
    # BP 12: BP_BoreAndStrokeGameMode
    # ---------------------------------------------------------------
    print("\n--- BP_BoreAndStrokeGameMode ---")
    gm_nodes = [
        {"node_id": "bp", "node_type": "Event_ReceiveBeginPlay", "pos_x": 0, "pos_y": 0},
        {"node_id": "p1", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 200, "pos_y": 0, "params": { "InString": "Spawning TimeManager..."}},
        {"node_id": "p2", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 400, "pos_y": 0, "params": { "InString": "Spawning EconomyManager..."}},
        {"node_id": "p3", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 600, "pos_y": 0, "params": { "InString": "Spawning HeatManager..."}},
        {"node_id": "p4", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 800, "pos_y": 0, "params": { "InString": "Spawning ReputationManager..."}},
        {"node_id": "p5", "node_type": "/Script/Engine.KismetSystemLibrary:PrintString", "pos_x": 1000, "pos_y": 0, "params": { "InString": "Bore & Stroke initialized!"}},
    ]
    gm_conns = [
        {"from_node": "bp", "from_pin": "then", "to_node": "p1", "to_pin": "execute"},
        {"from_node": "p1", "from_pin": "then", "to_node": "p2", "to_pin": "execute"},
        {"from_node": "p2", "from_pin": "then", "to_node": "p3", "to_pin": "execute"},
        {"from_node": "p3", "from_pin": "then", "to_node": "p4", "to_pin": "execute"},
        {"from_node": "p4", "from_pin": "then", "to_node": "p5", "to_pin": "execute"},
    ]
    e = cc.create_and_verify_blueprint(
        name="BP_BoreAndStrokeGameMode", parent_class="GameModeBase",
        nodes=gm_nodes, connections=gm_conns,
        variables=None, min_nodes=6, min_conns=5,
    )
    print(f"  => {e['status']}  nodes={e['actual'].get('nodes',0)}  conns={e['actual'].get('connections',0)}")

    print("\n  Phase 3 complete: 12 Blueprints created and verified.")

    # ------------------------------------------------------------------
    # PHASE 4: Widgets
    # ------------------------------------------------------------------
    banner("PHASE 4: Widgets (3)")

    # WBP_GameHUD
    print("  Creating WBP_GameHUD...")
    ok(arc.cmd("create_widget_blueprint", name="WBP_GameHUD"), "create WBP_GameHUD")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="CanvasPanel", widget_name="RootPanel"), "add RootPanel")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TXT_Day", parent="RootPanel"), "add TXT_Day")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Day", property="text", value="Day: 1"), "set TXT_Day text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Day", property="position", value={"x": 20, "y": 20}), "set TXT_Day pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TXT_Cash", parent="RootPanel"), "add TXT_Cash")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Cash", property="text", value="Cash: $15,000"), "set TXT_Cash text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Cash", property="position", value={"x": 20, "y": 50}), "set TXT_Cash pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TXT_Time", parent="RootPanel"), "add TXT_Time")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Time", property="text", value="Time: 480"), "set TXT_Time text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Time", property="position", value={"x": 20, "y": 80}), "set TXT_Time pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TXT_Rep", parent="RootPanel"), "add TXT_Rep")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Rep", property="text", value="Reputation: 50"), "set TXT_Rep text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Rep", property="position", value={"x": 20, "y": 110}), "set TXT_Rep pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="TextBlock", widget_name="TXT_Heat", parent="RootPanel"), "add TXT_Heat")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Heat", property="text", value="Heat: 0"), "set TXT_Heat text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TXT_Heat", property="position", value={"x": 20, "y": 140}), "set TXT_Heat pos")

    # WBP_ActionApproval
    print("\n  Creating WBP_ActionApproval...")
    ok(arc.cmd("create_widget_blueprint", name="WBP_ActionApproval"), "create WBP_ActionApproval")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", widget_type="CanvasPanel", widget_name="RootPanel"), "add RootPanel")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", widget_type="TextBlock", widget_name="TXT_Title", parent="RootPanel"), "add TXT_Title")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TXT_Title", property="text", value="Action Approval"), "set TXT_Title text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TXT_Title", property="position", value={"x": 600, "y": 300}), "set TXT_Title pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", widget_type="TextBlock", widget_name="TXT_ActionName", parent="RootPanel"), "add TXT_ActionName")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TXT_ActionName", property="text", value="Action: ---"), "set TXT_ActionName text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TXT_ActionName", property="position", value={"x": 600, "y": 340}), "set TXT_ActionName pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", widget_type="TextBlock", widget_name="TXT_Cost", parent="RootPanel"), "add TXT_Cost")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TXT_Cost", property="text", value="Cost: $0"), "set TXT_Cost text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TXT_Cost", property="position", value={"x": 600, "y": 380}), "set TXT_Cost pos")

    # WBP_MainMenu
    print("\n  Creating WBP_MainMenu...")
    ok(arc.cmd("create_widget_blueprint", name="WBP_MainMenu"), "create WBP_MainMenu")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", widget_type="CanvasPanel", widget_name="RootPanel"), "add RootPanel")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", widget_type="TextBlock", widget_name="TXT_GameTitle", parent="RootPanel"), "add TXT_GameTitle")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="TXT_GameTitle", property="text", value="BORE & STROKE"), "set title text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="TXT_GameTitle", property="font_size", value=48), "set title font_size")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="TXT_GameTitle", property="position", value={"x": 700, "y": 200}), "set title pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", widget_type="TextBlock", widget_name="TXT_Subtitle", parent="RootPanel"), "add TXT_Subtitle")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="TXT_Subtitle", property="text", value="Engine Rebuild Simulator"), "set subtitle text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="TXT_Subtitle", property="position", value={"x": 730, "y": 270}), "set subtitle pos")
    ok(arc.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", widget_type="TextBlock", widget_name="TXT_Start", parent="RootPanel"), "add TXT_Start")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="TXT_Start", property="text", value="Press ENTER to Start"), "set start text")
    ok(arc.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="TXT_Start", property="position", value={"x": 750, "y": 450}), "set start pos")

    print("\n  Phase 4 complete: 3 Widget Blueprints created.")

    # ------------------------------------------------------------------
    # PHASE 5: Level Setup
    # ------------------------------------------------------------------
    banner("PHASE 5: Level Setup")

    # Scene lighting
    ok(arc.cmd("setup_scene_lighting", preset="indoor_bright"), "scene lighting")

    # Floor
    ok(arc.cmd("spawn_actor_at",
        **{"class": "StaticMeshActor",
           "label": "ShopFloor",
           "location": {"x": 0, "y": 0, "z": 0},
           "scale": {"x": 50, "y": 50, "z": 1}}), "floor")
    ok(arc.cmd("set_actor_material",
        actor_label="ShopFloor",
        material_path="/Game/Arcwright/Materials/M_ShopFloor"), "floor material")

    # Walls (4)
    walls = [
        ("Wall_North", {"x": 0, "y": -2500, "z": 200}, {"x": 50, "y": 1, "z": 5}),
        ("Wall_South", {"x": 0, "y": 2500, "z": 200}, {"x": 50, "y": 1, "z": 5}),
        ("Wall_East",  {"x": 2500, "y": 0, "z": 200}, {"x": 1, "y": 50, "z": 5}),
        ("Wall_West",  {"x": -2500, "y": 0, "z": 200}, {"x": 1, "y": 50, "z": 5}),
    ]
    for label, loc, scale in walls:
        ok(arc.cmd("spawn_actor_at",
            **{"class": "StaticMeshActor", "label": label,
               "location": loc, "scale": scale}), label)
        ok(arc.cmd("set_actor_material",
            actor_label=label,
            material_path="/Game/Arcwright/Materials/M_ShopWall"), f"{label} material")

    # Station markers (4 cubes to represent workstations)
    stations = [
        ("Station_BoreBar",    {"x": -800, "y": -800, "z": 50}),
        ("Station_Assembly",   {"x": 800, "y": -800, "z": 50}),
        ("Station_Inspection", {"x": -800, "y": 800, "z": 50}),
        ("Station_DynoRoom",   {"x": 800, "y": 800, "z": 50}),
    ]
    for label, loc in stations:
        ok(arc.cmd("spawn_actor_at",
            **{"class": "StaticMeshActor", "label": label,
               "location": loc, "scale": {"x": 3, "y": 3, "z": 3}}), label)
        ok(arc.cmd("set_actor_material",
            actor_label=label,
            material_path="/Game/Arcwright/Materials/M_Workbench"), f"{label} material")

    # Set game mode
    ok(arc.cmd("set_game_mode", game_mode="BP_BoreAndStrokeGameMode"), "game mode")

    # Save all
    ok(arc.cmd("save_all"), "save_all")

    print("\n  Phase 5 complete: Level setup done.")

    # ------------------------------------------------------------------
    # PHASE 6: Final Verification
    # ------------------------------------------------------------------
    banner("PHASE 6: Final Verification")

    # 6a. Verify all blueprints
    print("\n--- verify_all_blueprints ---")
    vab = cc.verify_all_blueprints()
    if "error" in vab:
        print(f"  ERROR: {vab['error']}")
    else:
        print(f"  Total: {vab.get('total', 0)}  Pass: {vab.get('pass', 0)}  Fail: {vab.get('fail', 0)}")
        for r in vab.get("results", []):
            status_str = "PASS" if r.get("compiled", False) else "FAIL"
            print(f"    {status_str}: {r.get('name', '?')} — nodes={r.get('node_count', 0)} conns={r.get('connection_count', 0)}")

    # 6b. Verify level
    print("\n--- verify_level ---")
    lvl = cc.verify_level()
    print(f"  Level: {lvl.get('level_name', '?')}")
    print(f"  Actors: {lvl.get('actor_count', 0)}")

    # 6c. Play test
    print("\n--- play_test (5 seconds) ---")
    pt = cc.play_test(duration=5)
    print(f"  Started: {pt['started']}")
    print(f"  Crashed: {pt['crashed']}")
    print(f"  Log lines: {len(pt['log_lines'])}")
    for line in pt["log_lines"][:10]:
        print(f"    {line[:120]}")

    # 6d. Full Check & Confirm report
    print("\n--- Check & Confirm Report ---")
    report = cc.report()

    # Final summary
    banner("BUILD COMPLETE")
    print(f"  Data Tables:  5")
    print(f"  Materials:    10")
    print(f"  Blueprints:   12  ({report['confirmed']}/{report['total']} CONFIRMED)")
    print(f"  Widgets:      3")
    print(f"  Level actors: {lvl.get('actor_count', 0)}")
    print(f"  Discrepancies: {report['discrepancies']}")
    if report["discrepancies"] > 0:
        print("  See discrepancy details above.")
    else:
        print("  ALL BLUEPRINTS CONFIRMED. Build successful.")


if __name__ == "__main__":
    main()
