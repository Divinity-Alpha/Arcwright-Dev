"""Build styled station widgets in BoreAndStroke — 1920x1080 canvas version."""
import socket
import json
import time
import sys


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


def prop(wb, name, property_name, value):
    """Set a widget property. Returns True on success."""
    r = send("set_widget_property", {
        "widget_blueprint": wb,
        "widget_name": name,
        "property": property_name,
        "value": value,
    })
    if r.get("status") != "ok":
        print(f"    WARN: {name}.{property_name} = {value!r} -> {r.get('message', '?')[:80]}")
        return False
    return True


def add(wb, widget_type, name, parent=None):
    """Add a child widget. Returns True on success."""
    params = {
        "widget_blueprint": wb,
        "widget_type": widget_type,
        "widget_name": name,
    }
    if parent:
        params["parent_widget"] = parent
    r = send("add_widget_child", params)
    if r.get("status") != "ok":
        print(f"    FAIL: add {widget_type} '{name}' to '{parent}' -> {r.get('message', '?')[:80]}")
        return False
    return True


# ── Colors (exact from spec — unchanged) ─────────────────────────
C_PANEL_BG    = "(R=0.038,G=0.047,B=0.059,A=1.0)"
C_HEADER_BG   = "(R=0.0,G=0.0,B=0.0,A=0.35)"
C_CONTENT_BG  = "(R=0.071,G=0.086,B=0.110,A=1.0)"
C_STATUS_BG   = "(R=0.0,G=0.0,B=0.0,A=0.45)"
C_AMBER       = "(R=0.910,G=0.647,B=0.141,A=1.0)"
C_DIM         = "(R=0.439,G=0.471,B=0.533,A=1.0)"
C_BRIGHT      = "(R=0.816,G=0.831,B=0.863,A=1.0)"
C_ACTION      = "(R=0.941,G=0.753,B=0.251,A=1.0)"


def build_station(wb, title, desc):
    """Delete and rebuild one station widget at 1920x1080."""

    # 1. Delete existing
    send("delete_blueprint", {"name": wb})
    time.sleep(0.3)

    # 2. Create fresh widget at /Game/UI/
    r = send("create_widget_blueprint", {"name": wb, "path": "/Game/UI"})
    if r.get("status") != "ok":
        print(f"  CREATE FAILED: {r.get('message', '?')}")
        return False

    # ── Root CanvasPanel (required for absolute positioning) ──
    add(wb, "CanvasPanel", "RootCanvas")

    # ── Border_Panel (right-side panel: x:1248 y:0 w:672 h:1080) ──
    add(wb, "Border", "Border_Panel", "RootCanvas")
    prop(wb, "Border_Panel", "BrushColor", C_PANEL_BG)
    prop(wb, "Border_Panel", "Brush.DrawType", "Box")
    # Absolute positioning — anchors pinned to top-left
    prop(wb, "Border_Panel", "Slot.Anchors.Min.X", "0.0")
    prop(wb, "Border_Panel", "Slot.Anchors.Min.Y", "0.0")
    prop(wb, "Border_Panel", "Slot.Anchors.Max.X", "0.0")
    prop(wb, "Border_Panel", "Slot.Anchors.Max.Y", "0.0")
    # Position and size at 1920x1080
    prop(wb, "Border_Panel", "Slot.Position.X", "1248")
    prop(wb, "Border_Panel", "Slot.Position.Y", "0")
    prop(wb, "Border_Panel", "Slot.Size.X", "672")
    prop(wb, "Border_Panel", "Slot.Size.Y", "1080")

    # ── VBox_Main (inside Border_Panel) ──
    add(wb, "VerticalBox", "VBox_Main", "Border_Panel")

    # ══════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════
    add(wb, "Border", "Border_Header", "VBox_Main")
    prop(wb, "Border_Header", "BrushColor", C_HEADER_BG)
    prop(wb, "Border_Header", "Brush.DrawType", "Box")
    prop(wb, "Border_Header", "Padding", "(Left=24,Top=20,Right=24,Bottom=20)")
    prop(wb, "Border_Header", "HAlign", "Fill")
    prop(wb, "Border_Header", "VAlign", "Fill")
    prop(wb, "Border_Header", "Slot.FillHeight", "0.0")

    add(wb, "VerticalBox", "VBox_Header", "Border_Header")

    # txt_Title — Font.Size: 14 (halved from 28)
    add(wb, "TextBlock", "txt_Title", "VBox_Header")
    prop(wb, "txt_Title", "Text", title)
    prop(wb, "txt_Title", "Font.Size", "14")
    prop(wb, "txt_Title", "Font.LetterSpacing", "4")
    prop(wb, "txt_Title", "ColorAndOpacity", C_AMBER)

    # txt_Desc — Font.Size: 9 (halved from 18)
    add(wb, "TextBlock", "txt_Desc", "VBox_Header")
    prop(wb, "txt_Desc", "Text", desc)
    prop(wb, "txt_Desc", "Font.Size", "9")
    prop(wb, "txt_Desc", "ColorAndOpacity", C_DIM)
    prop(wb, "txt_Desc", "Slot.Padding", "(Left=0,Top=4,Right=0,Bottom=0)")

    # ══════════════════════════════════════════════════════════════
    # CONTENT (fills remaining vertical space)
    # ══════════════════════════════════════════════════════════════
    add(wb, "Border", "Border_Content", "VBox_Main")
    prop(wb, "Border_Content", "BrushColor", C_CONTENT_BG)
    prop(wb, "Border_Content", "Brush.DrawType", "Box")
    prop(wb, "Border_Content", "Padding", "(Left=24,Top=20,Right=24,Bottom=20)")
    prop(wb, "Border_Content", "HAlign", "Fill")
    prop(wb, "Border_Content", "VAlign", "Fill")
    prop(wb, "Border_Content", "Slot.FillHeight", "1.0")

    add(wb, "VerticalBox", "VBox_Content", "Border_Content")

    # txt_ItemInfo — Font.Size: 10 (halved from 20)
    add(wb, "TextBlock", "txt_ItemInfo", "VBox_Content")
    prop(wb, "txt_ItemInfo", "Text", "")
    prop(wb, "txt_ItemInfo", "Font.Size", "10")
    prop(wb, "txt_ItemInfo", "ColorAndOpacity", C_BRIGHT)
    prop(wb, "txt_ItemInfo", "AutoWrapText", "true")
    prop(wb, "txt_ItemInfo", "Slot.Padding", "(Left=0,Top=0,Right=0,Bottom=16)")

    # txt_ActionsHeader — Font.Size: 8 (halved from 16)
    add(wb, "TextBlock", "txt_ActionsHeader", "VBox_Content")
    prop(wb, "txt_ActionsHeader", "Text", "AVAILABLE ACTIONS")
    prop(wb, "txt_ActionsHeader", "Font.Size", "8")
    prop(wb, "txt_ActionsHeader", "Font.LetterSpacing", "3")
    prop(wb, "txt_ActionsHeader", "ColorAndOpacity", C_DIM)
    prop(wb, "txt_ActionsHeader", "Slot.Padding", "(Left=0,Top=0,Right=0,Bottom=8)")

    # txt_Actions — Font.Size: 10 (halved from 20)
    add(wb, "TextBlock", "txt_Actions", "VBox_Content")
    prop(wb, "txt_Actions", "Text", "")
    prop(wb, "txt_Actions", "Font.Size", "10")
    prop(wb, "txt_Actions", "ColorAndOpacity", C_ACTION)
    prop(wb, "txt_Actions", "AutoWrapText", "true")
    prop(wb, "txt_Actions", "Slot.FillHeight", "1.0")

    # txt_Equipment — Font.Size: 9 (halved from 18)
    add(wb, "TextBlock", "txt_Equipment", "VBox_Content")
    prop(wb, "txt_Equipment", "Text", "")
    prop(wb, "txt_Equipment", "Font.Size", "9")
    prop(wb, "txt_Equipment", "ColorAndOpacity", C_DIM)
    prop(wb, "txt_Equipment", "Slot.Padding", "(Left=0,Top=12,Right=0,Bottom=0)")

    # ══════════════════════════════════════════════════════════════
    # STATUS BAR
    # ══════════════════════════════════════════════════════════════
    add(wb, "Border", "Border_StatusBar", "VBox_Main")
    prop(wb, "Border_StatusBar", "BrushColor", C_STATUS_BG)
    prop(wb, "Border_StatusBar", "Brush.DrawType", "Box")
    prop(wb, "Border_StatusBar", "Padding", "(Left=24,Top=16,Right=24,Bottom=16)")
    prop(wb, "Border_StatusBar", "HAlign", "Fill")
    prop(wb, "Border_StatusBar", "VAlign", "Fill")
    prop(wb, "Border_StatusBar", "Slot.FillHeight", "0.0")

    # txt_ExitHint — Font.Size: 8 (halved from 16)
    add(wb, "TextBlock", "txt_ExitHint", "Border_StatusBar")
    prop(wb, "txt_ExitHint", "Text", "Press Q to exit")
    prop(wb, "txt_ExitHint", "Font.Size", "8")
    prop(wb, "txt_ExitHint", "ColorAndOpacity", C_DIM)

    return True


# ══════════════════════════════════════════════════════════════════
#  STATION DEFINITIONS
# ══════════════════════════════════════════════════════════════════
STATIONS = [
    ("WBP_Station_Office",       "FRONT OFFICE",     "Orders, Finance & Reputation"),
    ("WBP_Station_Disassembly",  "DISASSEMBLY",      "Station 02 \u00b7 Break Down to Components"),
    ("WBP_Station_Cleaning",     "CLEANING",          "Station 04 \u00b7 Deep Clean All Parts"),
    ("WBP_Station_Inspection",   "BLOCK INSPECTION",  "Station 03 \u00b7 Measure & Assess Condition"),
    ("WBP_Station_Bore",         "CYLINDER BORING",   "Station 05 \u00b7 Bore to Oversize"),
    ("WBP_Station_Hone",         "CYLINDER HONING",   "Station 06 \u00b7 Hone for Cross-Hatch"),
    ("WBP_Station_Deck",         "SURFACE GRINDING",  "Station 09 \u00b7 Deck & Head Surfaces"),
    ("WBP_Station_CrankGrind",   "CRANK INSPECTION",  "Station 07 \u00b7 Measure Journals & Runout"),
    ("WBP_Station_HeadWork",     "CYLINDER HEADS",    "Station 08 \u00b7 Valve Seats & Guides"),
    ("WBP_Station_ValveWork",    "VALVE WORK",        "Station 08b \u00b7 Valve Lapping & Seating"),
    ("WBP_Station_Assembly",     "ASSEMBLY",          "Station 11 \u00b7 Assemble with Torque Specs"),
    ("WBP_Station_Balancing",    "BALANCING",         "Station 10 \u00b7 Rotating Assembly Balance"),
    ("WBP_Station_Testing",      "TESTING",           "Station 12 \u00b7 Test Engine Performance"),
]

# Reparent targets
REPARENT = {
    "WBP_Station_Inspection": "BSInspectionWidget",
    "WBP_Station_Office":     "BSOfficeWidget",
}
DEFAULT_PARENT = "BSStationWidget"


if __name__ == "__main__":
    print(f"=== Building {len(STATIONS)} station widgets (1080p) ===\n")

    results = {}
    for wb, title, desc in STATIONS:
        print(f"{wb}:", flush=True)
        ok = build_station(wb, title, desc)
        results[wb] = ok
        print(f"  -> {'OK' if ok else 'FAIL'}")

    # Reparent
    print("\n=== Reparenting ===")
    for wb, _, _ in STATIONS:
        if not results.get(wb):
            continue
        target = REPARENT.get(wb, DEFAULT_PARENT)
        r = send("reparent_widget_blueprint", {"name": wb, "new_parent": target})
        if r.get("status") == "ok":
            old = r["data"].get("old_parent", "?")
            new = r["data"].get("new_parent", "?")
            print(f"  {wb}: {old} -> {new}")
        else:
            print(f"  {wb}: FAIL - {r.get('message', '?')[:60]}")

    # Save
    print("\n=== Saving ===")
    r = send("save_all", {})
    print(f"save_all: {r.get('status')}")

    # Summary
    ok_count = sum(results.values())
    print(f"\n=== {ok_count}/{len(results)} widgets built (1080p) ===")
    for wb, ok in results.items():
        print(f"  {'OK' if ok else 'FAIL'}  {wb}")
