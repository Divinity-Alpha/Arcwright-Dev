"""Build all 13 BoreAndStroke station widgets — approved 1080p design spec.

Layout: Dark overlay (anchor 0,0->1,1) + right-35% panel (anchor 0.65,0->1,1)
Fonts: BarlowCondensed, Barlow, ShareTechMono with typeface variants
Colors: Approved B&S palette (bg-deep, bg-panel, accent, etc.)
C++ required names: txt_Title, txt_Desc, txt_ItemInfo, txt_ActionsHeader,
                    txt_Actions, txt_Equipment, txt_ExitHint
"""
import socket
import json
import time


def send(cmd, params=None):
    if params is None:
        params = {}
    s = socket.socket()
    s.settimeout(30)
    s.connect(("localhost", 13377))
    s.send((json.dumps({"command": cmd, "params": params}) + "\n").encode())
    resp = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        resp += chunk
        if b"\n" in resp:
            break
    s.close()
    return json.loads(resp.decode().strip())


# ── Font paths ────────────────────────────────────────────────────
FC = "/Game/UI/Fonts/F_BarlowCondensed"
FB = "/Game/UI/Fonts/F_Barlow"
FM = "/Game/UI/Fonts/F_ShareTechMono"

# ── Colors (approved B&S palette) ─────────────────────────────────
BG_PANEL   = "(R=0.071,G=0.086,B=0.110,A=1.0)"
OVERLAY40  = "(R=0.0,G=0.0,B=0.0,A=0.4)"
OVERLAY35  = "(R=0.0,G=0.0,B=0.0,A=0.35)"
ACCENT     = "(R=0.910,G=0.647,B=0.141,A=1.0)"
YELLOW     = "(R=0.941,G=0.753,B=0.251,A=1.0)"
DIM        = "(R=0.439,G=0.471,B=0.533,A=1.0)"
BRIGHT     = "(R=0.933,G=0.941,B=0.957,A=1.0)"

# Widget path
WIDGET_PATH = "/Game/UI"


def build_station_widget(widget_name, title, desc, parent_class):
    """Build one station widget per approved 1080p spec."""
    wbp = widget_name
    warns = []

    def sp(wn, prop, val):
        r = send("set_widget_property", {
            "widget_blueprint": wbp,
            "widget_name": wn,
            "property": prop,
            "value": str(val),
        })
        if r.get("status") != "ok":
            warns.append(f"{wn}.{prop}")
        return r

    def child(parent, wtype, wname):
        params = {
            "widget_blueprint": wbp,
            "widget_type": wtype,
            "widget_name": wname,
        }
        if parent:
            params["parent_widget"] = parent
        return send("add_widget_child", params)

    # ── Create WBP ──────────────────────────────────────────
    send("delete_blueprint", {"name": wbp})
    time.sleep(0.3)
    result = send("create_widget_blueprint", {"name": wbp, "path": WIDGET_PATH})
    if result.get("status") != "ok":
        print(f"  CREATE FAILED: {result.get('message', '?')}")
        return False

    # ── Canvas root ─────────────────────────────────────────
    child("", "CanvasPanel", "CanvasPanel_Root")

    # ── Full screen dark overlay (anchor 0,0 → 1,1) ────────
    child("CanvasPanel_Root", "Border", "Border_Overlay")
    sp("Border_Overlay", "Slot.Anchors.Min.X", "0.0")
    sp("Border_Overlay", "Slot.Anchors.Min.Y", "0.0")
    sp("Border_Overlay", "Slot.Anchors.Max.X", "1.0")
    sp("Border_Overlay", "Slot.Anchors.Max.Y", "1.0")
    sp("Border_Overlay", "Slot.ZOrder", "0")
    sp("Border_Overlay", "BrushColor", OVERLAY40)
    sp("Border_Overlay", "Brush.DrawType", "Box")

    # ── Station panel — right 35% (anchor 0.65,0 → 1,1) ────
    child("CanvasPanel_Root", "Border", "Border_Panel")
    sp("Border_Panel", "Slot.Anchors.Min.X", "0.65")
    sp("Border_Panel", "Slot.Anchors.Min.Y", "0.0")
    sp("Border_Panel", "Slot.Anchors.Max.X", "1.0")
    sp("Border_Panel", "Slot.Anchors.Max.Y", "1.0")
    sp("Border_Panel", "Slot.ZOrder", "1")
    sp("Border_Panel", "BrushColor", BG_PANEL)
    sp("Border_Panel", "Brush.DrawType", "Box")
    sp("Border_Panel", "HAlign", "Fill")
    sp("Border_Panel", "VAlign", "Fill")

    # ── VBox_Main fills the panel ───────────────────────────
    child("Border_Panel", "VerticalBox", "VBox_Main")

    # ── HEADER (FillHeight=0) ───────────────────────────────
    child("VBox_Main", "Border", "Border_Header")
    sp("Border_Header", "BrushColor", OVERLAY35)
    sp("Border_Header", "Brush.DrawType", "Box")
    sp("Border_Header", "Padding", "(Left=20,Top=16,Right=20,Bottom=16)")
    sp("Border_Header", "HAlign", "Fill")
    sp("Border_Header", "VAlign", "Fill")
    sp("Border_Header", "Slot.FillHeight", "0.0")

    child("Border_Header", "VerticalBox", "VBox_Header")

    # txt_Title — C++ required
    child("VBox_Header", "TextBlock", "txt_Title")
    sp("txt_Title", "Text", title)
    sp("txt_Title", "Font.Family", FC)
    sp("txt_Title", "Font.Typeface", "Bold")
    sp("txt_Title", "Font.Size", "21")
    sp("txt_Title", "Font.LetterSpacing", "4")
    sp("txt_Title", "ColorAndOpacity", ACCENT)

    # txt_Desc — C++ required
    child("VBox_Header", "TextBlock", "txt_Desc")
    sp("txt_Desc", "Text", desc)
    sp("txt_Desc", "Font.Family", FC)
    sp("txt_Desc", "Font.Typeface", "Regular")
    sp("txt_Desc", "Font.Size", "15")
    sp("txt_Desc", "ColorAndOpacity", DIM)
    sp("txt_Desc", "Slot.Padding", "(Left=0,Top=4,Right=0,Bottom=0)")

    # ── CONTENT AREA (FillHeight=1) ─────────────────────────
    child("VBox_Main", "Border", "Border_Content")
    sp("Border_Content", "BrushColor", BG_PANEL)
    sp("Border_Content", "Brush.DrawType", "Box")
    sp("Border_Content", "Padding", "(Left=20,Top=16,Right=20,Bottom=16)")
    sp("Border_Content", "HAlign", "Fill")
    sp("Border_Content", "VAlign", "Fill")
    sp("Border_Content", "Slot.FillHeight", "1.0")

    child("Border_Content", "VerticalBox", "VBox_Content")

    # txt_ItemInfo — C++ required
    child("VBox_Content", "TextBlock", "txt_ItemInfo")
    sp("txt_ItemInfo", "Text", "")
    sp("txt_ItemInfo", "Font.Family", FB)
    sp("txt_ItemInfo", "Font.Typeface", "Regular")
    sp("txt_ItemInfo", "Font.Size", "18")
    sp("txt_ItemInfo", "ColorAndOpacity", BRIGHT)
    sp("txt_ItemInfo", "AutoWrapText", "true")
    sp("txt_ItemInfo", "Slot.Padding", "(Left=0,Top=0,Right=0,Bottom=12)")

    # txt_ActionsHeader — C++ required
    child("VBox_Content", "TextBlock", "txt_ActionsHeader")
    sp("txt_ActionsHeader", "Text", "AVAILABLE ACTIONS")
    sp("txt_ActionsHeader", "Font.Family", FC)
    sp("txt_ActionsHeader", "Font.Typeface", "SemiBold")
    sp("txt_ActionsHeader", "Font.Size", "14")
    sp("txt_ActionsHeader", "Font.LetterSpacing", "2")
    sp("txt_ActionsHeader", "ColorAndOpacity", DIM)
    sp("txt_ActionsHeader", "Slot.Padding", "(Left=0,Top=0,Right=0,Bottom=8)")

    # txt_Actions — C++ required (fills remaining space)
    child("VBox_Content", "TextBlock", "txt_Actions")
    sp("txt_Actions", "Text", "")
    sp("txt_Actions", "Font.Family", FB)
    sp("txt_Actions", "Font.Typeface", "Regular")
    sp("txt_Actions", "Font.Size", "18")
    sp("txt_Actions", "ColorAndOpacity", YELLOW)
    sp("txt_Actions", "AutoWrapText", "true")
    sp("txt_Actions", "Slot.FillHeight", "1.0")

    # txt_Equipment — C++ required
    child("VBox_Content", "TextBlock", "txt_Equipment")
    sp("txt_Equipment", "Text", "")
    sp("txt_Equipment", "Font.Family", FC)
    sp("txt_Equipment", "Font.Typeface", "Regular")
    sp("txt_Equipment", "Font.Size", "15")
    sp("txt_Equipment", "ColorAndOpacity", DIM)
    sp("txt_Equipment", "Slot.Padding", "(Left=0,Top=10,Right=0,Bottom=0)")

    # ── STATUS BAR (FillHeight=0) ───────────────────────────
    child("VBox_Main", "Border", "Border_StatusBar")
    sp("Border_StatusBar", "BrushColor", OVERLAY35)
    sp("Border_StatusBar", "Brush.DrawType", "Box")
    sp("Border_StatusBar", "Padding", "(Left=20,Top=14,Right=20,Bottom=14)")
    sp("Border_StatusBar", "HAlign", "Fill")
    sp("Border_StatusBar", "VAlign", "Fill")
    sp("Border_StatusBar", "Slot.FillHeight", "0.0")

    # txt_ExitHint — C++ required
    child("Border_StatusBar", "TextBlock", "txt_ExitHint")
    sp("txt_ExitHint", "Text", "Press Q to exit")
    sp("txt_ExitHint", "Font.Family", FC)
    sp("txt_ExitHint", "Font.Typeface", "Regular")
    sp("txt_ExitHint", "Font.Size", "16")
    sp("txt_ExitHint", "ColorAndOpacity", DIM)

    # ── Reparent to correct C++ base ────────────────────────
    result = send("reparent_widget_blueprint", {
        "name": wbp,
        "new_parent": parent_class
    })
    reparent_ok = result.get("status") == "ok"

    if warns:
        print(f"  WARNS ({len(warns)}): {', '.join(warns[:5])}")
    if not reparent_ok:
        print(f"  Reparent FAILED: {result.get('message', '?')[:60]}")
    else:
        print(f"  OK -> {parent_class}")

    return True  # Widget created even if some props warned


# ── All 13 stations ──────────────────────────────────────────
STATIONS = [
    ("WBP_Station_Office",       "FRONT OFFICE",     "Orders, Finance & Reputation",             "BSOfficeWidget"),
    ("WBP_Station_Disassembly",  "DISASSEMBLY",      "Station 02 \u00b7 Break Down to Components", "BSStationWidget"),
    ("WBP_Station_Cleaning",     "CLEANING",          "Station 04 \u00b7 Deep Clean All Parts",     "BSStationWidget"),
    ("WBP_Station_Inspection",   "BLOCK INSPECTION",  "Station 03 \u00b7 Measure & Assess Condition","BSInspectionWidget"),
    ("WBP_Station_Bore",         "CYLINDER BORING",   "Station 05 \u00b7 Bore to Oversize",         "BSStationWidget"),
    ("WBP_Station_Hone",         "CYLINDER HONING",   "Station 06 \u00b7 Hone for Cross-Hatch",     "BSStationWidget"),
    ("WBP_Station_Deck",         "SURFACE GRINDING",  "Station 09 \u00b7 Deck & Head Surfaces",     "BSStationWidget"),
    ("WBP_Station_CrankGrind",   "CRANK INSPECTION",  "Station 07 \u00b7 Measure Journals & Runout","BSStationWidget"),
    ("WBP_Station_HeadWork",     "CYLINDER HEADS",    "Station 08 \u00b7 Valve Seats & Guides",     "BSStationWidget"),
    ("WBP_Station_ValveWork",    "VALVE WORK",        "Station 08b \u00b7 Valve Lapping & Seating", "BSStationWidget"),
    ("WBP_Station_Assembly",     "ASSEMBLY",          "Station 11 \u00b7 Assemble with Torque Specs","BSStationWidget"),
    ("WBP_Station_Balancing",    "BALANCING",         "Station 10 \u00b7 Rotating Assembly Balance", "BSStationWidget"),
    ("WBP_Station_Testing",      "TESTING",           "Station 12 \u00b7 Test Engine Performance",   "BSStationWidget"),
]


if __name__ == "__main__":
    print(f"=== Building {len(STATIONS)} station widgets (approved 1080p spec) ===\n")

    results = {}
    for wbp, title, desc, parent in STATIONS:
        print(f"{wbp}:")
        ok = build_station_widget(wbp, title, desc, parent)
        results[wbp] = ok

    # Save
    print("\n=== Saving ===")
    r = send("save_all", {})
    print(f"save_all: {r.get('status')}")

    # Verify widget tree for first widget
    print("\n=== Verification: WBP_Station_Bore widget tree ===")
    r = send("get_widget_tree", {"widget_blueprint": "WBP_Station_Bore"})
    tree = r.get("data", {}).get("tree", [])
    total = r.get("data", {}).get("total_widgets", 0)
    print(f"Total widgets: {total}")

    # Check all 7 required txt_* names
    def find_names(nodes, found):
        for n in nodes:
            name = n.get("name", "")
            if name.startswith("txt_"):
                found.append(name)
            find_names(n.get("children", []), found)

    found_txt = []
    find_names(tree, found_txt)
    required = {"txt_Title", "txt_Desc", "txt_ItemInfo", "txt_ActionsHeader",
                "txt_Actions", "txt_Equipment", "txt_ExitHint"}
    missing = required - set(found_txt)
    print(f"txt_* widgets found: {found_txt}")
    if missing:
        print(f"MISSING: {missing}")
    else:
        print("All 7 required txt_* names present!")

    # Summary
    ok_count = sum(results.values())
    print(f"\n=== {ok_count}/{len(results)} widgets built ===")
    for wb, ok in results.items():
        print(f"  {'OK' if ok else 'FAIL'}  {wb}")
