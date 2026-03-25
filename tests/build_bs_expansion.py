"""Bore & Stroke Expansion Build — adds missing phases to v2 build."""
import socket, json, time
from datetime import datetime

class Arcwright:
    def __init__(self):
        self.log, self.errors, self.count = [], [], 0
        self.sock = None
        self.phase_stats = {}
        self.current_phase = "init"
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
        if self.count % 25 == 0: self.reconnect()
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
        print(f"\n{'='*60}\nPHASE: {name}\n{'='*60}")
    def dt(self, table_name, struct_name, columns, rows):
        ir = {"metadata": {"table_name": table_name, "struct_name": struct_name}, "columns": columns, "rows": rows}
        return self.cmd("create_data_table", ir_json=json.dumps(ir))

a = Arcwright()
r = a.cmd("health_check")
print(f"Connected: {r.get('data',{}).get('server','?')}")

# Phase 1b: Additional Data Tables
a.phase("Phase 1b: Additional Data Tables")
a.dt("DT_InspectionTools", "InspToolStruct",
    [{"name":"ToolID","type":"Name"},{"name":"ToolName","type":"String"},{"name":"Reveals","type":"String"},{"name":"Cost","type":"Float"}],
    [{"name":"Visual","values":{"ToolID":"Visual","ToolName":"Visual Inspection","Reveals":"Cracks, damage, rust","Cost":0}},
     {"name":"BoreGauge","values":{"ToolID":"BoreGauge","ToolName":"Bore Gauge","Reveals":"Bore diameter, taper","Cost":200}},
     {"name":"DialBore","values":{"ToolID":"DialBore","ToolName":"Dial Bore Gauge","Reveals":"Bore, taper, OOR","Cost":400}},
     {"name":"Plastigage","values":{"ToolID":"Plastigage","ToolName":"Plastigage","Reveals":"Bearing clearance","Cost":10}},
     {"name":"Straightedge","values":{"ToolID":"Straightedge","ToolName":"Straightedge","Reveals":"Deck flatness","Cost":50}},
     {"name":"SurfTest","values":{"ToolID":"SurfTest","ToolName":"Surface Roughness Tester","Reveals":"RA value","Cost":2500}}])
print("  DT_InspectionTools: 6 rows")

a.dt("DT_AuctionPricing", "AuctionStruct",
    [{"name":"Family","type":"Name"},{"name":"BasePrice","type":"Float"},{"name":"Variance","type":"Float"},{"name":"RarityMult","type":"Float"}],
    [{"name":"SBC","values":{"Family":"SBC","BasePrice":800,"Variance":25,"RarityMult":1.0}},
     {"name":"BBC","values":{"Family":"BBC","BasePrice":2500,"Variance":30,"RarityMult":1.5}},
     {"name":"FE","values":{"Family":"FE","BasePrice":1500,"Variance":20,"RarityMult":1.2}},
     {"name":"Hemi","values":{"Family":"Hemi","BasePrice":10000,"Variance":40,"RarityMult":3.0}},
     {"name":"Slant6","values":{"Family":"Slant6","BasePrice":400,"Variance":15,"RarityMult":0.8}}])
print("  DT_AuctionPricing: 5 rows")

a.dt("DT_EngineConditions", "ConditionStruct",
    [{"name":"CondID","type":"Name"},{"name":"MinScore","type":"Integer"},{"name":"MaxScore","type":"Integer"},{"name":"CrackPct","type":"Float"},{"name":"Desc","type":"String"}],
    [{"name":"Excellent","values":{"CondID":"Excellent","MinScore":80,"MaxScore":100,"CrackPct":0.02,"Desc":"Near-new"}},
     {"name":"Good","values":{"CondID":"Good","MinScore":60,"MaxScore":85,"CrackPct":0.05,"Desc":"Normal wear"}},
     {"name":"Fair","values":{"CondID":"Fair","MinScore":35,"MaxScore":65,"CrackPct":0.10,"Desc":"Needs work"}},
     {"name":"Poor","values":{"CondID":"Poor","MinScore":10,"MaxScore":40,"CrackPct":0.20,"Desc":"Heavy wear"}},
     {"name":"Scrap","values":{"CondID":"Scrap","MinScore":0,"MaxScore":15,"CrackPct":0.40,"Desc":"Beyond saving"}}])
print("  DT_EngineConditions: 5 rows")

# Phase 2: Input System
a.phase("Phase 2: Input System")
for name, vtype in [("IA_Move","Axis2D"),("IA_Look","Axis2D"),("IA_Interact","Bool"),("IA_Back","Bool"),("IA_EndDay","Bool"),("IA_Storage","Bool"),("IA_Pause","Bool"),("IA_QuickSave","Bool")]:
    a.cmd("create_input_action", action_name=name, value_type=vtype)
print("  Input actions: 8")

# Phase 5: Sound Design
a.phase("Phase 5: Sound Design")
for name, vol in [("SC_ShopAmbient",1.0),("SC_StationSFX",1.0),("SC_UISounds",0.8),("SC_ActionSounds",1.0),("SC_Music",0.5)]:
    a.cmd("create_sound_class", name=name, volume=vol, pitch=1.0)
a.cmd("create_attenuation_settings", name="ATT_StationClose", inner_radius=200, outer_radius=800, falloff="Linear")
a.cmd("create_attenuation_settings", name="ATT_ShopWide", inner_radius=500, outer_radius=2000, falloff="Linear")
print("  Sound classes: 5, Attenuation: 2")

# Phase 6: Dialogue Trees (as DataTables)
a.phase("Phase 6: Dialogue Trees")
dialogues = {
    "DLG_BudgetBuyer": [("greeting","Budget Buyer","Hey, got any cheap rebuilt engines?"),("browse","Budget Buyer","What is the cheapest V8?"),("accept","Budget Buyer","Deal!"),("decline","Budget Buyer","Too rich for me.")],
    "DLG_Enthusiast": [("greeting","Enthusiast","Looking for a solid small block."),("quality","Enthusiast","What quality score?"),("accept","Enthusiast","Perfect, let us do it."),("decline","Enthusiast","Need something better.")],
    "DLG_Restorer": [("greeting","Restorer","Need a numbers-matching 327."),("specific","Restorer","1962-1967 only."),("accept","Restorer","Exactly what I need."),("decline","Restorer","Will not work.")],
    "DLG_ShadyDealer": [("greeting","???","Got engines that fell off a truck."),("offer","???","50% below market. Interested?"),("accept","???","Smart move."),("decline","???","Your loss.")],
    "DLG_PartsVendor": [("greeting","Parts Vendor","Welcome! Looking for rebuild parts?"),("browse","Parts Vendor","Budget, standard, premium, or performance?"),("purchase","Parts Vendor","Added to your inventory.")],
    "DLG_PoliceInspector": [("greeting","Inspector","Routine inspection."),("clean","Inspector","Everything in order."),("suspicious","Inspector","These serial numbers do not match.")],
    "DLG_InsuranceAdj": [("greeting","Adjuster","Investigating a stolen engine claim."),("clear","Adjuster","All checks out."),("flagged","Adjuster","This VIN is flagged.")],
    "DLG_LoanShark": [("greeting","Vinnie","Heard you are in a tight spot."),("terms","Vinnie","25% weekly. No paperwork."),("accept","Vinnie","Money is in your account."),("decline","Vinnie","Your call.")],
}
for dlg_name, nodes in dialogues.items():
    cols = [{"name":"NodeID","type":"Name"},{"name":"Speaker","type":"String"},{"name":"Text","type":"String"}]
    rows = [{"name":n[0],"values":{"NodeID":n[0],"Speaker":n[1],"Text":n[2]}} for n in nodes]
    a.dt(dlg_name, dlg_name+"Struct", cols, rows)
    print(f"  {dlg_name}: {len(nodes)} nodes")

# Phase 8b: Station Widgets
a.phase("Phase 8b: Station Widgets")
for wbp, title, desc in [
    ("WBP_StationDegriming","Degriming Station","Remove exterior grime and buildup"),
    ("WBP_StationDisassembly","Disassembly Station","Break engine down to components"),
    ("WBP_StationInspection","Inspection Station","Inspect and measure engine block"),
    ("WBP_StationCleaning","Cleaning Station","Deep clean all engine parts")]:
    a.cmd("create_widget_blueprint", name=wbp)
    a.cmd("add_widget_child", widget_blueprint=wbp, widget_type="CanvasPanel", widget_name="Root")
    a.cmd("add_widget_child", widget_blueprint=wbp, parent_widget="Root", widget_type="TextBlock", widget_name="Title")
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="Title", property="text", value=title)
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="Title", property="color", value="#E8A624")
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="Title", property="font_size", value="24")
    a.cmd("set_widget_anchor", widget_blueprint=wbp, widget_name="Title", anchor="TopLeft", offset_x=20, offset_y=15)
    a.cmd("add_widget_child", widget_blueprint=wbp, parent_widget="Root", widget_type="TextBlock", widget_name="Desc")
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="Desc", property="text", value=desc)
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="Desc", property="color", value="#E8DCC8")
    a.cmd("set_widget_anchor", widget_blueprint=wbp, widget_name="Desc", anchor="TopLeft", offset_x=20, offset_y=50)
    a.cmd("add_widget_child", widget_blueprint=wbp, parent_widget="Root", widget_type="TextBlock", widget_name="EngineLabel")
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="EngineLabel", property="text", value="No engine loaded")
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="EngineLabel", property="color", value="#808FA3")
    a.cmd("add_widget_child", widget_blueprint=wbp, parent_widget="Root", widget_type="VerticalBox", widget_name="Actions")
    a.cmd("add_widget_child", widget_blueprint=wbp, parent_widget="Root", widget_type="TextBlock", widget_name="Status")
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="Status", property="text", value="Ready")
    a.cmd("set_widget_property", widget_blueprint=wbp, widget_name="Status", property="color", value="#33D166")
    print(f"  {wbp}: created")

# Phase 9: Level Sequences
a.phase("Phase 9: Level Sequences")
a.cmd("create_sequence", name="SEQ_DayStart", duration=3.0)
a.cmd("create_sequence", name="SEQ_EngineComplete", duration=18.0)
a.cmd("create_sequence", name="SEQ_DayEnd", duration=5.0)
print("  Sequences: 3")

a.cmd("save_all")

# Report
ok = len([l for l in a.log if l["status"] == "ok"])
err = len(a.errors)
print(f"\n{'='*60}")
print(f"EXPANSION COMPLETE")
print(f"{'='*60}")
print(f"Commands: {len(a.log)} | OK: {ok} | Errors: {err}")
for ph, st in a.phase_stats.items():
    print(f"  {ph}: {st['ok']} ok, {st['err']} err")
if a.errors:
    print(f"\nErrors:")
    for e in a.errors[:20]:
        print(f"  {e['cmd']}: {e.get('error','')[:100]}")
print(f"\n{'='*60}")
print(f"COMBINED TOTALS (v2 + expansion)")
print(f"{'='*60}")
print(f"v2: 274 ok | expansion: {ok} ok | TOTAL: {274+ok} ok, {err} errors")
print(f"\nAll assets: 13 DTs, 5 tag hierarchies, 10 materials, 12 BPs (171 nodes, 135 conns),")
print(f"11 widgets, 8 dialogues, 5 sound classes, 8 input actions, 3 sequences, level built")
