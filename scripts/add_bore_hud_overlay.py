#!/usr/bin/env python3
"""Add left-side HUD overlay elements to WBP_Station_Bore.
HUD chips top-left, station label bottom-left.
All on CanvasPanel_Root at ZOrder 3.
"""
import socket, json, time

def send(cmd, params):
    for attempt in range(3):
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
            if attempt < 2:
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
        print(f"  X {wname}.{prop}: {r.get('message','?')[:60]}")
    return ok

def add(wbp, parent, wtype, wname):
    r = send('add_widget_child', {
        'widget_blueprint': wbp, 'parent_widget': parent,
        'widget_type': wtype, 'widget_name': wname,
    })
    ok = r.get('status') == 'ok'
    if not ok:
        print(f"  X ADD {wname}: {r.get('message','?')[:60]}")
    return ok

WBP = 'WBP_Station_Bore'
FC = '/Game/UI/Fonts/F_BarlowCondensed'
FB = '/Game/UI/Fonts/F_Barlow'
FM = '/Game/UI/Fonts/F_ShareTechMono'

DIM        = 'hex:#707888'
ACCENT     = 'hex:#E8A624'
GREEN      = 'hex:#3DDC84'
BRIGHT     = 'hex:#EEF0F4'
CHIP_BG    = '(R=0.003,G=0.004,B=0.005,A=0.88)'
LABEL_BG   = '(R=0.003,G=0.004,B=0.005,A=0.92)'

print("=" * 60)
print("WBP_Station_Bore — HUD Overlay Elements")
print("=" * 60)

# ══════════════════════════════════════════════════════════════
# ELEMENT 1 — HUD chips top-left
# ══════════════════════════════════════════════════════════════
print("\n[1] HUD chips top-left")

add(WBP, 'CanvasPanel_Root', 'Border', 'Border_HudChips')
sp(WBP, 'Border_HudChips', 'Slot.Anchors.Min.X', '0.0')
sp(WBP, 'Border_HudChips', 'Slot.Anchors.Min.Y', '0.0')
sp(WBP, 'Border_HudChips', 'Slot.Anchors.Max.X', '0.0')
sp(WBP, 'Border_HudChips', 'Slot.Anchors.Max.Y', '0.0')
sp(WBP, 'Border_HudChips', 'Slot.Position.X', '16')
sp(WBP, 'Border_HudChips', 'Slot.Position.Y', '16')
sp(WBP, 'Border_HudChips', 'Slot.Size.X', '220')
sp(WBP, 'Border_HudChips', 'Slot.Size.Y', '110')
sp(WBP, 'Border_HudChips', 'BrushColor', '(R=0.0,G=0.0,B=0.0,A=0.0)')
sp(WBP, 'Border_HudChips', 'Slot.ZOrder', '3')

add(WBP, 'Border_HudChips', 'VerticalBox', 'VBox_HudChips')

# Chip: DAY
chips = [
    ('Day',  'DAY',            '14',       ACCENT),
    ('Time', 'TIME REMAINING', '3h 40m',   BRIGHT),
    ('Bar',  'BORING BAR',     '* Ready',  GREEN),
]

for tag, label, value, val_color in chips:
    bn = f'Border_HC_{tag}'
    hb = f'HBox_HC_{tag}'
    lt = f'Text_HC_{tag}L'
    vt = f'Text_HC_{tag}V'

    add(WBP, 'VBox_HudChips', 'Border', bn)
    sp(WBP, bn, 'BrushColor', CHIP_BG)
    sp(WBP, bn, 'Brush.DrawType', 'Box')
    sp(WBP, bn, 'Padding', '(Left=9,Top=5,Right=9,Bottom=5)')
    sp(WBP, bn, 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=5)')

    add(WBP, bn, 'HorizontalBox', hb)

    add(WBP, hb, 'TextBlock', lt)
    sp(WBP, lt, 'Text', label)
    sp(WBP, lt, 'Font.Family', FC)
    sp(WBP, lt, 'Font.Typeface', 'SemiBold')
    sp(WBP, lt, 'Font.Size', '12')
    sp(WBP, lt, 'ColorAndOpacity', DIM)
    sp(WBP, lt, 'Slot.FillWidth', '1.0')

    add(WBP, hb, 'TextBlock', vt)
    sp(WBP, vt, 'Text', value)
    sp(WBP, vt, 'Font.Family', FM)
    sp(WBP, vt, 'Font.Size', '14')
    sp(WBP, vt, 'ColorAndOpacity', val_color)
    sp(WBP, vt, 'Justification', 'Right')

    print(f"  OK {bn}: {label} = {value}")

# ══════════════════════════════════════════════════════════════
# ELEMENT 2 — Station label bottom-left
# ══════════════════════════════════════════════════════════════
print("\n[2] Station label bottom-left")

add(WBP, 'CanvasPanel_Root', 'Border', 'Border_StationLabel')
sp(WBP, 'Border_StationLabel', 'Slot.Anchors.Min.X', '0.0')
sp(WBP, 'Border_StationLabel', 'Slot.Anchors.Min.Y', '1.0')
sp(WBP, 'Border_StationLabel', 'Slot.Anchors.Max.X', '0.0')
sp(WBP, 'Border_StationLabel', 'Slot.Anchors.Max.Y', '1.0')
sp(WBP, 'Border_StationLabel', 'Slot.Position.X', '16')
sp(WBP, 'Border_StationLabel', 'Slot.Position.Y', '-80')
sp(WBP, 'Border_StationLabel', 'Slot.Size.X', '320')
sp(WBP, 'Border_StationLabel', 'Slot.Size.Y', '70')
sp(WBP, 'Border_StationLabel', 'BrushColor', LABEL_BG)
sp(WBP, 'Border_StationLabel', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_StationLabel', 'Slot.ZOrder', '3')

# HBox with accent bar + text
add(WBP, 'Border_StationLabel', 'HorizontalBox', 'HBox_StationLabel')

# Accent bar (4px wide, full height)
add(WBP, 'HBox_StationLabel', 'Border', 'Border_SL_Accent')
sp(WBP, 'Border_SL_Accent', 'BrushColor', ACCENT)
sp(WBP, 'Border_SL_Accent', 'Brush.DrawType', 'Box')
sp(WBP, 'Border_SL_Accent', 'Slot.Padding', '(Left=0,Top=0,Right=0,Bottom=0)')
# Force width via padding — 4px total (2 left + 2 right)
sp(WBP, 'Border_SL_Accent', 'Padding', '(Left=2,Top=0,Right=2,Bottom=0)')

# Text container with left padding
add(WBP, 'HBox_StationLabel', 'VerticalBox', 'VBox_StationLabel')
sp(WBP, 'VBox_StationLabel', 'Slot.FillWidth', '1.0')
sp(WBP, 'VBox_StationLabel', 'Slot.Padding', '(Left=12,Top=10,Right=10,Bottom=10)')

add(WBP, 'VBox_StationLabel', 'TextBlock', 'Text_SL_Name')
sp(WBP, 'Text_SL_Name', 'Text', 'STATION 05 -- CYLINDER BORING')
sp(WBP, 'Text_SL_Name', 'Font.Family', FC)
sp(WBP, 'Text_SL_Name', 'Font.Typeface', 'Bold')
sp(WBP, 'Text_SL_Name', 'Font.Size', '14')
sp(WBP, 'Text_SL_Name', 'Font.LetterSpacing', '3')
sp(WBP, 'Text_SL_Name', 'ColorAndOpacity', ACCENT)

add(WBP, 'VBox_StationLabel', 'TextBlock', 'Text_SL_Info')
sp(WBP, 'Text_SL_Info', 'Text', 'Boring Bar -- Tier 2 Equipment')
sp(WBP, 'Text_SL_Info', 'Font.Family', FB)
sp(WBP, 'Text_SL_Info', 'Font.Size', '11')
sp(WBP, 'Text_SL_Info', 'ColorAndOpacity', DIM)
sp(WBP, 'Text_SL_Info', 'Slot.Padding', '(Left=0,Top=3,Right=0,Bottom=0)')

print("  OK Border_StationLabel with accent bar")
print("  OK Text_SL_Name: STATION 05 -- CYLINDER BORING")
print("  OK Text_SL_Info: Boring Bar -- Tier 2 Equipment")

# ══════════════════════════════════════════════════════════════
# Verify & Save
# ══════════════════════════════════════════════════════════════
print("\n[3] Color verification")
for name, prop in [
    ('Border_HC_Day',      'BrushColor'),
    ('Border_HC_Time',     'BrushColor'),
    ('Border_HC_Bar',      'BrushColor'),
    ('Border_StationLabel','BrushColor'),
    ('Border_SL_Accent',   'BrushColor'),
    ('Text_HC_DayV',       'ColorAndOpacity'),
    ('Text_HC_BarV',       'ColorAndOpacity'),
    ('Text_SL_Name',       'ColorAndOpacity'),
]:
    r = send('get_widget_property', {
        'widget_blueprint': WBP, 'widget_name': name, 'property': prop
    })
    val = r.get('data', {}).get('value', '?')
    is_white = '1.0000,G=1.0000,B=1.0000' in val
    print(f"  {'X WHITE' if is_white else 'OK'} {name}: {val[:55]}")

print("\n[4] Save")
r = send('save_all', {})
print(f"  {r.get('status')}")

print("\n" + "=" * 60)
print("HUD OVERLAY ELEMENTS COMPLETE")
print("  - 3 HUD chips (Day/Time/Bar) — top-left Z:3")
print("  - Station label with accent bar — bottom-left Z:3")
print("=" * 60)
