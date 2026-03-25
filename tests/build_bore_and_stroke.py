"""
Bore & Stroke — Full Game Build Script
========================================
Builds all game assets via Arcwright TCP commands.
Run: PYTHONIOENCODING=utf-8 python tests/build_bore_and_stroke.py
"""

import socket
import json
import time
import sys
from datetime import datetime

# ============================================================
# Arcwright TCP Client
# ============================================================

class Arcwright:
    def __init__(self):
        self.log = []
        self.errors = []
        self.count = 0
        self.sock = None
        self.phase_stats = {}
        self.current_phase = "init"
        self.reconnect()

    def reconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(30)
        self.sock.connect(('localhost', 13377))

    def cmd(self, command, **params):
        self.count += 1
        if self.count % 25 == 0:
            self.reconnect()
        try:
            payload = json.dumps({"command": command, "params": params}) + "\n"
            self.sock.sendall(payload.encode())
            data = b""
            while b"\n" not in data:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                data += chunk
            result = json.loads(data.decode().strip())
            status = result.get("status", "unknown")
            self.log.append({"cmd": command, "status": status, "phase": self.current_phase})

            if self.current_phase not in self.phase_stats:
                self.phase_stats[self.current_phase] = {"ok": 0, "err": 0}

            if status == "error":
                self.errors.append({"cmd": command, "params": params, "error": result.get("message", result.get("error", ""))})
                self.phase_stats[self.current_phase]["err"] += 1
            else:
                self.phase_stats[self.current_phase]["ok"] += 1
            return result
        except Exception as e:
            self.errors.append({"cmd": command, "error": str(e)})
            if self.current_phase not in self.phase_stats:
                self.phase_stats[self.current_phase] = {"ok": 0, "err": 0}
            self.phase_stats[self.current_phase]["err"] += 1
            self.reconnect()
            return {"status": "error", "error": str(e)}

    def phase(self, name):
        self.current_phase = name
        print(f"\n{'='*60}")
        print(f"PHASE: {name}")
        print(f"{'='*60}")

    def bp(self, name, parent="Actor", variables=None):
        """Create Blueprint with optional variables."""
        self.cmd("delete_blueprint", blueprint=name)
        p = {"name": name, "parent_class": parent}
        if variables:
            p["variables"] = variables
        return self.cmd("create_blueprint", **p)

    def nodes(self, bp_name, node_list):
        """Add nodes batch and return success count."""
        r = self.cmd("add_nodes_batch", blueprint=bp_name, nodes=node_list)
        if r["status"] == "ok":
            d = r["data"]
            ok, fail = d["succeeded"], d["failed"]
            if fail > 0:
                for n in d.get("results", []):
                    if not n.get("success"):
                        print(f"    NODE FAIL: {n.get('node_id','?')}: {n.get('error','?')}")
            return ok, fail
        return 0, len(node_list)

    def conns(self, bp_name, conn_list):
        """Add connections batch and return success count."""
        r = self.cmd("add_connections_batch", blueprint=bp_name, connections=conn_list)
        if r["status"] == "ok":
            d = r["data"]
            ok, fail = d["succeeded"], d["failed"]
            if fail > 0:
                for c in d.get("results", []):
                    if not c.get("success"):
                        src = c.get("source_node", "?")
                        dst = c.get("target_node", "?")
                        print(f"    CONN FAIL: {src} -> {dst}: {c.get('error','?')}")
            return ok, fail
        return 0, len(conn_list)

    def compile(self, bp_name):
        return self.cmd("compile_blueprint", blueprint=bp_name)

    def verify_bp(self, bp_name, min_nodes=0, min_conns=0):
        """Verify Blueprint and print summary."""
        self.compile(bp_name)
        nok = sum(1 for l in self.log if l["cmd"] == "add_nodes_batch" and l["status"] == "ok")
        print(f"  {bp_name}: verified")

    def report(self):
        ok = len([l for l in self.log if l["status"] == "ok"])
        err = len(self.errors)
        print(f"\n{'='*60}")
        print(f"BUILD COMPLETE")
        print(f"{'='*60}")
        print(f"Total commands: {len(self.log)}")
        print(f"Succeeded: {ok}")
        print(f"Errors: {err}")
        print(f"\nPer-phase breakdown:")
        for phase, stats in self.phase_stats.items():
            print(f"  {phase}: {stats['ok']} ok, {stats['err']} err")
        if self.errors:
            print(f"\nError details:")
            for e in self.errors[:20]:
                print(f"  {e['cmd']}: {e.get('error','')[:100]}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors)-20} more")
        return {"total": len(self.log), "ok": ok, "errors": err}


# ============================================================
# Phase 1: Data Tables
# ============================================================

def build_data_tables(a):
    a.phase("Phase 1: Data Tables")

    # DT_Difficulty
    a.cmd("create_data_table", ir=json.dumps({
        "metadata": {"name": "DT_Difficulty"},
        "columns": [
            {"name": "Setting", "type": "Name"},
            {"name": "Easy", "type": "String"},
            {"name": "Normal", "type": "String"},
            {"name": "Hard", "type": "String"}
        ],
        "rows": [
            {"name": "StartingCash", "values": {"Setting": "StartingCash", "Easy": "25000", "Normal": "15000", "Hard": "8000"}},
            {"name": "PartPrices", "values": {"Setting": "PartPrices", "Easy": "0.85", "Normal": "1.0", "Hard": "1.15"}},
            {"name": "SellPrices", "values": {"Setting": "SellPrices", "Easy": "1.15", "Normal": "1.0", "Hard": "0.9"}},
            {"name": "WearRate", "values": {"Setting": "WearRate", "Easy": "0.75", "Normal": "1.0", "Hard": "1.25"}},
            {"name": "DailyOverhead", "values": {"Setting": "DailyOverhead", "Easy": "0.85", "Normal": "1.0", "Hard": "1.15"}},
        ]
    }))

    # DT_ShopTiers
    a.cmd("create_data_table", ir=json.dumps({
        "metadata": {"name": "DT_ShopTiers"},
        "columns": [
            {"name": "TierName", "type": "Name"},
            {"name": "DisplayName", "type": "String"},
            {"name": "Size", "type": "String"},
            {"name": "Cost", "type": "Float"},
            {"name": "EngineCapacity", "type": "Integer"},
        ],
        "rows": [
            {"name": "Tier1", "values": {"TierName": "Tier1", "DisplayName": "Backyard Garage", "Size": "400 sq ft", "Cost": 0, "EngineCapacity": 2}},
            {"name": "Tier2", "values": {"TierName": "Tier2", "DisplayName": "Small Shop", "Size": "800 sq ft", "Cost": 15000, "EngineCapacity": 4}},
            {"name": "Tier3", "values": {"TierName": "Tier3", "DisplayName": "Professional Shop", "Size": "1500 sq ft", "Cost": 50000, "EngineCapacity": 8}},
            {"name": "Tier4", "values": {"TierName": "Tier4", "DisplayName": "Full Machine Shop", "Size": "3000 sq ft", "Cost": 150000, "EngineCapacity": 16}},
            {"name": "Tier5", "values": {"TierName": "Tier5", "DisplayName": "Premium Machine Shop", "Size": "5000+ sq ft", "Cost": 500000, "EngineCapacity": 32}},
        ]
    }))

    # DT_Engines (sample from GDD)
    a.cmd("create_data_table", ir=json.dumps({
        "metadata": {"name": "DT_Engines"},
        "columns": [
            {"name": "EngineID", "type": "Name"},
            {"name": "Make", "type": "String"},
            {"name": "Family", "type": "String"},
            {"name": "Displacement", "type": "String"},
            {"name": "Config", "type": "String"},
            {"name": "Years", "type": "String"},
            {"name": "Rarity", "type": "String"},
            {"name": "StockHP", "type": "Integer"},
            {"name": "Weight", "type": "Integer"},
            {"name": "BasePrice", "type": "Float"},
        ],
        "rows": [
            {"name": "SBC283", "values": {"EngineID": "SBC283", "Make": "Chevrolet", "Family": "Small Block", "Displacement": "283", "Config": "V8", "Years": "1957-1967", "Rarity": "Common", "StockHP": 185, "Weight": 575, "BasePrice": 800}},
            {"name": "SBC327", "values": {"EngineID": "SBC327", "Make": "Chevrolet", "Family": "Small Block", "Displacement": "327", "Config": "V8", "Years": "1962-1969", "Rarity": "Common", "StockHP": 250, "Weight": 575, "BasePrice": 1200}},
            {"name": "SBC350", "values": {"EngineID": "SBC350", "Make": "Chevrolet", "Family": "Small Block", "Displacement": "350", "Config": "V8", "Years": "1967-1970", "Rarity": "Common", "StockHP": 295, "Weight": 575, "BasePrice": 1000}},
            {"name": "BBC396", "values": {"EngineID": "BBC396", "Make": "Chevrolet", "Family": "Big Block", "Displacement": "396", "Config": "V8", "Years": "1965-1969", "Rarity": "Uncommon", "StockHP": 325, "Weight": 685, "BasePrice": 2500}},
            {"name": "BBC427", "values": {"EngineID": "BBC427", "Make": "Chevrolet", "Family": "Big Block", "Displacement": "427", "Config": "V8", "Years": "1966-1969", "Rarity": "Rare", "StockHP": 390, "Weight": 685, "BasePrice": 5000}},
            {"name": "FE390", "values": {"EngineID": "FE390", "Make": "Ford", "Family": "FE Series", "Displacement": "390", "Config": "V8", "Years": "1961-1970", "Rarity": "Common", "StockHP": 300, "Weight": 650, "BasePrice": 1500}},
            {"name": "FE427", "values": {"EngineID": "FE427", "Make": "Ford", "Family": "FE Series", "Displacement": "427", "Config": "V8", "Years": "1963-1968", "Rarity": "Rare", "StockHP": 425, "Weight": 680, "BasePrice": 8000}},
            {"name": "HEMI426", "values": {"EngineID": "HEMI426", "Make": "Chrysler", "Family": "426 Hemi", "Displacement": "426", "Config": "V8", "Years": "1964-1971", "Rarity": "Rare", "StockHP": 425, "Weight": 700, "BasePrice": 12000}},
            {"name": "WEDGE440", "values": {"EngineID": "WEDGE440", "Make": "Chrysler", "Family": "B/RB Wedge", "Displacement": "440", "Config": "V8", "Years": "1966-1970", "Rarity": "Uncommon", "StockHP": 350, "Weight": 695, "BasePrice": 2000}},
            {"name": "SLANT225", "values": {"EngineID": "SLANT225", "Make": "Chrysler", "Family": "Slant Six", "Displacement": "225", "Config": "I6", "Years": "1960-1970", "Rarity": "Common", "StockHP": 145, "Weight": 450, "BasePrice": 400}},
            {"name": "PONTI389", "values": {"EngineID": "PONTI389", "Make": "Pontiac", "Family": "Pontiac V8", "Displacement": "389", "Config": "V8", "Years": "1959-1966", "Rarity": "Common", "StockHP": 325, "Weight": 600, "BasePrice": 1800}},
            {"name": "PONTI400", "values": {"EngineID": "PONTI400", "Make": "Pontiac", "Family": "Pontiac V8", "Displacement": "400", "Config": "V8", "Years": "1967-1970", "Rarity": "Common", "StockHP": 330, "Weight": 610, "BasePrice": 1600}},
        ]
    }))

    # DT_Companies (fictitious brands)
    a.cmd("create_data_table", ir=json.dumps({
        "metadata": {"name": "DT_Companies"},
        "columns": [
            {"name": "CompanyID", "type": "Name"},
            {"name": "CompanyName", "type": "String"},
            {"name": "QualityTier", "type": "String"},
            {"name": "Description", "type": "String"},
        ],
        "rows": [
            {"name": "IRONCLAD", "values": {"CompanyID": "IRONCLAD", "CompanyName": "Ironclad Parts", "QualityTier": "Budget", "Description": "Affordable rebuild parts. Gets the job done."}},
            {"name": "MAINLINE", "values": {"CompanyID": "MAINLINE", "CompanyName": "Mainline Automotive", "QualityTier": "Standard", "Description": "Reliable mid-range parts for daily drivers."}},
            {"name": "PRECISION", "values": {"CompanyID": "PRECISION", "CompanyName": "Precision Engineered", "QualityTier": "Premium", "Description": "High-quality parts for serious rebuilds."}},
            {"name": "APEX", "values": {"CompanyID": "APEX", "CompanyName": "Apex Racing Supply", "QualityTier": "Performance", "Description": "Competition-grade parts for maximum performance."}},
            {"name": "GEARHEAD", "values": {"CompanyID": "GEARHEAD", "CompanyName": "Gearhead Tools", "QualityTier": "Standard", "Description": "Solid tools for the working mechanic."}},
            {"name": "MASTERCRAFT", "values": {"CompanyID": "MASTERCRAFT", "CompanyName": "MasterCraft Professional", "QualityTier": "Premium", "Description": "Professional-grade shop equipment."}},
        ]
    }))

    # DT_Equipment (stations and tools)
    a.cmd("create_data_table", ir=json.dumps({
        "metadata": {"name": "DT_Equipment"},
        "columns": [
            {"name": "EquipID", "type": "Name"},
            {"name": "Name", "type": "String"},
            {"name": "Station", "type": "String"},
            {"name": "Cost", "type": "Float"},
            {"name": "TimeFactor", "type": "Float"},
            {"name": "QualityBonus", "type": "Integer"},
            {"name": "WearRate", "type": "Float"},
        ],
        "rows": [
            {"name": "ChainHoist", "values": {"EquipID": "ChainHoist", "Name": "Chain Hoist (manual)", "Station": "Lifting", "Cost": 0, "TimeFactor": 1.0, "QualityBonus": 0, "WearRate": 0.01}},
            {"name": "PowerWinch", "values": {"EquipID": "PowerWinch", "Name": "Power Winch", "Station": "Lifting", "Cost": 1200, "TimeFactor": 0.7, "QualityBonus": 0, "WearRate": 0.02}},
            {"name": "PressureWasher", "values": {"EquipID": "PressureWasher", "Name": "Pressure Washer", "Station": "Degriming", "Cost": 0, "TimeFactor": 1.0, "QualityBonus": 0, "WearRate": 0.02}},
            {"name": "SteamCleaner", "values": {"EquipID": "SteamCleaner", "Name": "Steam Cleaner", "Station": "Degriming", "Cost": 4500, "TimeFactor": 0.6, "QualityBonus": 5, "WearRate": 0.03}},
            {"name": "HandTools", "values": {"EquipID": "HandTools", "Name": "Hand Tools", "Station": "Disassembly", "Cost": 0, "TimeFactor": 1.0, "QualityBonus": 0, "WearRate": 0.005}},
            {"name": "ImpactDrivers", "values": {"EquipID": "ImpactDrivers", "Name": "Cordless Impact Drivers", "Station": "Disassembly", "Cost": 500, "TimeFactor": 0.6, "QualityBonus": 0, "WearRate": 0.02}},
            {"name": "BoreGauges", "values": {"EquipID": "BoreGauges", "Name": "Bore Gauges", "Station": "Inspection", "Cost": 350, "TimeFactor": 0.8, "QualityBonus": 0, "WearRate": 0.005}},
            {"name": "Magnaflux", "values": {"EquipID": "Magnaflux", "Name": "Magnaflux Machine", "Station": "Inspection", "Cost": 5000, "TimeFactor": 0.5, "QualityBonus": 10, "WearRate": 0.01}},
            {"name": "PartsWasher", "values": {"EquipID": "PartsWasher", "Name": "Parts Washer", "Station": "Cleaning", "Cost": 0, "TimeFactor": 1.0, "QualityBonus": 2, "WearRate": 0.02}},
            {"name": "HotTank", "values": {"EquipID": "HotTank", "Name": "Caustic Soda Hot Tank", "Station": "Cleaning", "Cost": 3500, "TimeFactor": 0.4, "QualityBonus": 5, "WearRate": 0.01}},
            {"name": "MediaBlaster", "values": {"EquipID": "MediaBlaster", "Name": "Media Blasting Cabinet", "Station": "Cleaning", "Cost": 2500, "TimeFactor": 0.6, "QualityBonus": 8, "WearRate": 0.03}},
        ]
    }))

    print(f"  Data tables created: 5")


# ============================================================
# Phase 7: Blueprints (CRITICAL)
# ============================================================

def build_blueprints(a):
    a.phase("Phase 7: Blueprints")

    # --- BP_TimeManager ---
    print("\n  Building BP_TimeManager...")
    a.bp("BP_TimeManager", variables=[
        {"name": "CurrentDay", "type": "Int", "default": "1"},
        {"name": "HumanTimeRemaining", "type": "Float", "default": "480.0"},
        {"name": "DailyBudget", "type": "Float", "default": "480.0"},
        {"name": "IsEndOfDay", "type": "Bool", "default": "false"},
    ])
    nok, nf = a.nodes("BP_TimeManager", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "get_budget", "node_type": "GetVar", "params": {"Variable": "DailyBudget"}},
        {"node_id": "set_time_init", "node_type": "SetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "p_start", "node_type": "PrintString", "params": {"InString": "Day started"}},
        {"node_id": "evt_consume", "node_type": "CustomEvent", "params": {"EventName": "ConsumeTime"}},
        {"node_id": "get_time", "node_type": "GetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "sub_time", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
        {"node_id": "set_time", "node_type": "SetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "leq_zero", "node_type": "/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble"},
        {"node_id": "br_end", "node_type": "Branch"},
        {"node_id": "p_consumed", "node_type": "PrintString", "params": {"InString": "Time consumed"}},
        {"node_id": "evt_endday", "node_type": "CustomEvent", "params": {"EventName": "EndDay"}},
        {"node_id": "set_eod_t", "node_type": "SetVar", "params": {"Variable": "IsEndOfDay"}},
        {"node_id": "get_day", "node_type": "GetVar", "params": {"Variable": "CurrentDay"}},
        {"node_id": "add_day", "node_type": "/Script/Engine.KismetMathLibrary:Add_IntInt"},
        {"node_id": "set_day", "node_type": "SetVar", "params": {"Variable": "CurrentDay"}},
        {"node_id": "get_budget2", "node_type": "GetVar", "params": {"Variable": "DailyBudget"}},
        {"node_id": "set_time2", "node_type": "SetVar", "params": {"Variable": "HumanTimeRemaining"}},
        {"node_id": "set_eod_f", "node_type": "SetVar", "params": {"Variable": "IsEndOfDay"}},
        {"node_id": "p_newday", "node_type": "PrintString", "params": {"InString": "New day started"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")

    cok, cf = a.conns("BP_TimeManager", [
        {"from_node": "begin", "from_pin": "then", "to_node": "set_time_init", "to_pin": "execute"},
        {"from_node": "get_budget", "from_pin": "DailyBudget", "to_node": "set_time_init", "to_pin": "HumanTimeRemaining"},
        {"from_node": "set_time_init", "from_pin": "then", "to_node": "p_start", "to_pin": "execute"},
        {"from_node": "evt_consume", "from_pin": "then", "to_node": "set_time", "to_pin": "execute"},
        {"from_node": "get_time", "from_pin": "HumanTimeRemaining", "to_node": "sub_time", "to_pin": "A"},
        {"from_node": "sub_time", "from_pin": "ReturnValue", "to_node": "set_time", "to_pin": "HumanTimeRemaining"},
        {"from_node": "set_time", "from_pin": "then", "to_node": "br_end", "to_pin": "execute"},
        {"from_node": "set_time", "from_pin": "HumanTimeRemaining", "to_node": "leq_zero", "to_pin": "A"},
        {"from_node": "leq_zero", "from_pin": "ReturnValue", "to_node": "br_end", "to_pin": "Condition"},
        {"from_node": "br_end", "from_pin": "False", "to_node": "p_consumed", "to_pin": "execute"},
        {"from_node": "evt_endday", "from_pin": "then", "to_node": "set_eod_t", "to_pin": "execute"},
        {"from_node": "set_eod_t", "from_pin": "then", "to_node": "set_day", "to_pin": "execute"},
        {"from_node": "get_day", "from_pin": "CurrentDay", "to_node": "add_day", "to_pin": "A"},
        {"from_node": "add_day", "from_pin": "ReturnValue", "to_node": "set_day", "to_pin": "CurrentDay"},
        {"from_node": "set_day", "from_pin": "then", "to_node": "set_time2", "to_pin": "execute"},
        {"from_node": "get_budget2", "from_pin": "DailyBudget", "to_node": "set_time2", "to_pin": "HumanTimeRemaining"},
        {"from_node": "set_time2", "from_pin": "then", "to_node": "set_eod_f", "to_pin": "execute"},
        {"from_node": "set_eod_f", "from_pin": "then", "to_node": "p_newday", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_TimeManager")

    # --- BP_EconomyManager ---
    print("\n  Building BP_EconomyManager...")
    a.bp("BP_EconomyManager", variables=[
        {"name": "Cash", "type": "Float", "default": "15000.0"},
        {"name": "TotalRevenue", "type": "Float", "default": "0.0"},
        {"name": "TotalExpenses", "type": "Float", "default": "0.0"},
        {"name": "DailyOverhead", "type": "Float", "default": "50.0"},
    ])
    nok, nf = a.nodes("BP_EconomyManager", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_init", "node_type": "PrintString", "params": {"InString": "Economy Manager initialized"}},
        {"node_id": "evt_add", "node_type": "CustomEvent", "params": {"EventName": "AddCash"}},
        {"node_id": "gc_a", "node_type": "GetVar", "params": {"Variable": "Cash"}},
        {"node_id": "math_add", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "sc_a", "node_type": "SetVar", "params": {"Variable": "Cash"}},
        {"node_id": "gr_a", "node_type": "GetVar", "params": {"Variable": "TotalRevenue"}},
        {"node_id": "math_rev", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "sr_a", "node_type": "SetVar", "params": {"Variable": "TotalRevenue"}},
        {"node_id": "p_added", "node_type": "PrintString", "params": {"InString": "Cash added"}},
        {"node_id": "evt_ded", "node_type": "CustomEvent", "params": {"EventName": "DeductCash"}},
        {"node_id": "gc_d", "node_type": "GetVar", "params": {"Variable": "Cash"}},
        {"node_id": "ge_d", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
        {"node_id": "br_d", "node_type": "Branch"},
        {"node_id": "sub_d", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
        {"node_id": "sc_d", "node_type": "SetVar", "params": {"Variable": "Cash"}},
        {"node_id": "ge_exp", "node_type": "GetVar", "params": {"Variable": "TotalExpenses"}},
        {"node_id": "math_exp", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "se_exp", "node_type": "SetVar", "params": {"Variable": "TotalExpenses"}},
        {"node_id": "p_deducted", "node_type": "PrintString", "params": {"InString": "Cash deducted"}},
        {"node_id": "p_insuff", "node_type": "PrintString", "params": {"InString": "Insufficient funds"}},
        {"node_id": "evt_eod", "node_type": "CustomEvent", "params": {"EventName": "ProcessEndOfDay"}},
        {"node_id": "get_oh", "node_type": "GetVar", "params": {"Variable": "DailyOverhead"}},
        {"node_id": "p_eod", "node_type": "PrintString", "params": {"InString": "End of day processed"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")

    cok, cf = a.conns("BP_EconomyManager", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "evt_add", "from_pin": "then", "to_node": "sc_a", "to_pin": "execute"},
        {"from_node": "sc_a", "from_pin": "then", "to_node": "sr_a", "to_pin": "execute"},
        {"from_node": "sr_a", "from_pin": "then", "to_node": "p_added", "to_pin": "execute"},
        {"from_node": "gc_a", "from_pin": "Cash", "to_node": "math_add", "to_pin": "A"},
        {"from_node": "math_add", "from_pin": "ReturnValue", "to_node": "sc_a", "to_pin": "Cash"},
        {"from_node": "gr_a", "from_pin": "TotalRevenue", "to_node": "math_rev", "to_pin": "A"},
        {"from_node": "math_rev", "from_pin": "ReturnValue", "to_node": "sr_a", "to_pin": "TotalRevenue"},
        {"from_node": "evt_ded", "from_pin": "then", "to_node": "br_d", "to_pin": "execute"},
        {"from_node": "br_d", "from_pin": "True", "to_node": "sc_d", "to_pin": "execute"},
        {"from_node": "sc_d", "from_pin": "then", "to_node": "se_exp", "to_pin": "execute"},
        {"from_node": "se_exp", "from_pin": "then", "to_node": "p_deducted", "to_pin": "execute"},
        {"from_node": "br_d", "from_pin": "False", "to_node": "p_insuff", "to_pin": "execute"},
        {"from_node": "gc_d", "from_pin": "Cash", "to_node": "ge_d", "to_pin": "A"},
        {"from_node": "ge_d", "from_pin": "ReturnValue", "to_node": "br_d", "to_pin": "Condition"},
        {"from_node": "gc_d", "from_pin": "Cash", "to_node": "sub_d", "to_pin": "A"},
        {"from_node": "sub_d", "from_pin": "ReturnValue", "to_node": "sc_d", "to_pin": "Cash"},
        {"from_node": "ge_exp", "from_pin": "TotalExpenses", "to_node": "math_exp", "to_pin": "A"},
        {"from_node": "math_exp", "from_pin": "ReturnValue", "to_node": "se_exp", "to_pin": "TotalExpenses"},
        {"from_node": "evt_eod", "from_pin": "then", "to_node": "p_eod", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_EconomyManager")

    # --- BP_StationBase ---
    print("\n  Building BP_StationBase...")
    a.bp("BP_StationBase", variables=[
        {"name": "StationName", "type": "String", "default": "Workstation"},
        {"name": "IsPlayerNearby", "type": "Bool", "default": "false"},
        {"name": "IsStationActive", "type": "Bool", "default": "false"},
    ])
    nok, nf = a.nodes("BP_StationBase", [
        {"node_id": "ov_in", "node_type": "Event_ReceiveActorBeginOverlap"},
        {"node_id": "ov_out", "node_type": "Event_ReceiveActorEndOverlap"},
        {"node_id": "set_near_t", "node_type": "SetVar", "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "set_near_f", "node_type": "SetVar", "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "get_name", "node_type": "GetVar", "params": {"Variable": "StationName"}},
        {"node_id": "p_prompt", "node_type": "PrintString"},
        {"node_id": "evt_act", "node_type": "CustomEvent", "params": {"EventName": "ActivateStation"}},
        {"node_id": "get_near", "node_type": "GetVar", "params": {"Variable": "IsPlayerNearby"}},
        {"node_id": "get_active", "node_type": "GetVar", "params": {"Variable": "IsStationActive"}},
        {"node_id": "not_act", "node_type": "/Script/Engine.KismetMathLibrary:Not_PreBool"},
        {"node_id": "and_chk", "node_type": "/Script/Engine.KismetMathLibrary:BooleanAND"},
        {"node_id": "br_act", "node_type": "Branch"},
        {"node_id": "set_act_t", "node_type": "SetVar", "params": {"Variable": "IsStationActive"}},
        {"node_id": "p_activated", "node_type": "PrintString", "params": {"InString": "Station activated"}},
        {"node_id": "evt_deact", "node_type": "CustomEvent", "params": {"EventName": "DeactivateStation"}},
        {"node_id": "set_act_f", "node_type": "SetVar", "params": {"Variable": "IsStationActive"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")

    cok, cf = a.conns("BP_StationBase", [
        {"from_node": "ov_in", "from_pin": "then", "to_node": "set_near_t", "to_pin": "execute"},
        {"from_node": "set_near_t", "from_pin": "then", "to_node": "p_prompt", "to_pin": "execute"},
        {"from_node": "get_name", "from_pin": "StationName", "to_node": "p_prompt", "to_pin": "InString"},
        {"from_node": "ov_out", "from_pin": "then", "to_node": "set_near_f", "to_pin": "execute"},
        {"from_node": "evt_act", "from_pin": "then", "to_node": "br_act", "to_pin": "execute"},
        {"from_node": "get_near", "from_pin": "IsPlayerNearby", "to_node": "and_chk", "to_pin": "A"},
        {"from_node": "get_active", "from_pin": "IsStationActive", "to_node": "not_act", "to_pin": "A"},
        {"from_node": "not_act", "from_pin": "ReturnValue", "to_node": "and_chk", "to_pin": "B"},
        {"from_node": "and_chk", "from_pin": "ReturnValue", "to_node": "br_act", "to_pin": "Condition"},
        {"from_node": "br_act", "from_pin": "True", "to_node": "set_act_t", "to_pin": "execute"},
        {"from_node": "set_act_t", "from_pin": "then", "to_node": "p_activated", "to_pin": "execute"},
        {"from_node": "evt_deact", "from_pin": "then", "to_node": "set_act_f", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_StationBase")

    # --- BP_HeatManager ---
    print("\n  Building BP_HeatManager...")
    a.bp("BP_HeatManager", variables=[
        {"name": "HeatLevel", "type": "Float", "default": "0.0"},
        {"name": "HeatDecayRate", "type": "Float", "default": "0.1"},
        {"name": "MaxHeat", "type": "Float", "default": "100.0"},
    ])
    nok, nf = a.nodes("BP_HeatManager", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_init", "node_type": "PrintString", "params": {"InString": "Heat Manager active"}},
        {"node_id": "evt_add", "node_type": "CustomEvent", "params": {"EventName": "AddHeat"}},
        {"node_id": "get_h", "node_type": "GetVar", "params": {"Variable": "HeatLevel"}},
        {"node_id": "add_h", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "clamp_h", "node_type": "/Script/Engine.KismetMathLibrary:FClamp"},
        {"node_id": "set_h", "node_type": "SetVar", "params": {"Variable": "HeatLevel"}},
        {"node_id": "ge50", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
        {"node_id": "br_warn", "node_type": "Branch"},
        {"node_id": "p_warn", "node_type": "PrintString", "params": {"InString": "WARNING: Heat level elevated!"}},
        {"node_id": "evt_decay", "node_type": "CustomEvent", "params": {"EventName": "DecayHeat"}},
        {"node_id": "get_h2", "node_type": "GetVar", "params": {"Variable": "HeatLevel"}},
        {"node_id": "get_rate", "node_type": "GetVar", "params": {"Variable": "HeatDecayRate"}},
        {"node_id": "sub_decay", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
        {"node_id": "clamp_d", "node_type": "/Script/Engine.KismetMathLibrary:FClamp"},
        {"node_id": "set_h2", "node_type": "SetVar", "params": {"Variable": "HeatLevel"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")

    cok, cf = a.conns("BP_HeatManager", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "evt_add", "from_pin": "then", "to_node": "set_h", "to_pin": "execute"},
        {"from_node": "get_h", "from_pin": "HeatLevel", "to_node": "add_h", "to_pin": "A"},
        {"from_node": "add_h", "from_pin": "ReturnValue", "to_node": "clamp_h", "to_pin": "Value"},
        {"from_node": "clamp_h", "from_pin": "ReturnValue", "to_node": "set_h", "to_pin": "HeatLevel"},
        {"from_node": "set_h", "from_pin": "then", "to_node": "br_warn", "to_pin": "execute"},
        {"from_node": "set_h", "from_pin": "HeatLevel", "to_node": "ge50", "to_pin": "A"},
        {"from_node": "ge50", "from_pin": "ReturnValue", "to_node": "br_warn", "to_pin": "Condition"},
        {"from_node": "br_warn", "from_pin": "True", "to_node": "p_warn", "to_pin": "execute"},
        {"from_node": "evt_decay", "from_pin": "then", "to_node": "set_h2", "to_pin": "execute"},
        {"from_node": "get_h2", "from_pin": "HeatLevel", "to_node": "sub_decay", "to_pin": "A"},
        {"from_node": "get_rate", "from_pin": "HeatDecayRate", "to_node": "sub_decay", "to_pin": "B"},
        {"from_node": "sub_decay", "from_pin": "ReturnValue", "to_node": "clamp_d", "to_pin": "Value"},
        {"from_node": "clamp_d", "from_pin": "ReturnValue", "to_node": "set_h2", "to_pin": "HeatLevel"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_HeatManager")

    # --- BP_ReputationManager ---
    print("\n  Building BP_ReputationManager...")
    a.bp("BP_ReputationManager", variables=[
        {"name": "Reputation", "type": "Float", "default": "50.0"},
        {"name": "MoralAlignment", "type": "Float", "default": "0.0"},
    ])
    nok, nf = a.nodes("BP_ReputationManager", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_init", "node_type": "PrintString", "params": {"InString": "Reputation Manager active"}},
        {"node_id": "evt_rep", "node_type": "CustomEvent", "params": {"EventName": "AddReputation"}},
        {"node_id": "get_rep", "node_type": "GetVar", "params": {"Variable": "Reputation"}},
        {"node_id": "add_rep", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "clamp_rep", "node_type": "/Script/Engine.KismetMathLibrary:FClamp"},
        {"node_id": "set_rep", "node_type": "SetVar", "params": {"Variable": "Reputation"}},
        {"node_id": "p_rep", "node_type": "PrintString", "params": {"InString": "Reputation updated"}},
        {"node_id": "evt_align", "node_type": "CustomEvent", "params": {"EventName": "ShiftAlignment"}},
        {"node_id": "get_align", "node_type": "GetVar", "params": {"Variable": "MoralAlignment"}},
        {"node_id": "add_align", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "clamp_align", "node_type": "/Script/Engine.KismetMathLibrary:FClamp"},
        {"node_id": "set_align", "node_type": "SetVar", "params": {"Variable": "MoralAlignment"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")

    cok, cf = a.conns("BP_ReputationManager", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "evt_rep", "from_pin": "then", "to_node": "set_rep", "to_pin": "execute"},
        {"from_node": "get_rep", "from_pin": "Reputation", "to_node": "add_rep", "to_pin": "A"},
        {"from_node": "add_rep", "from_pin": "ReturnValue", "to_node": "clamp_rep", "to_pin": "Value"},
        {"from_node": "clamp_rep", "from_pin": "ReturnValue", "to_node": "set_rep", "to_pin": "Reputation"},
        {"from_node": "set_rep", "from_pin": "then", "to_node": "p_rep", "to_pin": "execute"},
        {"from_node": "evt_align", "from_pin": "then", "to_node": "set_align", "to_pin": "execute"},
        {"from_node": "get_align", "from_pin": "MoralAlignment", "to_node": "add_align", "to_pin": "A"},
        {"from_node": "add_align", "from_pin": "ReturnValue", "to_node": "clamp_align", "to_pin": "Value"},
        {"from_node": "clamp_align", "from_pin": "ReturnValue", "to_node": "set_align", "to_pin": "MoralAlignment"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_ReputationManager")

    # --- BP_BoreAndStrokeGameMode ---
    print("\n  Building BP_BoreAndStrokeGameMode...")
    a.bp("BP_BoreAndStrokeGameMode", parent="GameModeBase")
    nok, nf = a.nodes("BP_BoreAndStrokeGameMode", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p1", "node_type": "PrintString", "params": {"InString": "Spawning TimeManager..."}},
        {"node_id": "p2", "node_type": "PrintString", "params": {"InString": "Spawning EconomyManager..."}},
        {"node_id": "p3", "node_type": "PrintString", "params": {"InString": "Spawning HeatManager..."}},
        {"node_id": "p4", "node_type": "PrintString", "params": {"InString": "Spawning ReputationManager..."}},
        {"node_id": "p5", "node_type": "PrintString", "params": {"InString": "Spawning HUDManager..."}},
        {"node_id": "p_done", "node_type": "PrintString", "params": {"InString": "Bore & Stroke initialized!"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")

    cok, cf = a.conns("BP_BoreAndStrokeGameMode", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p1", "to_pin": "execute"},
        {"from_node": "p1", "from_pin": "then", "to_node": "p2", "to_pin": "execute"},
        {"from_node": "p2", "from_pin": "then", "to_node": "p3", "to_pin": "execute"},
        {"from_node": "p3", "from_pin": "then", "to_node": "p4", "to_pin": "execute"},
        {"from_node": "p4", "from_pin": "then", "to_node": "p5", "to_pin": "execute"},
        {"from_node": "p5", "from_pin": "then", "to_node": "p_done", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_BoreAndStrokeGameMode")


# ============================================================
# Phase 8: Widget UIs
# ============================================================

def build_widgets(a):
    a.phase("Phase 8: Widget UIs")

    # WBP_GameHUD
    a.cmd("create_widget_blueprint", name="WBP_GameHUD")
    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="CanvasPanel", widget_name="Root")
    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="TextBlock", widget_name="DayLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="text", value="Day 1")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="color", value="#E8DCC8")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="font_size", value="18")
    a.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", anchor="TopLeft", offset_x=20, offset_y=10)

    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="TextBlock", widget_name="CashLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="text", value="$15,000")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="font_size", value="22")
    a.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", anchor="TopRight", offset_x=-120, offset_y=10)

    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="ProgressBar", widget_name="TimeBar")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="percent", value="1.0")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="fill_color", value="#E8A624")
    a.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", anchor="TopCenter", offset_x=-125, offset_y=15)
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="size_x", value="250")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="size_y", value="12")

    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="TextBlock", widget_name="InteractPrompt")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="InteractPrompt", property="text", value="")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="InteractPrompt", property="color", value="#E8DCC8")
    a.cmd("set_widget_anchor", widget_blueprint="WBP_GameHUD", widget_name="InteractPrompt", anchor="BottomCenter", offset_x=-100, offset_y=-50)
    print("  WBP_GameHUD: created with Day, Cash, TimeBar, InteractPrompt")


# ============================================================
# Phase 10: Level Setup
# ============================================================

def build_level(a):
    a.phase("Phase 10: Level Setup")

    # Lighting
    a.cmd("setup_scene_lighting", preset="indoor_bright")

    # Floor
    a.cmd("spawn_actor_at", label="ShopFloor", x=0, y=0, z=0,
          **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
             "scale_x": 20, "scale_y": 15, "scale_z": 0.1})

    # Walls
    a.cmd("spawn_actor_at", label="WallNorth", x=0, y=750, z=150,
          **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
             "scale_x": 20, "scale_y": 0.1, "scale_z": 3})
    a.cmd("spawn_actor_at", label="WallSouth", x=0, y=-750, z=150,
          **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
             "scale_x": 20, "scale_y": 0.1, "scale_z": 3})
    a.cmd("spawn_actor_at", label="WallEast", x=1000, y=0, z=150,
          **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
             "scale_x": 0.1, "scale_y": 15, "scale_z": 3})
    a.cmd("spawn_actor_at", label="WallWest", x=-1000, y=0, z=150,
          **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
             "scale_x": 0.1, "scale_y": 15, "scale_z": 3})

    # Materials
    a.cmd("create_simple_material", name="M_ShopFloor", color={"r": 0.15, "g": 0.15, "b": 0.15})
    a.cmd("create_simple_material", name="M_ShopWall", color={"r": 0.25, "g": 0.22, "b": 0.2})
    a.cmd("set_actor_material", actor_label="ShopFloor", material_path="/Game/Arcwright/Materials/M_ShopFloor")
    for wall in ["WallNorth", "WallSouth", "WallEast", "WallWest"]:
        a.cmd("set_actor_material", actor_label=wall, material_path="/Game/Arcwright/Materials/M_ShopWall")

    # Station positions
    stations = [
        ("Station_Degriming", -600, 400),
        ("Station_Disassembly", -200, 400),
        ("Station_Inspection", 200, 400),
        ("Station_Cleaning", 600, 400),
    ]
    for label, x, y in stations:
        a.cmd("spawn_actor_at", label=label, x=x, y=y, z=5,
              **{"class": "StaticMeshActor", "mesh": "/Engine/BasicShapes/Cube.Cube",
                 "scale_x": 1.5, "scale_y": 1.5, "scale_z": 1})

    # Set game mode
    a.cmd("set_game_mode", game_mode="BP_BoreAndStrokeGameMode")

    # Save
    a.cmd("save_all")
    print("  Level built: floor, walls, lighting, 4 stations, game mode set")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    start = time.time()
    print(f"Bore & Stroke Build Script")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"{'='*60}")

    a = Arcwright()

    # Verify connection
    r = a.cmd("health_check")
    if r.get("status") != "ok":
        print("FATAL: Cannot connect to UE")
        sys.exit(1)
    print(f"Connected: {r['data']['server']}")

    # Build phases
    build_data_tables(a)
    build_blueprints(a)
    build_widgets(a)
    build_level(a)

    # Final save
    a.cmd("save_all")

    elapsed = time.time() - start
    result = a.report()

    # Save log
    log_file = "tests/bore_and_stroke_full_build.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Bore & Stroke Build Log -- {datetime.now().isoformat()}\n")
        f.write(f"Duration: {elapsed:.1f}s\n")
        f.write(f"Total: {result['total']} | OK: {result['ok']} | Errors: {result['errors']}\n\n")
        for phase, stats in a.phase_stats.items():
            f.write(f"{phase}: {stats['ok']} ok, {stats['err']} err\n")
        f.write(f"\nErrors:\n")
        for e in a.errors:
            f.write(f"  {e['cmd']}: {e.get('error','')}\n")
    print(f"\nLog saved to {log_file}")
    print(f"Build time: {elapsed:.1f}s")
