"""
Bore & Stroke — Full Game Build Script v2
==========================================
Builds ALL game assets via Arcwright TCP commands (localhost:13377).
10 phases: DataTables, Tags, Materials, [4-6 skip], Blueprints, Widgets, [9 skip], Level.

Run: PYTHONIOENCODING=utf-8 python tests/build_bore_and_stroke_v2.py
"""

import socket
import json
import time
import sys
import os
from datetime import datetime


# ============================================================
# Arcwright TCP Client
# ============================================================

class Arcwright:
    def __init__(self):
        self.log, self.errors, self.count = [], [], 0
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
            self.sock.sendall((json.dumps({"command": command, "params": params}) + "\n").encode())
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

    def dt(self, table_name, struct_name, columns, rows):
        ir = {"metadata": {"table_name": table_name, "struct_name": struct_name}, "columns": columns, "rows": rows}
        return self.cmd("create_data_table", ir_json=json.dumps(ir))

    def bp(self, name, parent="Actor", variables=None):
        self.cmd("delete_blueprint", name=name)
        p = {"name": name, "parent_class": parent}
        if variables:
            p["variables"] = variables
        return self.cmd("create_blueprint", **p)

    def nodes(self, bp_name, node_list):
        r = self.cmd("add_nodes_batch", blueprint=bp_name, nodes=node_list)
        if r.get("status") == "ok":
            d = r["data"]
            if d["failed"] > 0:
                for n in d.get("results", []):
                    if not n.get("success"):
                        print(f"    NODE FAIL: {n.get('node_id','?')}: {n.get('error','?')}")
            return d["succeeded"], d["failed"]
        return 0, len(node_list)

    def conns(self, bp_name, conn_list):
        r = self.cmd("add_connections_batch", blueprint=bp_name, connections=conn_list)
        if r.get("status") == "ok":
            d = r["data"]
            if d["failed"] > 0:
                for c in d.get("results", []):
                    if not c.get("success"):
                        print(f"    CONN FAIL: {c.get('source_node','?')} -> {c.get('target_node','?')}: {c.get('error','?')}")
            return d["succeeded"], d["failed"]
        return 0, len(conn_list)

    def compile(self, bp_name):
        return self.cmd("compile_blueprint", name=bp_name)

    def report(self):
        ok = len([l for l in self.log if l["status"] == "ok"])
        err = len(self.errors)
        print(f"\n{'='*60}")
        print(f"BUILD COMPLETE")
        print(f"{'='*60}")
        print(f"Total: {len(self.log)} | OK: {ok} | Errors: {err}")
        for ph, st in self.phase_stats.items():
            print(f"  {ph}: {st['ok']} ok, {st['err']} err")
        if self.errors:
            print(f"\nErrors:")
            for e in self.errors[:30]:
                print(f"  {e['cmd']}: {e.get('error','')[:100]}")
        return {"total": len(self.log), "ok": ok, "errors": err}


# ============================================================
# PHASE 1: DATA TABLES (10 tables)
# ============================================================

def build_data_tables(a):
    a.phase("Phase 1: Data Tables")

    # 1. DT_Difficulty
    print("  Creating DT_Difficulty...")
    a.dt("DT_Difficulty", "DifficultyStruct",
        columns=[
            {"name": "Setting", "type": "Name"},
            {"name": "Easy", "type": "String"},
            {"name": "Normal", "type": "String"},
            {"name": "Hard", "type": "String"},
        ],
        rows=[
            {"name": "StartingCash", "values": {"Setting": "StartingCash", "Easy": "25000", "Normal": "15000", "Hard": "8000"}},
            {"name": "PartPrices", "values": {"Setting": "PartPrices", "Easy": "0.85", "Normal": "1.0", "Hard": "1.15"}},
            {"name": "SellPrices", "values": {"Setting": "SellPrices", "Easy": "1.15", "Normal": "1.0", "Hard": "0.9"}},
            {"name": "WearRate", "values": {"Setting": "WearRate", "Easy": "0.75", "Normal": "1.0", "Hard": "1.25"}},
            {"name": "DailyOverhead", "values": {"Setting": "DailyOverhead", "Easy": "0.85", "Normal": "1.0", "Hard": "1.15"}},
        ])

    # 2. DT_ShopTiers
    print("  Creating DT_ShopTiers...")
    a.dt("DT_ShopTiers", "ShopTierStruct",
        columns=[
            {"name": "TierName", "type": "Name"},
            {"name": "DisplayName", "type": "String"},
            {"name": "Size", "type": "String"},
            {"name": "Cost", "type": "Float"},
            {"name": "EngineCapacity", "type": "Int"},
        ],
        rows=[
            {"name": "Tier1", "values": {"TierName": "Tier1", "DisplayName": "Backyard Garage", "Size": "400 sq ft", "Cost": "0", "EngineCapacity": "2"}},
            {"name": "Tier2", "values": {"TierName": "Tier2", "DisplayName": "Small Shop", "Size": "800 sq ft", "Cost": "15000", "EngineCapacity": "4"}},
            {"name": "Tier3", "values": {"TierName": "Tier3", "DisplayName": "Professional Shop", "Size": "1500 sq ft", "Cost": "50000", "EngineCapacity": "8"}},
            {"name": "Tier4", "values": {"TierName": "Tier4", "DisplayName": "Full Machine Shop", "Size": "3000 sq ft", "Cost": "150000", "EngineCapacity": "16"}},
            {"name": "Tier5", "values": {"TierName": "Tier5", "DisplayName": "Premium Machine Shop", "Size": "5000+ sq ft", "Cost": "500000", "EngineCapacity": "32"}},
        ])

    # 3. DT_Engines (12 rows)
    print("  Creating DT_Engines...")
    a.dt("DT_Engines", "EngineStruct",
        columns=[
            {"name": "EngineID", "type": "Name"},
            {"name": "Make", "type": "String"},
            {"name": "Family", "type": "String"},
            {"name": "Displacement", "type": "String"},
            {"name": "Config", "type": "String"},
            {"name": "Years", "type": "String"},
            {"name": "Rarity", "type": "String"},
            {"name": "StockHP", "type": "Int"},
            {"name": "Weight", "type": "Int"},
            {"name": "BasePrice", "type": "Float"},
        ],
        rows=[
            {"name": "SBC283", "values": {"EngineID": "SBC283", "Make": "Chevrolet", "Family": "Small Block", "Displacement": "283", "Config": "V8", "Years": "1957-1967", "Rarity": "Common", "StockHP": "185", "Weight": "575", "BasePrice": "800"}},
            {"name": "SBC327", "values": {"EngineID": "SBC327", "Make": "Chevrolet", "Family": "Small Block", "Displacement": "327", "Config": "V8", "Years": "1962-1969", "Rarity": "Common", "StockHP": "250", "Weight": "575", "BasePrice": "1200"}},
            {"name": "SBC350", "values": {"EngineID": "SBC350", "Make": "Chevrolet", "Family": "Small Block", "Displacement": "350", "Config": "V8", "Years": "1967-1970", "Rarity": "Common", "StockHP": "295", "Weight": "575", "BasePrice": "1000"}},
            {"name": "BBC396", "values": {"EngineID": "BBC396", "Make": "Chevrolet", "Family": "Big Block", "Displacement": "396", "Config": "V8", "Years": "1965-1969", "Rarity": "Uncommon", "StockHP": "325", "Weight": "685", "BasePrice": "2500"}},
            {"name": "BBC427", "values": {"EngineID": "BBC427", "Make": "Chevrolet", "Family": "Big Block", "Displacement": "427", "Config": "V8", "Years": "1966-1969", "Rarity": "Rare", "StockHP": "390", "Weight": "685", "BasePrice": "5000"}},
            {"name": "FE390", "values": {"EngineID": "FE390", "Make": "Ford", "Family": "FE Series", "Displacement": "390", "Config": "V8", "Years": "1961-1970", "Rarity": "Common", "StockHP": "300", "Weight": "650", "BasePrice": "1500"}},
            {"name": "FE427", "values": {"EngineID": "FE427", "Make": "Ford", "Family": "FE Series", "Displacement": "427", "Config": "V8", "Years": "1963-1968", "Rarity": "Rare", "StockHP": "425", "Weight": "680", "BasePrice": "8000"}},
            {"name": "HEMI426", "values": {"EngineID": "HEMI426", "Make": "Chrysler", "Family": "426 Hemi", "Displacement": "426", "Config": "V8", "Years": "1964-1971", "Rarity": "Rare", "StockHP": "425", "Weight": "700", "BasePrice": "12000"}},
            {"name": "WEDGE440", "values": {"EngineID": "WEDGE440", "Make": "Chrysler", "Family": "B/RB Wedge", "Displacement": "440", "Config": "V8", "Years": "1966-1970", "Rarity": "Uncommon", "StockHP": "350", "Weight": "695", "BasePrice": "2000"}},
            {"name": "SLANT225", "values": {"EngineID": "SLANT225", "Make": "Chrysler", "Family": "Slant Six", "Displacement": "225", "Config": "I6", "Years": "1960-1970", "Rarity": "Common", "StockHP": "145", "Weight": "450", "BasePrice": "400"}},
            {"name": "PONTI389", "values": {"EngineID": "PONTI389", "Make": "Pontiac", "Family": "Pontiac V8", "Displacement": "389", "Config": "V8", "Years": "1959-1966", "Rarity": "Common", "StockHP": "325", "Weight": "600", "BasePrice": "1800"}},
            {"name": "PONTI400", "values": {"EngineID": "PONTI400", "Make": "Pontiac", "Family": "Pontiac V8", "Displacement": "400", "Config": "V8", "Years": "1967-1970", "Rarity": "Common", "StockHP": "330", "Weight": "610", "BasePrice": "1600"}},
        ])

    # 4. DT_Companies
    print("  Creating DT_Companies...")
    a.dt("DT_Companies", "CompanyStruct",
        columns=[
            {"name": "CompanyID", "type": "Name"},
            {"name": "CompanyName", "type": "String"},
            {"name": "QualityTier", "type": "String"},
            {"name": "Description", "type": "String"},
        ],
        rows=[
            {"name": "IRONCLAD", "values": {"CompanyID": "IRONCLAD", "CompanyName": "Ironclad Parts", "QualityTier": "Budget", "Description": "Affordable rebuild parts. Gets the job done."}},
            {"name": "MAINLINE", "values": {"CompanyID": "MAINLINE", "CompanyName": "Mainline Automotive", "QualityTier": "Standard", "Description": "Reliable mid-range parts for daily drivers."}},
            {"name": "PRECISION", "values": {"CompanyID": "PRECISION", "CompanyName": "Precision Engineered", "QualityTier": "Premium", "Description": "High-quality parts for serious rebuilds."}},
            {"name": "APEX", "values": {"CompanyID": "APEX", "CompanyName": "Apex Racing Supply", "QualityTier": "Performance", "Description": "Competition-grade parts for maximum performance."}},
            {"name": "GEARHEAD", "values": {"CompanyID": "GEARHEAD", "CompanyName": "Gearhead Tools", "QualityTier": "Standard", "Description": "Solid tools for the working mechanic."}},
            {"name": "MASTERCRAFT", "values": {"CompanyID": "MASTERCRAFT", "CompanyName": "MasterCraft Professional", "QualityTier": "Premium", "Description": "Professional-grade shop equipment."}},
        ])

    # 5. DT_Equipment
    print("  Creating DT_Equipment...")
    a.dt("DT_Equipment", "EquipmentStruct",
        columns=[
            {"name": "EquipID", "type": "Name"},
            {"name": "EquipName", "type": "String"},
            {"name": "Station", "type": "String"},
            {"name": "Cost", "type": "Float"},
            {"name": "TimeFactor", "type": "Float"},
            {"name": "QualityBonus", "type": "Int"},
            {"name": "WearRate", "type": "Float"},
        ],
        rows=[
            {"name": "ChainHoist", "values": {"EquipID": "ChainHoist", "EquipName": "Chain Hoist (manual)", "Station": "Lifting", "Cost": "0", "TimeFactor": "1.0", "QualityBonus": "0", "WearRate": "0.01"}},
            {"name": "PowerWinch", "values": {"EquipID": "PowerWinch", "EquipName": "Power Winch", "Station": "Lifting", "Cost": "1200", "TimeFactor": "0.7", "QualityBonus": "0", "WearRate": "0.02"}},
            {"name": "PressureWasher", "values": {"EquipID": "PressureWasher", "EquipName": "Pressure Washer", "Station": "Degriming", "Cost": "0", "TimeFactor": "1.0", "QualityBonus": "0", "WearRate": "0.02"}},
            {"name": "SteamCleaner", "values": {"EquipID": "SteamCleaner", "EquipName": "Steam Cleaner", "Station": "Degriming", "Cost": "4500", "TimeFactor": "0.6", "QualityBonus": "5", "WearRate": "0.03"}},
            {"name": "HandTools", "values": {"EquipID": "HandTools", "EquipName": "Hand Tools", "Station": "Disassembly", "Cost": "0", "TimeFactor": "1.0", "QualityBonus": "0", "WearRate": "0.005"}},
            {"name": "ImpactDrivers", "values": {"EquipID": "ImpactDrivers", "EquipName": "Cordless Impact Drivers", "Station": "Disassembly", "Cost": "500", "TimeFactor": "0.6", "QualityBonus": "0", "WearRate": "0.02"}},
            {"name": "BoreGauges", "values": {"EquipID": "BoreGauges", "EquipName": "Bore Gauges", "Station": "Inspection", "Cost": "350", "TimeFactor": "0.8", "QualityBonus": "0", "WearRate": "0.005"}},
            {"name": "Magnaflux", "values": {"EquipID": "Magnaflux", "EquipName": "Magnaflux Machine", "Station": "Inspection", "Cost": "5000", "TimeFactor": "0.5", "QualityBonus": "10", "WearRate": "0.01"}},
            {"name": "PartsWasher", "values": {"EquipID": "PartsWasher", "EquipName": "Parts Washer", "Station": "Cleaning", "Cost": "0", "TimeFactor": "1.0", "QualityBonus": "2", "WearRate": "0.02"}},
            {"name": "HotTank", "values": {"EquipID": "HotTank", "EquipName": "Caustic Soda Hot Tank", "Station": "Cleaning", "Cost": "3500", "TimeFactor": "0.4", "QualityBonus": "5", "WearRate": "0.01"}},
            {"name": "MediaBlaster", "values": {"EquipID": "MediaBlaster", "EquipName": "Media Blasting Cabinet", "Station": "Cleaning", "Cost": "2500", "TimeFactor": "0.6", "QualityBonus": "8", "WearRate": "0.03"}},
        ])

    # 6. DT_PartsPricing
    print("  Creating DT_PartsPricing...")
    a.dt("DT_PartsPricing", "PartsPricingStruct",
        columns=[
            {"name": "PartName", "type": "Name"},
            {"name": "Budget", "type": "Float"},
            {"name": "Standard", "type": "Float"},
            {"name": "Premium", "type": "Float"},
            {"name": "Performance", "type": "Float"},
        ],
        rows=[
            {"name": "HeadGasketSet", "values": {"PartName": "HeadGasketSet", "Budget": "45", "Standard": "85", "Premium": "150", "Performance": "275"}},
            {"name": "PistonRings", "values": {"PartName": "PistonRings", "Budget": "60", "Standard": "120", "Premium": "220", "Performance": "400"}},
            {"name": "MainBearings", "values": {"PartName": "MainBearings", "Budget": "35", "Standard": "75", "Premium": "140", "Performance": "250"}},
            {"name": "Camshaft", "values": {"PartName": "Camshaft", "Budget": "80", "Standard": "175", "Premium": "350", "Performance": "650"}},
            {"name": "RebuildKit", "values": {"PartName": "RebuildKit", "Budget": "200", "Standard": "450", "Premium": "800", "Performance": "1500"}},
            {"name": "OilPump", "values": {"PartName": "OilPump", "Budget": "30", "Standard": "65", "Premium": "120", "Performance": "200"}},
            {"name": "TimingChain", "values": {"PartName": "TimingChain", "Budget": "25", "Standard": "55", "Premium": "100", "Performance": "180"}},
        ])

    # 7. DT_Consumables
    print("  Creating DT_Consumables...")
    a.dt("DT_Consumables", "ConsumableStruct",
        columns=[
            {"name": "ItemName", "type": "Name"},
            {"name": "Cost", "type": "Float"},
            {"name": "UnitsPerUse", "type": "Int"},
        ],
        rows=[
            {"name": "Degreaser", "values": {"ItemName": "Degreaser", "Cost": "12", "UnitsPerUse": "3"}},
            {"name": "EngineOil", "values": {"ItemName": "EngineOil", "Cost": "8", "UnitsPerUse": "5"}},
            {"name": "ShopRags", "values": {"ItemName": "ShopRags", "Cost": "5", "UnitsPerUse": "10"}},
            {"name": "BlastMedia", "values": {"ItemName": "BlastMedia", "Cost": "20", "UnitsPerUse": "2"}},
            {"name": "CratingMaterials", "values": {"ItemName": "CratingMaterials", "Cost": "35", "UnitsPerUse": "1"}},
            {"name": "Paint", "values": {"ItemName": "Paint", "Cost": "25", "UnitsPerUse": "2"}},
        ])

    # 8. DT_Actions
    print("  Creating DT_Actions...")
    a.dt("DT_Actions", "ActionStruct",
        columns=[
            {"name": "ActionName", "type": "Name"},
            {"name": "HumanTime", "type": "Float"},
            {"name": "MachineTime", "type": "Float"},
            {"name": "MaterialCost", "type": "Float"},
            {"name": "QualityContribution", "type": "Float"},
        ],
        rows=[
            {"name": "Degrease", "values": {"ActionName": "Degrease", "HumanTime": "30", "MachineTime": "60", "MaterialCost": "12", "QualityContribution": "0.05"}},
            {"name": "Disassemble", "values": {"ActionName": "Disassemble", "HumanTime": "120", "MachineTime": "0", "MaterialCost": "0", "QualityContribution": "0.1"}},
            {"name": "InspectBlock", "values": {"ActionName": "InspectBlock", "HumanTime": "60", "MachineTime": "30", "MaterialCost": "0", "QualityContribution": "0.15"}},
            {"name": "CleanParts", "values": {"ActionName": "CleanParts", "HumanTime": "45", "MachineTime": "90", "MaterialCost": "8", "QualityContribution": "0.1"}},
            {"name": "BoreCylinder", "values": {"ActionName": "BoreCylinder", "HumanTime": "15", "MachineTime": "45", "MaterialCost": "5", "QualityContribution": "0.2"}},
            {"name": "HoneCylinder", "values": {"ActionName": "HoneCylinder", "HumanTime": "20", "MachineTime": "30", "MaterialCost": "3", "QualityContribution": "0.15"}},
            {"name": "AssembleEngine", "values": {"ActionName": "AssembleEngine", "HumanTime": "180", "MachineTime": "0", "MaterialCost": "15", "QualityContribution": "0.2"}},
            {"name": "PaintEngine", "values": {"ActionName": "PaintEngine", "HumanTime": "30", "MachineTime": "60", "MaterialCost": "25", "QualityContribution": "0.05"}},
        ])

    # 9. DT_Customers
    print("  Creating DT_Customers...")
    a.dt("DT_Customers", "CustomerStruct",
        columns=[
            {"name": "CustomerType", "type": "Name"},
            {"name": "BudgetMin", "type": "Float"},
            {"name": "BudgetMax", "type": "Float"},
            {"name": "QualityMin", "type": "Float"},
            {"name": "Patience", "type": "Float"},
        ],
        rows=[
            {"name": "BudgetBuyer", "values": {"CustomerType": "BudgetBuyer", "BudgetMin": "500", "BudgetMax": "1500", "QualityMin": "30", "Patience": "14"}},
            {"name": "Enthusiast", "values": {"CustomerType": "Enthusiast", "BudgetMin": "1500", "BudgetMax": "4000", "QualityMin": "60", "Patience": "21"}},
            {"name": "Restorer", "values": {"CustomerType": "Restorer", "BudgetMin": "3000", "BudgetMax": "8000", "QualityMin": "80", "Patience": "30"}},
            {"name": "RacerPro", "values": {"CustomerType": "RacerPro", "BudgetMin": "5000", "BudgetMax": "15000", "QualityMin": "90", "Patience": "10"}},
            {"name": "ShadyDealer", "values": {"CustomerType": "ShadyDealer", "BudgetMin": "200", "BudgetMax": "800", "QualityMin": "10", "Patience": "3"}},
        ])

    # 10. DT_Tolerances
    print("  Creating DT_Tolerances...")
    a.dt("DT_Tolerances", "ToleranceStruct",
        columns=[
            {"name": "EngineFamily", "type": "Name"},
            {"name": "MaxTaper", "type": "Float"},
            {"name": "MaxOutOfRound", "type": "Float"},
            {"name": "CondemnLimit", "type": "Float"},
            {"name": "OverboreIncrements", "type": "String"},
        ],
        rows=[
            {"name": "SBC", "values": {"EngineFamily": "SBC", "MaxTaper": "0.003", "MaxOutOfRound": "0.002", "CondemnLimit": "0.060", "OverboreIncrements": "0.010,0.020,0.030,0.040,0.060"}},
            {"name": "FE", "values": {"EngineFamily": "FE", "MaxTaper": "0.004", "MaxOutOfRound": "0.003", "CondemnLimit": "0.060", "OverboreIncrements": "0.010,0.020,0.030,0.040,0.060"}},
            {"name": "Slant6", "values": {"EngineFamily": "Slant6", "MaxTaper": "0.003", "MaxOutOfRound": "0.002", "CondemnLimit": "0.040", "OverboreIncrements": "0.010,0.020,0.030,0.040"}},
        ])

    print("  Data tables created: 10")


# ============================================================
# PHASE 2: GAMEPLAY TAGS
# ============================================================

def build_tags(a):
    a.phase("Phase 2: Gameplay Tags")

    # Quality tiers
    print("  Creating Quality tags...")
    a.cmd("create_tag_hierarchy", tags=[
        "Quality",
        "Quality.Budget",
        "Quality.Standard",
        "Quality.Premium",
        "Quality.Performance",
    ])

    # Engine manufacturers
    print("  Creating Engine tags...")
    a.cmd("create_tag_hierarchy", tags=[
        "Engine",
        "Engine.Chevy",
        "Engine.Ford",
        "Engine.Chrysler",
        "Engine.Pontiac",
    ])

    # Stations
    print("  Creating Station tags...")
    a.cmd("create_tag_hierarchy", tags=[
        "Station",
        "Station.Degriming",
        "Station.Disassembly",
        "Station.Inspection",
        "Station.Cleaning",
    ])

    # Heat levels
    print("  Creating Heat tags...")
    a.cmd("create_tag_hierarchy", tags=[
        "Heat",
        "Heat.None",
        "Heat.Low",
        "Heat.Medium",
        "Heat.High",
        "Heat.Critical",
    ])

    # Customer types
    print("  Creating Customer tags...")
    a.cmd("create_tag_hierarchy", tags=[
        "Customer",
        "Customer.Budget",
        "Customer.Enthusiast",
        "Customer.Restorer",
        "Customer.Racer",
    ])

    print("  Gameplay tag hierarchies created: 5")


# ============================================================
# PHASE 3: MATERIALS (10 materials)
# ============================================================

def build_materials(a):
    a.phase("Phase 3: Materials")

    materials = [
        ("M_ShopFloor",       {"r": 0.12, "g": 0.12, "b": 0.12}),   # dark grey
        ("M_ShopWall",        {"r": 0.28, "g": 0.24, "b": 0.20}),   # warm grey-brown
        ("M_Workbench",       {"r": 0.18, "g": 0.10, "b": 0.06}),   # dark wood brown
        ("M_EngineBlock",     {"r": 0.25, "g": 0.25, "b": 0.27}),   # cast iron grey
        ("M_Chrome",          {"r": 0.85, "g": 0.85, "b": 0.88}),   # bright silver
        ("M_Rust",            {"r": 0.55, "g": 0.28, "b": 0.10}),   # orange-brown
        ("M_OilStain",        {"r": 0.08, "g": 0.06, "b": 0.04}),   # dark brown-black
        ("M_CarbonDeposit",   {"r": 0.10, "g": 0.10, "b": 0.10}),   # dark grey-black
        ("M_CylinderWall",    {"r": 0.45, "g": 0.45, "b": 0.48}),   # medium grey
        ("M_BearingJournal",  {"r": 0.70, "g": 0.70, "b": 0.75}),   # polished steel grey
    ]

    for mat_name, color in materials:
        print(f"  Creating {mat_name}...")
        a.cmd("create_simple_material", name=mat_name, color=color)

    print(f"  Materials created: {len(materials)}")


# ============================================================
# PHASE 7: BLUEPRINTS (12 Blueprints)
# ============================================================

def build_blueprints(a):
    a.phase("Phase 7: Blueprints")

    # -------------------------------------------------------
    # 1. BP_TimeManager (20 nodes, 18 connections)
    # -------------------------------------------------------
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
    print("    BP_TimeManager: DONE")

    # -------------------------------------------------------
    # 2. BP_EconomyManager (24 nodes, 20 connections)
    # -------------------------------------------------------
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
    print("    BP_EconomyManager: DONE")

    # -------------------------------------------------------
    # 3. BP_StationBase (16 nodes, 12 connections)
    # -------------------------------------------------------
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
    print("    BP_StationBase: DONE")

    # -------------------------------------------------------
    # 4. BP_HeatManager (16 nodes, 14 connections)
    # -------------------------------------------------------
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
    print("    BP_HeatManager: DONE")

    # -------------------------------------------------------
    # 5. BP_ReputationManager (13 nodes, 10 connections)
    # -------------------------------------------------------
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
    print("    BP_ReputationManager: DONE")

    # -------------------------------------------------------
    # 6. BP_ShopInventory
    # -------------------------------------------------------
    print("\n  Building BP_ShopInventory...")
    a.bp("BP_ShopInventory", variables=[
        {"name": "EngineCount", "type": "Int", "default": "0"},
        {"name": "MaxCapacity", "type": "Int", "default": "2"},
        {"name": "StorageUsed", "type": "Float", "default": "0.0"},
    ])
    nok, nf = a.nodes("BP_ShopInventory", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_init", "node_type": "PrintString", "params": {"InString": "Shop Inventory initialized"}},
        {"node_id": "evt_add_eng", "node_type": "CustomEvent", "params": {"EventName": "AddEngine"}},
        {"node_id": "p_added", "node_type": "PrintString", "params": {"InString": "Engine added to inventory"}},
        {"node_id": "get_count", "node_type": "GetVar", "params": {"Variable": "EngineCount"}},
        {"node_id": "add_one", "node_type": "/Script/Engine.KismetMathLibrary:Add_IntInt"},
        {"node_id": "set_count", "node_type": "SetVar", "params": {"Variable": "EngineCount"}},
        {"node_id": "get_count2", "node_type": "GetVar", "params": {"Variable": "EngineCount"}},
        {"node_id": "get_max", "node_type": "GetVar", "params": {"Variable": "MaxCapacity"}},
        {"node_id": "ge_cap", "node_type": "/Script/Engine.KismetMathLibrary:GreaterEqual_IntInt"},
        {"node_id": "br_cap", "node_type": "Branch"},
        {"node_id": "p_full", "node_type": "PrintString", "params": {"InString": "WARNING: Shop at max capacity!"}},
        {"node_id": "evt_rem_eng", "node_type": "CustomEvent", "params": {"EventName": "RemoveEngine"}},
        {"node_id": "get_count3", "node_type": "GetVar", "params": {"Variable": "EngineCount"}},
        {"node_id": "sub_one", "node_type": "/Script/Engine.KismetMathLibrary:Subtract_IntInt"},
        {"node_id": "set_count2", "node_type": "SetVar", "params": {"Variable": "EngineCount"}},
        {"node_id": "p_removed", "node_type": "PrintString", "params": {"InString": "Engine removed from inventory"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")
    cok, cf = a.conns("BP_ShopInventory", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "evt_add_eng", "from_pin": "then", "to_node": "p_added", "to_pin": "execute"},
        {"from_node": "p_added", "from_pin": "then", "to_node": "set_count", "to_pin": "execute"},
        {"from_node": "get_count", "from_pin": "EngineCount", "to_node": "add_one", "to_pin": "A"},
        {"from_node": "add_one", "from_pin": "ReturnValue", "to_node": "set_count", "to_pin": "EngineCount"},
        {"from_node": "set_count", "from_pin": "then", "to_node": "br_cap", "to_pin": "execute"},
        {"from_node": "get_count2", "from_pin": "EngineCount", "to_node": "ge_cap", "to_pin": "A"},
        {"from_node": "get_max", "from_pin": "MaxCapacity", "to_node": "ge_cap", "to_pin": "B"},
        {"from_node": "ge_cap", "from_pin": "ReturnValue", "to_node": "br_cap", "to_pin": "Condition"},
        {"from_node": "br_cap", "from_pin": "True", "to_node": "p_full", "to_pin": "execute"},
        {"from_node": "evt_rem_eng", "from_pin": "then", "to_node": "set_count2", "to_pin": "execute"},
        {"from_node": "get_count3", "from_pin": "EngineCount", "to_node": "sub_one", "to_pin": "A"},
        {"from_node": "sub_one", "from_pin": "ReturnValue", "to_node": "set_count2", "to_pin": "EngineCount"},
        {"from_node": "set_count2", "from_pin": "then", "to_node": "p_removed", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_ShopInventory")
    print("    BP_ShopInventory: DONE")

    # -------------------------------------------------------
    # 7. BP_QualityCalculator
    # -------------------------------------------------------
    print("\n  Building BP_QualityCalculator...")
    a.bp("BP_QualityCalculator", variables=[
        {"name": "PartScore", "type": "Float", "default": "0.0"},
        {"name": "MachiningScore", "type": "Float", "default": "0.0"},
        {"name": "AssemblyScore", "type": "Float", "default": "0.0"},
        {"name": "OverallQuality", "type": "Float", "default": "0.0"},
    ])
    nok, nf = a.nodes("BP_QualityCalculator", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_init", "node_type": "PrintString", "params": {"InString": "Quality Calculator ready"}},
        {"node_id": "evt_calc", "node_type": "CustomEvent", "params": {"EventName": "CalculateQuality"}},
        {"node_id": "get_part", "node_type": "GetVar", "params": {"Variable": "PartScore"}},
        {"node_id": "get_mach", "node_type": "GetVar", "params": {"Variable": "MachiningScore"}},
        {"node_id": "get_asm", "node_type": "GetVar", "params": {"Variable": "AssemblyScore"}},
        {"node_id": "mul_part", "node_type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
        {"node_id": "mul_mach", "node_type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
        {"node_id": "mul_asm", "node_type": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"},
        {"node_id": "add_pm", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "add_total", "node_type": "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
        {"node_id": "clamp_q", "node_type": "/Script/Engine.KismetMathLibrary:FClamp"},
        {"node_id": "set_quality", "node_type": "SetVar", "params": {"Variable": "OverallQuality"}},
        {"node_id": "p_quality", "node_type": "PrintString", "params": {"InString": "Quality score calculated"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")
    cok, cf = a.conns("BP_QualityCalculator", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "evt_calc", "from_pin": "then", "to_node": "set_quality", "to_pin": "execute"},
        {"from_node": "get_part", "from_pin": "PartScore", "to_node": "mul_part", "to_pin": "A"},
        {"from_node": "get_mach", "from_pin": "MachiningScore", "to_node": "mul_mach", "to_pin": "A"},
        {"from_node": "get_asm", "from_pin": "AssemblyScore", "to_node": "mul_asm", "to_pin": "A"},
        {"from_node": "mul_part", "from_pin": "ReturnValue", "to_node": "add_pm", "to_pin": "A"},
        {"from_node": "mul_mach", "from_pin": "ReturnValue", "to_node": "add_pm", "to_pin": "B"},
        {"from_node": "add_pm", "from_pin": "ReturnValue", "to_node": "add_total", "to_pin": "A"},
        {"from_node": "mul_asm", "from_pin": "ReturnValue", "to_node": "add_total", "to_pin": "B"},
        {"from_node": "add_total", "from_pin": "ReturnValue", "to_node": "clamp_q", "to_pin": "Value"},
        {"from_node": "clamp_q", "from_pin": "ReturnValue", "to_node": "set_quality", "to_pin": "OverallQuality"},
        {"from_node": "set_quality", "from_pin": "then", "to_node": "p_quality", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_QualityCalculator")
    print("    BP_QualityCalculator: DONE")

    # -------------------------------------------------------
    # 8. BP_EngineInstance
    # -------------------------------------------------------
    print("\n  Building BP_EngineInstance...")
    a.bp("BP_EngineInstance", variables=[
        {"name": "SerialNumber", "type": "String", "default": "UNKNOWN"},
        {"name": "Make", "type": "String", "default": "Unknown"},
        {"name": "Model", "type": "String", "default": "Unknown"},
        {"name": "QualityScore", "type": "Float", "default": "0.0"},
        {"name": "IsRebuilt", "type": "Bool", "default": "false"},
    ])
    nok, nf = a.nodes("BP_EngineInstance", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "get_sn", "node_type": "GetVar", "params": {"Variable": "SerialNumber"}},
        {"node_id": "p_init", "node_type": "PrintString"},
        {"node_id": "evt_setq", "node_type": "CustomEvent", "params": {"EventName": "SetQuality"}},
        {"node_id": "set_q", "node_type": "SetVar", "params": {"Variable": "QualityScore"}},
        {"node_id": "p_quality", "node_type": "PrintString", "params": {"InString": "Quality score set"}},
        {"node_id": "evt_rebuild", "node_type": "CustomEvent", "params": {"EventName": "MarkRebuilt"}},
        {"node_id": "set_rebuilt", "node_type": "SetVar", "params": {"Variable": "IsRebuilt"}},
        {"node_id": "p_rebuilt", "node_type": "PrintString", "params": {"InString": "Engine marked as rebuilt"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")
    cok, cf = a.conns("BP_EngineInstance", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "get_sn", "from_pin": "SerialNumber", "to_node": "p_init", "to_pin": "InString"},
        {"from_node": "evt_setq", "from_pin": "then", "to_node": "set_q", "to_pin": "execute"},
        {"from_node": "set_q", "from_pin": "then", "to_node": "p_quality", "to_pin": "execute"},
        {"from_node": "evt_rebuild", "from_pin": "then", "to_node": "set_rebuilt", "to_pin": "execute"},
        {"from_node": "set_rebuilt", "from_pin": "then", "to_node": "p_rebuilt", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_EngineInstance")
    print("    BP_EngineInstance: DONE")

    # -------------------------------------------------------
    # 9. BP_ActionApproval
    # -------------------------------------------------------
    print("\n  Building BP_ActionApproval...")
    a.bp("BP_ActionApproval", variables=[
        {"name": "ActionName", "type": "String", "default": "None"},
        {"name": "TimeCost", "type": "Float", "default": "0.0"},
        {"name": "MaterialCost", "type": "Float", "default": "0.0"},
        {"name": "IsApproved", "type": "Bool", "default": "false"},
    ])
    nok, nf = a.nodes("BP_ActionApproval", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_init", "node_type": "PrintString", "params": {"InString": "Action Approval system ready"}},
        {"node_id": "evt_show", "node_type": "CustomEvent", "params": {"EventName": "ShowApproval"}},
        {"node_id": "get_action", "node_type": "GetVar", "params": {"Variable": "ActionName"}},
        {"node_id": "p_action", "node_type": "PrintString"},
        {"node_id": "get_tcost", "node_type": "GetVar", "params": {"Variable": "TimeCost"}},
        {"node_id": "p_tcost", "node_type": "PrintString", "params": {"InString": "Time cost displayed"}},
        {"node_id": "get_mcost", "node_type": "GetVar", "params": {"Variable": "MaterialCost"}},
        {"node_id": "p_mcost", "node_type": "PrintString", "params": {"InString": "Material cost displayed"}},
        {"node_id": "evt_approve", "node_type": "CustomEvent", "params": {"EventName": "Approve"}},
        {"node_id": "set_approved", "node_type": "SetVar", "params": {"Variable": "IsApproved"}},
        {"node_id": "p_approved", "node_type": "PrintString", "params": {"InString": "Action Approved"}},
        {"node_id": "evt_cancel", "node_type": "CustomEvent", "params": {"EventName": "Cancel"}},
        {"node_id": "p_cancelled", "node_type": "PrintString", "params": {"InString": "Action Cancelled"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")
    cok, cf = a.conns("BP_ActionApproval", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "evt_show", "from_pin": "then", "to_node": "p_action", "to_pin": "execute"},
        {"from_node": "get_action", "from_pin": "ActionName", "to_node": "p_action", "to_pin": "InString"},
        {"from_node": "p_action", "from_pin": "then", "to_node": "p_tcost", "to_pin": "execute"},
        {"from_node": "p_tcost", "from_pin": "then", "to_node": "p_mcost", "to_pin": "execute"},
        {"from_node": "evt_approve", "from_pin": "then", "to_node": "set_approved", "to_pin": "execute"},
        {"from_node": "set_approved", "from_pin": "then", "to_node": "p_approved", "to_pin": "execute"},
        {"from_node": "evt_cancel", "from_pin": "then", "to_node": "p_cancelled", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_ActionApproval")
    print("    BP_ActionApproval: DONE")

    # -------------------------------------------------------
    # 10. BP_QuestManager
    # -------------------------------------------------------
    print("\n  Building BP_QuestManager...")
    a.bp("BP_QuestManager", variables=[
        {"name": "ActiveQuestName", "type": "String", "default": "None"},
        {"name": "IsQuestActive", "type": "Bool", "default": "false"},
        {"name": "QuestsCompleted", "type": "Int", "default": "0"},
    ])
    nok, nf = a.nodes("BP_QuestManager", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_init", "node_type": "PrintString", "params": {"InString": "Quest Manager initialized"}},
        {"node_id": "evt_start", "node_type": "CustomEvent", "params": {"EventName": "StartQuest"}},
        {"node_id": "set_active_t", "node_type": "SetVar", "params": {"Variable": "IsQuestActive"}},
        {"node_id": "get_quest", "node_type": "GetVar", "params": {"Variable": "ActiveQuestName"}},
        {"node_id": "p_started", "node_type": "PrintString"},
        {"node_id": "evt_complete", "node_type": "CustomEvent", "params": {"EventName": "CompleteQuest"}},
        {"node_id": "get_completed", "node_type": "GetVar", "params": {"Variable": "QuestsCompleted"}},
        {"node_id": "add_completed", "node_type": "/Script/Engine.KismetMathLibrary:Add_IntInt"},
        {"node_id": "set_completed", "node_type": "SetVar", "params": {"Variable": "QuestsCompleted"}},
        {"node_id": "set_active_f", "node_type": "SetVar", "params": {"Variable": "IsQuestActive"}},
        {"node_id": "p_completed", "node_type": "PrintString", "params": {"InString": "Quest completed!"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")
    cok, cf = a.conns("BP_QuestManager", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_init", "to_pin": "execute"},
        {"from_node": "evt_start", "from_pin": "then", "to_node": "set_active_t", "to_pin": "execute"},
        {"from_node": "set_active_t", "from_pin": "then", "to_node": "p_started", "to_pin": "execute"},
        {"from_node": "get_quest", "from_pin": "ActiveQuestName", "to_node": "p_started", "to_pin": "InString"},
        {"from_node": "evt_complete", "from_pin": "then", "to_node": "set_completed", "to_pin": "execute"},
        {"from_node": "get_completed", "from_pin": "QuestsCompleted", "to_node": "add_completed", "to_pin": "A"},
        {"from_node": "add_completed", "from_pin": "ReturnValue", "to_node": "set_completed", "to_pin": "QuestsCompleted"},
        {"from_node": "set_completed", "from_pin": "then", "to_node": "set_active_f", "to_pin": "execute"},
        {"from_node": "set_active_f", "from_pin": "then", "to_node": "p_completed", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_QuestManager")
    print("    BP_QuestManager: DONE")

    # -------------------------------------------------------
    # 11. BP_HUDManager
    # -------------------------------------------------------
    print("\n  Building BP_HUDManager...")
    a.bp("BP_HUDManager", variables=[
        {"name": "IsHUDVisible", "type": "Bool", "default": "true"},
    ])
    nok, nf = a.nodes("BP_HUDManager", [
        {"node_id": "begin", "node_type": "Event_ReceiveBeginPlay"},
        {"node_id": "p_ready", "node_type": "PrintString", "params": {"InString": "HUD Manager ready"}},
        {"node_id": "evt_show_msg", "node_type": "CustomEvent", "params": {"EventName": "ShowMessage"}},
        {"node_id": "p_msg", "node_type": "PrintString", "params": {"InString": "HUD message displayed"}},
        {"node_id": "evt_toggle", "node_type": "CustomEvent", "params": {"EventName": "ToggleHUD"}},
        {"node_id": "get_vis", "node_type": "GetVar", "params": {"Variable": "IsHUDVisible"}},
        {"node_id": "not_vis", "node_type": "/Script/Engine.KismetMathLibrary:Not_PreBool"},
        {"node_id": "set_vis", "node_type": "SetVar", "params": {"Variable": "IsHUDVisible"}},
        {"node_id": "p_toggled", "node_type": "PrintString", "params": {"InString": "HUD visibility toggled"}},
    ])
    print(f"    Nodes: {nok}/{nok+nf}")
    cok, cf = a.conns("BP_HUDManager", [
        {"from_node": "begin", "from_pin": "then", "to_node": "p_ready", "to_pin": "execute"},
        {"from_node": "evt_show_msg", "from_pin": "then", "to_node": "p_msg", "to_pin": "execute"},
        {"from_node": "evt_toggle", "from_pin": "then", "to_node": "set_vis", "to_pin": "execute"},
        {"from_node": "get_vis", "from_pin": "IsHUDVisible", "to_node": "not_vis", "to_pin": "A"},
        {"from_node": "not_vis", "from_pin": "ReturnValue", "to_node": "set_vis", "to_pin": "IsHUDVisible"},
        {"from_node": "set_vis", "from_pin": "then", "to_node": "p_toggled", "to_pin": "execute"},
    ])
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile("BP_HUDManager")
    print("    BP_HUDManager: DONE")

    # -------------------------------------------------------
    # 12. BP_BoreAndStrokeGameMode (7 nodes, 6 connections)
    # -------------------------------------------------------
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
    print("    BP_BoreAndStrokeGameMode: DONE")

    print("\n  All 12 Blueprints built.")


# ============================================================
# PHASE 8: WIDGETS (7 Widget Blueprints)
# ============================================================

def build_widgets(a):
    a.phase("Phase 8: Widget UIs")

    # -------------------------------------------------------
    # 1. WBP_GameHUD
    # -------------------------------------------------------
    print("  Building WBP_GameHUD...")
    a.cmd("create_widget_blueprint", name="WBP_GameHUD")
    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", widget_type="CanvasPanel", widget_name="Root")

    # DayLabel - top left
    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="TextBlock", widget_name="DayLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="text", value="Day 1")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="color", value="#E8DCC8")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="font_size", value="18")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="DayLabel", property="position", value="20,10")

    # CashLabel - top right, amber
    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="TextBlock", widget_name="CashLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="text", value="$15,000")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="font_size", value="22")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="CashLabel", property="position", value="1700,10")

    # TimeBar - top center, amber fill
    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="ProgressBar", widget_name="TimeBar")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="percent", value="1.0")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="fill_color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="TimeBar", property="position", value="760,15")

    # InteractPrompt - bottom center
    a.cmd("add_widget_child", widget_blueprint="WBP_GameHUD", parent_widget="Root", widget_type="TextBlock", widget_name="InteractPrompt")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="InteractPrompt", property="text", value="Press E to interact")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="InteractPrompt", property="color", value="#E8DCC8")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="InteractPrompt", property="font_size", value="16")
    a.cmd("set_widget_property", widget_blueprint="WBP_GameHUD", widget_name="InteractPrompt", property="position", value="860,1000")
    print("    WBP_GameHUD: DONE")

    # -------------------------------------------------------
    # 2. WBP_ActionApproval
    # -------------------------------------------------------
    print("  Building WBP_ActionApproval...")
    a.cmd("create_widget_blueprint", name="WBP_ActionApproval")
    a.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", widget_type="CanvasPanel", widget_name="Root")

    a.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", parent_widget="Root", widget_type="TextBlock", widget_name="Title")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="Title", property="text", value="Action Approval")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="Title", property="color", value="#FFFFFF")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="Title", property="font_size", value="20")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="Title", property="position", value="660,350")

    a.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", parent_widget="Root", widget_type="TextBlock", widget_name="TimeCostLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TimeCostLabel", property="text", value="Time: 0 min")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TimeCostLabel", property="color", value="#C8C8C8")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TimeCostLabel", property="font_size", value="16")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="TimeCostLabel", property="position", value="660,400")

    a.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", parent_widget="Root", widget_type="TextBlock", widget_name="MaterialCostLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="MaterialCostLabel", property="text", value="Materials: $0")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="MaterialCostLabel", property="color", value="#C8C8C8")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="MaterialCostLabel", property="font_size", value="16")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="MaterialCostLabel", property="position", value="660,430")

    a.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", parent_widget="Root", widget_type="TextBlock", widget_name="ApproveButtonText")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="ApproveButtonText", property="text", value="[APPROVE]")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="ApproveButtonText", property="color", value="#33CC66")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="ApproveButtonText", property="font_size", value="18")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="ApproveButtonText", property="position", value="660,480")

    a.cmd("add_widget_child", widget_blueprint="WBP_ActionApproval", parent_widget="Root", widget_type="TextBlock", widget_name="CancelButtonText")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="CancelButtonText", property="text", value="[CANCEL]")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="CancelButtonText", property="color", value="#CC3333")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="CancelButtonText", property="font_size", value="18")
    a.cmd("set_widget_property", widget_blueprint="WBP_ActionApproval", widget_name="CancelButtonText", property="position", value="860,480")
    print("    WBP_ActionApproval: DONE")

    # -------------------------------------------------------
    # 3. WBP_StationPanel
    # -------------------------------------------------------
    print("  Building WBP_StationPanel...")
    a.cmd("create_widget_blueprint", name="WBP_StationPanel")
    a.cmd("add_widget_child", widget_blueprint="WBP_StationPanel", widget_type="CanvasPanel", widget_name="Root")

    a.cmd("add_widget_child", widget_blueprint="WBP_StationPanel", parent_widget="Root", widget_type="TextBlock", widget_name="StationNameLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StationNameLabel", property="text", value="Station Name")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StationNameLabel", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StationNameLabel", property="font_size", value="20")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StationNameLabel", property="position", value="50,50")

    a.cmd("add_widget_child", widget_blueprint="WBP_StationPanel", parent_widget="Root", widget_type="TextBlock", widget_name="EngineNameLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="EngineNameLabel", property="text", value="No engine loaded")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="EngineNameLabel", property="color", value="#C8C8C8")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="EngineNameLabel", property="font_size", value="16")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="EngineNameLabel", property="position", value="50,90")

    a.cmd("add_widget_child", widget_blueprint="WBP_StationPanel", parent_widget="Root", widget_type="VerticalBox", widget_name="ActionsList")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="ActionsList", property="position", value="50,130")

    a.cmd("add_widget_child", widget_blueprint="WBP_StationPanel", parent_widget="Root", widget_type="TextBlock", widget_name="StatusText")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StatusText", property="text", value="Idle")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StatusText", property="color", value="#66CC66")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StatusText", property="font_size", value="14")
    a.cmd("set_widget_property", widget_blueprint="WBP_StationPanel", widget_name="StatusText", property="position", value="50,400")
    print("    WBP_StationPanel: DONE")

    # -------------------------------------------------------
    # 4. WBP_ShopStorage
    # -------------------------------------------------------
    print("  Building WBP_ShopStorage...")
    a.cmd("create_widget_blueprint", name="WBP_ShopStorage")
    a.cmd("add_widget_child", widget_blueprint="WBP_ShopStorage", widget_type="CanvasPanel", widget_name="Root")

    a.cmd("add_widget_child", widget_blueprint="WBP_ShopStorage", parent_widget="Root", widget_type="TextBlock", widget_name="TitleLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="TitleLabel", property="text", value="Shop Storage")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="TitleLabel", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="TitleLabel", property="font_size", value="20")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="TitleLabel", property="position", value="50,50")

    a.cmd("add_widget_child", widget_blueprint="WBP_ShopStorage", parent_widget="Root", widget_type="TextBlock", widget_name="CapacityLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="CapacityLabel", property="text", value="Capacity: 0/2")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="CapacityLabel", property="color", value="#C8C8C8")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="CapacityLabel", property="font_size", value="16")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="CapacityLabel", property="position", value="50,90")

    a.cmd("add_widget_child", widget_blueprint="WBP_ShopStorage", parent_widget="Root", widget_type="VerticalBox", widget_name="EngineList")
    a.cmd("set_widget_property", widget_blueprint="WBP_ShopStorage", widget_name="EngineList", property="position", value="50,130")
    print("    WBP_ShopStorage: DONE")

    # -------------------------------------------------------
    # 5. WBP_MainMenu
    # -------------------------------------------------------
    print("  Building WBP_MainMenu...")
    a.cmd("create_widget_blueprint", name="WBP_MainMenu")
    a.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", widget_type="CanvasPanel", widget_name="Root")

    a.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", parent_widget="Root", widget_type="TextBlock", widget_name="GameTitle")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="GameTitle", property="text", value="BORE & STROKE")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="GameTitle", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="GameTitle", property="font_size", value="48")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="GameTitle", property="position", value="660,200")

    a.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", parent_widget="Root", widget_type="TextBlock", widget_name="NewGameBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="NewGameBtn", property="text", value="NEW GAME")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="NewGameBtn", property="color", value="#FFFFFF")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="NewGameBtn", property="font_size", value="24")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="NewGameBtn", property="position", value="810,400")

    a.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", parent_widget="Root", widget_type="TextBlock", widget_name="ContinueBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="ContinueBtn", property="text", value="CONTINUE")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="ContinueBtn", property="color", value="#AAAAAA")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="ContinueBtn", property="font_size", value="24")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="ContinueBtn", property="position", value="810,460")

    a.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", parent_widget="Root", widget_type="TextBlock", widget_name="SettingsBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="SettingsBtn", property="text", value="SETTINGS")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="SettingsBtn", property="color", value="#AAAAAA")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="SettingsBtn", property="font_size", value="24")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="SettingsBtn", property="position", value="810,520")

    a.cmd("add_widget_child", widget_blueprint="WBP_MainMenu", parent_widget="Root", widget_type="TextBlock", widget_name="QuitBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="QuitBtn", property="text", value="QUIT")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="QuitBtn", property="color", value="#AAAAAA")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="QuitBtn", property="font_size", value="24")
    a.cmd("set_widget_property", widget_blueprint="WBP_MainMenu", widget_name="QuitBtn", property="position", value="810,580")
    print("    WBP_MainMenu: DONE")

    # -------------------------------------------------------
    # 6. WBP_PauseMenu
    # -------------------------------------------------------
    print("  Building WBP_PauseMenu...")
    a.cmd("create_widget_blueprint", name="WBP_PauseMenu")
    a.cmd("add_widget_child", widget_blueprint="WBP_PauseMenu", widget_type="CanvasPanel", widget_name="Root")

    a.cmd("add_widget_child", widget_blueprint="WBP_PauseMenu", parent_widget="Root", widget_type="TextBlock", widget_name="PausedLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PausedLabel", property="text", value="PAUSED")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PausedLabel", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PausedLabel", property="font_size", value="36")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PausedLabel", property="position", value="830,250")

    a.cmd("add_widget_child", widget_blueprint="WBP_PauseMenu", parent_widget="Root", widget_type="TextBlock", widget_name="ResumeBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="ResumeBtn", property="text", value="RESUME")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="ResumeBtn", property="color", value="#FFFFFF")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="ResumeBtn", property="font_size", value="22")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="ResumeBtn", property="position", value="850,380")

    a.cmd("add_widget_child", widget_blueprint="WBP_PauseMenu", parent_widget="Root", widget_type="TextBlock", widget_name="SaveBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="SaveBtn", property="text", value="SAVE GAME")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="SaveBtn", property="color", value="#AAAAAA")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="SaveBtn", property="font_size", value="22")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="SaveBtn", property="position", value="850,430")

    a.cmd("add_widget_child", widget_blueprint="WBP_PauseMenu", parent_widget="Root", widget_type="TextBlock", widget_name="PauseSettingsBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseSettingsBtn", property="text", value="SETTINGS")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseSettingsBtn", property="color", value="#AAAAAA")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseSettingsBtn", property="font_size", value="22")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseSettingsBtn", property="position", value="850,480")

    a.cmd("add_widget_child", widget_blueprint="WBP_PauseMenu", parent_widget="Root", widget_type="TextBlock", widget_name="PauseQuitBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseQuitBtn", property="text", value="QUIT TO MENU")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseQuitBtn", property="color", value="#CC3333")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseQuitBtn", property="font_size", value="22")
    a.cmd("set_widget_property", widget_blueprint="WBP_PauseMenu", widget_name="PauseQuitBtn", property="position", value="850,530")
    print("    WBP_PauseMenu: DONE")

    # -------------------------------------------------------
    # 7. WBP_EndOfDay
    # -------------------------------------------------------
    print("  Building WBP_EndOfDay...")
    a.cmd("create_widget_blueprint", name="WBP_EndOfDay")
    a.cmd("add_widget_child", widget_blueprint="WBP_EndOfDay", widget_type="CanvasPanel", widget_name="Root")

    a.cmd("add_widget_child", widget_blueprint="WBP_EndOfDay", parent_widget="Root", widget_type="TextBlock", widget_name="DaySummaryTitle")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="DaySummaryTitle", property="text", value="END OF DAY SUMMARY")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="DaySummaryTitle", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="DaySummaryTitle", property="font_size", value="28")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="DaySummaryTitle", property="position", value="700,250")

    a.cmd("add_widget_child", widget_blueprint="WBP_EndOfDay", parent_widget="Root", widget_type="TextBlock", widget_name="RevenueLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="RevenueLabel", property="text", value="Revenue: $0")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="RevenueLabel", property="color", value="#33CC66")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="RevenueLabel", property="font_size", value="20")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="RevenueLabel", property="position", value="750,340")

    a.cmd("add_widget_child", widget_blueprint="WBP_EndOfDay", parent_widget="Root", widget_type="TextBlock", widget_name="ExpensesLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ExpensesLabel", property="text", value="Expenses: $0")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ExpensesLabel", property="color", value="#CC3333")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ExpensesLabel", property="font_size", value="20")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ExpensesLabel", property="position", value="750,380")

    a.cmd("add_widget_child", widget_blueprint="WBP_EndOfDay", parent_widget="Root", widget_type="TextBlock", widget_name="ProfitLabel")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ProfitLabel", property="text", value="Profit: $0")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ProfitLabel", property="color", value="#FFFFFF")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ProfitLabel", property="font_size", value="24")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ProfitLabel", property="position", value="750,430")

    a.cmd("add_widget_child", widget_blueprint="WBP_EndOfDay", parent_widget="Root", widget_type="TextBlock", widget_name="ContinueBtn")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ContinueBtn", property="text", value="CONTINUE TO NEXT DAY")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ContinueBtn", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ContinueBtn", property="font_size", value="22")
    a.cmd("set_widget_property", widget_blueprint="WBP_EndOfDay", widget_name="ContinueBtn", property="position", value="760,510")
    print("    WBP_EndOfDay: DONE")

    print("  All 7 Widget Blueprints built.")


# ============================================================
# PHASE 10: LEVEL SETUP
# ============================================================

def build_level(a):
    a.phase("Phase 10: Level Setup")

    # 1. Scene lighting
    print("  Setting up scene lighting...")
    a.cmd("setup_scene_lighting", preset="indoor_bright")

    # 2. Floor - large cube scaled flat (20x15 meters, 0.1 thick)
    print("  Spawning floor...")
    a.cmd("spawn_actor_at",
        label="ShopFloor", x=0, y=0, z=0,
        **{"class": "StaticMeshActor",
           "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": 20, "scale_y": 15, "scale_z": 0.1})

    # 3. Four walls
    print("  Spawning walls...")
    a.cmd("spawn_actor_at",
        label="WallNorth", x=0, y=750, z=150,
        **{"class": "StaticMeshActor",
           "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": 20, "scale_y": 0.1, "scale_z": 3})
    a.cmd("spawn_actor_at",
        label="WallSouth", x=0, y=-750, z=150,
        **{"class": "StaticMeshActor",
           "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": 20, "scale_y": 0.1, "scale_z": 3})
    a.cmd("spawn_actor_at",
        label="WallEast", x=1000, y=0, z=150,
        **{"class": "StaticMeshActor",
           "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": 0.1, "scale_y": 15, "scale_z": 3})
    a.cmd("spawn_actor_at",
        label="WallWest", x=-1000, y=0, z=150,
        **{"class": "StaticMeshActor",
           "mesh": "/Engine/BasicShapes/Cube.Cube",
           "scale_x": 0.1, "scale_y": 15, "scale_z": 3})

    # 4. Apply materials to floor and walls
    print("  Applying materials...")
    a.cmd("set_actor_material",
        actor_label="ShopFloor",
        material_path="/Game/Arcwright/Materials/M_ShopFloor")
    for wall in ["WallNorth", "WallSouth", "WallEast", "WallWest"]:
        a.cmd("set_actor_material",
            actor_label=wall,
            material_path="/Game/Arcwright/Materials/M_ShopWall")

    # 5. Station markers at cardinal positions
    print("  Placing station markers...")
    stations = [
        ("Station_Degriming",   -600, 400, "Degriming Station"),
        ("Station_Disassembly", -200, 400, "Disassembly Station"),
        ("Station_Inspection",   200, 400, "Inspection Station"),
        ("Station_Cleaning",     600, 400, "Cleaning Station"),
    ]
    for label, x, y, name in stations:
        a.cmd("spawn_actor_at",
            label=label, x=x, y=y, z=5,
            **{"class": "StaticMeshActor",
               "mesh": "/Engine/BasicShapes/Cube.Cube",
               "scale_x": 1.5, "scale_y": 1.5, "scale_z": 1})
        a.cmd("set_actor_material",
            actor_label=label,
            material_path="/Game/Arcwright/Materials/M_Workbench")

    # 6. Overhead lights
    print("  Placing overhead lights...")
    lights = [
        ("Light_Bay1", -500, 0, 350),
        ("Light_Bay2",    0, 0, 350),
        ("Light_Bay3",  500, 0, 350),
        ("Light_Station", 0, 400, 300),
    ]
    for label, x, y, z in lights:
        a.cmd("spawn_actor_at",
            label=label, x=x, y=y, z=z,
            **{"class": "PointLight"})

    # 7. Set game mode
    print("  Setting game mode...")
    a.cmd("set_game_mode", game_mode="BP_BoreAndStrokeGameMode")

    # 8. Save all
    print("  Saving level...")
    a.cmd("save_all")

    print("  Level setup complete: floor, 4 walls, 4 stations, 4 lights, game mode set.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    start = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Bore & Stroke Full Build Script v2")
    print(f"Started: {timestamp}")
    print(f"{'='*60}")

    a = Arcwright()

    # Verify connection
    r = a.cmd("health_check")
    if r.get("status") != "ok":
        print("FATAL: Cannot connect to Arcwright on localhost:13377")
        print("Make sure UE Editor is running with the Arcwright plugin.")
        sys.exit(1)
    server_info = r.get("data", {})
    print(f"Connected: {server_info.get('server', 'Unknown')} v{server_info.get('version', '?')}")

    # ---- Build all 10 phases ----
    build_data_tables(a)      # Phase 1: 10 Data Tables
    build_tags(a)             # Phase 2: 5 Tag Hierarchies
    build_materials(a)        # Phase 3: 10 Materials
    # Phases 4-6 are design/audio/narrative — no TCP commands
    build_blueprints(a)       # Phase 7: 12 Blueprints
    build_widgets(a)          # Phase 8: 7 Widget Blueprints
    # Phase 9 is sound design — no TCP commands
    build_level(a)            # Phase 10: Level geometry + lighting + game mode

    # Final save
    a.cmd("save_all")

    elapsed = time.time() - start
    result = a.report()

    # Save log
    log_path = os.path.join(os.path.dirname(__file__), "bore_and_stroke_full_build.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Bore & Stroke Full Build Log v2\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Duration: {elapsed:.1f}s\n")
        f.write(f"Total commands: {result['total']}\n")
        f.write(f"Succeeded: {result['ok']}\n")
        f.write(f"Errors: {result['errors']}\n")
        f.write(f"\n{'='*60}\n")
        f.write(f"Phase Breakdown:\n")
        f.write(f"{'='*60}\n")
        for phase, stats in a.phase_stats.items():
            total_ph = stats['ok'] + stats['err']
            f.write(f"  {phase}: {stats['ok']}/{total_ph} ok ({stats['err']} errors)\n")
        f.write(f"\n{'='*60}\n")
        f.write(f"Assets Created:\n")
        f.write(f"{'='*60}\n")
        f.write(f"  Data Tables: 10 (DT_Difficulty, DT_ShopTiers, DT_Engines, DT_Companies,\n")
        f.write(f"                    DT_Equipment, DT_PartsPricing, DT_Consumables,\n")
        f.write(f"                    DT_Actions, DT_Customers, DT_Tolerances)\n")
        f.write(f"  Tag Hierarchies: 5 (Quality, Engine, Station, Heat, Customer)\n")
        f.write(f"  Materials: 10 (M_ShopFloor, M_ShopWall, M_Workbench, M_EngineBlock,\n")
        f.write(f"                  M_Chrome, M_Rust, M_OilStain, M_CarbonDeposit,\n")
        f.write(f"                  M_CylinderWall, M_BearingJournal)\n")
        f.write(f"  Blueprints: 12 (BP_TimeManager, BP_EconomyManager, BP_StationBase,\n")
        f.write(f"                   BP_HeatManager, BP_ReputationManager, BP_ShopInventory,\n")
        f.write(f"                   BP_QualityCalculator, BP_EngineInstance, BP_ActionApproval,\n")
        f.write(f"                   BP_QuestManager, BP_HUDManager, BP_BoreAndStrokeGameMode)\n")
        f.write(f"  Widget Blueprints: 7 (WBP_GameHUD, WBP_ActionApproval, WBP_StationPanel,\n")
        f.write(f"                        WBP_ShopStorage, WBP_MainMenu, WBP_PauseMenu,\n")
        f.write(f"                        WBP_EndOfDay)\n")
        f.write(f"  Level Actors: floor + 4 walls + 4 stations + 4 lights = 13\n")
        f.write(f"\n{'='*60}\n")
        f.write(f"Error Details:\n")
        f.write(f"{'='*60}\n")
        if a.errors:
            for i, e in enumerate(a.errors):
                f.write(f"  [{i+1}] {e['cmd']}: {e.get('error','')}\n")
                if 'params' in e:
                    params_str = json.dumps(e['params'], default=str)
                    if len(params_str) > 200:
                        params_str = params_str[:200] + "..."
                    f.write(f"      params: {params_str}\n")
        else:
            f.write(f"  (none)\n")
        f.write(f"\n{'='*60}\n")
        f.write(f"Full Command Log:\n")
        f.write(f"{'='*60}\n")
        for i, entry in enumerate(a.log):
            f.write(f"  [{i+1:3d}] {entry['phase']:30s} | {entry['cmd']:30s} | {entry['status']}\n")

    print(f"\nLog saved to: {log_path}")
    print(f"Build time: {elapsed:.1f}s")

    # Exit code based on error count
    sys.exit(0 if result['errors'] == 0 else 1)
