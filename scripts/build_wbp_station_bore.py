"""Rebuild WBP_Station_Bore — two-layer architecture matching approved 1080p HTML spec.

Layer 1: 7 hidden TextBlocks for C++ data binding (Z:0)
Layer 2: Full visual layout matching bore_and_stroke_huds_1080p_large.html Station View (Z:1+)

Source spec: C:/Projects/claude-bridge/bore_and_stroke_huds_1080p_large.html
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


# ── Constants ──────────────────────────────────────────────────

WBP = "WBP_Station_Bore"
warns = []

# Colors matching CSS :root from bore_and_stroke_huds_1080p_large.html
BG_PANEL      = "(R=0.071,G=0.086,B=0.110,A=1.0)"      # #12161C
BG_CARD       = "(R=0.094,G=0.114,B=0.149,A=1.0)"      # #181D26
C_BORDER      = "(R=0.165,G=0.188,B=0.251,A=1.0)"      # #2A3040
ACCENT        = "(R=0.910,G=0.651,B=0.141,A=1.0)"      # #E8A624
GREEN         = "(R=0.239,G=0.863,B=0.518,A=1.0)"      # #3DDC84
YELLOW        = "(R=0.941,G=0.753,B=0.251,A=1.0)"      # #F0C040
RED           = "(R=0.878,G=0.251,B=0.314,A=1.0)"      # #E04050
TEXT_C        = "(R=0.816,G=0.831,B=0.863,A=1.0)"      # #D0D4DC
TEXT_DIM      = "(R=0.439,G=0.471,B=0.533,A=1.0)"      # #707888
TEXT_BRIGHT   = "(R=0.933,G=0.941,B=0.957,A=1.0)"      # #EEF0F4

OVERLAY_40    = "(R=0.0,G=0.0,B=0.0,A=0.4)"
HEADER_BG     = "(R=0.0,G=0.0,B=0.0,A=0.35)"
STATUS_BG     = "(R=0.0,G=0.0,B=0.0,A=0.35)"
COST_BG       = "(R=0.0,G=0.0,B=0.0,A=0.22)"
PROG_TRACK_BG = "(R=1.0,G=1.0,B=1.0,A=0.05)"
APPROVE_BG    = "(R=0.239,G=0.863,B=0.518,A=0.10)"
CANCEL_BG     = "(R=0.878,G=0.251,B=0.314,A=0.08)"
SELECTED_BG   = "(R=0.910,G=0.651,B=0.141,A=0.05)"

# Font asset paths
FC = "/Game/UI/Fonts/F_BarlowCondensed"
FB = "/Game/UI/Fonts/F_Barlow"
FM = "/Game/UI/Fonts/F_ShareTechMono"


# ── Helpers ────────────────────────────────────────────────────

def sp(name, prop, val):
    r = send("set_widget_property", {
        "widget_blueprint": WBP,
        "widget_name": name,
        "property": prop,
        "value": str(val),
    })
    if r.get("status") != "ok":
        warns.append(f"{name}.{prop}")
    return r


def child(parent, wtype, wname):
    params = {
        "widget_blueprint": WBP,
        "widget_type": wtype,
        "widget_name": wname,
    }
    if parent:
        params["parent_widget"] = parent
    r = send("add_widget_child", params)
    if r.get("status") != "ok":
        print(f"  FAIL: {wtype} '{wname}' -> '{parent}': {r.get('message', '?')[:80]}")
    return r


def anchor(name, min_x, min_y, max_x, max_y):
    sp(name, "Slot.Anchors.Min.X", str(min_x))
    sp(name, "Slot.Anchors.Min.Y", str(min_y))
    sp(name, "Slot.Anchors.Max.X", str(max_x))
    sp(name, "Slot.Anchors.Max.Y", str(max_y))


def text(parent, name, content, font_family, typeface, size, color, **extra):
    child(parent, "TextBlock", name)
    sp(name, "Text", content)
    sp(name, "Font.Family", font_family)
    sp(name, "Font.Typeface", typeface)
    sp(name, "Font.Size", str(size))
    sp(name, "ColorAndOpacity", color)
    for k, v in extra.items():
        sp(name, k, str(v))


# ── Build ──────────────────────────────────────────────────────

def build():
    global warns
    warns = []

    print("=== Rebuilding WBP_Station_Bore (two-layer, approved 1080p spec) ===\n")

    # Delete existing
    print("  Deleting existing...", flush=True)
    send("delete_blueprint", {"name": WBP})
    time.sleep(0.3)

    # Create fresh
    r = send("create_widget_blueprint", {"name": WBP, "path": "/Game/UI"})
    if r.get("status") != "ok":
        print(f"  CREATE FAILED: {r.get('message', '?')}")
        return False
    print("  Created WBP_Station_Bore\n", flush=True)

    # Root canvas
    child("", "CanvasPanel", "CanvasPanel_Root")

    # ═══════════════════════════════════════════════════════════
    # LAYER 1 — Hidden C++ bridge widgets (Z:0)
    # ═══════════════════════════════════════════════════════════
    print("  LAYER 1: hidden C++ bridge...", flush=True)

    hidden = [
        "txt_Title", "txt_Desc", "txt_ItemInfo",
        "txt_ActionsHeader", "txt_Actions", "txt_Equipment", "txt_ExitHint"
    ]
    for txt_name in hidden:
        child("CanvasPanel_Root", "TextBlock", txt_name)
        sp(txt_name, "Visibility", "Hidden")
        sp(txt_name, "Slot.Position.X", "0")
        sp(txt_name, "Slot.Position.Y", "0")
        sp(txt_name, "Slot.Size.X", "1")
        sp(txt_name, "Slot.Size.Y", "1")
        sp(txt_name, "Slot.ZOrder", "0")

    print(f"    7 hidden txt_* widgets placed\n", flush=True)

    # ═══════════════════════════════════════════════════════════
    # LAYER 2 — Full visual layout (Z:1+)
    # ═══════════════════════════════════════════════════════════
    print("  LAYER 2: visual layout...\n", flush=True)

    # ── Full screen dark overlay ──────────────────────────────
    child("CanvasPanel_Root", "Border", "Border_Overlay")
    anchor("Border_Overlay", 0.0, 0.0, 1.0, 1.0)
    sp("Border_Overlay", "BrushColor", OVERLAY_40)
    sp("Border_Overlay", "Brush.DrawType", "Box")
    sp("Border_Overlay", "Slot.ZOrder", "1")
    print("    Border_Overlay (fullscreen dim)", flush=True)

    # ── Decision panel — right 35% ────────────────────────────
    child("CanvasPanel_Root", "Border", "Border_Panel")
    anchor("Border_Panel", 0.65, 0.0, 1.0, 1.0)
    sp("Border_Panel", "BrushColor", BG_PANEL)
    sp("Border_Panel", "Brush.DrawType", "Box")
    sp("Border_Panel", "Slot.ZOrder", "2")
    print("    Border_Panel (right 35%)", flush=True)

    # Main vertical layout fills the panel
    child("Border_Panel", "VerticalBox", "VBox_Main")

    # ══════════════════════════════════════════════════════════
    # PANEL HEADER — rgba(0,0,0,0.35), pad 20,16
    # CSS: .panel-header h:68, .panel-station-name 21px bold,
    #      .panel-station-sub 15px dim
    # ══════════════════════════════════════════════════════════
    print("    Header...", flush=True)
    child("VBox_Main", "Border", "Border_Header")
    sp("Border_Header", "BrushColor", HEADER_BG)
    sp("Border_Header", "Brush.DrawType", "Box")
    sp("Border_Header", "Padding", "(Left=20,Top=16,Right=20,Bottom=16)")
    sp("Border_Header", "Slot.FillHeight", "0.0")

    child("Border_Header", "VerticalBox", "VBox_Header")

    text("VBox_Header", "Text_StationName", "CYLINDER BORING",
         FC, "Bold", 21, ACCENT,
         **{"Font.LetterSpacing": "4"})

    text("VBox_Header", "Text_StationSub", "Station 05 \u00b7 Tier 2 Boring Bar",
         FC, "Regular", 15, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=2,Right=0,Bottom=0)"})

    # ══════════════════════════════════════════════════════════
    # ENGINE BADGE — bg-card, border 1px #2A3040, pad 10
    # CSS: .engine-badge h:72, flex row, gap:10
    #   icon 40x40 | name+serial+specs | quality score
    # ══════════════════════════════════════════════════════════
    print("    Engine badge...", flush=True)
    child("VBox_Main", "Border", "Border_Badge")
    sp("Border_Badge", "BrushColor", BG_CARD)
    sp("Border_Badge", "Brush.DrawType", "Box")
    sp("Border_Badge", "Padding", "(Left=10,Top=10,Right=10,Bottom=10)")
    sp("Border_Badge", "Slot.FillHeight", "0.0")
    sp("Border_Badge", "Slot.Padding", "(Left=11,Top=6,Right=11,Bottom=0)")

    child("Border_Badge", "HorizontalBox", "HBox_Badge")

    # Badge icon — 40x40 dark square placeholder
    child("HBox_Badge", "SizeBox", "SizeBox_BadgeIcon")
    sp("SizeBox_BadgeIcon", "WidthOverride", "40")
    sp("SizeBox_BadgeIcon", "HeightOverride", "40")
    child("SizeBox_BadgeIcon", "Border", "Border_BadgeIcon")
    sp("Border_BadgeIcon", "BrushColor", "(R=0.165,G=0.118,B=0.063,A=1.0)")
    sp("Border_BadgeIcon", "Brush.DrawType", "Box")

    # Badge info (flex:1)
    child("HBox_Badge", "VerticalBox", "VBox_BadgeInfo")
    sp("VBox_BadgeInfo", "Slot.FillWidth", "1.0")
    sp("VBox_BadgeInfo", "Slot.Padding", "(Left=10,Top=0,Right=10,Bottom=0)")

    text("VBox_BadgeInfo", "Text_EngineName", "1967 Chevy 327 SBC",
         FC, "Bold", 20, TEXT_BRIGHT,
         **{"Font.LetterSpacing": "0"})
    text("VBox_BadgeInfo", "Text_EngineSerial", "SN: E2-7740192",
         FM, "Regular", 14, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=1,Right=0,Bottom=0)"})
    text("VBox_BadgeInfo", "Text_EngineSpecs", "V8 \u00b7 327 ci \u00b7 4-Bolt Main",
         FB, "Regular", 14, TEXT_DIM,
         **{"Slot.Padding": "(Left=0,Top=1,Right=0,Bottom=0)"})

    # Quality score (right-aligned)
    child("HBox_Badge", "VerticalBox", "VBox_QualityScore")
    sp("VBox_QualityScore", "Slot.VAlign", "Center")

    text("VBox_QualityScore", "Text_QualityNum", "54",
         FM, "Regular", 33, YELLOW)
    text("VBox_QualityScore", "Text_QualityLbl", "QUALITY",
         FC, "Regular", 12, TEXT_DIM,
         **{"Font.LetterSpacing": "1"})

    # ══════════════════════════════════════════════════════════
    # PROGRESS SECTION
    # CSS: .progress-labels top:160, .prog-track-outer top:182 h:6
    # ══════════════════════════════════════════════════════════
    print("    Progress...", flush=True)
    child("VBox_Main", "Border", "Border_Progress")
    sp("Border_Progress", "BrushColor", BG_PANEL)
    sp("Border_Progress", "Brush.DrawType", "Box")
    sp("Border_Progress", "Padding", "(Left=11,Top=10,Right=11,Bottom=6)")
    sp("Border_Progress", "Slot.FillHeight", "0.0")

    child("Border_Progress", "VerticalBox", "VBox_Progress")

    # Progress labels row — "CYLINDER PROGRESS" left, "3 / 8 Bored" right
    child("VBox_Progress", "HorizontalBox", "HBox_ProgLabels")

    text("HBox_ProgLabels", "Text_ProgLabel", "CYLINDER PROGRESS",
         FC, "SemiBold", 14, TEXT_DIM,
         **{"Font.LetterSpacing": "2", "Slot.FillWidth": "1.0"})
    text("HBox_ProgLabels", "Text_ProgCount", "3 / 8 Bored",
         FM, "Regular", 16, GREEN)

    # Progress bar — 6px track with green fill at 37.5%
    child("VBox_Progress", "SizeBox", "SizeBox_ProgTrack")
    sp("SizeBox_ProgTrack", "HeightOverride", "6")
    sp("SizeBox_ProgTrack", "Slot.Padding", "(Left=0,Top=6,Right=0,Bottom=0)")

    child("SizeBox_ProgTrack", "HorizontalBox", "HBox_ProgTrack")

    child("HBox_ProgTrack", "Border", "Border_ProgFill")
    sp("Border_ProgFill", "BrushColor", GREEN)
    sp("Border_ProgFill", "Brush.DrawType", "Box")
    sp("Border_ProgFill", "Slot.FillWidth", "3.0")

    child("HBox_ProgTrack", "Border", "Border_ProgEmpty")
    sp("Border_ProgEmpty", "BrushColor", PROG_TRACK_BG)
    sp("Border_ProgEmpty", "Brush.DrawType", "Box")
    sp("Border_ProgEmpty", "Slot.FillWidth", "5.0")

    # ══════════════════════════════════════════════════════════
    # SECTION LABEL — "Available Actions"
    # CSS: .section-lbl 14px BarlowCond semibold, tracking:2
    # ══════════════════════════════════════════════════════════
    child("VBox_Main", "Border", "Border_SectionLbl")
    sp("Border_SectionLbl", "BrushColor", BG_PANEL)
    sp("Border_SectionLbl", "Brush.DrawType", "Box")
    sp("Border_SectionLbl", "Padding", "(Left=11,Top=6,Right=11,Bottom=4)")
    sp("Border_SectionLbl", "Slot.FillHeight", "0.0")

    text("Border_SectionLbl", "Text_SectionLabel", "AVAILABLE ACTIONS",
         FC, "SemiBold", 14, TEXT_DIM,
         **{"Font.LetterSpacing": "2"})

    # ══════════════════════════════════════════════════════════
    # ACTION LIST — scrollable, fills remaining vertical space
    # CSS: .action-list top:202 h:530, flex col gap:5
    #   .action-btn — bg-card, border 1px, radius 4, pad 12 14
    #   .action-name — Barlow 18px semibold, text-bright
    #   .action-meta — BarlowCond 14px dim
    #   .prereq-text — 14px red
    # ══════════════════════════════════════════════════════════
    print("    Action list...", flush=True)
    child("VBox_Main", "ScrollBox", "ScrollBox_Actions")
    sp("ScrollBox_Actions", "Slot.FillHeight", "1.0")
    sp("ScrollBox_Actions", "Slot.Padding", "(Left=11,Top=0,Right=11,Bottom=0)")

    child("ScrollBox_Actions", "VerticalBox", "VBox_ActionList")

    actions = [
        ("Action1", 'Bore Cylinder 4 \u2014 0.030" Over',
         "45 min human  \u00b7  90 min machine  \u00b7  +6 quality pts",
         True, None),
        ("Action2", 'Bore Cylinder 4 \u2014 0.040" Over',
         "45 min human  \u00b7  120 min machine  \u00b7  +8 quality pts",
         False, None),
        ("Action3", 'Bore All Remaining \u2014 0.030"',
         "4h human  \u00b7  7.5h machine  \u00b7  +30 quality pts",
         False, None),
        ("Action4", "CNC Precision Bore \u2014 All Cylinders",
         "2h human  \u00b7  +48 quality pts",
         False, "Requires: CNC Boring Machine (Station Upgrade)"),
        ("Action5", "Inspect Bore Diameter After Machining",
         "20 min human  \u00b7  +2 quality pts",
         False, None),
    ]

    for act_id, act_name, act_meta, selected, prereq in actions:
        border_name = f"Border_{act_id}"
        child("VBox_ActionList", "Border", border_name)
        sp(border_name, "BrushColor", SELECTED_BG if selected else BG_CARD)
        sp(border_name, "Brush.DrawType", "Box")
        sp(border_name, "Padding", "(Left=14,Top=12,Right=14,Bottom=12)")
        sp(border_name, "Slot.Padding", "(Left=0,Top=0,Right=0,Bottom=5)")

        vbox_name = f"VBox_{act_id}"
        child(border_name, "VerticalBox", vbox_name)

        text(vbox_name, f"Text_{act_id}_Name", act_name,
             FB, "SemiBold", 18, TEXT_BRIGHT)
        text(vbox_name, f"Text_{act_id}_Meta", act_meta,
             FC, "Regular", 14, TEXT_DIM,
             **{"Slot.Padding": "(Left=0,Top=4,Right=0,Bottom=0)"})

        if prereq:
            text(vbox_name, f"Text_{act_id}_Prereq", f"\u2715 {prereq}",
                 FC, "Regular", 14, RED,
                 **{"Slot.Padding": "(Left=0,Top=3,Right=0,Bottom=0)"})

    # ══════════════════════════════════════════════════════════
    # COST DETAIL — rgba(0,0,0,0.22), border 1px border-active
    # CSS: .cost-detail top:742 w:650 h:160, pad 12 14
    # ══════════════════════════════════════════════════════════
    print("    Cost detail...", flush=True)
    child("VBox_Main", "Border", "Border_CostDetail")
    sp("Border_CostDetail", "BrushColor", COST_BG)
    sp("Border_CostDetail", "Brush.DrawType", "Box")
    sp("Border_CostDetail", "Padding", "(Left=14,Top=12,Right=14,Bottom=12)")
    sp("Border_CostDetail", "Slot.FillHeight", "0.0")
    sp("Border_CostDetail", "Slot.Padding", "(Left=11,Top=4,Right=11,Bottom=0)")

    child("Border_CostDetail", "VerticalBox", "VBox_Costs")

    def cost_row(row_id, label, value, val_color):
        hbox = f"HBox_{row_id}"
        child("VBox_Costs", "HorizontalBox", hbox)
        sp(hbox, "Slot.Padding", "(Left=0,Top=2,Right=0,Bottom=2)")
        text(hbox, f"Text_{row_id}_Lbl", label,
             FC, "Regular", 14, TEXT_DIM,
             **{"Slot.FillWidth": "1.0"})
        text(hbox, f"Text_{row_id}_Val", value,
             FM, "Regular", 16, val_color)

    def cost_divider(div_id):
        child("VBox_Costs", "SizeBox", f"SizeBox_{div_id}")
        sp(f"SizeBox_{div_id}", "HeightOverride", "1")
        sp(f"SizeBox_{div_id}", "Slot.Padding", "(Left=0,Top=3,Right=0,Bottom=3)")
        child(f"SizeBox_{div_id}", "Border", f"Border_{div_id}")
        sp(f"Border_{div_id}", "BrushColor", C_BORDER)
        sp(f"Border_{div_id}", "Brush.DrawType", "Box")

    cost_row("CostHuman",    "HUMAN TIME",      "45 min",              TEXT_BRIGHT)
    cost_row("CostMachine",  "MACHINE TIME",    "90 min",              TEXT_BRIGHT)
    cost_divider("CostDiv1")
    cost_row("CostConsum",   "CONSUMABLES",     "Boring Oil \u2014 0.5 L",  YELLOW)
    cost_row("CostWear",     "EQUIPMENT WEAR",  "Boring Bar \u20133%",      TEXT_DIM)
    cost_divider("CostDiv2")
    cost_row("CostQuality",  "QUALITY GAIN",    "+6 pts (54 \u2192 60)",    GREEN)

    # ══════════════════════════════════════════════════════════
    # ACTION BUTTONS — Approve + Cancel
    # CSS: .action-btns top:912 w:650 h:60, flex gap:6
    #   .btn-approve flex:1 h:60 green
    #   .btn-cancel w:120 h:60 red
    # ══════════════════════════════════════════════════════════
    print("    Action buttons...", flush=True)
    child("VBox_Main", "Border", "Border_BtnArea")
    sp("Border_BtnArea", "BrushColor", BG_PANEL)
    sp("Border_BtnArea", "Brush.DrawType", "Box")
    sp("Border_BtnArea", "Padding", "(Left=11,Top=4,Right=11,Bottom=4)")
    sp("Border_BtnArea", "Slot.FillHeight", "0.0")

    child("Border_BtnArea", "HorizontalBox", "HBox_ActionBtns")

    # Approve
    child("HBox_ActionBtns", "SizeBox", "SizeBox_Approve")
    sp("SizeBox_Approve", "HeightOverride", "60")
    sp("SizeBox_Approve", "Slot.FillWidth", "1.0")
    sp("SizeBox_Approve", "Slot.Padding", "(Left=0,Top=0,Right=3,Bottom=0)")
    child("SizeBox_Approve", "Border", "Border_BtnApprove")
    sp("Border_BtnApprove", "BrushColor", APPROVE_BG)
    sp("Border_BtnApprove", "Brush.DrawType", "Box")
    sp("Border_BtnApprove", "HAlign", "Center")
    sp("Border_BtnApprove", "VAlign", "Center")
    text("Border_BtnApprove", "Text_BtnApprove", "\u2713 APPROVE",
         FC, "Bold", 18, GREEN,
         **{"Font.LetterSpacing": "3"})

    # Cancel
    child("HBox_ActionBtns", "SizeBox", "SizeBox_Cancel")
    sp("SizeBox_Cancel", "WidthOverride", "120")
    sp("SizeBox_Cancel", "HeightOverride", "60")
    sp("SizeBox_Cancel", "Slot.Padding", "(Left=3,Top=0,Right=0,Bottom=0)")
    child("SizeBox_Cancel", "Border", "Border_BtnCancel")
    sp("Border_BtnCancel", "BrushColor", CANCEL_BG)
    sp("Border_BtnCancel", "Brush.DrawType", "Box")
    sp("Border_BtnCancel", "HAlign", "Center")
    sp("Border_BtnCancel", "VAlign", "Center")
    text("Border_BtnCancel", "Text_BtnCancel", "\u2715 CANCEL",
         FC, "Bold", 18, RED,
         **{"Font.LetterSpacing": "3"})

    # ══════════════════════════════════════════════════════════
    # STATUS BAR — rgba(0,0,0,0.35), border-top 1px
    # CSS: .status-bar top:988 w:672 h:48, flex gap:4
    #   .stat-chip — bg-card, border 1px, pad 5 8, flex:1 h:36
    #   .stat-chip-lbl 12px BarlowCond semibold dim
    #   .stat-chip-val 16px ShareTechMono colored
    # ══════════════════════════════════════════════════════════
    print("    Status bar...", flush=True)
    child("VBox_Main", "Border", "Border_StatusBar")
    sp("Border_StatusBar", "BrushColor", STATUS_BG)
    sp("Border_StatusBar", "Brush.DrawType", "Box")
    sp("Border_StatusBar", "Padding", "(Left=8,Top=6,Right=8,Bottom=6)")
    sp("Border_StatusBar", "Slot.FillHeight", "0.0")

    child("Border_StatusBar", "HorizontalBox", "HBox_Status")

    stats = [
        ("Cash",    "CASH",    "$4,820",  GREEN),
        ("Time",    "TIME",    "3h 40m",  YELLOW),
        ("Bar",     "BAR",     "82%",     GREEN),
        ("Storage", "STORAGE", "14/24",   ACCENT),
    ]

    for stat_id, stat_lbl, stat_val, stat_color in stats:
        chip = f"Border_Stat{stat_id}"
        child("HBox_Status", "Border", chip)
        sp(chip, "BrushColor", BG_CARD)
        sp(chip, "Brush.DrawType", "Box")
        sp(chip, "Padding", "(Left=8,Top=5,Right=8,Bottom=5)")
        sp(chip, "Slot.FillWidth", "1.0")
        sp(chip, "Slot.Padding", "(Left=2,Top=0,Right=2,Bottom=0)")

        hbox = f"HBox_Stat{stat_id}"
        child(chip, "HorizontalBox", hbox)

        text(hbox, f"Text_Stat{stat_id}_Lbl", stat_lbl,
             FC, "SemiBold", 12, TEXT_DIM,
             **{"Font.LetterSpacing": "1", "Slot.FillWidth": "1.0"})
        text(hbox, f"Text_Stat{stat_id}_Val", stat_val,
             FM, "Regular", 16, stat_color)

    # ══════════════════════════════════════════════════════════
    # REPARENT + SAVE
    # ══════════════════════════════════════════════════════════
    print("\n  Reparenting to BSStationWidget...", flush=True)
    r = send("reparent_widget_blueprint", {"name": WBP, "new_parent": "BSStationWidget"})
    if r.get("status") == "ok":
        print(f"    OK: {r['data'].get('old_parent','?')} -> {r['data'].get('new_parent','?')}")
    else:
        print(f"    FAIL: {r.get('message', '?')[:80]}")

    print("  Saving...", flush=True)
    r = send("save_all", {})
    print(f"    save_all: {r.get('status')}")

    # ══════════════════════════════════════════════════════════
    # VERIFICATION
    # ══════════════════════════════════════════════════════════
    print("\n=== Verification ===", flush=True)
    r = send("get_widget_tree", {"widget_blueprint": WBP})
    total = r.get("data", {}).get("total_widgets", 0)
    tree = r.get("data", {}).get("tree", [])
    print(f"  Total widgets: {total}")

    # Check all 7 hidden bridge widgets
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
    if missing:
        print(f"  MISSING bridge widgets: {missing}")
    else:
        print(f"  All 7 hidden txt_* bridge widgets present")

    # Count visual layer widgets
    visual_count = total - len(hidden) - 1  # minus hidden + root canvas
    print(f"  Visual layer widgets: ~{visual_count}")

    if warns:
        print(f"\n  Property warnings ({len(warns)}):")
        for w in warns[:15]:
            print(f"    {w}")
        if len(warns) > 15:
            print(f"    ...and {len(warns) - 15} more")

    print(f"\n=== WBP_Station_Bore rebuild complete ({total} widgets) ===")
    return True


if __name__ == "__main__":
    ok = build()
    sys.exit(0 if ok else 1)
