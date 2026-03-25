#!/usr/bin/env python3
"""WBP_Station_Bore Check & Confirm build — v4
Reusable — run to rebuild from scratch.
Generated from BRIDGE_cc_station_bore.md
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
            time.sleep(0.15)  # delay between commands to avoid overwhelming UE
            return json.loads(resp.decode().strip())
        except (ConnectionResetError, ConnectionRefusedError, socket.timeout, json.JSONDecodeError) as e:
            if attempt < retries - 1:
                print(f"  [RETRY {attempt+1}] {cmd} — {e}")
                time.sleep(5)
            else:
                raise

# ── Check & Confirm helpers ──────────────────────────────────

def set_and_verify(wbp, widget_name, prop, value):
    """Set a property and immediately read it back to confirm."""
    r = send('set_widget_property', {
        'widget_blueprint': wbp,
        'widget_name': widget_name,
        'property': prop,
        'value': str(value)
    })
    if r.get('status') != 'ok':
        print(f"  ✗ SET FAILED {widget_name}.{prop}: {r.get('error','?')[:60]}")
        return False

    # Read back
    r2 = send('get_widget_property', {
        'widget_blueprint': wbp,
        'widget_name': widget_name,
        'property': prop
    })
    if r2.get('status') != 'ok':
        print(f"  ~ SET OK {widget_name}.{prop} (readback not supported)")
        return True

    got = r2.get('data', {}).get('value', '')

    # For color values, check they are not white
    if 'BrushColor' in prop or 'ColorAndOpacity' in prop:
        if '1.0000,G=1.0000,B=1.0000' in got:
            print(f"  ✗ COLOR IS WHITE {widget_name}.{prop} — set failed silently")
            return False
        print(f"  ✓ {widget_name}.{prop} = {got[:50]}")
        return True

    print(f"  ✓ {widget_name}.{prop} = {got[:50]}")
    return True

def add_child(wbp, parent, wtype, wname):
    r = send('add_widget_child', {
        'widget_blueprint': wbp,
        'parent_widget': parent,
        'widget_type': wtype,
        'widget_name': wname,
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  ✗ ADD CHILD FAILED {wname}: {r.get('error','?')[:60]}")
    return ok

def sp(wbp, wname, prop, val):
    return set_and_verify(wbp, wname, prop, val)

def compile_and_check(wbp):
    r = send('compile_blueprint', {'name': wbp})
    ok = r.get('status') == 'ok'
    errors = r.get('data', {}).get('errors', [])
    if errors:
        print(f"  ✗ COMPILE ERRORS: {errors[:3]}")
    elif ok:
        print(f"  ✓ Compiled OK")
    time.sleep(0.5)  # give UE time to settle after compile
    return ok

# ── Constants ────────────────────────────────────────────────
WBP = 'WBP_Station_Bore'
FC = '/Game/UI/Fonts/F_BarlowCondensed'
FB = '/Game/UI/Fonts/F_Barlow'
FM = '/Game/UI/Fonts/F_ShareTechMono'

BG_PANEL  = '(R=0.071,G=0.086,B=0.110,A=1.0)'
BG_CARD   = '(R=0.094,G=0.114,B=0.149,A=1.0)'
OVERLAY40 = '(R=0.0,G=0.0,B=0.0,A=0.4)'
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
print("WBP_Station_Bore — Check & Confirm Rebuild")
print("=" * 60)

# ── STEP 1: Delete and recreate ──────────────────────────────
print("\n[STEP 1] Delete and recreate WBP_Station_Bore")
send('delete_blueprint', {'name': WBP})
r = send('create_widget_blueprint', {'name': WBP, 'path': '/Game/UI'})
assert r.get('status') == 'ok', f"CREATE FAILED: {r}"
print(f"  ✓ Created {WBP}")

# ── STEP 2: Canvas root ──────────────────────────────────────
print("\n[STEP 2] Canvas root")
add_child(WBP, '', 'CanvasPanel', 'CanvasPanel_Root')

# ── STEP 3: Layer 1 — Hidden C++ bridge widgets ──────────────
print("\n[STEP 3] Layer 1 — 7 hidden txt_* bridge widgets")
for w in ['txt_Title','txt_Desc','txt_ItemInfo','txt_ActionsHeader',
          'txt_Actions','txt_Equipment','txt_ExitHint']:
    add_child(WBP, 'CanvasPanel_Root', 'TextBlock', w)
    sp(WBP, w, 'Visibility', 'Collapsed')
    sp(WBP, w, 'Slot.Position.X', '0')
    sp(WBP, w, 'Slot.Position.Y', '0')
    sp(WBP, w, 'Slot.Size.X', '1')
    sp(WBP, w, 'Slot.Size.Y', '1')
    sp(WBP, w, 'Slot.ZOrder', '0')
    print(f"  ✓ {w}: Collapsed")
compile_and_check(WBP)

# ── STEP 4: Full screen overlay ──────────────────────────────
print("\n[STEP 4] Full screen dark overlay")
add_child(WBP, 'CanvasPanel_Root', 'Border', 'Border_Overlay')
sp(WBP, 'Border_Overlay', 'Slot.Anchors.Min.X', '0.0')
sp(WBP, 'Border_Overlay', 'Slot.Anchors.Min.Y', '0.0')
sp(WBP, 'Border_Overlay', 'Slot.Anchors.Max.X', '1.0')
sp(WBP, 'Border_Overlay', 'Slot.Anchors.Max.Y', '1.0')
sp(WBP, 'Border_Overlay', 'Slot.Offsets.Left',   '0')
sp(WBP, 'Border_Overlay', 'Slot.Offsets.Top',    '0')
sp(WBP, 'Border_Overlay', 'Slot.Offsets.Right',  '0')
sp(WBP, 'Border_Overlay', 'Slot.Offsets.Bottom', '0')
sp(WBP, 'Border_Overlay', 'Slot.ZOrder', '1')
sp(WBP, 'Border_Overlay', 'BrushColor', OVERLAY40)
sp(WBP, 'Border_Overlay', 'Brush.DrawType', 'Box')
compile_and_check(WBP)

# ── STEP 5: Right panel ──────────────────────────────────────
print("\n[STEP 5] Right panel — anchor 0.65,0 → 1,1")
add_child(WBP, 'CanvasPanel_Root', 'Border', 'Border_Panel')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Min.X', '0.65')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Min.Y', '0.0')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Max.X', '1.0')
sp(WBP, 'Border_Panel', 'Slot.Anchors.Max.Y', '1.0')
sp(WBP, 'Border_Panel', 'Slot.Offsets.Left',   '0')
sp(WBP, 'Border_Panel', 'Slot.Offsets.Top',    '0')
sp(WBP, 'Border_Panel', 'Slot.Offsets.Right',  '0')
sp(WBP, 'Border_Panel', 'Slot.Offsets.Bottom', '0')
sp(WBP, 'Border_Panel', 'Slot.ZOrder', '2')
sp(WBP, 'Border_Panel', 'BrushColor', BG_PANEL)
sp(WBP, 'Border_Panel', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_Panel', 'HAlign', 'Fill')
sp(WBP, 'Border_Panel', 'VAlign', 'Fill')
add_child(WBP, 'Border_Panel', 'VerticalBox', 'VBox_Main')
compile_and_check(WBP)

# ── STEP 6: Header ───────────────────────────────────────────
print("\n[STEP 6] Header")
add_child(WBP, 'VBox_Main', 'Border', 'Border_Header')
sp(WBP, 'Border_Header', 'BrushColor', OVERLAY35)
sp(WBP, 'Border_Header', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_Header', 'Padding', '(Left=20,Top=16,Right=20,Bottom=16)')
sp(WBP, 'Border_Header', 'HAlign', 'Fill')
sp(WBP, 'Border_Header', 'VAlign', 'Fill')
sp(WBP, 'Border_Header', 'Slot.FillHeight', '0.0')

add_child(WBP, 'Border_Header', 'VerticalBox', 'VBox_Header')

add_child(WBP, 'VBox_Header', 'TextBlock', 'Text_StationName')
sp(WBP, 'Text_StationName', 'Text', 'CYLINDER BORING')
sp(WBP, 'Text_StationName', 'Font.Family', FC)
sp(WBP, 'Text_StationName', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_StationName', 'Font.Size', '21')
sp(WBP, 'Text_StationName', 'Font.LetterSpacing', '4')
sp(WBP, 'Text_StationName', 'ColorAndOpacity', ACCENT)

add_child(WBP, 'VBox_Header', 'TextBlock', 'Text_StationSub')
sp(WBP, 'Text_StationSub', 'Text', 'Station 05 · Tier 2 Boring Bar')
sp(WBP, 'Text_StationSub', 'Font.Family', FC)
sp(WBP, 'Text_StationSub', 'Font.Typeface', 'Regular')
sp(WBP, 'Text_StationSub', 'Font.Size', '15')
sp(WBP, 'Text_StationSub', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_StationSub', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')
compile_and_check(WBP)

# ── STEP 7: Engine badge ─────────────────────────────────────
print("\n[STEP 7] Engine badge")
add_child(WBP, 'VBox_Main', 'Border', 'Border_Badge')
sp(WBP, 'Border_Badge', 'BrushColor', BG_CARD)
sp(WBP, 'Border_Badge', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_Badge', 'Padding', '(Left=10,Top=0,Right=10,Bottom=0)')
sp(WBP, 'Border_Badge', 'HAlign', 'Fill')
sp(WBP, 'Border_Badge', 'VAlign', 'Center')
sp(WBP, 'Border_Badge', 'Slot.FillHeight', '0.0')
sp(WBP, 'Border_Badge', 'Slot.Padding', '(Left=11,Top=8,Right=11,Bottom=0)')

add_child(WBP, 'Border_Badge', 'HorizontalBox', 'HBox_Badge')

add_child(WBP, 'HBox_Badge', 'Border', 'Border_BadgeIcon')
sp(WBP, 'Border_BadgeIcon', 'BrushColor', '(R=0.038,G=0.047,B=0.059,A=1.0)')
sp(WBP, 'Border_BadgeIcon', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_BadgeIcon', 'HAlign', 'Center')
sp(WBP, 'Border_BadgeIcon', 'VAlign', 'Center')
sp(WBP, 'Border_BadgeIcon', 'Slot.Size.X', '40')
sp(WBP, 'Border_BadgeIcon', 'Slot.Size.Y', '40')
sp(WBP, 'Border_BadgeIcon', 'Slot.Padding', '(Left=0,Top=0,Right=10,Bottom=0)')
add_child(WBP, 'Border_BadgeIcon', 'TextBlock', 'Text_BadgeIcon')
sp(WBP, 'Text_BadgeIcon', 'Text', '🔧')
sp(WBP, 'Text_BadgeIcon', 'Font.Size', '20')

add_child(WBP, 'HBox_Badge', 'VerticalBox', 'VBox_BadgeInfo')
sp(WBP, 'VBox_BadgeInfo', 'Slot.FillWidth', '1.0')

add_child(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeName')
sp(WBP, 'Text_BadgeName', 'Text', '1967 Chevy 327 SBC')
sp(WBP, 'Text_BadgeName', 'Font.Family', FC)
sp(WBP, 'Text_BadgeName', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BadgeName', 'Font.Size', '20')
sp(WBP, 'Text_BadgeName', 'ColorAndOpacity', BRIGHT)

add_child(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSerial')
sp(WBP, 'Text_BadgeSerial', 'Text', 'SN: E2-7740192')
sp(WBP, 'Text_BadgeSerial', 'Font.Family', FM)
sp(WBP, 'Text_BadgeSerial', 'Font.Size', '14')
sp(WBP, 'Text_BadgeSerial', 'ColorAndOpacity', DIM)

add_child(WBP, 'VBox_BadgeInfo', 'TextBlock', 'Text_BadgeSpecs')
sp(WBP, 'Text_BadgeSpecs', 'Text', 'V8 · 327ci · 4-Bolt')
sp(WBP, 'Text_BadgeSpecs', 'Font.Family', FC)
sp(WBP, 'Text_BadgeSpecs', 'Font.Typeface', 'Regular')
sp(WBP, 'Text_BadgeSpecs', 'Font.Size', '13')
sp(WBP, 'Text_BadgeSpecs', 'ColorAndOpacity', DIM)

add_child(WBP, 'HBox_Badge', 'VerticalBox', 'VBox_Quality')
sp(WBP, 'VBox_Quality', 'Slot.HorizontalAlignment', 'Right')

add_child(WBP, 'VBox_Quality', 'TextBlock', 'Text_QualityNum')
sp(WBP, 'Text_QualityNum', 'Text', '54')
sp(WBP, 'Text_QualityNum', 'Font.Family', FM)
sp(WBP, 'Text_QualityNum', 'Font.Size', '33')
sp(WBP, 'Text_QualityNum', 'ColorAndOpacity', YELLOW)
sp(WBP, 'Text_QualityNum', 'Justification', 'Right')

add_child(WBP, 'VBox_Quality', 'TextBlock', 'Text_QualityLbl')
sp(WBP, 'Text_QualityLbl', 'Text', 'QUALITY')
sp(WBP, 'Text_QualityLbl', 'Font.Family', FC)
sp(WBP, 'Text_QualityLbl', 'Font.Size', '10')
sp(WBP, 'Text_QualityLbl', 'Font.LetterSpacing', '2')
sp(WBP, 'Text_QualityLbl', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_QualityLbl', 'Justification', 'Right')
compile_and_check(WBP)

# ── STEP 8: Progress ─────────────────────────────────────────
print("\n[STEP 8] Progress bar")
add_child(WBP, 'VBox_Main', 'Border', 'Border_Progress')
sp(WBP, 'Border_Progress', 'BrushColor', '(R=0.0,G=0.0,B=0.0,A=0.0)')
sp(WBP, 'Border_Progress', 'Padding', '(Left=11,Top=8,Right=11,Bottom=4)')
sp(WBP, 'Border_Progress', 'HAlign', 'Fill')
sp(WBP, 'Border_Progress', 'Slot.FillHeight', '0.0')

add_child(WBP, 'Border_Progress', 'VerticalBox', 'VBox_Progress')
add_child(WBP, 'VBox_Progress', 'HorizontalBox', 'HBox_ProgLabels')

add_child(WBP, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgLabel')
sp(WBP, 'Text_ProgLabel', 'Text', 'CYLINDER PROGRESS')
sp(WBP, 'Text_ProgLabel', 'Font.Family', FC)
sp(WBP, 'Text_ProgLabel', 'Font.Typeface', 'SemiBold')
sp(WBP, 'Text_ProgLabel', 'Font.Size', '12')
sp(WBP, 'Text_ProgLabel', 'Font.LetterSpacing', '2')
sp(WBP, 'Text_ProgLabel', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_ProgLabel', 'Slot.FillWidth', '1.0')

add_child(WBP, 'HBox_ProgLabels', 'TextBlock', 'Text_ProgCount')
sp(WBP, 'Text_ProgCount', 'Text', '3 / 8 Bored')
sp(WBP, 'Text_ProgCount', 'Font.Family', FM)
sp(WBP, 'Text_ProgCount', 'Font.Size', '14')
sp(WBP, 'Text_ProgCount', 'ColorAndOpacity', GREEN)
sp(WBP, 'Text_ProgCount', 'Justification', 'Right')

add_child(WBP, 'VBox_Progress', 'ProgressBar', 'ProgBar_Cylinders')
sp(WBP, 'ProgBar_Cylinders', 'Percent', '0.375')
sp(WBP, 'ProgBar_Cylinders', 'FillColorAndOpacity', GREEN)
sp(WBP, 'ProgBar_Cylinders', 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')
compile_and_check(WBP)

# ── STEP 9: Action list ──────────────────────────────────────
print("\n[STEP 9] Action list with 5 cards")
add_child(WBP, 'VBox_Main', 'Border', 'Border_Actions')
sp(WBP, 'Border_Actions', 'BrushColor', BG_PANEL)
sp(WBP, 'Border_Actions', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_Actions', 'Padding', '(Left=11,Top=8,Right=11,Bottom=8)')
sp(WBP, 'Border_Actions', 'HAlign', 'Fill')
sp(WBP, 'Border_Actions', 'VAlign', 'Fill')
sp(WBP, 'Border_Actions', 'Slot.FillHeight', '1.0')

add_child(WBP, 'Border_Actions', 'VerticalBox', 'VBox_Actions')

add_child(WBP, 'VBox_Actions', 'TextBlock', 'Text_ActionsLabel')
sp(WBP, 'Text_ActionsLabel', 'Text', 'AVAILABLE ACTIONS')
sp(WBP, 'Text_ActionsLabel', 'Font.Family', FC)
sp(WBP, 'Text_ActionsLabel', 'Font.Typeface', 'SemiBold')
sp(WBP, 'Text_ActionsLabel', 'Font.Size', '14')
sp(WBP, 'Text_ActionsLabel', 'Font.LetterSpacing', '2')
sp(WBP, 'Text_ActionsLabel', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_ActionsLabel', 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=8)')

actions = [
    (1, True,  False, 'Bore Cylinder 4 — 0.030" Over',
     '45 min human','90 min machine','+6 quality pts', None),
    (2, False, False, 'Bore Cylinder 4 — 0.040" Over',
     '45 min human','120 min machine','+8 quality pts', None),
    (3, False, False, 'Bore All Remaining Cylinders — 0.030"',
     '4h human','7.5h machine','+30 quality pts', None),
    (4, False, True,  'CNC Precision Bore — All Cylinders',
     '2h human','+48 quality pts','', 'Requires: CNC Boring Machine (Station Upgrade)'),
    (5, False, False, 'Inspect Bore Diameter After Machining',
     '20 min human','+2 quality pts','', None),
]

for num, selected, disabled, name, m1, m2, m3, prereq in actions:
    bn = f'Border_Action{num}'
    vn = f'VBox_Action{num}'
    hn = f'HBox_A{num}Meta'

    add_child(WBP, 'VBox_Actions', 'Border', bn)
    bg = '(R=0.094,G=0.114,B=0.149,A=0.9)' if selected else BG_CARD
    bc = ACCENT if selected else BORDER_C
    sp(WBP, bn, 'BrushColor', bg)
    sp(WBP, bn, 'Brush.DrawType', 'Box')
    sp(WBP, bn, 'Padding', '(Left=10,Top=9,Right=10,Bottom=9)')
    sp(WBP, bn, 'HAlign', 'Fill')
    sp(WBP, bn, 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=5)')
    if disabled:
        sp(WBP, bn, 'RenderOpacity', '0.36')

    add_child(WBP, bn, 'VerticalBox', vn)

    tn = f'Text_A{num}Name'
    add_child(WBP, vn, 'TextBlock', tn)
    sp(WBP, tn, 'Text', name)
    sp(WBP, tn, 'Font.Family', FB)
    sp(WBP, tn, 'Font.Typeface', 'SemiBold')
    sp(WBP, tn, 'Font.Size', '18')
    sp(WBP, tn, 'ColorAndOpacity', BRIGHT)

    add_child(WBP, vn, 'HorizontalBox', hn)
    sp(WBP, hn, 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')

    for j, (mt, mc) in enumerate([(m1,DIM),(m2,DIM),(m3,GREEN)], 1):
        if mt:
            mtn = f'Text_A{num}M{j}'
            add_child(WBP, hn, 'TextBlock', mtn)
            sp(WBP, mtn, 'Text', f'• {mt}')
            sp(WBP, mtn, 'Font.Family', FC)
            sp(WBP, mtn, 'Font.Size', '14')
            sp(WBP, mtn, 'ColorAndOpacity', mc)
            sp(WBP, mtn, 'Slot.Padding', '(Left=0,Top=0,Right=12,Bottom=0)')

    if prereq:
        ptn = f'Text_A{num}Prereq'
        add_child(WBP, vn, 'TextBlock', ptn)
        sp(WBP, ptn, 'Text', prereq)
        sp(WBP, ptn, 'Font.Family', FC)
        sp(WBP, ptn, 'Font.Size', '13')
        sp(WBP, ptn, 'ColorAndOpacity', RED)
        sp(WBP, ptn, 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=0)')

    print(f"  ✓ Action {num}: {name[:45]}")
    # Compile after each action card to let UE settle
    if num % 2 == 0:
        compile_and_check(WBP)

compile_and_check(WBP)

# ── STEP 10: Cost detail ─────────────────────────────────────
print("\n[STEP 10] Cost detail")
add_child(WBP, 'VBox_Main', 'Border', 'Border_Costs')
sp(WBP, 'Border_Costs', 'BrushColor', OVERLAY22)
sp(WBP, 'Border_Costs', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_Costs', 'Padding', '(Left=14,Top=12,Right=14,Bottom=12)')
sp(WBP, 'Border_Costs', 'HAlign', 'Fill')
sp(WBP, 'Border_Costs', 'Slot.FillHeight', '0.0')
sp(WBP, 'Border_Costs', 'Slot.Padding', '(Left=11,Top=0,Right=11,Bottom=0)')

add_child(WBP, 'Border_Costs', 'VerticalBox', 'VBox_Costs')

cost_rows = [
    ('HUMAN TIME',   '45 min',         BRIGHT),
    ('MACHINE TIME', '90 min',         BRIGHT),
    None,
    ('CONSUMABLES',  'Boring Oil 0.5L', YELLOW),
    ('EQUIP WEAR',   'Boring Bar -3%',  DIM),
    None,
    ('QUALITY GAIN', '+6 pts (54→60)', GREEN),
]

for idx, row in enumerate(cost_rows):
    if row is None:
        dn = f'Border_Div{idx}'
        add_child(WBP, 'VBox_Costs', 'Border', dn)
        sp(WBP, dn, 'BrushColor', BORDER_C)
        sp(WBP, dn, 'Brush.DrawType', 'Box')
        sp(WBP, dn, 'Slot.Padding', '(Left=0,Top=4,Right=0,Bottom=4)')
        continue
    label, value, val_color = row
    rn = f'HBox_Cost{idx}'
    add_child(WBP, 'VBox_Costs', 'HorizontalBox', rn)
    sp(WBP, rn, 'Slot.Padding', '(Left=0,Top=2,Right=0,Bottom=2)')

    ln = f'Text_CostL{idx}'
    add_child(WBP, rn, 'TextBlock', ln)
    sp(WBP, ln, 'Text', label)
    sp(WBP, ln, 'Font.Family', FC)
    sp(WBP, ln, 'Font.Size', '14')
    sp(WBP, ln, 'ColorAndOpacity', DIM)
    sp(WBP, ln, 'Slot.FillWidth', '1.0')

    vn2 = f'Text_CostV{idx}'
    add_child(WBP, rn, 'TextBlock', vn2)
    sp(WBP, vn2, 'Text', value)
    sp(WBP, vn2, 'Font.Family', FM)
    sp(WBP, vn2, 'Font.Size', '16')
    sp(WBP, vn2, 'ColorAndOpacity', val_color)
    sp(WBP, vn2, 'Justification', 'Right')

compile_and_check(WBP)

# ── STEP 11: Approve / Cancel buttons ───────────────────────
print("\n[STEP 11] Approve / Cancel buttons")
add_child(WBP, 'VBox_Main', 'Border', 'Border_Btns')
sp(WBP, 'Border_Btns', 'BrushColor', '(R=0.0,G=0.0,B=0.0,A=0.0)')
sp(WBP, 'Border_Btns', 'Padding', '(Left=11,Top=8,Right=11,Bottom=8)')
sp(WBP, 'Border_Btns', 'HAlign', 'Fill')
sp(WBP, 'Border_Btns', 'Slot.FillHeight', '0.0')
add_child(WBP, 'Border_Btns', 'HorizontalBox', 'HBox_Btns')

add_child(WBP, 'HBox_Btns', 'Border', 'Border_BtnApprove')
sp(WBP, 'Border_BtnApprove', 'BrushColor', '(R=0.061,G=0.220,B=0.118,A=0.9)')
sp(WBP, 'Border_BtnApprove', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_BtnApprove', 'HAlign', 'Center')
sp(WBP, 'Border_BtnApprove', 'VAlign', 'Center')
sp(WBP, 'Border_BtnApprove', 'Slot.FillWidth', '1.0')
sp(WBP, 'Border_BtnApprove', 'Slot.Padding', '(Left=0,Top=0,Right=6,Bottom=0)')
add_child(WBP, 'Border_BtnApprove', 'TextBlock', 'Text_BtnApprove')
sp(WBP, 'Text_BtnApprove', 'Text', '✓  APPROVE')
sp(WBP, 'Text_BtnApprove', 'Font.Family', FC)
sp(WBP, 'Text_BtnApprove', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BtnApprove', 'Font.Size', '21')
sp(WBP, 'Text_BtnApprove', 'Font.LetterSpacing', '4')
sp(WBP, 'Text_BtnApprove', 'ColorAndOpacity', GREEN)

add_child(WBP, 'HBox_Btns', 'Border', 'Border_BtnCancel')
sp(WBP, 'Border_BtnCancel', 'BrushColor', '(R=0.224,G=0.051,B=0.063,A=0.8)')
sp(WBP, 'Border_BtnCancel', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_BtnCancel', 'HAlign', 'Center')
sp(WBP, 'Border_BtnCancel', 'VAlign', 'Center')
sp(WBP, 'Border_BtnCancel', 'Slot.Size.X', '120')
add_child(WBP, 'Border_BtnCancel', 'TextBlock', 'Text_BtnCancel')
sp(WBP, 'Text_BtnCancel', 'Text', '✕  CANCEL')
sp(WBP, 'Text_BtnCancel', 'Font.Family', FC)
sp(WBP, 'Text_BtnCancel', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_BtnCancel', 'Font.Size', '21')
sp(WBP, 'Text_BtnCancel', 'Font.LetterSpacing', '3')
sp(WBP, 'Text_BtnCancel', 'ColorAndOpacity', RED)
compile_and_check(WBP)

# ── STEP 12: Status bar ──────────────────────────────────────
print("\n[STEP 12] Status bar")
add_child(WBP, 'VBox_Main', 'Border', 'Border_StatusBar')
sp(WBP, 'Border_StatusBar', 'BrushColor', OVERLAY35)
sp(WBP, 'Border_StatusBar', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_StatusBar', 'Padding', '(Left=8,Top=0,Right=8,Bottom=0)')
sp(WBP, 'Border_StatusBar', 'HAlign', 'Fill')
sp(WBP, 'Border_StatusBar', 'VAlign', 'Fill')
sp(WBP, 'Border_StatusBar', 'Slot.FillHeight', '0.0')
add_child(WBP, 'Border_StatusBar', 'HorizontalBox', 'HBox_Status')

for chip_label, chip_val, chip_color in [
    ('Cash',    '$4,820', GREEN),
    ('Time',    '3h 40m', YELLOW),
    ('Bar',     '82%',    GREEN),
    ('Storage', '14/24',  ACCENT),
]:
    cb = f'Border_SC_{chip_label}'
    hb = f'HBox_SC_{chip_label}'
    lt = f'Text_SC_{chip_label}L'
    vt = f'Text_SC_{chip_label}V'

    add_child(WBP, 'HBox_Status', 'Border', cb)
    sp(WBP, cb, 'BrushColor', BG_CARD)
    sp(WBP, cb, 'Brush.DrawType', 'Box')
    sp(WBP, cb, 'Padding', '(Left=8,Top=5,Right=8,Bottom=5)')
    sp(WBP, cb, 'HAlign', 'Fill')
    sp(WBP, cb, 'VAlign', 'Center')
    sp(WBP, cb, 'Slot.FillWidth', '1.0')
    sp(WBP, cb, 'Slot.Padding', '(Left=0,Top=0,Right=4,Bottom=0)')

    add_child(WBP, cb, 'HorizontalBox', hb)

    add_child(WBP, hb, 'TextBlock', lt)
    sp(WBP, lt, 'Text', chip_label.upper())
    sp(WBP, lt, 'Font.Family', FC)
    sp(WBP, lt, 'Font.Typeface', 'SemiBold')
    sp(WBP, lt, 'Font.Size', '12')
    sp(WBP, lt, 'ColorAndOpacity', DIM)
    sp(WBP, lt, 'Slot.FillWidth', '1.0')
    sp(WBP, lt, 'Slot.VerticalAlignment', 'Center')

    add_child(WBP, hb, 'TextBlock', vt)
    sp(WBP, vt, 'Text', chip_val)
    sp(WBP, vt, 'Font.Family', FM)
    sp(WBP, vt, 'Font.Size', '16')
    sp(WBP, vt, 'ColorAndOpacity', chip_color)
    sp(WBP, vt, 'Justification', 'Right')
    sp(WBP, vt, 'Slot.VerticalAlignment', 'Center')
    print(f"  ✓ {chip_label}: {chip_val}")

compile_and_check(WBP)

# ── STEP 13: Reparent ────────────────────────────────────────
print("\n[STEP 13] Reparent to BSStationWidget")
r = send('reparent_widget_blueprint', {
    'name': WBP, 'new_parent': 'BSStationWidget'
})
print(f"  ✓ Parent: {r.get('data',{}).get('new_parent','?')}")
compile_and_check(WBP)

# ── STEP 14: Final verification ──────────────────────────────
print("\n[STEP 14] Final verification")
r = send('get_widget_tree', {'widget_blueprint': WBP})
tree = r.get('data', {}).get('widgets', [])
widget_names = [w.get('name','') for w in tree]
print(f"  Total widgets: {len(tree)}")

required = [
    'txt_Title','txt_Desc','txt_ItemInfo','txt_ActionsHeader',
    'txt_Actions','txt_Equipment','txt_ExitHint',
    'Border_Overlay','Border_Panel','Border_Header',
    'Border_Badge','Border_Actions','Border_Costs',
    'Border_BtnApprove','Border_BtnCancel','Border_StatusBar',
    'Text_StationName','Text_QualityNum','ProgBar_Cylinders',
    'Border_Action1','Border_Action2','Border_Action3',
    'Border_Action4','Border_Action5',
]
missing = [w for w in required if w not in widget_names]
if missing:
    print(f"  ✗ MISSING: {missing}")
else:
    print(f"  ✓ All {len(required)} required widgets present")

print("\n  Color verification:")
for border_name, expected in [
    ('Border_Panel',  'not white'),
    ('Border_Header', 'not white'),
    ('Border_Costs',  'not white'),
    ('Border_StatusBar', 'not white'),
]:
    r2 = send('get_widget_property', {
        'widget_blueprint': WBP,
        'widget_name': border_name,
        'property': 'BrushColor'
    })
    val = r2.get('data', {}).get('value', 'ERROR')
    is_white = '1.0000,G=1.0000,B=1.0000' in val
    print(f"  {'✗ WHITE' if is_white else '✓'} {border_name}: {val[:50]}")

send('save_all', {})

print("\n" + "=" * 60)
print("BUILD COMPLETE")
print("Press Play → Walk to Bore Station → Press E")
print("Screenshot and share for approval")
print("If it matches HTML → replicate to all 13 stations")
print("=" * 60)
