#!/usr/bin/env python3
"""Build all 12 remaining BoreAndStroke station widgets.
Same structure as WBP_Station_Bore — FillHeight=1.0, hex: colors, 1920x1080.
"""
import socket, json, time, sys

def send(cmd, params, retries=3):
    for attempt in range(retries):
        try:
            s = socket.socket()
            s.settimeout(30)
            s.connect(('localhost', 13377))
            s.send((json.dumps({'command': cmd, 'params': params}) + '\n').encode())
            resp = b''
            while True:
                chunk = s.recv(65536)
                if not chunk: break
                resp += chunk
                if b'\n' in resp: break
            s.close()
            time.sleep(0.15)
            return json.loads(resp.decode().strip())
        except (ConnectionResetError, ConnectionRefusedError, socket.timeout) as e:
            if attempt < retries - 1:
                time.sleep(5)
            else:
                raise

def sp(wbp, wname, prop, val):
    r = send('set_widget_property', {
        'widget_blueprint': wbp, 'widget_name': wname,
        'property': prop, 'value': str(val)
    })
    return r.get('status') == 'ok'

def add(wbp, parent, wtype, wname):
    r = send('add_widget_child', {
        'widget_blueprint': wbp, 'parent_widget': parent,
        'widget_type': wtype, 'widget_name': wname,
    })
    return r.get('status') == 'ok'

def validate(wbp):
    r = send('validate_widget_layout', {'name': wbp})
    time.sleep(0.3)
    return r.get('data', {}).get('score', 0)

# ── hex: color constants ─────────────────────────────────────
BG_PANEL   = 'hex:#12161C'
BG_CARD    = 'hex:#181D26'
BORDER     = 'hex:#2A3040'
ACCENT     = 'hex:#E8A624'
GREEN      = 'hex:#3DDC84'
YELLOW     = 'hex:#F0C040'
RED        = 'hex:#E04050'
DIM        = 'hex:#707888'
BRIGHT     = 'hex:#EEF0F4'
OVERLAY35  = '(R=0.0,G=0.0,B=0.0,A=0.35)'
OVERLAY22  = '(R=0.0,G=0.0,B=0.0,A=0.22)'
APPROVE_BG = 'hex:#16382DE6'
CANCEL_BG  = 'hex:#4A0F14CC'

FC = '/Game/UI/Fonts/F_BarlowCondensed'
FB = '/Game/UI/Fonts/F_Barlow'
FM = '/Game/UI/Fonts/F_ShareTechMono'

# ── Station definitions ──────────────────────────────────────
STATIONS = [
    ('WBP_Station_Office',      'FRONT OFFICE',      'Orders, Finance & Reputation',            'BSOfficeWidget'),
    ('WBP_Station_Disassembly', 'DISASSEMBLY',       'Station 02 . Break Down to Components',   'BSStationWidget'),
    ('WBP_Station_Cleaning',    'CLEANING',          'Station 04 . Deep Clean All Parts',       'BSStationWidget'),
    ('WBP_Station_Inspection',  'BLOCK INSPECTION',  'Station 03 . Measure & Assess Condition', 'BSInspectionWidget'),
    ('WBP_Station_Hone',        'CYLINDER HONING',   'Station 06 . Hone for Cross-Hatch',       'BSStationWidget'),
    ('WBP_Station_Deck',        'SURFACE GRINDING',  'Station 09 . Deck & Head Surfaces',       'BSStationWidget'),
    ('WBP_Station_CrankGrind',  'CRANK INSPECTION',  'Station 07 . Measure Journals & Runout',  'BSStationWidget'),
    ('WBP_Station_HeadWork',    'CYLINDER HEADS',    'Station 08 . Valve Seats & Guides',       'BSStationWidget'),
    ('WBP_Station_ValveWork',   'VALVE WORK',        'Station 08b . Valve Lapping & Seating',   'BSStationWidget'),
    ('WBP_Station_Assembly',    'ASSEMBLY',          'Station 11 . Assemble with Torque Specs', 'BSStationWidget'),
    ('WBP_Station_Balancing',   'BALANCING',         'Station 10 . Rotating Assembly Balance',  'BSStationWidget'),
    ('WBP_Station_Testing',     'TESTING',           'Station 12 . Test Engine Performance',    'BSStationWidget'),
]

def build_station(wbp, title, subtitle, parent_class):
    """Build one station widget — same structure as WBP_Station_Bore."""

    # Delete and recreate
    send('delete_blueprint', {'name': wbp})
    time.sleep(0.3)
    r = send('create_widget_blueprint', {'name': wbp, 'path': '/Game/UI'})
    if r.get('status') != 'ok':
        return False, f"CREATE FAILED: {r.get('message','?')}"

    # Root canvas
    add(wbp, '', 'CanvasPanel', 'CanvasPanel_Root')

    # Border_Panel anchored 0.65,0 -> 1,1
    add(wbp, 'CanvasPanel_Root', 'Border', 'Border_Panel')
    sp(wbp, 'Border_Panel', 'Slot.Anchors.Min.X', '0.65')
    sp(wbp, 'Border_Panel', 'Slot.Anchors.Min.Y', '0.0')
    sp(wbp, 'Border_Panel', 'Slot.Anchors.Max.X', '1.0')
    sp(wbp, 'Border_Panel', 'Slot.Anchors.Max.Y', '1.0')
    sp(wbp, 'Border_Panel', 'Slot.Position.X', '0')
    sp(wbp, 'Border_Panel', 'Slot.Position.Y', '0')
    sp(wbp, 'Border_Panel', 'Slot.Size.X', '0')
    sp(wbp, 'Border_Panel', 'Slot.Size.Y', '0')
    sp(wbp, 'Border_Panel', 'BrushColor', BG_PANEL)
    sp(wbp, 'Border_Panel', 'Brush.DrawType', 'Box')

    # VBox_Main
    add(wbp, 'Border_Panel', 'VerticalBox', 'VBox_Main')

    # 7 sections — FillHeight = 1.0
    sections = [
        ('Border_Header',    0.07, OVERLAY35),
        ('Border_Badge',     0.08, BG_CARD),
        ('Border_Progress',  0.04, '(R=0.0,G=0.0,B=0.0,A=0.0)'),
        ('Border_Actions',   0.52, BG_PANEL),
        ('Border_Costs',     0.15, OVERLAY22),
        ('Border_Btns',      0.07, '(R=0.0,G=0.0,B=0.0,A=0.0)'),
        ('Border_StatusBar', 0.07, OVERLAY35),
    ]
    for bname, fh, bg in sections:
        add(wbp, 'VBox_Main', 'Border', bname)
        sp(wbp, bname, 'BrushColor', bg)
        sp(wbp, bname, 'Brush.DrawType', 'Box')
        sp(wbp, bname, 'Slot.FillHeight', str(fh))

    # ── Header ────────────────────────────────────────────
    sp(wbp, 'Border_Header', 'Padding', '(Left=20,Top=12,Right=20,Bottom=12)')
    add(wbp, 'Border_Header', 'VerticalBox', 'VBox_Header')

    add(wbp, 'VBox_Header', 'TextBlock', 'Text_StationName')
    sp(wbp, 'Text_StationName', 'Text', title)
    sp(wbp, 'Text_StationName', 'Font.Family', FC)
    sp(wbp, 'Text_StationName', 'Font.Typeface', 'Bold')
    sp(wbp, 'Text_StationName', 'Font.Size', '21')
    sp(wbp, 'Text_StationName', 'Font.LetterSpacing', '4')
    sp(wbp, 'Text_StationName', 'ColorAndOpacity', ACCENT)

    add(wbp, 'VBox_Header', 'TextBlock', 'Text_StationSub')
    sp(wbp, 'Text_StationSub', 'Text', subtitle)
    sp(wbp, 'Text_StationSub', 'Font.Family', FC)
    sp(wbp, 'Text_StationSub', 'Font.Size', '15')
    sp(wbp, 'Text_StationSub', 'ColorAndOpacity', DIM)
    sp(wbp, 'Text_StationSub', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')

    # ── Badge ─────────────────────────────────────────────
    sp(wbp, 'Border_Badge', 'Padding', '(Left=10,Top=6,Right=10,Bottom=6)')
    add(wbp, 'Border_Badge', 'HorizontalBox', 'HBox_Badge')

    add(wbp, 'HBox_Badge', 'VerticalBox', 'VBox_BadgeInfo')
    sp(wbp, 'VBox_BadgeInfo', 'Slot.FillWidth', '1.0')

    add(wbp, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeName')
    sp(wbp, 'Text_BadgeName', 'Text', '1967 Chevy 327 SBC')
    sp(wbp, 'Text_BadgeName', 'Font.Family', FC)
    sp(wbp, 'Text_BadgeName', 'Font.Typeface', 'Bold')
    sp(wbp, 'Text_BadgeName', 'Font.Size', '20')
    sp(wbp, 'Text_BadgeName', 'ColorAndOpacity', BRIGHT)

    add(wbp, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSerial')
    sp(wbp, 'Text_BadgeSerial', 'Text', 'SN: E2-7740192')
    sp(wbp, 'Text_BadgeSerial', 'Font.Family', FM)
    sp(wbp, 'Text_BadgeSerial', 'Font.Size', '14')
    sp(wbp, 'Text_BadgeSerial', 'ColorAndOpacity', DIM)

    add(wbp, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSpecs')
    sp(wbp, 'Text_BadgeSpecs', 'Text', 'V8 . 327ci . 4-Bolt')
    sp(wbp, 'Text_BadgeSpecs', 'Font.Family', FC)
    sp(wbp, 'Text_BadgeSpecs', 'Font.Size', '13')
    sp(wbp, 'Text_BadgeSpecs', 'ColorAndOpacity', DIM)

    add(wbp, 'HBox_Badge', 'VerticalBox', 'VBox_Quality')

    add(wbp, 'VBox_Quality', 'TextBlock', 'Text_QualityNum')
    sp(wbp, 'Text_QualityNum', 'Text', '54')
    sp(wbp, 'Text_QualityNum', 'Font.Family', FM)
    sp(wbp, 'Text_QualityNum', 'Font.Size', '33')
    sp(wbp, 'Text_QualityNum', 'ColorAndOpacity', YELLOW)
    sp(wbp, 'Text_QualityNum', 'Justification', 'Right')

    add(wbp, 'VBox_Quality', 'TextBlock', 'Text_QualityLbl')
    sp(wbp, 'Text_QualityLbl', 'Text', 'QUALITY')
    sp(wbp, 'Text_QualityLbl', 'Font.Family', FC)
    sp(wbp, 'Text_QualityLbl', 'Font.Size', '10')
    sp(wbp, 'Text_QualityLbl', 'Font.LetterSpacing', '2')
    sp(wbp, 'Text_QualityLbl', 'ColorAndOpacity', DIM)
    sp(wbp, 'Text_QualityLbl', 'Justification', 'Right')

    # ── Progress ──────────────────────────────────────────
    sp(wbp, 'Border_Progress', 'Padding', '(Left=11,Top=4,Right=11,Bottom=4)')
    add(wbp, 'Border_Progress', 'VerticalBox', 'VBox_Progress')
    add(wbp, 'VBox_Progress', 'HorizontalBox', 'HBox_ProgLabels')

    add(wbp, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgLabel')
    sp(wbp, 'Text_ProgLabel', 'Text', 'PROGRESS')
    sp(wbp, 'Text_ProgLabel', 'Font.Family', FC)
    sp(wbp, 'Text_ProgLabel', 'Font.Typeface', 'SemiBold')
    sp(wbp, 'Text_ProgLabel', 'Font.Size', '12')
    sp(wbp, 'Text_ProgLabel', 'Font.LetterSpacing', '2')
    sp(wbp, 'Text_ProgLabel', 'ColorAndOpacity', DIM)
    sp(wbp, 'Text_ProgLabel', 'Slot.FillWidth', '1.0')

    add(wbp, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgCount')
    sp(wbp, 'Text_ProgCount', 'Text', '0 / 8')
    sp(wbp, 'Text_ProgCount', 'Font.Family', FM)
    sp(wbp, 'Text_ProgCount', 'Font.Size', '14')
    sp(wbp, 'Text_ProgCount', 'ColorAndOpacity', GREEN)
    sp(wbp, 'Text_ProgCount', 'Justification', 'Right')

    add(wbp, 'VBox_Progress', 'ProgressBar', 'ProgBar_Main')
    sp(wbp, 'ProgBar_Main', 'Percent', '0.0')
    sp(wbp, 'ProgBar_Main', 'FillColorAndOpacity', GREEN)
    sp(wbp, 'ProgBar_Main', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')

    # ── Actions (placeholder — 3 generic action cards) ────
    sp(wbp, 'Border_Actions', 'Padding', '(Left=11,Top=6,Right=11,Bottom=6)')
    add(wbp, 'Border_Actions', 'VerticalBox', 'VBox_Actions')

    add(wbp, 'VBox_Actions', 'TextBlock', 'Text_ActionsLabel')
    sp(wbp, 'Text_ActionsLabel', 'Text', 'AVAILABLE ACTIONS')
    sp(wbp, 'Text_ActionsLabel', 'Font.Family', FC)
    sp(wbp, 'Text_ActionsLabel', 'Font.Typeface', 'SemiBold')
    sp(wbp, 'Text_ActionsLabel', 'Font.Size', '14')
    sp(wbp, 'Text_ActionsLabel', 'Font.LetterSpacing', '2')
    sp(wbp, 'Text_ActionsLabel', 'ColorAndOpacity', DIM)
    sp(wbp, 'Text_ActionsLabel', 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=6)')

    for i in range(1, 4):
        bn = f'Border_Action{i}'
        add(wbp, 'VBox_Actions', 'Border', bn)
        sp(wbp, bn, 'BrushColor', BG_CARD)
        sp(wbp, bn, 'Brush.DrawType', 'Box')
        sp(wbp, bn, 'Padding', '(Left=10,Top=8,Right=10,Bottom=8)')
        sp(wbp, bn, 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=4)')
        add(wbp, bn, 'VerticalBox', f'VBox_A{i}')
        add(wbp, f'VBox_A{i}', 'TextBlock', f'Text_A{i}Name')
        sp(wbp, f'Text_A{i}Name', 'Text', f'Action {i} — Placeholder')
        sp(wbp, f'Text_A{i}Name', 'Font.Family', FB)
        sp(wbp, f'Text_A{i}Name', 'Font.Typeface', 'SemiBold')
        sp(wbp, f'Text_A{i}Name', 'Font.Size', '17')
        sp(wbp, f'Text_A{i}Name', 'ColorAndOpacity', BRIGHT)
        add(wbp, f'VBox_A{i}', 'TextBlock', f'Text_A{i}Meta')
        sp(wbp, f'Text_A{i}Meta', 'Text', '. Populated by C++ at runtime')
        sp(wbp, f'Text_A{i}Meta', 'Font.Family', FC)
        sp(wbp, f'Text_A{i}Meta', 'Font.Size', '13')
        sp(wbp, f'Text_A{i}Meta', 'ColorAndOpacity', DIM)
        sp(wbp, f'Text_A{i}Meta', 'Slot.Padding', '(Left=0,Top=3,Right=0,Bottom=0)')

    # ── Costs ─────────────────────────────────────────────
    sp(wbp, 'Border_Costs', 'Padding', '(Left=14,Top=8,Right=14,Bottom=8)')
    add(wbp, 'Border_Costs', 'VerticalBox', 'VBox_Costs')

    for idx, (label, value, vc) in enumerate([
        ('TIME', '-- min', BRIGHT),
        ('CONSUMABLES', '--', YELLOW),
        ('QUALITY', '--', GREEN),
    ]):
        rn = f'HBox_Cost{idx}'
        add(wbp, 'VBox_Costs', 'HorizontalBox', rn)
        sp(wbp, rn, 'Slot.Padding', '(Left=0,Top=2,Right=0,Bottom=2)')
        ln = f'Text_CostL{idx}'
        add(wbp, rn, 'TextBlock', ln)
        sp(wbp, ln, 'Text', label)
        sp(wbp, ln, 'Font.Family', FC)
        sp(wbp, ln, 'Font.Size', '13')
        sp(wbp, ln, 'ColorAndOpacity', DIM)
        sp(wbp, ln, 'Slot.FillWidth', '1.0')
        vn = f'Text_CostV{idx}'
        add(wbp, rn, 'TextBlock', vn)
        sp(wbp, vn, 'Text', value)
        sp(wbp, vn, 'Font.Family', FM)
        sp(wbp, vn, 'Font.Size', '15')
        sp(wbp, vn, 'ColorAndOpacity', vc)
        sp(wbp, vn, 'Justification', 'Right')

    # ── Buttons ───────────────────────────────────────────
    sp(wbp, 'Border_Btns', 'Padding', '(Left=11,Top=6,Right=11,Bottom=6)')
    add(wbp, 'Border_Btns', 'HorizontalBox', 'HBox_Btns')

    add(wbp, 'HBox_Btns', 'Border', 'Border_BtnApprove')
    sp(wbp, 'Border_BtnApprove', 'BrushColor', APPROVE_BG)
    sp(wbp, 'Border_BtnApprove', 'Brush.DrawType', 'Box')
    sp(wbp, 'Border_BtnApprove', 'HAlign', 'Center')
    sp(wbp, 'Border_BtnApprove', 'VAlign', 'Center')
    sp(wbp, 'Border_BtnApprove', 'Slot.FillWidth', '1.0')
    sp(wbp, 'Border_BtnApprove', 'Slot.Padding', '(Left=0,Top=0,Right=6,Bottom=0)')
    add(wbp, 'Border_BtnApprove', 'TextBlock', 'Text_BtnApprove')
    sp(wbp, 'Text_BtnApprove', 'Text', 'APPROVE')
    sp(wbp, 'Text_BtnApprove', 'Font.Family', FC)
    sp(wbp, 'Text_BtnApprove', 'Font.Typeface', 'Bold')
    sp(wbp, 'Text_BtnApprove', 'Font.Size', '21')
    sp(wbp, 'Text_BtnApprove', 'Font.LetterSpacing', '4')
    sp(wbp, 'Text_BtnApprove', 'ColorAndOpacity', GREEN)

    add(wbp, 'HBox_Btns', 'Border', 'Border_BtnCancel')
    sp(wbp, 'Border_BtnCancel', 'BrushColor', CANCEL_BG)
    sp(wbp, 'Border_BtnCancel', 'Brush.DrawType', 'Box')
    sp(wbp, 'Border_BtnCancel', 'HAlign', 'Center')
    sp(wbp, 'Border_BtnCancel', 'VAlign', 'Center')
    add(wbp, 'Border_BtnCancel', 'TextBlock', 'Text_BtnCancel')
    sp(wbp, 'Text_BtnCancel', 'Text', 'CANCEL')
    sp(wbp, 'Text_BtnCancel', 'Font.Family', FC)
    sp(wbp, 'Text_BtnCancel', 'Font.Typeface', 'Bold')
    sp(wbp, 'Text_BtnCancel', 'Font.Size', '21')
    sp(wbp, 'Text_BtnCancel', 'Font.LetterSpacing', '3')
    sp(wbp, 'Text_BtnCancel', 'ColorAndOpacity', RED)

    # ── Status bar ────────────────────────────────────────
    sp(wbp, 'Border_StatusBar', 'Padding', '(Left=8,Top=4,Right=8,Bottom=4)')
    add(wbp, 'Border_StatusBar', 'HorizontalBox', 'HBox_Status')

    for chip_label, chip_val, chip_color in [
        ('Cash', '$4,820', GREEN),
        ('Time', '3h 40m', YELLOW),
        ('Bar', '82%', GREEN),
        ('Storage', '14/24', ACCENT),
    ]:
        cb = f'Border_SC_{chip_label}'
        hb = f'HBox_SC_{chip_label}'
        add(wbp, 'HBox_Status', 'Border', cb)
        sp(wbp, cb, 'BrushColor', BG_CARD)
        sp(wbp, cb, 'Brush.DrawType', 'Box')
        sp(wbp, cb, 'Padding', '(Left=8,Top=4,Right=8,Bottom=4)')
        sp(wbp, cb, 'Slot.FillWidth', '1.0')
        sp(wbp, cb, 'Slot.Padding', '(Left=0,Top=0,Right=4,Bottom=0)')
        add(wbp, cb, 'HorizontalBox', hb)
        lt = f'Text_SC_{chip_label}L'
        add(wbp, hb, 'TextBlock', lt)
        sp(wbp, lt, 'Text', chip_label.upper())
        sp(wbp, lt, 'Font.Family', FC)
        sp(wbp, lt, 'Font.Typeface', 'SemiBold')
        sp(wbp, lt, 'Font.Size', '11')
        sp(wbp, lt, 'ColorAndOpacity', DIM)
        sp(wbp, lt, 'Slot.FillWidth', '1.0')
        vt = f'Text_SC_{chip_label}V'
        add(wbp, hb, 'TextBlock', vt)
        sp(wbp, vt, 'Text', chip_val)
        sp(wbp, vt, 'Font.Family', FM)
        sp(wbp, vt, 'Font.Size', '15')
        sp(wbp, vt, 'ColorAndOpacity', chip_color)
        sp(wbp, vt, 'Justification', 'Right')

    # ── Hidden bridge widgets ─────────────────────────────
    for w in ['txt_Title','txt_Desc','txt_ItemInfo',
              'txt_ActionsHeader','txt_Actions',
              'txt_Equipment','txt_ExitHint']:
        add(wbp, 'CanvasPanel_Root', 'TextBlock', w)
        sp(wbp, w, 'Visibility', 'Collapsed')
        sp(wbp, w, 'Slot.Position.X', '0')
        sp(wbp, w, 'Slot.Position.Y', '0')
        sp(wbp, w, 'Slot.Size.X', '1')
        sp(wbp, w, 'Slot.Size.Y', '1')
        sp(wbp, w, 'Slot.ZOrder', '0')

    # ── Reparent ──────────────────────────────────────────
    r = send('reparent_widget_blueprint', {'name': wbp, 'new_parent': parent_class})
    reparent_ok = r.get('status') == 'ok'
    actual_parent = r.get('data', {}).get('new_parent', '?')

    # ── Design size ───────────────────────────────────────
    send('set_widget_design_size', {'name': wbp, 'width': 1920, 'height': 1080})

    # ── Verify colors ─────────────────────────────────────
    colors_ok = True
    for check_name in ['Border_Panel', 'Border_Header', 'Border_Badge', 'Border_BtnApprove']:
        r2 = send('get_widget_property', {
            'widget_blueprint': wbp, 'widget_name': check_name, 'property': 'BrushColor'
        })
        val = r2.get('data', {}).get('value', '')
        if '1.0000,G=1.0000,B=1.0000' in val:
            colors_ok = False

    # ── Save ──────────────────────────────────────────────
    send('save_all', {})

    return True, f"parent={actual_parent}, reparent={'OK' if reparent_ok else 'FAIL'}, colors={'OK' if colors_ok else 'WHITE'}"


# ══════════════════════════════════════════════════════════════
# Main — build all 12 stations
# ══════════════════════════════════════════════════════════════
print("=" * 60)
print("Building 12 station widgets — BoreAndStroke")
print("=" * 60)

results = []
for i, (wbp, title, subtitle, parent) in enumerate(STATIONS, 1):
    print(f"\n[{i}/12] {wbp} — {title}")
    try:
        ok, detail = build_station(wbp, title, subtitle, parent)
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {detail}")
        results.append((wbp, status, detail))
    except Exception as e:
        print(f"  FAIL: {e}")
        results.append((wbp, "FAIL", str(e)))

# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
passes = 0
for wbp, status, detail in results:
    print(f"  {status} {wbp}: {detail}")
    if status == "PASS":
        passes += 1
print(f"\n  {passes}/12 PASSED")
print("=" * 60)
