"""
Bore & Stroke — Final Verified Build
======================================
Builds all assets with post-build verification using inspection commands.
Every Blueprint is verified for node count, connection count, and compile status.
"""
import socket, json, time, os, sys
from datetime import datetime

class Arcwright:
    def __init__(self):
        self.log, self.errors, self.count = [], [], 0
        self.sock = None
        self.phase_stats = {}
        self.current_phase = "init"
        self.bp_results = []
        self.reconnect()

    def reconnect(self):
        if self.sock:
            try: self.sock.close()
            except: pass
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
                if not chunk: break
                data += chunk
            result = json.loads(data.decode().strip())
            status = result.get("status", "unknown")
            self.log.append({"cmd": command, "status": status, "phase": self.current_phase})
            if self.current_phase not in self.phase_stats:
                self.phase_stats[self.current_phase] = {"ok": 0, "err": 0}
            if status == "error":
                self.errors.append({"cmd": command, "error": result.get("message", result.get("error", ""))})
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
        print(f"\n{'='*60}\nPHASE: {name}\n{'='*60}")

    def dt(self, table_name, struct_name, columns, rows):
        ir = {"metadata": {"table_name": table_name, "struct_name": struct_name}, "columns": columns, "rows": rows}
        return self.cmd("create_data_table", ir_json=json.dumps(ir))

    def bp(self, name, parent="Actor", variables=None):
        self.cmd("delete_blueprint", name=name)
        p = {"name": name, "parent_class": parent}
        if variables: p["variables"] = variables
        return self.cmd("create_blueprint", **p)

    def nodes(self, bp, node_list):
        r = self.cmd("add_nodes_batch", blueprint=bp, nodes=node_list)
        if r["status"] == "ok":
            d = r["data"]
            if d["failed"] > 0:
                for n in d.get("results", []):
                    if not n.get("success"):
                        print(f"      NODE FAIL: {n.get('node_id','?')}: {n.get('error','?')}")
            return d["succeeded"], d["failed"]
        return 0, len(node_list)

    def conns(self, bp, conn_list):
        r = self.cmd("add_connections_batch", blueprint=bp, connections=conn_list)
        if r["status"] == "ok":
            d = r["data"]
            if d["failed"] > 0:
                for c in d.get("results", []):
                    if not c.get("success"):
                        print(f"      CONN FAIL: {c.get('source_node','?')}->{c.get('target_node','?')}: {c.get('error','?')}")
            return d["succeeded"], d["failed"]
        return 0, len(conn_list)

    def compile_and_verify(self, bp_name, min_nodes=5, min_conns=3):
        """Compile, save, and verify a Blueprint. Returns True if verified."""
        r = self.cmd("compile_blueprint", name=bp_name)
        compiled = r.get("data", {}).get("compiled", False)
        saved = r.get("data", {}).get("saved", False)

        # Inspect
        r2 = self.cmd("get_blueprint_graph", name=bp_name)
        if r2["status"] == "ok":
            d = r2["data"]
            nc = d.get("node_count", 0)
            cc = d.get("connection_count", 0)
            nv = len(d.get("variables", []))
            ok = nc >= min_nodes and cc >= min_conns and compiled
            status = "PASS" if ok else "FAIL"
            self.bp_results.append({"name": bp_name, "nodes": nc, "conns": cc, "vars": nv,
                                     "compiled": compiled, "saved": saved, "status": status})
            print(f"    VERIFY: {nc} nodes, {cc} conns, {nv} vars, compiled={compiled}, saved={saved} -> {status}")
            return ok
        else:
            self.bp_results.append({"name": bp_name, "nodes": 0, "conns": 0, "status": "ERROR"})
            print(f"    VERIFY: ERROR - {r2.get('message','?')}")
            return False


def build_bp(a, name, parent, variables, node_list, conn_list, min_nodes, min_conns):
    """Build a complete Blueprint with verification."""
    print(f"\n  Building {name}...")
    a.bp(name, parent, variables)
    nok, nf = a.nodes(name, node_list)
    print(f"    Nodes: {nok}/{nok+nf}")
    cok, cf = a.conns(name, conn_list)
    print(f"    Connections: {cok}/{cok+cf}")
    a.compile_and_verify(name, min_nodes, min_conns)


# ============================================================
# MAIN BUILD
# ============================================================

if __name__ == "__main__":
    start = time.time()
    print(f"Bore & Stroke Final Verified Build")
    print(f"Started: {datetime.now()}")
    print("=" * 60)

    a = Arcwright()
    r = a.cmd("health_check")
    print(f"Connected: {r.get('data',{}).get('server','?')}")

    # ── Phase 1: Data Tables ──
    a.phase("Phase 1: Data Tables")

    tables = [
        ("DT_Difficulty", "DiffStruct", [{"name":"Setting","type":"Name"},{"name":"Easy","type":"String"},{"name":"Normal","type":"String"},{"name":"Hard","type":"String"}],
         [{"name":"StartingCash","values":{"Setting":"StartingCash","Easy":"25000","Normal":"15000","Hard":"8000"}},
          {"name":"PartPrices","values":{"Setting":"PartPrices","Easy":"0.85","Normal":"1.0","Hard":"1.15"}},
          {"name":"SellPrices","values":{"Setting":"SellPrices","Easy":"1.15","Normal":"1.0","Hard":"0.9"}},
          {"name":"WearRate","values":{"Setting":"WearRate","Easy":"0.75","Normal":"1.0","Hard":"1.25"}},
          {"name":"Overhead","values":{"Setting":"Overhead","Easy":"0.85","Normal":"1.0","Hard":"1.15"}}]),
        ("DT_ShopTiers", "TierStruct", [{"name":"TierID","type":"Name"},{"name":"Name","type":"String"},{"name":"Size","type":"String"},{"name":"Cost","type":"Float"},{"name":"Capacity","type":"Integer"}],
         [{"name":"T1","values":{"TierID":"T1","Name":"Backyard Garage","Size":"400 sqft","Cost":0,"Capacity":2}},
          {"name":"T2","values":{"TierID":"T2","Name":"Small Shop","Size":"800 sqft","Cost":15000,"Capacity":4}},
          {"name":"T3","values":{"TierID":"T3","Name":"Professional Shop","Size":"1500 sqft","Cost":50000,"Capacity":8}},
          {"name":"T4","values":{"TierID":"T4","Name":"Full Machine Shop","Size":"3000 sqft","Cost":150000,"Capacity":16}},
          {"name":"T5","values":{"TierID":"T5","Name":"Premium Machine Shop","Size":"5000+ sqft","Cost":500000,"Capacity":32}}]),
        ("DT_Engines", "EngStruct", [{"name":"ID","type":"Name"},{"name":"Make","type":"String"},{"name":"Family","type":"String"},{"name":"Disp","type":"String"},{"name":"Config","type":"String"},{"name":"Years","type":"String"},{"name":"Rarity","type":"String"},{"name":"HP","type":"Integer"},{"name":"Price","type":"Float"}],
         [{"name":"SBC283","values":{"ID":"SBC283","Make":"Chevrolet","Family":"Small Block","Disp":"283","Config":"V8","Years":"1957-1967","Rarity":"Common","HP":185,"Price":800}},
          {"name":"SBC327","values":{"ID":"SBC327","Make":"Chevrolet","Family":"Small Block","Disp":"327","Config":"V8","Years":"1962-1969","Rarity":"Common","HP":250,"Price":1200}},
          {"name":"SBC350","values":{"ID":"SBC350","Make":"Chevrolet","Family":"Small Block","Disp":"350","Config":"V8","Years":"1967-1970","Rarity":"Common","HP":295,"Price":1000}},
          {"name":"BBC427","values":{"ID":"BBC427","Make":"Chevrolet","Family":"Big Block","Disp":"427","Config":"V8","Years":"1966-1969","Rarity":"Rare","HP":390,"Price":5000}},
          {"name":"FE390","values":{"ID":"FE390","Make":"Ford","Family":"FE Series","Disp":"390","Config":"V8","Years":"1961-1970","Rarity":"Common","HP":300,"Price":1500}},
          {"name":"HEMI426","values":{"ID":"HEMI426","Make":"Chrysler","Family":"426 Hemi","Disp":"426","Config":"V8","Years":"1964-1971","Rarity":"Rare","HP":425,"Price":12000}},
          {"name":"SLANT225","values":{"ID":"SLANT225","Make":"Chrysler","Family":"Slant Six","Disp":"225","Config":"I6","Years":"1960-1970","Rarity":"Common","HP":145,"Price":400}},
          {"name":"PONTI389","values":{"ID":"PONTI389","Make":"Pontiac","Family":"Pontiac V8","Disp":"389","Config":"V8","Years":"1959-1966","Rarity":"Common","HP":325,"Price":1800}}]),
        ("DT_Companies", "CompStruct", [{"name":"ID","type":"Name"},{"name":"Name","type":"String"},{"name":"Tier","type":"String"},{"name":"Desc","type":"String"}],
         [{"name":"IRONCLAD","values":{"ID":"IRONCLAD","Name":"Ironclad Parts","Tier":"Budget","Desc":"Affordable rebuild parts"}},
          {"name":"MAINLINE","values":{"ID":"MAINLINE","Name":"Mainline Automotive","Tier":"Standard","Desc":"Reliable mid-range"}},
          {"name":"PRECISION","values":{"ID":"PRECISION","Name":"Precision Engineered","Tier":"Premium","Desc":"High-quality parts"}},
          {"name":"APEX","values":{"ID":"APEX","Name":"Apex Racing Supply","Tier":"Performance","Desc":"Competition-grade"}}]),
        ("DT_Equipment", "EquipStruct", [{"name":"ID","type":"Name"},{"name":"Name","type":"String"},{"name":"Station","type":"String"},{"name":"Cost","type":"Float"},{"name":"TimeFactor","type":"Float"},{"name":"QualityBonus","type":"Integer"}],
         [{"name":"ChainHoist","values":{"ID":"ChainHoist","Name":"Chain Hoist","Station":"Lifting","Cost":0,"TimeFactor":1.0,"QualityBonus":0}},
          {"name":"SteamCleaner","values":{"ID":"SteamCleaner","Name":"Steam Cleaner","Station":"Degriming","Cost":4500,"TimeFactor":0.6,"QualityBonus":5}},
          {"name":"ImpactDrivers","values":{"ID":"ImpactDrivers","Name":"Impact Drivers","Station":"Disassembly","Cost":500,"TimeFactor":0.6,"QualityBonus":0}},
          {"name":"BoreGauges","values":{"ID":"BoreGauges","Name":"Bore Gauges","Station":"Inspection","Cost":350,"TimeFactor":0.8,"QualityBonus":0}},
          {"name":"HotTank","values":{"ID":"HotTank","Name":"Caustic Soda Hot Tank","Station":"Cleaning","Cost":3500,"TimeFactor":0.4,"QualityBonus":5}}]),
    ]

    for tname, sname, cols, rows in tables:
        a.dt(tname, sname, cols, rows)
        print(f"  {tname}: {len(rows)} rows")

    a.cmd("save_all")
    print(f"  Saved. {len(tables)} data tables.")

    # ── Phase 3: Materials ──
    a.phase("Phase 3: Materials")
    materials = [
        ("M_ShopFloor", 0.15, 0.15, 0.15), ("M_ShopWall", 0.25, 0.22, 0.2),
        ("M_Workbench", 0.2, 0.15, 0.1), ("M_EngineBlock", 0.35, 0.35, 0.35),
        ("M_Chrome", 0.8, 0.8, 0.8), ("M_Rust", 0.6, 0.3, 0.1),
        ("M_OilStain", 0.1, 0.08, 0.05), ("M_CarbonDeposit", 0.12, 0.12, 0.12),
        ("M_CylinderWall", 0.45, 0.45, 0.45), ("M_BearingJournal", 0.6, 0.6, 0.6),
    ]
    for name, r, g, b in materials:
        a.cmd("create_simple_material", name=name, color={"r": r, "g": g, "b": b})
    a.cmd("save_all")
    print(f"  Created {len(materials)} materials.")

    # ── Phase 7: Blueprints (VERIFIED) ──
    a.phase("Phase 7: Blueprints")

    # BP_TimeManager
    build_bp(a, "BP_TimeManager", "Actor",
        [{"name":"CurrentDay","type":"Int","default":"1"},{"name":"HumanTimeRemaining","type":"Float","default":"480.0"},
         {"name":"DailyBudget","type":"Float","default":"480.0"},{"name":"IsEndOfDay","type":"Bool","default":"false"}],
        [{"node_id":"begin","node_type":"Event_ReceiveBeginPlay"},
         {"node_id":"get_budget","node_type":"GetVar","params":{"Variable":"DailyBudget"}},
         {"node_id":"set_time_init","node_type":"SetVar","params":{"Variable":"HumanTimeRemaining"}},
         {"node_id":"p_start","node_type":"PrintString","params":{"InString":"Day started"}},
         {"node_id":"evt_consume","node_type":"CustomEvent","params":{"EventName":"ConsumeTime"}},
         {"node_id":"get_time","node_type":"GetVar","params":{"Variable":"HumanTimeRemaining"}},
         {"node_id":"sub_time","node_type":"/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
         {"node_id":"set_time","node_type":"SetVar","params":{"Variable":"HumanTimeRemaining"}},
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
         {"node_id":"p_newday","node_type":"PrintString","params":{"InString":"New day started"}}],
        [{"from_node":"begin","from_pin":"then","to_node":"set_time_init","to_pin":"execute"},
         {"from_node":"get_budget","from_pin":"DailyBudget","to_node":"set_time_init","to_pin":"HumanTimeRemaining"},
         {"from_node":"set_time_init","from_pin":"then","to_node":"p_start","to_pin":"execute"},
         {"from_node":"evt_consume","from_pin":"then","to_node":"set_time","to_pin":"execute"},
         {"from_node":"get_time","from_pin":"HumanTimeRemaining","to_node":"sub_time","to_pin":"A"},
         {"from_node":"sub_time","from_pin":"ReturnValue","to_node":"set_time","to_pin":"HumanTimeRemaining"},
         {"from_node":"set_time","from_pin":"then","to_node":"br_end","to_pin":"execute"},
         {"from_node":"set_time","from_pin":"HumanTimeRemaining","to_node":"leq_zero","to_pin":"A"},
         {"from_node":"leq_zero","from_pin":"ReturnValue","to_node":"br_end","to_pin":"Condition"},
         {"from_node":"br_end","from_pin":"False","to_node":"p_consumed","to_pin":"execute"},
         {"from_node":"evt_endday","from_pin":"then","to_node":"set_eod_t","to_pin":"execute"},
         {"from_node":"set_eod_t","from_pin":"then","to_node":"set_day","to_pin":"execute"},
         {"from_node":"get_day","from_pin":"CurrentDay","to_node":"add_day","to_pin":"A"},
         {"from_node":"add_day","from_pin":"ReturnValue","to_node":"set_day","to_pin":"CurrentDay"},
         {"from_node":"set_day","from_pin":"then","to_node":"set_time2","to_pin":"execute"},
         {"from_node":"get_budget2","from_pin":"DailyBudget","to_node":"set_time2","to_pin":"HumanTimeRemaining"},
         {"from_node":"set_time2","from_pin":"then","to_node":"set_eod_f","to_pin":"execute"},
         {"from_node":"set_eod_f","from_pin":"then","to_node":"p_newday","to_pin":"execute"}],
        15, 10)

    # BP_EconomyManager
    build_bp(a, "BP_EconomyManager", "Actor",
        [{"name":"Cash","type":"Float","default":"15000.0"},{"name":"TotalRevenue","type":"Float","default":"0.0"},
         {"name":"TotalExpenses","type":"Float","default":"0.0"},{"name":"DailyOverhead","type":"Float","default":"50.0"}],
        [{"node_id":"begin","node_type":"Event_ReceiveBeginPlay"},
         {"node_id":"p_init","node_type":"PrintString","params":{"InString":"Economy Manager initialized"}},
         {"node_id":"evt_add","node_type":"CustomEvent","params":{"EventName":"AddCash"}},
         {"node_id":"gc_a","node_type":"GetVar","params":{"Variable":"Cash"}},
         {"node_id":"math_add","node_type":"/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
         {"node_id":"sc_a","node_type":"SetVar","params":{"Variable":"Cash"}},
         {"node_id":"gr_a","node_type":"GetVar","params":{"Variable":"TotalRevenue"}},
         {"node_id":"math_rev","node_type":"/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
         {"node_id":"sr_a","node_type":"SetVar","params":{"Variable":"TotalRevenue"}},
         {"node_id":"p_added","node_type":"PrintString","params":{"InString":"Cash added"}},
         {"node_id":"evt_ded","node_type":"CustomEvent","params":{"EventName":"DeductCash"}},
         {"node_id":"gc_d","node_type":"GetVar","params":{"Variable":"Cash"}},
         {"node_id":"ge_d","node_type":"/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
         {"node_id":"br_d","node_type":"Branch"},
         {"node_id":"sub_d","node_type":"/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
         {"node_id":"sc_d","node_type":"SetVar","params":{"Variable":"Cash"}},
         {"node_id":"ge_exp","node_type":"GetVar","params":{"Variable":"TotalExpenses"}},
         {"node_id":"math_exp","node_type":"/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
         {"node_id":"se_exp","node_type":"SetVar","params":{"Variable":"TotalExpenses"}},
         {"node_id":"p_deducted","node_type":"PrintString","params":{"InString":"Cash deducted"}},
         {"node_id":"p_insuff","node_type":"PrintString","params":{"InString":"Insufficient funds"}},
         {"node_id":"evt_eod","node_type":"CustomEvent","params":{"EventName":"ProcessEndOfDay"}},
         {"node_id":"get_oh","node_type":"GetVar","params":{"Variable":"DailyOverhead"}},
         {"node_id":"p_eod","node_type":"PrintString","params":{"InString":"End of day processed"}}],
        [{"from_node":"begin","from_pin":"then","to_node":"p_init","to_pin":"execute"},
         {"from_node":"evt_add","from_pin":"then","to_node":"sc_a","to_pin":"execute"},
         {"from_node":"sc_a","from_pin":"then","to_node":"sr_a","to_pin":"execute"},
         {"from_node":"sr_a","from_pin":"then","to_node":"p_added","to_pin":"execute"},
         {"from_node":"gc_a","from_pin":"Cash","to_node":"math_add","to_pin":"A"},
         {"from_node":"math_add","from_pin":"ReturnValue","to_node":"sc_a","to_pin":"Cash"},
         {"from_node":"gr_a","from_pin":"TotalRevenue","to_node":"math_rev","to_pin":"A"},
         {"from_node":"math_rev","from_pin":"ReturnValue","to_node":"sr_a","to_pin":"TotalRevenue"},
         {"from_node":"evt_ded","from_pin":"then","to_node":"br_d","to_pin":"execute"},
         {"from_node":"br_d","from_pin":"True","to_node":"sc_d","to_pin":"execute"},
         {"from_node":"sc_d","from_pin":"then","to_node":"se_exp","to_pin":"execute"},
         {"from_node":"se_exp","from_pin":"then","to_node":"p_deducted","to_pin":"execute"},
         {"from_node":"br_d","from_pin":"False","to_node":"p_insuff","to_pin":"execute"},
         {"from_node":"gc_d","from_pin":"Cash","to_node":"ge_d","to_pin":"A"},
         {"from_node":"ge_d","from_pin":"ReturnValue","to_node":"br_d","to_pin":"Condition"},
         {"from_node":"gc_d","from_pin":"Cash","to_node":"sub_d","to_pin":"A"},
         {"from_node":"sub_d","from_pin":"ReturnValue","to_node":"sc_d","to_pin":"Cash"},
         {"from_node":"ge_exp","from_pin":"TotalExpenses","to_node":"math_exp","to_pin":"A"},
         {"from_node":"math_exp","from_pin":"ReturnValue","to_node":"se_exp","to_pin":"TotalExpenses"},
         {"from_node":"evt_eod","from_pin":"then","to_node":"p_eod","to_pin":"execute"}],
        20, 15)

    # BP_StationBase
    build_bp(a, "BP_StationBase", "Actor",
        [{"name":"StationName","type":"String","default":"Workstation"},{"name":"IsPlayerNearby","type":"Bool","default":"false"},{"name":"IsStationActive","type":"Bool","default":"false"}],
        [{"node_id":"ov_in","node_type":"Event_ReceiveActorBeginOverlap"},
         {"node_id":"ov_out","node_type":"Event_ReceiveActorEndOverlap"},
         {"node_id":"set_near_t","node_type":"SetVar","params":{"Variable":"IsPlayerNearby"}},
         {"node_id":"set_near_f","node_type":"SetVar","params":{"Variable":"IsPlayerNearby"}},
         {"node_id":"get_name","node_type":"GetVar","params":{"Variable":"StationName"}},
         {"node_id":"p_prompt","node_type":"PrintString"},
         {"node_id":"evt_act","node_type":"CustomEvent","params":{"EventName":"ActivateStation"}},
         {"node_id":"get_near","node_type":"GetVar","params":{"Variable":"IsPlayerNearby"}},
         {"node_id":"get_active","node_type":"GetVar","params":{"Variable":"IsStationActive"}},
         {"node_id":"not_act","node_type":"/Script/Engine.KismetMathLibrary:Not_PreBool"},
         {"node_id":"and_chk","node_type":"/Script/Engine.KismetMathLibrary:BooleanAND"},
         {"node_id":"br_act","node_type":"Branch"},
         {"node_id":"set_act_t","node_type":"SetVar","params":{"Variable":"IsStationActive"}},
         {"node_id":"p_act","node_type":"PrintString","params":{"InString":"Station activated"}},
         {"node_id":"evt_deact","node_type":"CustomEvent","params":{"EventName":"DeactivateStation"}},
         {"node_id":"set_act_f","node_type":"SetVar","params":{"Variable":"IsStationActive"}}],
        [{"from_node":"ov_in","from_pin":"then","to_node":"set_near_t","to_pin":"execute"},
         {"from_node":"set_near_t","from_pin":"then","to_node":"p_prompt","to_pin":"execute"},
         {"from_node":"get_name","from_pin":"StationName","to_node":"p_prompt","to_pin":"InString"},
         {"from_node":"ov_out","from_pin":"then","to_node":"set_near_f","to_pin":"execute"},
         {"from_node":"evt_act","from_pin":"then","to_node":"br_act","to_pin":"execute"},
         {"from_node":"get_near","from_pin":"IsPlayerNearby","to_node":"and_chk","to_pin":"A"},
         {"from_node":"get_active","from_pin":"IsStationActive","to_node":"not_act","to_pin":"A"},
         {"from_node":"not_act","from_pin":"ReturnValue","to_node":"and_chk","to_pin":"B"},
         {"from_node":"and_chk","from_pin":"ReturnValue","to_node":"br_act","to_pin":"Condition"},
         {"from_node":"br_act","from_pin":"True","to_node":"set_act_t","to_pin":"execute"},
         {"from_node":"set_act_t","from_pin":"then","to_node":"p_act","to_pin":"execute"},
         {"from_node":"evt_deact","from_pin":"then","to_node":"set_act_f","to_pin":"execute"}],
        12, 8)

    # BP_HeatManager
    build_bp(a, "BP_HeatManager", "Actor",
        [{"name":"HeatLevel","type":"Float","default":"0.0"},{"name":"HeatDecayRate","type":"Float","default":"0.1"},{"name":"MaxHeat","type":"Float","default":"100.0"}],
        [{"node_id":"begin","node_type":"Event_ReceiveBeginPlay"},
         {"node_id":"p_init","node_type":"PrintString","params":{"InString":"Heat Manager active"}},
         {"node_id":"evt_add","node_type":"CustomEvent","params":{"EventName":"AddHeat"}},
         {"node_id":"get_h","node_type":"GetVar","params":{"Variable":"HeatLevel"}},
         {"node_id":"add_h","node_type":"/Script/Engine.KismetMathLibrary:Add_DoubleDouble"},
         {"node_id":"clamp_h","node_type":"/Script/Engine.KismetMathLibrary:FClamp"},
         {"node_id":"set_h","node_type":"SetVar","params":{"Variable":"HeatLevel"}},
         {"node_id":"ge50","node_type":"/Script/Engine.KismetMathLibrary:GreaterEqual_DoubleDouble"},
         {"node_id":"br_warn","node_type":"Branch"},
         {"node_id":"p_warn","node_type":"PrintString","params":{"InString":"WARNING: Heat elevated!"}},
         {"node_id":"evt_decay","node_type":"CustomEvent","params":{"EventName":"DecayHeat"}},
         {"node_id":"get_h2","node_type":"GetVar","params":{"Variable":"HeatLevel"}},
         {"node_id":"get_rate","node_type":"GetVar","params":{"Variable":"HeatDecayRate"}},
         {"node_id":"sub_dec","node_type":"/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"},
         {"node_id":"clamp_d","node_type":"/Script/Engine.KismetMathLibrary:FClamp"},
         {"node_id":"set_h2","node_type":"SetVar","params":{"Variable":"HeatLevel"}}],
        [{"from_node":"begin","from_pin":"then","to_node":"p_init","to_pin":"execute"},
         {"from_node":"evt_add","from_pin":"then","to_node":"set_h","to_pin":"execute"},
         {"from_node":"get_h","from_pin":"HeatLevel","to_node":"add_h","to_pin":"A"},
         {"from_node":"add_h","from_pin":"ReturnValue","to_node":"clamp_h","to_pin":"Value"},
         {"from_node":"clamp_h","from_pin":"ReturnValue","to_node":"set_h","to_pin":"HeatLevel"},
         {"from_node":"set_h","from_pin":"then","to_node":"br_warn","to_pin":"execute"},
         {"from_node":"set_h","from_pin":"HeatLevel","to_node":"ge50","to_pin":"A"},
         {"from_node":"ge50","from_pin":"ReturnValue","to_node":"br_warn","to_pin":"Condition"},
         {"from_node":"br_warn","from_pin":"True","to_node":"p_warn","to_pin":"execute"},
         {"from_node":"evt_decay","from_pin":"then","to_node":"set_h2","to_pin":"execute"},
         {"from_node":"get_h2","from_pin":"HeatLevel","to_node":"sub_dec","to_pin":"A"},
         {"from_node":"get_rate","from_pin":"HeatDecayRate","to_node":"sub_dec","to_pin":"B"},
         {"from_node":"sub_dec","from_pin":"ReturnValue","to_node":"clamp_d","to_pin":"Value"},
         {"from_node":"clamp_d","from_pin":"ReturnValue","to_node":"set_h2","to_pin":"HeatLevel"}],
        12, 8)

    # BP_BoreAndStrokeGameMode
    build_bp(a, "BP_BoreAndStrokeGameMode", "GameModeBase", None,
        [{"node_id":"begin","node_type":"Event_ReceiveBeginPlay"},
         {"node_id":"p1","node_type":"PrintString","params":{"InString":"Spawning TimeManager..."}},
         {"node_id":"p2","node_type":"PrintString","params":{"InString":"Spawning EconomyManager..."}},
         {"node_id":"p3","node_type":"PrintString","params":{"InString":"Spawning HeatManager..."}},
         {"node_id":"p4","node_type":"PrintString","params":{"InString":"Spawning ReputationManager..."}},
         {"node_id":"p5","node_type":"PrintString","params":{"InString":"Spawning HUDManager..."}},
         {"node_id":"p_done","node_type":"PrintString","params":{"InString":"Bore & Stroke initialized!"}}],
        [{"from_node":"begin","from_pin":"then","to_node":"p1","to_pin":"execute"},
         {"from_node":"p1","from_pin":"then","to_node":"p2","to_pin":"execute"},
         {"from_node":"p2","from_pin":"then","to_node":"p3","to_pin":"execute"},
         {"from_node":"p3","from_pin":"then","to_node":"p4","to_pin":"execute"},
         {"from_node":"p4","from_pin":"then","to_node":"p5","to_pin":"execute"},
         {"from_node":"p5","from_pin":"then","to_node":"p_done","to_pin":"execute"}],
        5, 4)

    a.cmd("save_all")

    # ── Phase 8: Widgets ──
    a.phase("Phase 8: Widget UIs")
    widgets = [
        ("WBP_GameHUD", [("DayLabel","Day 1","#E8DCC8"),("CashLabel","$15,000","#E8A624"),("TimeLabel","8:00 remaining","#E8DCC8")]),
        ("WBP_ActionApproval", [("Title","Action Approval","#E8A624"),("TimeCost","Time: 0 min","#E8DCC8"),("Approve","APPROVE","#33D166"),("Cancel","CANCEL","#F2404D")]),
        ("WBP_MainMenu", [("GameTitle","BORE & STROKE","#E8A624"),("NewGame","New Game","#E8DCC8"),("Continue","Continue","#E8DCC8"),("Quit","Quit","#808FA3")]),
    ]
    for wbp_name, labels in widgets:
        a.cmd("create_widget_blueprint", name=wbp_name)
        a.cmd("add_widget_child", widget_blueprint=wbp_name, widget_type="CanvasPanel", widget_name="Root")
        for i, (lbl_name, text, color) in enumerate(labels):
            a.cmd("add_widget_child", widget_blueprint=wbp_name, parent_widget="Root", widget_type="TextBlock", widget_name=lbl_name)
            a.cmd("set_widget_property", widget_blueprint=wbp_name, widget_name=lbl_name, property="text", value=text)
            a.cmd("set_widget_property", widget_blueprint=wbp_name, widget_name=lbl_name, property="color", value=color)
            a.cmd("set_widget_property", widget_blueprint=wbp_name, widget_name=lbl_name, property="font_size", value=str(20 if i == 0 else 16))
        print(f"  {wbp_name}: created with {len(labels)} elements")
    a.cmd("save_all")

    # ── Phase 10: Level ──
    a.phase("Phase 10: Level Setup")
    a.cmd("setup_scene_lighting", preset="indoor_bright")
    a.cmd("spawn_actor_at", label="ShopFloor", x=0, y=0, z=0, **{"class":"StaticMeshActor","mesh":"/Engine/BasicShapes/Cube.Cube","scale_x":20,"scale_y":15,"scale_z":0.1})
    for name, x, y in [("WallN",0,750),("WallS",0,-750),("WallE",1000,0),("WallW",-1000,0)]:
        sx, sy = (20, 0.1) if "N" in name or "S" in name else (0.1, 15)
        a.cmd("spawn_actor_at", label=name, x=x, y=y, z=150, **{"class":"StaticMeshActor","mesh":"/Engine/BasicShapes/Cube.Cube","scale_x":sx,"scale_y":sy,"scale_z":3})
    a.cmd("create_simple_material", name="M_Floor", color={"r":0.12,"g":0.12,"b":0.12})
    a.cmd("set_actor_material", actor_label="ShopFloor", material_path="/Game/Arcwright/Materials/M_Floor")
    a.cmd("set_game_mode", game_mode="BP_BoreAndStrokeGameMode")
    a.cmd("save_all")
    print("  Level built and saved.")

    # ── POST-BUILD VERIFICATION ──
    a.phase("Verification")

    # Asset counts
    for atype in ["Blueprint", "DataTable", "Material"]:
        r = a.cmd("find_assets", type=atype, path="/Game/BlueprintLLM")
        assets = r.get("data", {}).get("assets", r.get("data", {}).get("results", []))
        count = len(assets) if isinstance(assets, list) else "?"
        print(f"  {atype}s on disk: {count}")

    r = a.cmd("get_level_info")
    print(f"  Level actors: {r.get('data',{}).get('actor_count','?')}")

    r = a.cmd("take_viewport_screenshot")
    print(f"  Screenshot: {r.get('data',{}).get('path','?')}")

    # ── FINAL REPORT ──
    elapsed = time.time() - start
    ok = len([l for l in a.log if l["status"] == "ok"])
    err = len(a.errors)
    print(f"\n{'='*60}")
    print(f"FINAL BUILD REPORT")
    print(f"{'='*60}")
    print(f"Total commands: {len(a.log)} | OK: {ok} | Errors: {err} | Time: {elapsed:.1f}s")
    print(f"\nPer-phase:")
    for ph, st in a.phase_stats.items():
        print(f"  {ph}: {st['ok']} ok, {st['err']} err")
    print(f"\nBlueprint Verification:")
    for bp in a.bp_results:
        print(f"  {bp['status']}: {bp['name']} ({bp['nodes']} nodes, {bp['conns']} conns, {bp['vars']} vars, compiled={bp['compiled']}, saved={bp['saved']})")
    if a.errors:
        print(f"\nErrors ({err}):")
        for e in a.errors[:15]:
            print(f"  {e['cmd']}: {e.get('error','')[:80]}")

    # On-disk check
    print(f"\nOn-disk verification:")
    base = "C:/Projects/BoreandStroke/Content/BlueprintLLM"
    for sub in ["Generated", "DataTables", "Materials"]:
        p = os.path.join(base, sub)
        if os.path.exists(p):
            count = len([f for f in os.listdir(p) if f.endswith('.uasset')])
            print(f"  {sub}/: {count} .uasset files")

    with open("tests/bore_and_stroke_final_build.log", "w", encoding="utf-8") as f:
        f.write(f"Bore & Stroke Final Build -- {datetime.now()}\n")
        f.write(f"Commands: {len(a.log)} OK: {ok} Errors: {err} Time: {elapsed:.1f}s\n\n")
        f.write("Blueprint Verification:\n")
        for bp in a.bp_results:
            f.write(f"  {bp['status']}: {bp['name']} ({bp['nodes']} nodes, {bp['conns']} conns)\n")
    print(f"\nLog: tests/bore_and_stroke_final_build.log")
