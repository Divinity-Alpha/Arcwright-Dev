"""Import B&S fonts into UE, then rebuild all 13 station widgets with font references.

Step 1: import_font_family for BarlowCondensed, Barlow, ShareTechMono
Step 2: Rebuild all 13 station widgets (two-layer architecture for Bore, standard for others)
Step 3: Verify + save
"""

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


# ── Font asset paths (after import) ──────────────────────────
FC = "/Game/UI/Fonts/F_BarlowCondensed"
FB = "/Game/UI/Fonts/F_Barlow"
FM = "/Game/UI/Fonts/F_ShareTechMono"

# ── TTF source folders ────────────────────────────────────────
TTF_BASE = r"C:\Arcwright\assets\fonts"

# ── Colors (approved B&S palette) ─────────────────────────────
BG_PANEL      = "(R=0.071,G=0.086,B=0.110,A=1.0)"
BG_CARD       = "(R=0.094,G=0.114,B=0.149,A=1.0)"
C_BORDER      = "(R=0.165,G=0.188,B=0.251,A=1.0)"
ACCENT        = "(R=0.910,G=0.651,B=0.141,A=1.0)"
GREEN         = "(R=0.239,G=0.863,B=0.518,A=1.0)"
YELLOW        = "(R=0.941,G=0.753,B=0.251,A=1.0)"
RED           = "(R=0.878,G=0.251,B=0.314,A=1.0)"
TEXT_DIM      = "(R=0.439,G=0.471,B=0.533,A=1.0)"
TEXT_BRIGHT   = "(R=0.933,G=0.941,B=0.957,A=1.0)"

OVERLAY_40    = "(R=0.0,G=0.0,B=0.0,A=0.4)"
HEADER_BG     = "(R=0.0,G=0.0,B=0.0,A=0.35)"
STATUS_BG     = "(R=0.0,G=0.0,B=0.0,A=0.35)"
COST_BG       = "(R=0.0,G=0.0,B=0.0,A=0.22)"
PROG_TRACK_BG = "(R=1.0,G=1.0,B=1.0,A=0.05)"
APPROVE_BG    = "(R=0.239,G=0.863,B=0.518,A=0.10)"
CANCEL_BG     = "(R=0.878,G=0.251,B=0.314,A=0.08)"
SELECTED_BG   = "(R=0.910,G=0.651,B=0.141,A=0.05)"


# ── Widget build helpers ──────────────────────────────────────
warns = []


def sp(wbp, name, prop, val):
    r = send("set_widget_property", {
        "widget_blueprint": wbp,
        "widget_name": name,
        "property": prop,
        "value": str(val),
    })
    if r.get("status") != "ok":
        warns.append(f"{name}.{prop}")
    return r


def child(wbp, parent, wtype, wname):
    params = {
        "widget_blueprint": wbp,
        "widget_type": wtype,
        "widget_name": wname,
    }
    if parent:
        params["parent_widget"] = parent
    r = send("add_widget_child", params)
    if r.get("status") != "ok":
        print(f"    FAIL: {wtype} '{wname}' -> '{parent}': {r.get('message', '?')[:80]}")
    return r


def anchor(wbp, name, min_x, min_y, max_x, max_y):
    sp(wbp, name, "Slot.Anchors.Min.X", str(min_x))
    sp(wbp, name, "Slot.Anchors.Min.Y", str(min_y))
    sp(wbp, name, "Slot.Anchors.Max.X", str(max_x))
    sp(wbp, name, "Slot.Anchors.Max.Y", str(max_y))


def text(wbp, parent, name, content, font_family, typeface, size, color, **extra):
    child(wbp, parent, "TextBlock", name)
    sp(wbp, name, "Text", content)
    sp(wbp, name, "Font.Family", font_family)
    sp(wbp, name, "Font.Typeface", typeface)
    sp(wbp, name, "Font.Size", str(size))
    sp(wbp, name, "ColorAndOpacity", color)
    for k, v in extra.items():
        sp(wbp, name, k, str(v))


# ══════════════════════════════════════════════════════════════
# STEP 1: Import fonts
# ══════════════════════════════════════════════════════════════

def import_fonts():
    print("=" * 60)
    print("STEP 1: Import fonts into UE at /Game/UI/Fonts/")
    print("=" * 60)

    families = [
        ("BarlowCondensed", TTF_BASE + r"\BarlowCondensed"),
        ("Barlow",          TTF_BASE + r"\Barlow"),
        ("ShareTechMono",   TTF_BASE + r"\ShareTechMono"),
    ]

    results = {}
    for family_name, ttf_folder in families:
        print(f"\n  {family_name}:", flush=True)
        print(f"    Source: {ttf_folder}", flush=True)

        r = send("import_font_family", {
            "family_name": family_name,
            "ttf_folder": ttf_folder,
            "asset_path": "/Game/UI/Fonts"
        })

        if r.get("status") == "ok":
            data = r.get("data", {})
            faces = data.get("faces_imported", [])
            asset = data.get("font_asset", "?")
            print(f"    OK -> {asset}")
            for face in faces:
                print(f"      {face.get('typeface', '?')}: {face.get('asset_path', '?')}")
            results[family_name] = True
        else:
            print(f"    FAIL: {r.get('message', '?')[:80]}")
            results[family_name] = False

    # Save after all imports
    print("\n  Saving fonts...", flush=True)
    send("save_all", {})

    # Verify
    print("\n  Verifying font assets...", flush=True)
    r = send("list_font_assets", {})
    if r.get("status") == "ok":
        fonts = r.get("data", {}).get("fonts", [])
        print(f"    Found {len(fonts)} font assets:")
        for f in fonts:
            print(f"      {f.get('name', '?')}: {f.get('path', '?')}")

    return all(results.values())


# ══════════════════════════════════════════════════════════════
# STEP 2a: Build WBP_Station_Bore (two-layer architecture)
# ══════════════════════════════════════════════════════════════

def build_station_bore():
    wbp = "WBP_Station_Bore"
    print(f"\n  {wbp}: (two-layer)", flush=True)

    send("delete_blueprint", {"name": wbp})
    time.sleep(0.3)
    r = send("create_widget_blueprint", {"name": wbp, "path": "/Game/UI"})
    if r.get("status") != "ok":
        print(f"    CREATE FAILED: {r.get('message', '?')}")
        return False

    # Root canvas
    child(wbp, "", "CanvasPanel", "CanvasPanel_Root")

    # ── LAYER 1: Hidden C++ bridge (Z:0) ─────────────────────
    hidden = ["txt_Title", "txt_Desc", "txt_ItemInfo",
              "txt_ActionsHeader", "txt_Actions", "txt_Equipment", "txt_ExitHint"]
    for t in hidden:
        child(wbp, "CanvasPanel_Root", "TextBlock", t)
        sp(wbp, t, "Visibility", "Hidden")
        sp(wbp, t, "Slot.Position.X", "0")
        sp(wbp, t, "Slot.Position.Y", "0")
        sp(wbp, t, "Slot.Size.X", "1")
        sp(wbp, t, "Slot.Size.Y", "1")
        sp(wbp, t, "Slot.ZOrder", "0")

    # ── LAYER 2: Visual layout (Z:1+) ────────────────────────

    # Fullscreen overlay
    child(wbp, "CanvasPanel_Root", "Border", "Border_Overlay")
    anchor(wbp, "Border_Overlay", 0.0, 0.0, 1.0, 1.0)
    sp(wbp, "Border_Overlay", "BrushColor", OVERLAY_40)
    sp(wbp, "Border_Overlay", "Brush.DrawType", "Box")
    sp(wbp, "Border_Overlay", "Slot.ZOrder", "1")

    # Decision panel — right 35%
    child(wbp, "CanvasPanel_Root", "Border", "Border_Panel")
    anchor(wbp, "Border_Panel", 0.65, 0.0, 1.0, 1.0)
    sp(wbp, "Border_Panel", "BrushColor", BG_PANEL)
    sp(wbp, "Border_Panel", "Brush.DrawType", "Box")
    sp(wbp, "Border_Panel", "Slot.ZOrder", "2")

    child(wbp, "Border_Panel", "VerticalBox", "VBox_Main")

    # ── HEADER ────────────────────────────────────────────────
    child(wbp, "VBox_Main", "Border", "Border_Header")
    sp(wbp, "Border_Header", "BrushColor", HEADER_BG)
    sp(wbp, "Border_Header", "Brush.DrawType", "Box")
    sp(wbp, "Border_Header", "Padding", "(Left=20,Top=16,Right=20,Bottom=16)")
    sp(wbp, "Border_Header", "Slot.FillHeight", "0.0")

    child(wbp, "Border_Header", "VerticalBox", "VBox_Header")

    text(wbp, "VBox_Header", "Text_StationName", "CYLINDER BORING",
         FC, "Bold", 21, ACCENT, **{"Font.LetterSpacing": "4"})
    text(wbp, "VBox_Header", "Text_StationSub", "Station 05 \u00b7 Tier 2 Boring Bar",
         FC, "Regular", 15, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=2,Right=0,Bottom=0)"})

    # ── ENGINE BADGE ──────────────────────────────────────────
    child(wbp, "VBox_Main", "Border", "Border_Badge")
    sp(wbp, "Border_Badge", "BrushColor", BG_CARD)
    sp(wbp, "Border_Badge", "Brush.DrawType", "Box")
    sp(wbp, "Border_Badge", "Padding", "(Left=10,Top=10,Right=10,Bottom=10)")
    sp(wbp, "Border_Badge", "Slot.FillHeight", "0.0")
    sp(wbp, "Border_Badge", "Slot.Padding", "(Left=11,Top=6,Right=11,Bottom=0)")

    child(wbp, "Border_Badge", "HorizontalBox", "HBox_Badge")

    # Icon placeholder
    child(wbp, "HBox_Badge", "SizeBox", "SizeBox_BadgeIcon")
    sp(wbp, "SizeBox_BadgeIcon", "WidthOverride", "40")
    sp(wbp, "SizeBox_BadgeIcon", "HeightOverride", "40")
    child(wbp, "SizeBox_BadgeIcon", "Border", "Border_BadgeIcon")
    sp(wbp, "Border_BadgeIcon", "BrushColor", "(R=0.165,G=0.118,B=0.063,A=1.0)")
    sp(wbp, "Border_BadgeIcon", "Brush.DrawType", "Box")

    # Engine info
    child(wbp, "HBox_Badge", "VerticalBox", "VBox_BadgeInfo")
    sp(wbp, "VBox_BadgeInfo", "Slot.FillWidth", "1.0")
    sp(wbp, "VBox_BadgeInfo", "Slot.Padding", "(Left=10,Top=0,Right=10,Bottom=0)")

    text(wbp, "VBox_BadgeInfo", "Text_EngineName", "1967 Chevy 327 SBC",
         FC, "Bold", 20, TEXT_BRIGHT)
    text(wbp, "VBox_BadgeInfo", "Text_EngineSerial", "SN: E2-7740192",
         FM, "Regular", 14, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=1,Right=0,Bottom=0)"})
    text(wbp, "VBox_BadgeInfo", "Text_EngineSpecs", "V8 \u00b7 327 ci \u00b7 4-Bolt Main",
         FB, "Regular", 14, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=1,Right=0,Bottom=0)"})

    # Quality score
    child(wbp, "HBox_Badge", "VerticalBox", "VBox_QualityScore")
    sp(wbp, "VBox_QualityScore", "Slot.VAlign", "Center")

    text(wbp, "VBox_QualityScore", "Text_QualityNum", "54",
         FM, "Regular", 33, YELLOW)
    text(wbp, "VBox_QualityScore", "Text_QualityLbl", "QUALITY",
         FC, "Regular", 12, TEXT_DIM, **{"Font.LetterSpacing": "1"})

    # ── PROGRESS ──────────────────────────────────────────────
    child(wbp, "VBox_Main", "Border", "Border_Progress")
    sp(wbp, "Border_Progress", "BrushColor", BG_PANEL)
    sp(wbp, "Border_Progress", "Brush.DrawType", "Box")
    sp(wbp, "Border_Progress", "Padding", "(Left=11,Top=10,Right=11,Bottom=6)")
    sp(wbp, "Border_Progress", "Slot.FillHeight", "0.0")

    child(wbp, "Border_Progress", "VerticalBox", "VBox_Progress")

    child(wbp, "VBox_Progress", "HorizontalBox", "HBox_ProgLabels")
    text(wbp, "HBox_ProgLabels", "Text_ProgLabel", "CYLINDER PROGRESS",
         FC, "SemiBold", 14, TEXT_DIM,
         **{"Font.LetterSpacing": "2", "Slot.FillWidth": "1.0"})
    text(wbp, "HBox_ProgLabels", "Text_ProgCount", "3 / 8 Bored",
         FM, "Regular", 16, GREEN)

    # Progress bar 6px
    child(wbp, "VBox_Progress", "SizeBox", "SizeBox_ProgTrack")
    sp(wbp, "SizeBox_ProgTrack", "HeightOverride", "6")
    sp(wbp, "SizeBox_ProgTrack", "Slot.Padding", "(Left=0,Top=6,Right=0,Bottom=0)")

    child(wbp, "SizeBox_ProgTrack", "HorizontalBox", "HBox_ProgTrack")
    child(wbp, "HBox_ProgTrack", "Border", "Border_ProgFill")
    sp(wbp, "Border_ProgFill", "BrushColor", GREEN)
    sp(wbp, "Border_ProgFill", "Brush.DrawType", "Box")
    sp(wbp, "Border_ProgFill", "Slot.FillWidth", "3.0")
    child(wbp, "HBox_ProgTrack", "Border", "Border_ProgEmpty")
    sp(wbp, "Border_ProgEmpty", "BrushColor", PROG_TRACK_BG)
    sp(wbp, "Border_ProgEmpty", "Brush.DrawType", "Box")
    sp(wbp, "Border_ProgEmpty", "Slot.FillWidth", "5.0")

    # ── SECTION LABEL ─────────────────────────────────────────
    child(wbp, "VBox_Main", "Border", "Border_SectionLbl")
    sp(wbp, "Border_SectionLbl", "BrushColor", BG_PANEL)
    sp(wbp, "Border_SectionLbl", "Brush.DrawType", "Box")
    sp(wbp, "Border_SectionLbl", "Padding", "(Left=11,Top=6,Right=11,Bottom=4)")
    sp(wbp, "Border_SectionLbl", "Slot.FillHeight", "0.0")

    text(wbp, "Border_SectionLbl", "Text_SectionLabel", "AVAILABLE ACTIONS",
         FC, "SemiBold", 14, TEXT_DIM, **{"Font.LetterSpacing": "2"})

    # ── ACTION LIST ───────────────────────────────────────────
    child(wbp, "VBox_Main", "ScrollBox", "ScrollBox_Actions")
    sp(wbp, "ScrollBox_Actions", "Slot.FillHeight", "1.0")
    sp(wbp, "ScrollBox_Actions", "Slot.Padding", "(Left=11,Top=0,Right=11,Bottom=0)")

    child(wbp, "ScrollBox_Actions", "VerticalBox", "VBox_ActionList")

    actions = [
        ("Action1", 'Bore Cylinder 4 \u2014 0.030" Over',
         "45 min human  \u00b7  90 min machine  \u00b7  +6 quality pts", True, None),
        ("Action2", 'Bore Cylinder 4 \u2014 0.040" Over',
         "45 min human  \u00b7  120 min machine  \u00b7  +8 quality pts", False, None),
        ("Action3", 'Bore All Remaining \u2014 0.030"',
         "4h human  \u00b7  7.5h machine  \u00b7  +30 quality pts", False, None),
        ("Action4", "CNC Precision Bore \u2014 All Cylinders",
         "2h human  \u00b7  +48 quality pts", False,
         "Requires: CNC Boring Machine (Station Upgrade)"),
        ("Action5", "Inspect Bore Diameter After Machining",
         "20 min human  \u00b7  +2 quality pts", False, None),
    ]
    for act_id, act_name, act_meta, selected, prereq in actions:
        bn = f"Border_{act_id}"
        child(wbp, "VBox_ActionList", "Border", bn)
        sp(wbp, bn, "BrushColor", SELECTED_BG if selected else BG_CARD)
        sp(wbp, bn, "Brush.DrawType", "Box")
        sp(wbp, bn, "Padding", "(Left=14,Top=12,Right=14,Bottom=12)")
        sp(wbp, bn, "Slot.Padding", "(Left=0,Top=0,Right=0,Bottom=5)")
        vn = f"VBox_{act_id}"
        child(wbp, bn, "VerticalBox", vn)
        text(wbp, vn, f"Text_{act_id}_Name", act_name, FB, "SemiBold", 18, TEXT_BRIGHT)
        text(wbp, vn, f"Text_{act_id}_Meta", act_meta, FC, "Regular", 14, TEXT_DIM,
             **{"Slot.Padding": "(Left=0,Top=4,Right=0,Bottom=0)"})
        if prereq:
            text(wbp, vn, f"Text_{act_id}_Prereq", f"\u2715 {prereq}",
                 FC, "Regular", 14, RED,
                 **{"Slot.Padding": "(Left=0,Top=3,Right=0,Bottom=0)"})

    # ── COST DETAIL ───────────────────────────────────────────
    child(wbp, "VBox_Main", "Border", "Border_CostDetail")
    sp(wbp, "Border_CostDetail", "BrushColor", COST_BG)
    sp(wbp, "Border_CostDetail", "Brush.DrawType", "Box")
    sp(wbp, "Border_CostDetail", "Padding", "(Left=14,Top=12,Right=14,Bottom=12)")
    sp(wbp, "Border_CostDetail", "Slot.FillHeight", "0.0")
    sp(wbp, "Border_CostDetail", "Slot.Padding", "(Left=11,Top=4,Right=11,Bottom=0)")

    child(wbp, "Border_CostDetail", "VerticalBox", "VBox_Costs")

    def cost_row(rid, lbl, val, vc):
        h = f"HBox_{rid}"
        child(wbp, "VBox_Costs", "HorizontalBox", h)
        sp(wbp, h, "Slot.Padding", "(Left=0,Top=2,Right=0,Bottom=2)")
        text(wbp, h, f"Text_{rid}_Lbl", lbl, FC, "Regular", 14, TEXT_DIM,
             **{"Slot.FillWidth": "1.0"})
        text(wbp, h, f"Text_{rid}_Val", val, FM, "Regular", 16, vc)

    def cost_div(did):
        child(wbp, "VBox_Costs", "SizeBox", f"SizeBox_{did}")
        sp(wbp, f"SizeBox_{did}", "HeightOverride", "1")
        sp(wbp, f"SizeBox_{did}", "Slot.Padding", "(Left=0,Top=3,Right=0,Bottom=3)")
        child(wbp, f"SizeBox_{did}", "Border", f"Border_{did}")
        sp(wbp, f"Border_{did}", "BrushColor", C_BORDER)
        sp(wbp, f"Border_{did}", "Brush.DrawType", "Box")

    cost_row("CostHuman",   "HUMAN TIME",     "45 min",                    TEXT_BRIGHT)
    cost_row("CostMachine", "MACHINE TIME",   "90 min",                    TEXT_BRIGHT)
    cost_div("CostDiv1")
    cost_row("CostConsum",  "CONSUMABLES",    "Boring Oil \u2014 0.5 L",   YELLOW)
    cost_row("CostWear",    "EQUIPMENT WEAR", "Boring Bar \u20133%",       TEXT_DIM)
    cost_div("CostDiv2")
    cost_row("CostQuality", "QUALITY GAIN",   "+6 pts (54 \u2192 60)",     GREEN)

    # ── ACTION BUTTONS ────────────────────────────────────────
    child(wbp, "VBox_Main", "Border", "Border_BtnArea")
    sp(wbp, "Border_BtnArea", "BrushColor", BG_PANEL)
    sp(wbp, "Border_BtnArea", "Brush.DrawType", "Box")
    sp(wbp, "Border_BtnArea", "Padding", "(Left=11,Top=4,Right=11,Bottom=4)")
    sp(wbp, "Border_BtnArea", "Slot.FillHeight", "0.0")

    child(wbp, "Border_BtnArea", "HorizontalBox", "HBox_ActionBtns")

    child(wbp, "HBox_ActionBtns", "SizeBox", "SizeBox_Approve")
    sp(wbp, "SizeBox_Approve", "HeightOverride", "60")
    sp(wbp, "SizeBox_Approve", "Slot.FillWidth", "1.0")
    sp(wbp, "SizeBox_Approve", "Slot.Padding", "(Left=0,Top=0,Right=3,Bottom=0)")
    child(wbp, "SizeBox_Approve", "Border", "Border_BtnApprove")
    sp(wbp, "Border_BtnApprove", "BrushColor", APPROVE_BG)
    sp(wbp, "Border_BtnApprove", "Brush.DrawType", "Box")
    sp(wbp, "Border_BtnApprove", "HAlign", "Center")
    sp(wbp, "Border_BtnApprove", "VAlign", "Center")
    text(wbp, "Border_BtnApprove", "Text_BtnApprove", "\u2713 APPROVE",
         FC, "Bold", 18, GREEN, **{"Font.LetterSpacing": "3"})

    child(wbp, "HBox_ActionBtns", "SizeBox", "SizeBox_Cancel")
    sp(wbp, "SizeBox_Cancel", "WidthOverride", "120")
    sp(wbp, "SizeBox_Cancel", "HeightOverride", "60")
    sp(wbp, "SizeBox_Cancel", "Slot.Padding", "(Left=3,Top=0,Right=0,Bottom=0)")
    child(wbp, "SizeBox_Cancel", "Border", "Border_BtnCancel")
    sp(wbp, "Border_BtnCancel", "BrushColor", CANCEL_BG)
    sp(wbp, "Border_BtnCancel", "Brush.DrawType", "Box")
    sp(wbp, "Border_BtnCancel", "HAlign", "Center")
    sp(wbp, "Border_BtnCancel", "VAlign", "Center")
    text(wbp, "Border_BtnCancel", "Text_BtnCancel", "\u2715 CANCEL",
         FC, "Bold", 18, RED, **{"Font.LetterSpacing": "3"})

    # ── STATUS BAR ────────────────────────────────────────────
    child(wbp, "VBox_Main", "Border", "Border_StatusBar")
    sp(wbp, "Border_StatusBar", "BrushColor", STATUS_BG)
    sp(wbp, "Border_StatusBar", "Brush.DrawType", "Box")
    sp(wbp, "Border_StatusBar", "Padding", "(Left=8,Top=6,Right=8,Bottom=6)")
    sp(wbp, "Border_StatusBar", "Slot.FillHeight", "0.0")

    child(wbp, "Border_StatusBar", "HorizontalBox", "HBox_Status")

    for sid, slbl, sval, sclr in [
        ("Cash", "CASH", "$4,820", GREEN),
        ("Time", "TIME", "3h 40m", YELLOW),
        ("Bar", "BAR", "82%", GREEN),
        ("Storage", "STORAGE", "14/24", ACCENT),
    ]:
        chip = f"Border_Stat{sid}"
        child(wbp, "HBox_Status", "Border", chip)
        sp(wbp, chip, "BrushColor", BG_CARD)
        sp(wbp, chip, "Brush.DrawType", "Box")
        sp(wbp, chip, "Padding", "(Left=8,Top=5,Right=8,Bottom=5)")
        sp(wbp, chip, "Slot.FillWidth", "1.0")
        sp(wbp, chip, "Slot.Padding", "(Left=2,Top=0,Right=2,Bottom=0)")
        hbox = f"HBox_Stat{sid}"
        child(wbp, chip, "HorizontalBox", hbox)
        text(wbp, hbox, f"Text_Stat{sid}_Lbl", slbl,
             FC, "SemiBold", 12, TEXT_DIM,
             **{"Font.LetterSpacing": "1", "Slot.FillWidth": "1.0"})
        text(wbp, hbox, f"Text_Stat{sid}_Val", sval, FM, "Regular", 16, sclr)

    # Reparent
    r = send("reparent_widget_blueprint", {"name": wbp, "new_parent": "BSStationWidget"})
    rp_ok = r.get("status") == "ok"
    print(f"    Reparent: {'OK' if rp_ok else 'FAIL'}", flush=True)
    return True


# ══════════════════════════════════════════════════════════════
# STEP 2b: Build standard station widget (non-Bore)
# ══════════════════════════════════════════════════════════════

def build_standard_station(wbp, title, desc, parent_class):
    """Build a standard station widget with C++ txt_* names as visual + bridge."""

    send("delete_blueprint", {"name": wbp})
    time.sleep(0.3)
    r = send("create_widget_blueprint", {"name": wbp, "path": "/Game/UI"})
    if r.get("status") != "ok":
        print(f"    CREATE FAILED: {r.get('message', '?')}")
        return False

    child(wbp, "", "CanvasPanel", "CanvasPanel_Root")

    # Overlay
    child(wbp, "CanvasPanel_Root", "Border", "Border_Overlay")
    anchor(wbp, "Border_Overlay", 0.0, 0.0, 1.0, 1.0)
    sp(wbp, "Border_Overlay", "BrushColor", OVERLAY_40)
    sp(wbp, "Border_Overlay", "Brush.DrawType", "Box")
    sp(wbp, "Border_Overlay", "Slot.ZOrder", "0")

    # Panel
    child(wbp, "CanvasPanel_Root", "Border", "Border_Panel")
    anchor(wbp, "Border_Panel", 0.65, 0.0, 1.0, 1.0)
    sp(wbp, "Border_Panel", "BrushColor", BG_PANEL)
    sp(wbp, "Border_Panel", "Brush.DrawType", "Box")
    sp(wbp, "Border_Panel", "Slot.ZOrder", "1")

    child(wbp, "Border_Panel", "VerticalBox", "VBox_Main")

    # Header
    child(wbp, "VBox_Main", "Border", "Border_Header")
    sp(wbp, "Border_Header", "BrushColor", HEADER_BG)
    sp(wbp, "Border_Header", "Brush.DrawType", "Box")
    sp(wbp, "Border_Header", "Padding", "(Left=20,Top=16,Right=20,Bottom=16)")
    sp(wbp, "Border_Header", "Slot.FillHeight", "0.0")

    child(wbp, "Border_Header", "VerticalBox", "VBox_Header")

    text(wbp, "VBox_Header", "txt_Title", title,
         FC, "Bold", 21, ACCENT, **{"Font.LetterSpacing": "4"})
    text(wbp, "VBox_Header", "txt_Desc", desc,
         FC, "Regular", 15, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=4,Right=0,Bottom=0)"})

    # Content area
    child(wbp, "VBox_Main", "Border", "Border_Content")
    sp(wbp, "Border_Content", "BrushColor", BG_PANEL)
    sp(wbp, "Border_Content", "Brush.DrawType", "Box")
    sp(wbp, "Border_Content", "Padding", "(Left=20,Top=16,Right=20,Bottom=16)")
    sp(wbp, "Border_Content", "Slot.FillHeight", "1.0")

    child(wbp, "Border_Content", "VerticalBox", "VBox_Content")

    text(wbp, "VBox_Content", "txt_ItemInfo", "",
         FB, "Regular", 18, TEXT_BRIGHT,
         **{"AutoWrapText": "true", "Slot.Padding": "(Left=0,Top=0,Right=0,Bottom=12)"})

    text(wbp, "VBox_Content", "txt_ActionsHeader", "AVAILABLE ACTIONS",
         FC, "SemiBold", 14, TEXT_DIM,
         **{"Font.LetterSpacing": "2", "Slot.Padding": "(Left=0,Top=0,Right=0,Bottom=8)"})

    text(wbp, "VBox_Content", "txt_Actions", "",
         FB, "Regular", 18, YELLOW,
         **{"AutoWrapText": "true", "Slot.FillHeight": "1.0"})

    text(wbp, "VBox_Content", "txt_Equipment", "",
         FC, "Regular", 15, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=10,Right=0,Bottom=0)"})

    # Status bar
    child(wbp, "VBox_Main", "Border", "Border_StatusBar")
    sp(wbp, "Border_StatusBar", "BrushColor", STATUS_BG)
    sp(wbp, "Border_StatusBar", "Brush.DrawType", "Box")
    sp(wbp, "Border_StatusBar", "Padding", "(Left=20,Top=14,Right=20,Bottom=14)")
    sp(wbp, "Border_StatusBar", "Slot.FillHeight", "0.0")

    text(wbp, "Border_StatusBar", "txt_ExitHint", "Press Q to exit",
         FC, "Regular", 16, TEXT_DIM)

    # Reparent
    r = send("reparent_widget_blueprint", {"name": wbp, "new_parent": parent_class})
    rp_ok = r.get("status") == "ok"
    if not rp_ok:
        print(f"    Reparent FAIL: {r.get('message', '?')[:60]}")
    return True


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

STATIONS = [
    ("WBP_Station_Office",       "FRONT OFFICE",     "Orders, Finance & Reputation",                "BSOfficeWidget"),
    ("WBP_Station_Disassembly",  "DISASSEMBLY",      "Station 02 \u00b7 Break Down to Components",  "BSStationWidget"),
    ("WBP_Station_Cleaning",     "CLEANING",          "Station 04 \u00b7 Deep Clean All Parts",      "BSStationWidget"),
    ("WBP_Station_Inspection",   "BLOCK INSPECTION",  "Station 03 \u00b7 Measure & Assess Condition","BSInspectionWidget"),
    ("WBP_Station_Bore",         "CYLINDER BORING",   "Station 05 \u00b7 Bore to Oversize",          "BSStationWidget"),
    ("WBP_Station_Hone",         "CYLINDER HONING",   "Station 06 \u00b7 Hone for Cross-Hatch",      "BSStationWidget"),
    ("WBP_Station_Deck",         "SURFACE GRINDING",  "Station 09 \u00b7 Deck & Head Surfaces",      "BSStationWidget"),
    ("WBP_Station_CrankGrind",   "CRANK INSPECTION",  "Station 07 \u00b7 Measure Journals & Runout", "BSStationWidget"),
    ("WBP_Station_HeadWork",     "CYLINDER HEADS",    "Station 08 \u00b7 Valve Seats & Guides",      "BSStationWidget"),
    ("WBP_Station_ValveWork",    "VALVE WORK",        "Station 08b \u00b7 Valve Lapping & Seating",  "BSStationWidget"),
    ("WBP_Station_Assembly",     "ASSEMBLY",          "Station 11 \u00b7 Assemble with Torque Specs","BSStationWidget"),
    ("WBP_Station_Balancing",    "BALANCING",         "Station 10 \u00b7 Rotating Assembly Balance", "BSStationWidget"),
    ("WBP_Station_Testing",      "TESTING",           "Station 12 \u00b7 Test Engine Performance",   "BSStationWidget"),
]


if __name__ == "__main__":
    # Step 1: Import fonts
    fonts_ok = import_fonts()
    if not fonts_ok:
        print("\nWARNING: Font import had failures — continuing with widget build anyway\n")

    # Step 2: Rebuild all 13 station widgets
    print("\n" + "=" * 60)
    print("STEP 2: Rebuild all 13 station widgets")
    print("=" * 60)

    results = {}
    for wbp_name, title, desc, parent in STATIONS:
        print(f"\n  {wbp_name}:", flush=True)
        if wbp_name == "WBP_Station_Bore":
            ok = build_station_bore()
        else:
            ok = build_standard_station(wbp_name, title, desc, parent)
        results[wbp_name] = ok
        status = "OK" if ok else "FAIL"
        print(f"    -> {status}", flush=True)

    # Step 3: Save all
    print("\n" + "=" * 60)
    print("STEP 3: Save & Verify")
    print("=" * 60)

    print("\n  Saving all...", flush=True)
    r = send("save_all", {})
    print(f"  save_all: {r.get('status')}")

    # Compile WBP_Station_Bore
    print("\n  Compiling WBP_Station_Bore...", flush=True)
    r = send("compile_blueprint", {"name": "WBP_Station_Bore"})
    print(f"  compile: {r.get('status')} - {r.get('data', {}).get('compiled', '?')}")

    # Verify Bore widget tree
    print("\n  WBP_Station_Bore widget tree:", flush=True)
    r = send("get_widget_tree", {"widget_blueprint": "WBP_Station_Bore"})
    total = r.get("data", {}).get("total_widgets", 0)
    tree = r.get("data", {}).get("tree", [])

    def find_txt(nodes, found):
        for n in nodes:
            nm = n.get("name", "")
            if nm.startswith("txt_"):
                found.append(nm)
            find_txt(n.get("children", []), found)

    found = []
    find_txt(tree, found)
    required = {"txt_Title", "txt_Desc", "txt_ItemInfo", "txt_ActionsHeader",
                "txt_Actions", "txt_Equipment", "txt_ExitHint"}
    missing = required - set(found)
    print(f"    Total widgets: {total}")
    if missing:
        print(f"    MISSING bridge: {missing}")
    else:
        print(f"    All 7 txt_* bridge widgets present")

    # Check font warnings
    print("\n  Checking message log for font issues...", flush=True)
    r = send("get_message_log", {"filter": "Font"})
    msgs = r.get("data", {}).get("messages", [])
    if msgs:
        print(f"    {len(msgs)} font-related messages:")
        for m in msgs[:5]:
            print(f"      {m.get('text', '?')[:100]}")
    else:
        print(f"    No font warnings in log")

    # Property warnings
    if warns:
        # Filter out expected font warnings if fonts imported OK
        non_font = [w for w in warns if "Font.Family" not in w]
        font_warns = [w for w in warns if "Font.Family" in w]
        if font_warns:
            print(f"\n  Font.Family warnings: {len(font_warns)}")
        if non_font:
            print(f"  Other warnings ({len(non_font)}):")
            for w in non_font[:10]:
                print(f"    {w}")
    else:
        print(f"\n  No property warnings!")

    # Summary
    ok_count = sum(results.values())
    print(f"\n{'=' * 60}")
    print(f"DONE: {ok_count}/{len(results)} widgets built")
    print("=" * 60)
    for wn, ok in results.items():
        print(f"  {'OK' if ok else 'FAIL'}  {wn}")
