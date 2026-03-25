#!/usr/bin/env python3
"""Apply hex: colors to WBP_Station_Bore and verify sRGB->Linear conversion."""
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

WBP = 'WBP_Station_Bore'

# hex: color constants
BG_PANEL   = 'hex:#12161C'
BG_CARD    = 'hex:#181D26'
BORDER     = 'hex:#2A3040'
ACCENT     = 'hex:#E8A624'
GREEN      = 'hex:#3DDC84'
YELLOW     = 'hex:#F0C040'
RED        = 'hex:#E04050'
DIM        = 'hex:#707888'
BRIGHT     = 'hex:#EEF0F4'

# Overlays stay raw (need specific alpha)
OVERLAY40  = '(R=0.0,G=0.0,B=0.0,A=0.4)'
OVERLAY35  = '(R=0.0,G=0.0,B=0.0,A=0.35)'
OVERLAY22  = '(R=0.0,G=0.0,B=0.0,A=0.22)'
APPROVE_BG = 'hex:#16382DE6'
CANCEL_BG  = 'hex:#4A0F14CC'

print("=" * 60)
print("WBP_Station_Bore -- hex: Color Application")
print("=" * 60)

all_updates = [
    # Borders
    ('Border_Panel',      'BrushColor', BG_PANEL),
    ('Border_Header',     'BrushColor', OVERLAY35),
    ('Border_Badge',      'BrushColor', BG_CARD),
    ('Border_Progress',   'BrushColor', '(R=0.0,G=0.0,B=0.0,A=0.0)'),
    ('Border_Actions',    'BrushColor', BG_PANEL),
    ('Border_Costs',      'BrushColor', OVERLAY22),
    ('Border_Btns',       'BrushColor', '(R=0.0,G=0.0,B=0.0,A=0.0)'),
    ('Border_BtnApprove', 'BrushColor', APPROVE_BG),
    ('Border_BtnCancel',  'BrushColor', CANCEL_BG),
    ('Border_StatusBar',  'BrushColor', OVERLAY35),
    # Action card borders
    ('Border_Action1',    'BrushColor', BG_CARD),
    ('Border_Action2',    'BrushColor', BG_CARD),
    ('Border_Action3',    'BrushColor', BG_CARD),
    ('Border_Action4',    'BrushColor', BG_CARD),
    ('Border_Action5',    'BrushColor', BG_CARD),
    # Stat chip borders
    ('Border_SC_Cash',    'BrushColor', BG_CARD),
    ('Border_SC_Time',    'BrushColor', BG_CARD),
    ('Border_SC_Bar',     'BrushColor', BG_CARD),
    ('Border_SC_Storage', 'BrushColor', BG_CARD),
    # Dividers
    ('Border_Div2',       'BrushColor', BORDER),
    ('Border_Div5',       'BrushColor', BORDER),
    # Text colors
    ('Text_StationName',  'ColorAndOpacity', ACCENT),
    ('Text_StationSub',   'ColorAndOpacity', DIM),
    ('Text_BadgeName',    'ColorAndOpacity', BRIGHT),
    ('Text_BadgeSerial',  'ColorAndOpacity', DIM),
    ('Text_BadgeSpecs',   'ColorAndOpacity', DIM),
    ('Text_QualityNum',   'ColorAndOpacity', YELLOW),
    ('Text_QualityLbl',   'ColorAndOpacity', DIM),
    ('Text_ProgLabel',    'ColorAndOpacity', DIM),
    ('Text_ProgCount',    'ColorAndOpacity', GREEN),
    ('ProgBar_Cylinders', 'FillColorAndOpacity', GREEN),
    ('Text_ActionsLabel', 'ColorAndOpacity', DIM),
    ('Text_A1Name',       'ColorAndOpacity', BRIGHT),
    ('Text_A2Name',       'ColorAndOpacity', BRIGHT),
    ('Text_A3Name',       'ColorAndOpacity', BRIGHT),
    ('Text_A4Name',       'ColorAndOpacity', BRIGHT),
    ('Text_A5Name',       'ColorAndOpacity', BRIGHT),
    ('Text_A1M1',         'ColorAndOpacity', DIM),
    ('Text_A1M2',         'ColorAndOpacity', DIM),
    ('Text_A1M3',         'ColorAndOpacity', GREEN),
    ('Text_A2M1',         'ColorAndOpacity', DIM),
    ('Text_A2M2',         'ColorAndOpacity', DIM),
    ('Text_A2M3',         'ColorAndOpacity', GREEN),
    ('Text_A3M1',         'ColorAndOpacity', DIM),
    ('Text_A3M2',         'ColorAndOpacity', DIM),
    ('Text_A3M3',         'ColorAndOpacity', GREEN),
    ('Text_A4M1',         'ColorAndOpacity', DIM),
    ('Text_A4M2',         'ColorAndOpacity', GREEN),
    ('Text_A4Prereq',     'ColorAndOpacity', RED),
    ('Text_A5M1',         'ColorAndOpacity', DIM),
    ('Text_A5M2',         'ColorAndOpacity', GREEN),
    ('Text_BtnApprove',   'ColorAndOpacity', GREEN),
    ('Text_BtnCancel',    'ColorAndOpacity', RED),
    ('Text_SC_CashL',     'ColorAndOpacity', DIM),
    ('Text_SC_CashV',     'ColorAndOpacity', GREEN),
    ('Text_SC_TimeL',     'ColorAndOpacity', DIM),
    ('Text_SC_TimeV',     'ColorAndOpacity', YELLOW),
    ('Text_SC_BarL',      'ColorAndOpacity', DIM),
    ('Text_SC_BarV',      'ColorAndOpacity', GREEN),
    ('Text_SC_StorageL',  'ColorAndOpacity', DIM),
    ('Text_SC_StorageV',  'ColorAndOpacity', ACCENT),
    # Cost labels
    ('Text_CostL0',       'ColorAndOpacity', DIM),
    ('Text_CostL1',       'ColorAndOpacity', DIM),
    ('Text_CostL3',       'ColorAndOpacity', DIM),
    ('Text_CostL4',       'ColorAndOpacity', DIM),
    ('Text_CostL6',       'ColorAndOpacity', DIM),
    # Cost values
    ('Text_CostV0',       'ColorAndOpacity', BRIGHT),
    ('Text_CostV1',       'ColorAndOpacity', BRIGHT),
    ('Text_CostV3',       'ColorAndOpacity', YELLOW),
    ('Text_CostV4',       'ColorAndOpacity', DIM),
    ('Text_CostV6',       'ColorAndOpacity', GREEN),
]

fails = []
for wname, prop, color in all_updates:
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': wname,
        'property': prop, 'value': color
    })
    ok = r.get('status') == 'ok'
    if not ok:
        fails.append(wname)
        print(f"  X {wname}.{prop}: {r.get('message','?')[:50]}")
    else:
        is_hex = color.startswith('hex:')
        print(f"  OK {wname}.{prop} = {color}" + (" [hex->linear]" if is_hex else ""))

# ── Verify key conversions ────────────────────────────────────
print("\n--- Readback verification (hex->linear conversion check) ---")
# Expected linear values for key hex colors:
# #E8A624 -> R~0.807, G~0.381, B~0.018
# #3DDC84 -> R~0.047, G~0.716, B~0.231
# #707888 -> R~0.162, G~0.188, B~0.246
checks = [
    ('Text_StationName', 'ColorAndOpacity', '#E8A624', 0.807, 0.381),
    ('Text_ProgCount',   'ColorAndOpacity', '#3DDC84', 0.047, 0.716),
    ('Text_BadgeSerial', 'ColorAndOpacity', '#707888', 0.162, 0.188),
    ('Text_A1Name',      'ColorAndOpacity', '#EEF0F4', 0.855, 0.871),
    ('Border_Panel',     'BrushColor',      '#12161C', 0.006, 0.008),
    ('Border_Div2',      'BrushColor',      '#2A3040', 0.023, 0.030),
]

all_conversions_ok = True
for wname, prop, hex_val, expected_r, expected_g in checks:
    r = send('get_widget_property', {
        'widget_blueprint': WBP, 'widget_name': wname, 'property': prop
    })
    val = r.get('data', {}).get('value', '')
    # Parse R and G from readback
    import re
    rm = re.search(r'R=([\d.]+)', val)
    gm = re.search(r'G=([\d.]+)', val)
    got_r = float(rm.group(1)) if rm else -1
    got_g = float(gm.group(1)) if gm else -1
    r_ok = abs(got_r - expected_r) < 0.01
    g_ok = abs(got_g - expected_g) < 0.01
    ok = r_ok and g_ok
    if not ok:
        all_conversions_ok = False
    print(f"  {'OK' if ok else 'X MISMATCH'} {wname} ({hex_val}): R={got_r:.4f} (exp {expected_r}), G={got_g:.4f} (exp {expected_g})")

# Save
print("\n--- Save ---")
r = send('save_all', {})
print(f"  {r.get('status')}")

print("\n" + "=" * 60)
if fails:
    print(f"SET FAILURES: {len(fails)} -- {fails}")
elif not all_conversions_ok:
    print("CONVERSION MISMATCH -- hex values not converting correctly")
else:
    print("ALL hex: COLORS APPLIED AND VERIFIED")
    print("sRGB->Linear conversion confirmed correct")
print("=" * 60)
