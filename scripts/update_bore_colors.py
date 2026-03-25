#!/usr/bin/env python3
"""Update all WBP_Station_Bore colors to correct sRGB->Linear values."""
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
                print(f"  [RETRY {attempt+1}] {cmd} -- {e}")
                time.sleep(5)
            else:
                raise

WBP = 'WBP_Station_Bore'

# ── Linear color constants (sRGB hex -> Linear) ─────────────
BG_DEEP    = '(R=0.0030,G=0.0037,B=0.0048,A=1.0)'
BG_PANEL   = '(R=0.0060,G=0.0080,B=0.0116,A=1.0)'
BG_CARD    = '(R=0.0091,G=0.0123,B=0.0194,A=1.0)'
BORDER     = '(R=0.0232,G=0.0296,B=0.0513,A=1.0)'
BORDER_ACT = '(R=0.0423,G=0.0595,B=0.1170,A=1.0)'
ACCENT     = '(R=0.8070,G=0.3813,B=0.0176,A=1.0)'
GREEN      = '(R=0.0467,G=0.7157,B=0.2307,A=1.0)'
YELLOW     = '(R=0.8714,G=0.5271,B=0.0513,A=1.0)'
RED        = '(R=0.7454,G=0.0513,B=0.0802,A=1.0)'
TEXT       = '(R=0.6308,G=0.6584,B=0.7157,A=1.0)'
DIM        = '(R=0.1620,G=0.1878,B=0.2462,A=1.0)'
BRIGHT     = '(R=0.8550,G=0.8714,B=0.9047,A=1.0)'
OVERLAY40  = '(R=0.0,G=0.0,B=0.0,A=0.4)'
OVERLAY35  = '(R=0.0,G=0.0,B=0.0,A=0.35)'
OVERLAY22  = '(R=0.0,G=0.0,B=0.0,A=0.22)'
APPROVE_BG = '(R=0.008,G=0.052,B=0.022,A=0.9)'
CANCEL_BG  = '(R=0.073,G=0.006,B=0.009,A=0.8)'

print("=" * 60)
print("WBP_Station_Bore -- Linear Color Update")
print("=" * 60)

# ── Main widget colors ───────────────────────────────────────
widgets = {
    'Border_Panel':      ('BrushColor', BG_PANEL),
    'Border_Header':     ('BrushColor', OVERLAY35),
    'Border_Badge':      ('BrushColor', BG_CARD),
    'Border_Progress':   ('BrushColor', '(R=0.0,G=0.0,B=0.0,A=0.0)'),
    'Border_Actions':    ('BrushColor', BG_PANEL),
    'Border_Costs':      ('BrushColor', OVERLAY22),
    'Border_Btns':       ('BrushColor', '(R=0.0,G=0.0,B=0.0,A=0.0)'),
    'Border_BtnApprove': ('BrushColor', APPROVE_BG),
    'Border_BtnCancel':  ('BrushColor', CANCEL_BG),
    'Border_StatusBar':  ('BrushColor', OVERLAY35),
    'Text_StationName':  ('ColorAndOpacity', ACCENT),
    'Text_StationSub':   ('ColorAndOpacity', DIM),
    'Text_BadgeName':    ('ColorAndOpacity', BRIGHT),
    'Text_BadgeSerial':  ('ColorAndOpacity', DIM),
    'Text_BadgeSpecs':   ('ColorAndOpacity', DIM),
    'Text_QualityNum':   ('ColorAndOpacity', YELLOW),
    'Text_QualityLbl':   ('ColorAndOpacity', DIM),
    'Text_ProgLabel':    ('ColorAndOpacity', DIM),
    'Text_ProgCount':    ('ColorAndOpacity', GREEN),
    'ProgBar_Cylinders': ('FillColorAndOpacity', GREEN),
    'Text_ActionsLabel': ('ColorAndOpacity', DIM),
    'Text_A1Name':       ('ColorAndOpacity', BRIGHT),
    'Text_A2Name':       ('ColorAndOpacity', BRIGHT),
    'Text_A3Name':       ('ColorAndOpacity', BRIGHT),
    'Text_A4Name':       ('ColorAndOpacity', BRIGHT),
    'Text_A5Name':       ('ColorAndOpacity', BRIGHT),
    'Text_A1M3':         ('ColorAndOpacity', GREEN),
    'Text_A2M3':         ('ColorAndOpacity', GREEN),
    'Text_A3M3':         ('ColorAndOpacity', GREEN),
    'Text_A4M2':         ('ColorAndOpacity', GREEN),
    'Text_A5M2':         ('ColorAndOpacity', GREEN),
    'Text_A4Prereq':     ('ColorAndOpacity', RED),
    'Text_BtnApprove':   ('ColorAndOpacity', GREEN),
    'Text_BtnCancel':    ('ColorAndOpacity', RED),
    'Text_SC_CashV':     ('ColorAndOpacity', GREEN),
    'Text_SC_TimeV':     ('ColorAndOpacity', YELLOW),
    'Text_SC_BarV':      ('ColorAndOpacity', GREEN),
    'Text_SC_StorageV':  ('ColorAndOpacity', ACCENT),
}

fails = []
print("\n[1] Main widget colors")
for wname, (prop, color) in widgets.items():
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': wname,
        'property': prop, 'value': color
    })
    ok = r.get('status') == 'ok'
    if not ok:
        fails.append(wname)
        print(f"  X {wname}.{prop}: {r.get('message','?')[:50]}")
    else:
        print(f"  OK {wname}.{prop}")

# ── Stat chip labels ─────────────────────────────────────────
print("\n[2] Stat chip label colors")
for label in ['Text_SC_CashL','Text_SC_TimeL','Text_SC_BarL','Text_SC_StorageL']:
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': label,
        'property': 'ColorAndOpacity', 'value': DIM
    })
    ok = r.get('status') == 'ok'
    if not ok: fails.append(label)
    print(f"  {'OK' if ok else 'X'} {label}")

# ── Action meta text (grey dots) ─────────────────────────────
print("\n[3] Action meta text colors")
for w in ['Text_A1M1','Text_A1M2','Text_A2M1','Text_A2M2',
          'Text_A3M1','Text_A3M2','Text_A4M1','Text_A5M1']:
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': w,
        'property': 'ColorAndOpacity', 'value': DIM
    })
    ok = r.get('status') == 'ok'
    if not ok: fails.append(w)
    print(f"  {'OK' if ok else 'X'} {w}")

# ── Action card backgrounds ──────────────────────────────────
print("\n[4] Action card backgrounds")
for i in range(1, 6):
    bn = f'Border_Action{i}'
    bg = BG_CARD
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': bn,
        'property': 'BrushColor', 'value': bg
    })
    ok = r.get('status') == 'ok'
    if not ok: fails.append(bn)
    print(f"  {'OK' if ok else 'X'} {bn}")

# ── Stat chip border backgrounds ─────────────────────────────
print("\n[5] Stat chip border backgrounds")
for chip in ['Border_SC_Cash','Border_SC_Time','Border_SC_Bar','Border_SC_Storage']:
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': chip,
        'property': 'BrushColor', 'value': BG_CARD
    })
    ok = r.get('status') == 'ok'
    if not ok: fails.append(chip)
    print(f"  {'OK' if ok else 'X'} {chip}")

# ── Cost row labels ──────────────────────────────────────────
print("\n[6] Cost row labels & values")
for idx in [0, 1, 3, 4, 6]:
    ln = f'Text_CostL{idx}'
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': ln,
        'property': 'ColorAndOpacity', 'value': DIM
    })
    ok = r.get('status') == 'ok'
    if not ok: fails.append(ln)
    print(f"  {'OK' if ok else 'X'} {ln}")

# Cost values: 0,1=BRIGHT, 3=YELLOW, 4=DIM, 6=GREEN
cost_colors = {0: BRIGHT, 1: BRIGHT, 3: YELLOW, 4: DIM, 6: GREEN}
for idx, color in cost_colors.items():
    vn = f'Text_CostV{idx}'
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': vn,
        'property': 'ColorAndOpacity', 'value': color
    })
    ok = r.get('status') == 'ok'
    if not ok: fails.append(vn)
    print(f"  {'OK' if ok else 'X'} {vn}")

# ── Divider borders ──────────────────────────────────────────
print("\n[7] Divider borders")
for dn in ['Border_Div2', 'Border_Div5']:
    r = send('set_widget_property', {
        'widget_blueprint': WBP, 'widget_name': dn,
        'property': 'BrushColor', 'value': BORDER
    })
    ok = r.get('status') == 'ok'
    if not ok: fails.append(dn)
    print(f"  {'OK' if ok else 'X'} {dn}")

# ── Readback verification ────────────────────────────────────
print("\n[8] Color readback verification")
verify = [
    ('Border_Panel',     'BrushColor',      'BG_PANEL'),
    ('Border_Badge',     'BrushColor',      'BG_CARD'),
    ('Border_BtnApprove','BrushColor',      'APPROVE_BG'),
    ('Border_BtnCancel', 'BrushColor',      'CANCEL_BG'),
    ('Text_StationName', 'ColorAndOpacity', 'ACCENT'),
    ('Text_QualityNum',  'ColorAndOpacity', 'YELLOW'),
    ('Text_ProgCount',   'ColorAndOpacity', 'GREEN'),
    ('Text_A4Prereq',    'ColorAndOpacity', 'RED'),
    ('Text_BadgeName',   'ColorAndOpacity', 'BRIGHT'),
    ('Text_BadgeSerial', 'ColorAndOpacity', 'DIM'),
    ('Border_Action1',   'BrushColor',      'BG_CARD'),
    ('Border_SC_Cash',   'BrushColor',      'BG_CARD'),
    ('Border_Div2',      'BrushColor',      'BORDER'),
]
for wname, prop, label in verify:
    r = send('get_widget_property', {
        'widget_blueprint': WBP, 'widget_name': wname, 'property': prop
    })
    val = r.get('data', {}).get('value', '?')
    is_white = '1.0000,G=1.0000,B=1.0000' in val
    print(f"  {'X WHITE' if is_white else 'OK'} {wname} ({label}): {val[:55]}")

# ── Save ─────────────────────────────────────────────────────
print("\n[9] Save")
r = send('save_all', {})
print(f"  {r.get('status')}")

print("\n" + "=" * 60)
if fails:
    print(f"DONE -- {len(fails)} FAILURES: {fails}")
else:
    print("DONE -- ALL COLORS UPDATED SUCCESSFULLY")
print("=" * 60)
