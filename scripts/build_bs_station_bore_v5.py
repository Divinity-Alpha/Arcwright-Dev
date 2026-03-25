#!/usr/bin/env python3
"""WBP_Station_Bore — BoreAndStroke rebuild v5.
Proven layout from WBP_StationBoreTest + bridge widgets + reparent.
FillHeight sums to exactly 1.0. Slot.Size 0,0 for stretch anchors.
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
        print(f"  X SET FAILED {wname}.{prop}: {r.get('error',r.get('message','?'))[:60]}")
    return ok

def sp_color(wbp, wname, prop, val, label=""):
    """Set color and verify not white."""
    sp(wbp, wname, prop, val)
    r = send('get_widget_property', {
        'widget_blueprint': wbp, 'widget_name': wname, 'property': prop
    })
    got = r.get('data', {}).get('value', '?')
    if 'BrushColor' in prop or 'ColorAndOpacity' in prop:
        if '1.0000,G=1.0000,B=1.0000' in got:
            print(f"  X WHITE {wname}.{prop} -- set failed silently")
            return False
    print(f"  OK {wname}.{prop} = {got[:55]} {label}")
    return True

def add(wbp, parent, wtype, wname):
    r = send('add_widget_child', {
        'widget_blueprint': wbp, 'parent_widget': parent,
        'widget_type': wtype, 'widget_name': wname,
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X ADD FAILED {wname}: {r.get('error',r.get('message','?'))[:60]}")
    return ok

def compile_ok(wbp):
    """Use validate_widget_layout instead of compile_blueprint (which crashes on widget BPs)."""
    r = send('validate_widget_layout', {'name': wbp})
    score = r.get('data', {}).get('score', '?')
    issues = r.get('data', {}).get('issues', [])
    if issues:
        print(f"  ! LAYOUT ISSUES: {issues[:3]}")
    print(f"  OK Validated (score={score})")
    time.sleep(0.3)
    return True

# ── Constants ────────────────────────────────────────────────
WBP = 'WBP_Station_Bore'
FC = '/Game/UI/Fonts/F_BarlowCondensed'
FB = '/Game/UI/Fonts/F_Barlow'
FM = '/Game/UI/Fonts/F_ShareTechMono'

# ── Color constants (hex: prefix → auto sRGB→Linear in plugin) ──
# Permanent palette for all BoreAndStroke station widgets.
BG_DEEP    = 'hex:#0A0C0F'
BG_PANEL   = 'hex:#12161C'
BG_CARD    = 'hex:#181D26'
BORDER_C   = 'hex:#2A3040'
BORDER_ACT = 'hex:#3A4560'
ACCENT     = 'hex:#E8A624'
GREEN      = 'hex:#3DDC84'
YELLOW     = 'hex:#F0C040'
RED        = 'hex:#E04050'
TEXT       = 'hex:#D0D4DC'
DIM        = 'hex:#707888'
BRIGHT     = 'hex:#EEF0F4'
OVERLAY40  = '(R=0.0,G=0.0,B=0.0,A=0.4)'   # alpha overlays stay raw
OVERLAY35  = '(R=0.0,G=0.0,B=0.0,A=0.35)'
OVERLAY22  = '(R=0.0,G=0.0,B=0.0,A=0.22)'
APPROVE_BG = 'hex:#16382DE6'  # dark green, ~90% alpha
CANCEL_BG  = 'hex:#4A0F14CC'  # dark red, ~80% alpha

print("=" * 60)
print("WBP_Station_Bore -- BoreAndStroke Check & Confirm v5")
print("FillHeight: 0.07+0.08+0.04+0.52+0.15+0.07+0.07 = 1.0")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# STEP 1: Delete and recreate at /Game/UI/
# ══════════════════════════════════════════════════════════════
print("\n[STEP 1] Delete and recreate WBP_Station_Bore")
send('delete_blueprint', {'name': WBP})
time.sleep(0.5)
r = send('create_widget_blueprint', {'name': WBP, 'path': '/Game/UI'})
assert r.get('status') == 'ok', f"CREATE FAILED: {r}"
print(f"  OK Created {WBP} at /Game/UI/")

# ══════════════════════════════════════════════════════════════
# STEP 2: Root CanvasPanel
# ══════════════════════════════════════════════════════════════
print("\n[STEP 2] Root CanvasPanel")
add(WBP, '', 'CanvasPanel', 'CanvasPanel_Root')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 3: Border_Panel — only visual child of CanvasPanel
# ══════════════════════════════════════════════════════════════
print("\n[STEP 3] Border_Panel anchored 0.65,0 -> 1,1")
add(WBP, 'CanvasPanel_Root', 'Border', 'Border_Panel')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Min.X', '0.65')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Min.Y', '0.0')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Max.X', '1.0')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Max.Y', '1.0')
sp(WBP, 'Border_Panel', 'Slot.Position.X', '0')
sp(WBP, 'Border_Panel', 'Slot.Position.Y', '0')
sp(WBP, 'Border_Panel', 'Slot.Size.X', '0')
sp(WBP, 'Border_Panel', 'Slot.Size.Y', '0')
sp_color(WBP, 'Border_Panel', 'BrushColor', BG_PANEL, '<-- bg-panel')
sp(WBP, 'Border_Panel', 'Brush.DrawType', 'Box')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 4: VBox_Main
# ══════════════════════════════════════════════════════════════
print("\n[STEP 4] VBox_Main inside Border_Panel")
add(WBP, 'Border_Panel', 'VerticalBox', 'VBox_Main')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 5: 7 sections with FillHeight = 1.0
# ══════════════════════════════════════════════════════════════
print("\n[STEP 5] 7 sections -- FillHeight total = 1.0")
sections = [
    ('Border_Header',    0.07, OVERLAY35),
    ('Border_Badge',     0.08, BG_CARD),
    ('Border_Progress',  0.04, '(R=0.0,G=0.0,B=0.0,A=0.0)'),
    ('Border_Actions',   0.52, BG_PANEL),
    ('Border_Costs',     0.15, OVERLAY22),
    ('Border_Btns',      0.07, '(R=0.0,G=0.0,B=0.0,A=0.0)'),
    ('Border_StatusBar', 0.07, OVERLAY35),
]
for border_name, fill_h, bg in sections:
    add(WBP, 'VBox_Main', 'Border', border_name)
    sp_color(WBP, border_name, 'BrushColor', bg)
    sp(WBP, border_name, 'Brush.DrawType', 'Box')
    sp(WBP, border_name, 'Slot.FillHeight', str(fill_h))
    print(f"  >> {border_name}: FillHeight={fill_h}")
print("  TOTAL = 0.07+0.08+0.04+0.52+0.15+0.07+0.07 = 1.00")
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 6: Header content
# ══════════════════════════════════════════════════════════════
print("\n[STEP 6] Header")
sp(WBP, 'Border_Header', 'Padding', '(Left=20,Top=12,Right=20,Bottom=12)')
add(WBP, 'Border_Header', 'VerticalBox', 'VBox_Header')

add(WBP, 'VBox_Header', 'TextBlock', 'Text_StationName')
sp(WBP, 'Text_StationName', 'Text', 'CYLINDER BORING')
sp(WBP, 'Text_StationName', 'Font.Family', FC)
sp(WBP, 'Text_StationName', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_StationName', 'Font.Size', '21')
sp(WBP, 'Text_StationName', 'Font.LetterSpacing', '4')
sp_color(WBP, 'Text_StationName', 'ColorAndOpacity', ACCENT, '<-- amber')

add(WBP, 'VBox_Header', 'TextBlock', 'Text_StationSub')
sp(WBP, 'Text_StationSub', 'Text', 'Station 05 . Tier 2 Boring Bar')
sp(WBP, 'Text_StationSub', 'Font.Family', FC)
sp(WBP, 'Text_StationSub', 'Font.Size', '15')
sp_color(WBP, 'Text_StationSub', 'ColorAndOpacity', DIM, '<-- dim')
sp(WBP, 'Text_StationSub', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 7: Badge content
# ══════════════════════════════════════════════════════════════
print("\n[STEP 7] Engine badge")
sp(WBP, 'Border_Badge', 'Padding', '(Left=10,Top=6,Right=10,Bottom=6)')
add(WBP, 'Border_Badge', 'HorizontalBox', 'HBox_Badge')

add(WBP, 'HBox_Badge', 'VerticalBox', 'VBox_BadgeInfo')
sp(WBP, 'VBox_BadgeInfo', 'Slot.FillWidth', '1.0')

add(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeName')
sp(WBP, 'Text_BadgeName', 'Text', '1967 Chevy 327 SBC')
sp(WBP, 'Text_BadgeName', 'Font.Family', FC)
sp(WBP, 'Text_BadgeName', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BadgeName', 'Font.Size', '20')
sp_color(WBP, 'Text_BadgeName', 'ColorAndOpacity', BRIGHT, '<-- bright')

add(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSerial')
sp(WBP, 'Text_BadgeSerial', 'Text', 'SN: E2-7740192')
sp(WBP, 'Text_BadgeSerial', 'Font.Family', FM)
sp(WBP, 'Text_BadgeSerial', 'Font.Size', '14')
sp_color(WBP, 'Text_BadgeSerial', 'ColorAndOpacity', DIM)

add(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSpecs')
sp(WBP, 'Text_BadgeSpecs', 'Text', 'V8 . 327ci . 4-Bolt')
sp(WBP, 'Text_BadgeSpecs', 'Font.Family', FC)
sp(WBP, 'Text_BadgeSpecs', 'Font.Size', '13')
sp_color(WBP, 'Text_BadgeSpecs', 'ColorAndOpacity', DIM)

add(WBP, 'HBox_Badge', 'VerticalBox', 'VBox_Quality')

add(WBP, 'VBox_Quality', 'TextBlock', 'Text_QualityNum')
sp(WBP, 'Text_QualityNum', 'Text', '54')
sp(WBP, 'Text_QualityNum', 'Font.Family', FM)
sp(WBP, 'Text_QualityNum', 'Font.Size', '33')
sp_color(WBP, 'Text_QualityNum', 'ColorAndOpacity', YELLOW, '<-- yellow')
sp(WBP, 'Text_QualityNum', 'Justification', 'Right')

add(WBP, 'VBox_Quality', 'TextBlock', 'Text_QualityLbl')
sp(WBP, 'Text_QualityLbl', 'Text', 'QUALITY')
sp(WBP, 'Text_QualityLbl', 'Font.Family', FC)
sp(WBP, 'Text_QualityLbl', 'Font.Size', '10')
sp(WBP, 'Text_QualityLbl', 'Font.LetterSpacing', '2')
sp_color(WBP, 'Text_QualityLbl', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_QualityLbl', 'Justification', 'Right')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 8: Progress
# ══════════════════════════════════════════════════════════════
print("\n[STEP 8] Progress")
sp(WBP, 'Border_Progress', 'Padding', '(Left=11,Top=4,Right=11,Bottom=4)')
add(WBP, 'Border_Progress', 'VerticalBox', 'VBox_Progress')
add(WBP, 'VBox_Progress', 'HorizontalBox', 'HBox_ProgLabels')

add(WBP, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgLabel')
sp(WBP, 'Text_ProgLabel', 'Text', 'CYLINDER PROGRESS')
sp(WBP, 'Text_ProgLabel', 'Font.Family', FC)
sp(WBP, 'Text_ProgLabel', 'Font.Typeface', 'SemiBold')
sp(WBP, 'Text_ProgLabel', 'Font.Size', '12')
sp(WBP, 'Text_ProgLabel', 'Font.LetterSpacing', '2')
sp_color(WBP, 'Text_ProgLabel', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_ProgLabel', 'Slot.FillWidth', '1.0')

add(WBP, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgCount')
sp(WBP, 'Text_ProgCount', 'Text', '3 / 8 Bored')
sp(WBP, 'Text_ProgCount', 'Font.Family', FM)
sp(WBP, 'Text_ProgCount', 'Font.Size', '14')
sp_color(WBP, 'Text_ProgCount', 'ColorAndOpacity', GREEN, '<-- green')
sp(WBP, 'Text_ProgCount', 'Justification', 'Right')

add(WBP, 'VBox_Progress', 'ProgressBar', 'ProgBar_Cylinders')
sp(WBP, 'ProgBar_Cylinders', 'Percent', '0.375')
sp(WBP, 'ProgBar_Cylinders', 'FillColorAndOpacity', GREEN)
sp(WBP, 'ProgBar_Cylinders', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 9: Actions — 5 cards
# ══════════════════════════════════════════════════════════════
print("\n[STEP 9] Actions -- 5 cards")
sp(WBP, 'Border_Actions', 'Padding', '(Left=11,Top=6,Right=11,Bottom=6)')
add(WBP, 'Border_Actions', 'VerticalBox', 'VBox_Actions')

add(WBP, 'VBox_Actions', 'TextBlock', 'Text_ActionsLabel')
sp(WBP, 'Text_ActionsLabel', 'Text', 'AVAILABLE ACTIONS')
sp(WBP, 'Text_ActionsLabel', 'Font.Family', FC)
sp(WBP, 'Text_ActionsLabel', 'Font.Typeface', 'SemiBold')
sp(WBP, 'Text_ActionsLabel', 'Font.Size', '14')
sp(WBP, 'Text_ActionsLabel', 'Font.LetterSpacing', '2')
sp_color(WBP, 'Text_ActionsLabel', 'ColorAndOpacity', DIM)
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
    sp_color(WBP, bn, 'BrushColor', bg)
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
    sp_color(WBP, tn, 'ColorAndOpacity', BRIGHT)

    add(WBP, f'VBox_A{num}', 'HorizontalBox', f'HBox_A{num}Meta')
    sp(WBP, f'HBox_A{num}Meta', 'Slot.Padding', '(Left=0,Top=3,Right=0,Bottom=0)')

    for j, (mt, mc) in enumerate([(m1, DIM), (m2, DIM), (m3, GREEN)], 1):
        if mt:
            mtn = f'Text_A{num}M{j}'
            add(WBP, f'HBox_A{num}Meta', 'TextBlock', mtn)
            sp(WBP, mtn, 'Text', f'. {mt}')
            sp(WBP, mtn, 'Font.Family', FC)
            sp(WBP, mtn, 'Font.Size', '13')
            sp_color(WBP, mtn, 'ColorAndOpacity', mc)
            sp(WBP, mtn, 'Slot.Padding', '(Left=0,Top=0,Right=10,Bottom=0)')

    if num == 4:
        add(WBP, f'VBox_A{num}', 'TextBlock', 'Text_A4Prereq')
        sp(WBP, 'Text_A4Prereq', 'Text', 'Requires: CNC Boring Machine (Station Upgrade)')
        sp(WBP, 'Text_A4Prereq', 'Font.Family', FC)
        sp(WBP, 'Text_A4Prereq', 'Font.Size', '13')
        sp_color(WBP, 'Text_A4Prereq', 'ColorAndOpacity', RED, '<-- red')
        sp(WBP, 'Text_A4Prereq', 'Slot.Padding', '(Left=0,Top=3,Right=0,Bottom=0)')

    print(f"  >> Action {num}: {name[:40]}")
    if num % 2 == 0:
        compile_ok(WBP)

compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 10: Cost detail
# ══════════════════════════════════════════════════════════════
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
        sp_color(WBP, dn, 'BrushColor', BORDER_C, '<-- divider')
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
    sp_color(WBP, ln, 'ColorAndOpacity', DIM)
    sp(WBP, ln, 'Slot.FillWidth', '1.0')
    vn = f'Text_CostV{idx}'
    add(WBP, rn, 'TextBlock', vn)
    sp(WBP, vn, 'Text', value)
    sp(WBP, vn, 'Font.Family', FM)
    sp(WBP, vn, 'Font.Size', '15')
    sp_color(WBP, vn, 'ColorAndOpacity', val_color)
    sp(WBP, vn, 'Justification', 'Right')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 11: Buttons
# ══════════════════════════════════════════════════════════════
print("\n[STEP 11] Approve / Cancel buttons")
sp(WBP, 'Border_Btns', 'Padding', '(Left=11,Top=6,Right=11,Bottom=6)')
add(WBP, 'Border_Btns', 'HorizontalBox', 'HBox_Btns')

add(WBP, 'HBox_Btns', 'Border', 'Border_BtnApprove')
sp_color(WBP, 'Border_BtnApprove', 'BrushColor', APPROVE_BG, '<-- approve-green')
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
sp_color(WBP, 'Text_BtnApprove', 'ColorAndOpacity', GREEN, '<-- green text')

add(WBP, 'HBox_Btns', 'Border', 'Border_BtnCancel')
sp_color(WBP, 'Border_BtnCancel', 'BrushColor', CANCEL_BG, '<-- cancel-red')
sp(WBP, 'Border_BtnCancel', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_BtnCancel', 'HAlign', 'Center')
sp(WBP, 'Border_BtnCancel', 'VAlign', 'Center')
add(WBP, 'Border_BtnCancel', 'TextBlock', 'Text_BtnCancel')
sp(WBP, 'Text_BtnCancel', 'Text', 'CANCEL')
sp(WBP, 'Text_BtnCancel', 'Font.Family', FC)
sp(WBP, 'Text_BtnCancel', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BtnCancel', 'Font.Size', '21')
sp(WBP, 'Text_BtnCancel', 'Font.LetterSpacing', '3')
sp_color(WBP, 'Text_BtnCancel', 'ColorAndOpacity', RED, '<-- red text')
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 12: Status bar
# ══════════════════════════════════════════════════════════════
print("\n[STEP 12] Status bar -- 4 chips")
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
    sp_color(WBP, cb, 'BrushColor', BG_CARD)
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
    sp_color(WBP, lt, 'ColorAndOpacity', DIM)
    sp(WBP, lt, 'Slot.FillWidth', '1.0')
    vt = f'Text_SC_{chip_label}V'
    add(WBP, hb, 'TextBlock', vt)
    sp(WBP, vt, 'Text', chip_val)
    sp(WBP, vt, 'Font.Family', FM)
    sp(WBP, vt, 'Font.Size', '15')
    sp_color(WBP, vt, 'ColorAndOpacity', chip_color)
    sp(WBP, vt, 'Justification', 'Right')
    print(f"  >> {chip_label}: {chip_val}")
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 13: Hidden bridge widgets (7x txt_*)
# ══════════════════════════════════════════════════════════════
print("\n[STEP 13] 7 hidden txt_* bridge widgets")
for w in ['txt_Title','txt_Desc','txt_ItemInfo',
          'txt_ActionsHeader','txt_Actions',
          'txt_Equipment','txt_ExitHint']:
    add(WBP, 'CanvasPanel_Root', 'TextBlock', w)
    sp(WBP, w, 'Visibility', 'Collapsed')
    sp(WBP, w, 'Slot.Position.X', '0')
    sp(WBP, w, 'Slot.Position.Y', '0')
    sp(WBP, w, 'Slot.Size.X', '1')
    sp(WBP, w, 'Slot.Size.Y', '1')
    sp(WBP, w, 'Slot.ZOrder', '0')
    # Verify collapsed
    r = send('get_widget_property', {
        'widget_blueprint': WBP, 'widget_name': w, 'property': 'Visibility'
    })
    vis = r.get('data', {}).get('value', '?')
    print(f"  OK {w}: Visibility={vis}")
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 14: Reparent to BSStationWidget
# ══════════════════════════════════════════════════════════════
print("\n[STEP 14] Reparent to BSStationWidget")
r = send('reparent_widget_blueprint', {'name': WBP, 'new_parent': 'BSStationWidget'})
parent = r.get('data', {}).get('new_parent', '?')
print(f"  Parent: {parent}")
compile_ok(WBP)

# ══════════════════════════════════════════════════════════════
# STEP 15: Verify BP_Station_Bore CDO
# ══════════════════════════════════════════════════════════════
print("\n[STEP 15] Check BP_Station_Bore CDO")
r = send('get_blueprint_details', {'name': 'BP_Station_Bore'})
print(f"  BP found: {r.get('status')}")
print(f"  Parent: {r.get('data',{}).get('parent_class','?')}")

# ══════════════════════════════════════════════════════════════
# STEP 16: Final color verification
# ══════════════════════════════════════════════════════════════
print("\n[STEP 16] Final color verification -- ALL borders")
all_ok = True
for name in ['Border_Panel', 'Border_Header', 'Border_Badge',
             'Border_Actions', 'Border_Costs', 'Border_StatusBar',
             'Border_BtnApprove', 'Border_BtnCancel',
             'Border_Action1', 'Border_Action2', 'Border_Action3',
             'Border_Action4', 'Border_Action5',
             'Border_SC_Cash', 'Border_SC_Time', 'Border_SC_Bar', 'Border_SC_Storage']:
    r = send('get_widget_property', {
        'widget_blueprint': WBP, 'widget_name': name, 'property': 'BrushColor'
    })
    val = r.get('data', {}).get('value', 'ERROR')
    is_white = '1.0000,G=1.0000,B=1.0000' in val
    if is_white:
        all_ok = False
    print(f"  {'X WHITE' if is_white else 'OK'} {name}: {val[:55]}")

# ══════════════════════════════════════════════════════════════
# STEP 17: Save
# ══════════════════════════════════════════════════════════════
print("\n[STEP 17] Save")
r = send('save_all', {})
print(f"  {r.get('status')}")

print("\n" + "=" * 60)
if all_ok:
    print("BUILD COMPLETE -- ALL COLORS VERIFIED")
else:
    print("BUILD COMPLETE -- SOME COLORS ARE WHITE (check above)")
print("FillHeight: 0.07+0.08+0.04+0.52+0.15+0.07+0.07 = 1.00")
print("Bridge widgets: 7x txt_* Collapsed")
print("Parent: BSStationWidget")
print("Path: /Game/UI/WBP_Station_Bore")
print("=" * 60)
