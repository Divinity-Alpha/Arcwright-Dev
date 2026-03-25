#!/usr/bin/env python3
"""WBP_StationBoreTest — pure UserWidget visual proof of concept.
No C++ parent. No txt_* bridge layer. FillHeight sums to exactly 1.0.
"""
import socket, json, time

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
        except (ConnectionResetError, ConnectionRefusedError, socket.timeout, json.JSONDecodeError) as e:
            if attempt < retries - 1:
                print(f"  [RETRY {attempt+1}] {cmd} -- {e}")
                time.sleep(5)
            else:
                raise

def sp(wbp, wname, prop, val):
    r = send('set_widget_property', {
        'widget_blueprint': wbp, 'widget_name': wname,
        'property': prop, 'value': str(val)
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X SET FAILED {wname}.{prop}: {r.get('error','?')[:60]}")
    return ok

def add(wbp, parent, wtype, wname):
    r = send('add_widget_child', {
        'widget_blueprint': wbp, 'parent_widget': parent,
        'widget_type': wtype, 'widget_name': wname,
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X ADD FAILED {wname}: {r.get('error','?')[:60]}")
    return ok

def compile_ok(wbp):
    r = send('compile_blueprint', {'name': wbp})
    ok = r.get('status') == 'ok'
    errors = r.get('data', {}).get('errors', [])
    if errors:
        print(f"  X COMPILE ERRORS: {errors[:3]}")
    else:
        print(f"  OK Compiled")
    time.sleep(0.5)
    return ok

# ── Constants ────────────────────────────────────────────────
WBP = 'WBP_StationBoreTest'
FC = '/Game/UI/Fonts/F_BarlowCondensed'
FB = '/Game/UI/Fonts/F_Barlow'
FM = '/Game/UI/Fonts/F_ShareTechMono'

BG_PANEL  = '(R=0.071,G=0.086,B=0.110,A=1.0)'
BG_CARD   = '(R=0.094,G=0.114,B=0.149,A=1.0)'
OVERLAY35 = '(R=0.0,G=0.0,B=0.0,A=0.35)'
OVERLAY22 = '(R=0.0,G=0.0,B=0.0,A=0.22)'
BORDER_C  = '(R=0.165,G=0.188,B=0.251,A=1.0)'
ACCENT    = '(R=0.910,G=0.647,B=0.141,A=1.0)'
GREEN     = '(R=0.239,G=0.863,B=0.518,A=1.0)'
YELLOW    = '(R=0.941,G=0.753,B=0.251,A=1.0)'
RED       = '(R=0.878,G=0.251,B=0.314,A=1.0)'
DIM       = '(R=0.439,G=0.471,B=0.533,A=1.0)'
BRIGHT    = '(R=0.933,G=0.941,B=0.957,A=1.0)'

print("=" * 60)
print("WBP_StationBoreTest -- Pure Visual Proof of Concept")
print("=" * 60)

# ── STEP 1: Delete and recreate ──────────────────────────────
print("\n[STEP 1] Delete and recreate")
send('delete_blueprint', {'name': WBP})
time.sleep(0.3)
r = send('create_widget_blueprint', {'name': WBP})
assert r.get('status') == 'ok', f"CREATE FAILED: {r}"
print(f"  OK Created {WBP}")

# ── STEP 2: Root CanvasPanel ─────────────────────────────────
print("\n[STEP 2] Root CanvasPanel")
add(WBP, '', 'CanvasPanel', 'CanvasPanel_Root')
compile_ok(WBP)

# ── STEP 3: Border_Panel — only child of CanvasPanel ─────────
print("\n[STEP 3] Border_Panel anchored 0.65,0 -> 1,1")
add(WBP, 'CanvasPanel_Root', 'Border', 'Border_Panel')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Min.X', '0.65')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Min.Y', '0.0')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Max.X', '1.0')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Max.Y', '1.0')
sp(WBP, 'Border_Panel', 'Slot.Alignment.X', '0.0')
sp(WBP, 'Border_Panel', 'Slot.Alignment.Y', '0.0')
sp(WBP, 'Border_Panel', 'BrushColor', BG_PANEL)
sp(WBP, 'Border_Panel', 'Brush.DrawType', 'Box')
compile_ok(WBP)

# ── STEP 4: VBox_Main inside Border_Panel ─────────────────────
print("\n[STEP 4] VBox_Main inside Border_Panel")
add(WBP, 'Border_Panel', 'VerticalBox', 'VBox_Main')
sp(WBP, 'VBox_Main', 'Clipping', 'ClipToBounds')
compile_ok(WBP)

# ── STEP 5: 7 sections with FillHeight summing to 1.0 ────────
print("\n[STEP 5] 7 sections -- FillHeight total = 1.0")

sections = [
    # (name, fill_height, bg_color, label)
    ('Border_Header',    0.07, OVERLAY35, 'CYLINDER BORING'),
    ('Border_Badge',     0.08, BG_CARD,   '1967 Chevy 327 SBC'),
    ('Border_Progress',  0.04, '(R=0.0,G=0.0,B=0.0,A=0.0)', 'PROGRESS'),
    ('Border_Actions',   0.52, BG_PANEL,  'AVAILABLE ACTIONS'),
    ('Border_Costs',     0.15, OVERLAY22, 'COST DETAIL'),
    ('Border_Btns',      0.07, '(R=0.0,G=0.0,B=0.0,A=0.0)', 'BUTTONS'),
    ('Border_StatusBar', 0.07, OVERLAY35, 'STATUS BAR'),
]

total_fill = 0.0
for border_name, fill_h, bg, label in sections:
    add(WBP, 'VBox_Main', 'Border', border_name)
    sp(WBP, border_name, 'BrushColor', bg)
    sp(WBP, border_name, 'Brush.DrawType', 'Box')
    sp(WBP, border_name, 'Slot.FillHeight', str(fill_h))
    sp(WBP, border_name, 'Slot.SizeRule', 'Fill')
    total_fill += fill_h
    print(f"  {border_name}: FillHeight={fill_h}  ({label})")

print(f"\n  TOTAL FillHeight = {total_fill}")
compile_ok(WBP)

# ── STEP 6: Header content ───────────────────────────────────
print("\n[STEP 6] Header content")
add(WBP, 'Border_Header', 'VerticalBox', 'VBox_Header')
sp(WBP, 'Border_Header', 'Padding', '(Left=20,Top=12,Right=20,Bottom=12)')

add(WBP, 'VBox_Header', 'TextBlock', 'Text_StationName')
sp(WBP, 'Text_StationName', 'Text', 'CYLINDER BORING')
sp(WBP, 'Text_StationName', 'Font.Family', FC)
sp(WBP, 'Text_StationName', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_StationName', 'Font.Size', '21')
sp(WBP, 'Text_StationName', 'Font.LetterSpacing', '4')
sp(WBP, 'Text_StationName', 'ColorAndOpacity', ACCENT)

add(WBP, 'VBox_Header', 'TextBlock', 'Text_StationSub')
sp(WBP, 'Text_StationSub', 'Text', 'Station 05 . Tier 2 Boring Bar')
sp(WBP, 'Text_StationSub', 'Font.Family', FC)
sp(WBP, 'Text_StationSub', 'Font.Size', '15')
sp(WBP, 'Text_StationSub', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_StationSub', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')
compile_ok(WBP)

# ── STEP 7: Badge content ────────────────────────────────────
print("\n[STEP 7] Badge content")
sp(WBP, 'Border_Badge', 'Padding', '(Left=10,Top=6,Right=10,Bottom=6)')
add(WBP, 'Border_Badge', 'HorizontalBox', 'HBox_Badge')

add(WBP, 'HBox_Badge', 'VerticalBox', 'VBox_BadgeInfo')
sp(WBP, 'VBox_BadgeInfo', 'Slot.FillWidth', '1.0')

add(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeName')
sp(WBP, 'Text_BadgeName', 'Text', '1967 Chevy 327 SBC')
sp(WBP, 'Text_BadgeName', 'Font.Family', FC)
sp(WBP, 'Text_BadgeName', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BadgeName', 'Font.Size', '20')
sp(WBP, 'Text_BadgeName', 'ColorAndOpacity', BRIGHT)

add(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSerial')
sp(WBP, 'Text_BadgeSerial', 'Text', 'SN: E2-7740192')
sp(WBP, 'Text_BadgeSerial', 'Font.Family', FM)
sp(WBP, 'Text_BadgeSerial', 'Font.Size', '14')
sp(WBP, 'Text_BadgeSerial', 'ColorAndOpacity', DIM)

add(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSpecs')
sp(WBP, 'Text_BadgeSpecs', 'Text', 'V8 . 327ci . 4-Bolt')
sp(WBP, 'Text_BadgeSpecs', 'Font.Family', FC)
sp(WBP, 'Text_BadgeSpecs', 'Font.Size', '13')
sp(WBP, 'Text_BadgeSpecs', 'ColorAndOpacity', DIM)

add(WBP, 'HBox_Badge', 'VerticalBox', 'VBox_Quality')

add(WBP, 'VBox_Quality', 'TextBlock', 'Text_QualityNum')
sp(WBP, 'Text_QualityNum', 'Text', '54')
sp(WBP, 'Text_QualityNum', 'Font.Family', FM)
sp(WBP, 'Text_QualityNum', 'Font.Size', '33')
sp(WBP, 'Text_QualityNum', 'ColorAndOpacity', YELLOW)
sp(WBP, 'Text_QualityNum', 'Justification', 'Right')

add(WBP, 'VBox_Quality', 'TextBlock', 'Text_QualityLbl')
sp(WBP, 'Text_QualityLbl', 'Text', 'QUALITY')
sp(WBP, 'Text_QualityLbl', 'Font.Family', FC)
sp(WBP, 'Text_QualityLbl', 'Font.Size', '10')
sp(WBP, 'Text_QualityLbl', 'Font.LetterSpacing', '2')
sp(WBP, 'Text_QualityLbl', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_QualityLbl', 'Justification', 'Right')
compile_ok(WBP)

# ── STEP 8: Progress content ─────────────────────────────────
print("\n[STEP 8] Progress content")
sp(WBP, 'Border_Progress', 'Padding', '(Left=11,Top=4,Right=11,Bottom=4)')
add(WBP, 'Border_Progress', 'VerticalBox', 'VBox_Progress')

add(WBP, 'VBox_Progress', 'HorizontalBox', 'HBox_ProgLabels')

add(WBP, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgLabel')
sp(WBP, 'Text_ProgLabel', 'Text', 'CYLINDER PROGRESS')
sp(WBP, 'Text_ProgLabel', 'Font.Family', FC)
sp(WBP, 'Text_ProgLabel', 'Font.Typeface', 'SemiBold')
sp(WBP, 'Text_ProgLabel', 'Font.Size', '12')
sp(WBP, 'Text_ProgLabel', 'Font.LetterSpacing', '2')
sp(WBP, 'Text_ProgLabel', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_ProgLabel', 'Slot.FillWidth', '1.0')

add(WBP, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgCount')
sp(WBP, 'Text_ProgCount', 'Text', '3 / 8 Bored')
sp(WBP, 'Text_ProgCount', 'Font.Family', FM)
sp(WBP, 'Text_ProgCount', 'Font.Size', '14')
sp(WBP, 'Text_ProgCount', 'ColorAndOpacity', GREEN)
sp(WBP, 'Text_ProgCount', 'Justification', 'Right')

add(WBP, 'VBox_Progress', 'ProgressBar', 'ProgBar_Cylinders')
sp(WBP, 'ProgBar_Cylinders', 'Percent', '0.375')
sp(WBP, 'ProgBar_Cylinders', 'FillColorAndOpacity', GREEN)
sp(WBP, 'ProgBar_Cylinders', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')
compile_ok(WBP)

# ── STEP 9: Actions content ──────────────────────────────────
print("\n[STEP 9] Actions content — 5 cards")
sp(WBP, 'Border_Actions', 'Padding', '(Left=11,Top=6,Right=11,Bottom=6)')
add(WBP, 'Border_Actions', 'VerticalBox', 'VBox_Actions')

add(WBP, 'VBox_Actions', 'TextBlock', 'Text_ActionsLabel')
sp(WBP, 'Text_ActionsLabel', 'Text', 'AVAILABLE ACTIONS')
sp(WBP, 'Text_ActionsLabel', 'Font.Family', FC)
sp(WBP, 'Text_ActionsLabel', 'Font.Typeface', 'SemiBold')
sp(WBP, 'Text_ActionsLabel', 'Font.Size', '14')
sp(WBP, 'Text_ActionsLabel', 'Font.LetterSpacing', '2')
sp(WBP, 'Text_ActionsLabel', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_ActionsLabel', 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=6)')

actions = [
    (1, True,  False, 'Bore Cylinder 4 -- 0.030" Over',     '45 min', '90 min',  '+6 quality'),
    (2, False, False, 'Bore Cylinder 4 -- 0.040" Over',     '45 min', '120 min', '+8 quality'),
    (3, False, False, 'Bore All Remaining -- 0.030"',       '4h',     '7.5h',    '+30 quality'),
    (4, False, True,  'CNC Precision Bore -- All Cylinders', '2h',     '+48 quality', ''),
    (5, False, False, 'Inspect Bore Diameter',               '20 min', '+2 quality',  ''),
]

for num, selected, disabled, name, m1, m2, m3 in actions:
    bn = f'Border_Action{num}'
    add(WBP, 'VBox_Actions', 'Border', bn)
    bg = '(R=0.094,G=0.114,B=0.149,A=0.9)' if selected else BG_CARD
    sp(WBP, bn, 'BrushColor', bg)
    sp(WBP, bn, 'Brush.DrawType', 'Box')
    sp(WBP, bn, 'Padding', '(Left=10,Top=8,Right=10,Bottom=8)')
    sp(WBP, bn, 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=4)')
    if disabled:
        sp(WBP, bn, 'RenderOpacity', '0.36')

    add(WBP, bn, 'VerticalBox', f'VBox_A{num}')

    tn = f'Text_A{num}Name'
    add(WBP, f'VBox_A{num}', 'TextBlock', tn)
    sp(WBP, tn, 'Text', name)
    sp(WBP, tn, 'Font.Family', FB)
    sp(WBP, tn, 'Font.Typeface', 'SemiBold')
    sp(WBP, tn, 'Font.Size', '17')
    sp(WBP, tn, 'ColorAndOpacity', BRIGHT)

    add(WBP, f'VBox_A{num}', 'HorizontalBox', f'HBox_A{num}Meta')
    sp(WBP, f'HBox_A{num}Meta', 'Slot.Padding', '(Left=0,Top=3,Right=0,Bottom=0)')

    for j, (mt, mc) in enumerate([(m1, DIM), (m2, DIM), (m3, GREEN)], 1):
        if mt:
            mtn = f'Text_A{num}M{j}'
            add(WBP, f'HBox_A{num}Meta', 'TextBlock', mtn)
            sp(WBP, mtn, 'Text', f'. {mt}')
            sp(WBP, mtn, 'Font.Family', FC)
            sp(WBP, mtn, 'Font.Size', '13')
            sp(WBP, mtn, 'ColorAndOpacity', mc)
            sp(WBP, mtn, 'Slot.Padding', '(Left=0,Top=0,Right=10,Bottom=0)')

    if num == 4:
        add(WBP, f'VBox_A{num}', 'TextBlock', 'Text_A4Prereq')
        sp(WBP, 'Text_A4Prereq', 'Text', 'Requires: CNC Boring Machine (Station Upgrade)')
        sp(WBP, 'Text_A4Prereq', 'Font.Family', FC)
        sp(WBP, 'Text_A4Prereq', 'Font.Size', '13')
        sp(WBP, 'Text_A4Prereq', 'ColorAndOpacity', RED)
        sp(WBP, 'Text_A4Prereq', 'Slot.Padding', '(Left=0,Top=3,Right=0,Bottom=0)')

    print(f"  Action {num}: {name[:40]}")

    # compile every 2 actions to keep UE stable
    if num % 2 == 0:
        compile_ok(WBP)

compile_ok(WBP)

# ── STEP 10: Cost detail ─────────────────────────────────────
print("\n[STEP 10] Cost detail")
sp(WBP, 'Border_Costs', 'Padding', '(Left=14,Top=8,Right=14,Bottom=8)')
add(WBP, 'Border_Costs', 'VerticalBox', 'VBox_Costs')

cost_rows = [
    ('HUMAN TIME',   '45 min',         BRIGHT),
    ('MACHINE TIME', '90 min',         BRIGHT),
    None,
    ('CONSUMABLES',  'Boring Oil 0.5L', YELLOW),
    ('EQUIP WEAR',   'Boring Bar -3%',  DIM),
    None,
    ('QUALITY GAIN', '+6 pts (54->60)', GREEN),
]

for idx, row in enumerate(cost_rows):
    if row is None:
        dn = f'Border_Div{idx}'
        add(WBP, 'VBox_Costs', 'Border', dn)
        sp(WBP, dn, 'BrushColor', BORDER_C)
        sp(WBP, dn, 'Brush.DrawType', 'Box')
        sp(WBP, dn, 'Slot.Padding', '(Left=0,Top=3,Right=0,Bottom=3)')
        continue
    label, value, val_color = row
    rn = f'HBox_Cost{idx}'
    add(WBP, 'VBox_Costs', 'HorizontalBox', rn)
    sp(WBP, rn, 'Slot.Padding', '(Left=0,Top=2,Right=0,Bottom=2)')

    ln = f'Text_CostL{idx}'
    add(WBP, rn, 'TextBlock', ln)
    sp(WBP, ln, 'Text', label)
    sp(WBP, ln, 'Font.Family', FC)
    sp(WBP, ln, 'Font.Size', '13')
    sp(WBP, ln, 'ColorAndOpacity', DIM)
    sp(WBP, ln, 'Slot.FillWidth', '1.0')

    vn = f'Text_CostV{idx}'
    add(WBP, rn, 'TextBlock', vn)
    sp(WBP, vn, 'Text', value)
    sp(WBP, vn, 'Font.Family', FM)
    sp(WBP, vn, 'Font.Size', '15')
    sp(WBP, vn, 'ColorAndOpacity', val_color)
    sp(WBP, vn, 'Justification', 'Right')

compile_ok(WBP)

# ── STEP 11: Buttons ─────────────────────────────────────────
print("\n[STEP 11] Approve / Cancel buttons")
sp(WBP, 'Border_Btns', 'Padding', '(Left=11,Top=6,Right=11,Bottom=6)')
add(WBP, 'Border_Btns', 'HorizontalBox', 'HBox_Btns')

add(WBP, 'HBox_Btns', 'Border', 'Border_BtnApprove')
sp(WBP, 'Border_BtnApprove', 'BrushColor', '(R=0.061,G=0.220,B=0.118,A=0.9)')
sp(WBP, 'Border_BtnApprove', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_BtnApprove', 'HAlign', 'Center')
sp(WBP, 'Border_BtnApprove', 'VAlign', 'Center')
sp(WBP, 'Border_BtnApprove', 'Slot.FillWidth', '1.0')
sp(WBP, 'Border_BtnApprove', 'Slot.Padding', '(Left=0,Top=0,Right=6,Bottom=0)')
add(WBP, 'Border_BtnApprove', 'TextBlock', 'Text_BtnApprove')
sp(WBP, 'Text_BtnApprove', 'Text', 'APPROVE')
sp(WBP, 'Text_BtnApprove', 'Font.Family', FC)
sp(WBP, 'Text_BtnApprove', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BtnApprove', 'Font.Size', '21')
sp(WBP, 'Text_BtnApprove', 'Font.LetterSpacing', '4')
sp(WBP, 'Text_BtnApprove', 'ColorAndOpacity', GREEN)

add(WBP, 'HBox_Btns', 'Border', 'Border_BtnCancel')
sp(WBP, 'Border_BtnCancel', 'BrushColor', '(R=0.224,G=0.051,B=0.063,A=0.8)')
sp(WBP, 'Border_BtnCancel', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_BtnCancel', 'HAlign', 'Center')
sp(WBP, 'Border_BtnCancel', 'VAlign', 'Center')
add(WBP, 'Border_BtnCancel', 'TextBlock', 'Text_BtnCancel')
sp(WBP, 'Text_BtnCancel', 'Text', 'CANCEL')
sp(WBP, 'Text_BtnCancel', 'Font.Family', FC)
sp(WBP, 'Text_BtnCancel', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BtnCancel', 'Font.Size', '21')
sp(WBP, 'Text_BtnCancel', 'Font.LetterSpacing', '3')
sp(WBP, 'Text_BtnCancel', 'ColorAndOpacity', RED)
compile_ok(WBP)

# ── STEP 12: Status bar ──────────────────────────────────────
print("\n[STEP 12] Status bar — 4 chips")
sp(WBP, 'Border_StatusBar', 'Padding', '(Left=8,Top=4,Right=8,Bottom=4)')
add(WBP, 'Border_StatusBar', 'HorizontalBox', 'HBox_Status')

for chip_label, chip_val, chip_color in [
    ('Cash',    '$4,820', GREEN),
    ('Time',    '3h 40m', YELLOW),
    ('Bar',     '82%',    GREEN),
    ('Storage', '14/24',  ACCENT),
]:
    cb = f'Border_SC_{chip_label}'
    hb = f'HBox_SC_{chip_label}'

    add(WBP, 'HBox_Status', 'Border', cb)
    sp(WBP, cb, 'BrushColor', BG_CARD)
    sp(WBP, cb, 'Brush.DrawType', 'Box')
    sp(WBP, cb, 'Padding', '(Left=8,Top=4,Right=8,Bottom=4)')
    sp(WBP, cb, 'Slot.FillWidth', '1.0')
    sp(WBP, cb, 'Slot.Padding', '(Left=0,Top=0,Right=4,Bottom=0)')

    add(WBP, cb, 'HorizontalBox', hb)

    lt = f'Text_SC_{chip_label}L'
    add(WBP, hb, 'TextBlock', lt)
    sp(WBP, lt, 'Text', chip_label.upper())
    sp(WBP, lt, 'Font.Family', FC)
    sp(WBP, lt, 'Font.Typeface', 'SemiBold')
    sp(WBP, lt, 'Font.Size', '11')
    sp(WBP, lt, 'ColorAndOpacity', DIM)
    sp(WBP, lt, 'Slot.FillWidth', '1.0')

    vt = f'Text_SC_{chip_label}V'
    add(WBP, hb, 'TextBlock', vt)
    sp(WBP, vt, 'Text', chip_val)
    sp(WBP, vt, 'Font.Family', FM)
    sp(WBP, vt, 'Font.Size', '15')
    sp(WBP, vt, 'ColorAndOpacity', chip_color)
    sp(WBP, vt, 'Justification', 'Right')

    print(f"  {chip_label}: {chip_val}")

compile_ok(WBP)

# ── STEP 13: Final verification ──────────────────────────────
print("\n[STEP 13] Final verification")
r = send('get_widget_tree', {'widget_blueprint': WBP})
tree = r.get('data', {}).get('widgets', [])
print(f"  Total widgets in tree: {len(tree)}")
for w in tree:
    depth = w.get('depth', 0)
    indent = '  ' * depth
    print(f"    {indent}{w.get('name','')} ({w.get('type','')})")

# Verify FillHeight on the 7 VBox_Main children
print("\n  FillHeight verification:")
fill_total = 0.0
for border_name, expected_fill in [
    ('Border_Header',    0.07),
    ('Border_Badge',     0.08),
    ('Border_Progress',  0.04),
    ('Border_Actions',   0.52),
    ('Border_Costs',     0.15),
    ('Border_Btns',      0.07),
    ('Border_StatusBar', 0.07),
]:
    r2 = send('get_widget_property', {
        'widget_blueprint': WBP,
        'widget_name': border_name,
        'property': 'Slot.FillHeight'
    })
    val = r2.get('data', {}).get('value', '?')
    fill_total += expected_fill
    print(f"    {border_name}: FillHeight={val} (expected {expected_fill})")

print(f"\n  Expected total: {fill_total}")

# Verify colors
print("\n  Color verification:")
for border_name in ['Border_Panel', 'Border_Header', 'Border_Badge', 'Border_Costs', 'Border_StatusBar']:
    r2 = send('get_widget_property', {
        'widget_blueprint': WBP,
        'widget_name': border_name,
        'property': 'BrushColor'
    })
    val = r2.get('data', {}).get('value', 'ERROR')
    is_white = '1.0000,G=1.0000,B=1.0000' in val
    print(f"    {'X WHITE' if is_white else 'OK'} {border_name}: {val[:50]}")

send('save_all', {})

print("\n" + "=" * 60)
print("BUILD COMPLETE -- WBP_StationBoreTest")
print("Open in UMG Designer to verify layout")
print("FillHeight sum: 0.07+0.08+0.04+0.52+0.15+0.07+0.07 = 1.00")
print("=" * 60)
